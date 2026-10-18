import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from importlib.metadata import version

from .metrics import score_evidence
from .settings import CANDIDATE_K, CONTEXT_TOKENS, EMBEDDING_MODEL, EMBEDDING_REVISION, FINAL_K, RERANKER_MODEL, RERANKER_REVISION, ROOT
from .storage import write_json
from .workflow import Application
from .generation import prompt_fingerprint
from .retrieval import RETRIEVAL_POLICY, retrieval_budget
from .metric_registry import registry_metadata


def evaluate(questions_path: Path, generate: bool = False) -> Path:
    questions = [json.loads(line) for line in questions_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not questions:
        raise ValueError("Question file is empty")
    if any(q.get("annotation_status") != "reviewed" for q in questions):
        raise ValueError("Gold questions need annotation_status=reviewed after manual source validation; draft questions cannot produce scored results.")
    if len({q["id"] for q in questions}) != len(questions):
        raise ValueError("Question IDs must be unique")
    for q in questions:
        if q["expected_behavior"] == "answered":
            if not q.get("evidence") or not q.get("expected_answer"):
                raise ValueError(f"Question {q['id']} needs gold evidence and an expected answer")
            for unit in q["evidence"]:
                if not unit.get("document_id") or not unit.get("quote", "").strip():
                    raise ValueError("Gold evidence requires a document ID and exact source quote")
    directory = ROOT / "runs" / ("evaluation-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    directory.mkdir(parents=True)
    write_json(directory / "configuration.json", {"embedding": EMBEDDING_MODEL, "reranker": RERANKER_MODEL,
               "retrieval_policy": RETRIEVAL_POLICY,
               "metric_registry": registry_metadata(),
               "embedding_revision": EMBEDDING_REVISION, "reranker_revision": RERANKER_REVISION,
               "candidate_k": CANDIDATE_K, "final_k": FINAL_K, "context_tokens": CONTEXT_TOKENS,
               "generation": generate, "question_hash": hashlib.sha256(questions_path.read_bytes()).hexdigest(),
               "scope": "Frozen configured corpus; assistant-reviewed labels; some question types overlap development checks.",
               "budget_note": "Budgets scale for >2 banks. Generic recall/precision fields use each query's recorded budget; legacy @5/@20 fields are populated only at those exact limits.",
               "prompt_hash": prompt_fingerprint(),
               "framework_versions": {name: version(name) for name in
                                      ("langchain-core", "langchain-chroma", "langchain-openai", "langgraph")},
               "note": "First query includes model loading. Timings are not warm-latency benchmarks."})
    rows = []
    for name, strategy, rerank in [("A", "fixed", False), ("B", "semantic", False),
                                   ("C", "fixed", True), ("D", "semantic", True)]:
        application = Application(strategy, rerank, generate)
        for question in questions:
            answer, trace = application.ask(question["question"], save=False, base_bank=question.get("base_bank"))
            chunks = [hit.chunk.model_dump() for hit in answer.hits]
            units = question.get("evidence", [])
            final_scores = score_evidence(units, chunks)
            candidate_scores = score_evidence(units, [hit["chunk"] for hit in trace["candidate_hits"]])
            # Evidence-only output is deliberately not scored as a generated answer.
            expected = question["expected_behavior"]
            behavior_correct = (answer.status == expected) if generate or expected != "answered" else None
            budget = trace["retrieval_budget"]
            rows.append({"run": name, "question_id": question["id"], "status": answer.status,
                         "final_hit_limit": budget["final_k"], "candidate_limit": budget["candidate_k"],
                         "context_token_limit": budget["context_tokens"],
                         "evidence_recall": final_scores["evidence_recall"], "retrieval_precision": final_scores["precision"],
                         "candidate_recall": candidate_scores["evidence_recall"],
                         "evidence_recall_at_5": final_scores["evidence_recall"] if budget["final_k"] == 5 else None,
                         "retrieval_precision_at_5": final_scores["precision"] if budget["final_k"] == 5 else None,
                         "candidate_recall_at_20": candidate_scores["evidence_recall"] if budget["candidate_k"] == 20 else None,
                         "behavior_correct": behavior_correct, "elapsed_seconds": answer.elapsed_seconds,
                         "faithfulness_manual": "", "numeric_accuracy_manual": "", "citation_support_manual": ""})
            trace["gold"] = question
            write_json(directory / f"{name}-{question['id']}.json", trace)
            print(f"{name} {question['id']}: {answer.status}")
    with (directory / "scores.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summaries = []
    for run in "ABCD":
        group = [r for r in rows if r["run"] == run]
        summary = {"run": run, "questions": len(group)}
        for key in ("evidence_recall", "retrieval_precision", "candidate_recall", "evidence_recall_at_5", "retrieval_precision_at_5", "candidate_recall_at_20", "behavior_correct"):
            values = [r[key] for r in group if r[key] is not None]
            summary[key] = sum(values) / len(values) if values else None
            summary[key + "_denominator"] = len(values)
        summaries.append(summary)
    write_json(directory / "summary.json", summaries)
    return directory
