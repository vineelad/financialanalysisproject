import json
import time
from datetime import datetime, timezone
from typing import TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from .facts import calculate
from .reported import reported_metric_answer
from .models import Answer
from .generation import ANSWER_POLICY, calculation_answer, complete_segment_answer, explanation_context, generate_answer, prompt_fingerprint, segment_context
from .retrieval import RETRIEVAL_POLICY, Retriever, narrative_question, retrieval_budget, retrieval_queries, segment_structure_question
from .models import Claim, GeneratedAnswer
from .scope import resolve
from .settings import ROOT
from .metric_registry import registry_metadata
from .storage import write_json


class State(TypedDict, total=False):
    question: str
    scope: dict
    hits: list
    candidates: list
    calculations: list
    status: str
    text: str
    usage: dict
    answer_mode: str
    base_bank: str | None


class Application:
    def __init__(self, strategy: str = "fixed", rerank: bool = False, generate: bool = False):
        self.retriever = Retriever(strategy)
        self.strategy, self.rerank, self.generate = strategy, rerank, generate
        self.banks = {c.bank for c in self.retriever.chunks}
        self.periods = {p for c in self.retriever.chunks for p in c.periods}
        graph = StateGraph(State)
        graph.add_node("scope", self.resolve_scope)
        graph.add_node("retrieve", self.retrieve)
        graph.add_node("calculate", self.calculate)
        graph.add_node("answer", self.answer)
        graph.add_edge(START, "scope")
        graph.add_conditional_edges("scope", lambda state: END if state.get("status") else "retrieve")
        graph.add_edge("retrieve", "calculate")
        graph.add_conditional_edges("calculate", lambda state: END if state.get("status") else "answer")
        graph.add_edge("answer", END)
        self.graph = graph.compile()

    def resolve_scope(self, state: State) -> dict:
        scope = resolve(state["question"], self.banks, self.periods, base_bank=state.get("base_bank"))
        if scope.unsupported:
            return {"scope": vars(scope), "status": "insufficient_evidence", "text": scope.unsupported}
        if scope.clarification:
            return {"scope": vars(scope), "status": "clarification", "text": scope.clarification}
        return {"scope": vars(scope)}

    def retrieve(self, state: State) -> dict:
        hits, candidates = self.retriever.search(state["question"], state["scope"]["banks"], state["scope"]["periods"], self.rerank)
        return {"hits": hits, "candidates": candidates}

    def calculate(self, state: State) -> dict:
        if not state["hits"]:
            return {"status": "insufficient_evidence", "text": "No matching source evidence was retrieved."}
        try:
            calculations = calculate(state["question"], state["scope"]["banks"], state["scope"]["periods"], state["hits"])
        except ValueError as exc:
            return {"status": "insufficient_evidence", "text": str(exc)}
        return {"calculations": calculations}

    def answer(self, state: State) -> dict:
        if not self.generate:
            lines = ["Evidence-only mode: retrieved excerpts are shown below; no language-model answer was generated."]
            if state.get("calculations"):
                lines.append("Validated calculations:\n" + json.dumps(state["calculations"], indent=2))
            for hit in state["hits"]:
                chunk = hit.chunk
                lines.append(f"[{chunk.chunk_id}] {chunk.location}\n{chunk.text}\n{chunk.url}")
            return {"status": "evidence_only", "text": "\n\n".join(lines)}
        evidence = [{"chunk_id": h.chunk.chunk_id, "text": h.chunk.text, "source": h.chunk.url} for h in state["hits"]]
        labels = segment_context(state["hits"]) if segment_structure_question(state["question"]) else []
        explanations = explanation_context(state["hits"], state["question"]) if narrative_question(state["question"]) else []
        scope = state.get("scope", {})
        reported = reported_metric_answer(state["question"], scope.get("banks", []), scope.get("periods", []), state["hits"], base_bank=state.get("base_bank"))
        if state.get("calculations"):
            generated, usage, answer_mode = calculation_answer(state["calculations"], state["hits"]), {}, "validated_calculation"
        elif reported is not None:
            generated, usage, answer_mode = reported, {}, "verified_reported_metrics"
        else:
            generation_question = state["question"]
            if state.get("base_bank"):
                generation_question += f"\nSelected comparison base bank: {state['base_bank']}. Use this bank as the denominator for any supported peer percentage comparison."
            generation_question += f"\nRequested banks: {', '.join(scope.get('banks', []))}. Cover each requested bank; explicitly mark unavailable evidence."
            generated, usage = generate_answer(generation_question, evidence, [],
                                               reported_segment_labels=labels or None,
                                               reported_explanations=explanations or None)
            answer_mode = "generated"
        allowed = {h.chunk.chunk_id for h in state["hits"]}
        if any(cid not in allowed for claim in generated.claims for cid in claim.citations):
            raise ValueError("Generated answer cited evidence that was not retrieved")
        if generated.status == "answered" and not generated.claims:
            raise ValueError("Answered response contained no cited claims")
        generated, fallback = complete_segment_answer(generated, labels, state["scope"]["banks"]) if labels else (generated, False)
        if generated.status == "insufficient_evidence" and explanations:
            generated = GeneratedAnswer(status="answered", claims=[
                Claim(text=f"{item['bank']}'s retrieved earnings material states: “{item['quote']}”", citations=item["citations"])
                for item in explanations], limitations=["This quotes the explanation stated in the retrieved material; no additional cause is inferred."])
            answer_mode = "source_excerpt"
        lines = [f"{claim.text} " + " ".join(f"[{cid}]" for cid in claim.citations) for claim in generated.claims]
        lines.extend(generated.limitations)
        if generated.status == "insufficient_evidence" and not lines:
            lines = ["The retrieved evidence does not support an answer."]
        lines.extend(f"[{h.chunk.chunk_id}] {h.chunk.location}: {h.chunk.url}" for h in state["hits"])
        return {"status": generated.status, "text": "\n\n".join(lines), "usage": usage,
                "answer_mode": "source_summary" if fallback else answer_mode}

    def ask(self, question: str, save: bool = True, base_bank: str | None = None) -> tuple[Answer, dict]:
        start = time.perf_counter()
        state = self.graph.invoke({"question": question, "base_bank": base_bank}, config={
            "run_name": "ir_financial_rag", "tags": [self.strategy, "reranked" if self.rerank else "baseline"],
            "metadata": {"chunking": self.strategy, "reranking": self.rerank, "generation": self.generate}})
        answer = Answer(question=question, status=state["status"], mode=state.get("answer_mode", "generated" if self.generate else "evidence_only"),
                        text=state["text"], hits=state.get("hits", []), elapsed_seconds=round(time.perf_counter() - start, 3),
                        usage=state.get("usage", {}))
        trace = {"strategy": self.strategy, "reranking": self.rerank, "scope": state["scope"],
                 "retrieval_policy": RETRIEVAL_POLICY,
                 "retrieval_budget": retrieval_budget(question, state["scope"]["banks"]),
                 "answer_policy": ANSWER_POLICY,
                 "metric_registry": registry_metadata(),
                 "base_bank": base_bank,
                 "retrieval_queries": retrieval_queries(question, state["scope"]["banks"]),
                 "framework": "LangChain + LangGraph", "prompt_hash": prompt_fingerprint(),
                 "calculations": state.get("calculations", []),
                 "candidate_hits": [hit.model_dump() for hit in state.get("candidates", [])],
                 "answer": answer.model_dump(), "timestamp": datetime.now(timezone.utc).isoformat()}
        if save:
            write_json(ROOT / "runs" / f"{uuid4().hex}.json", trace)
        return answer, trace
