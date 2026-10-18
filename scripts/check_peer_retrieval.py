"""Local development regressions; uses cached models and makes no hosted calls."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ir_assistant.retrieval import RETRIEVAL_POLICY
from ir_assistant.workflow import Application


CASES = [
    ("reported-segments", "Which corporate banking segment names do JPMorgan and Bank of America report in Q2 2025, and why should comparisons be qualified?",
     ["commercial & investment bank", "global banking", "global markets"]),
    ("segment-scope", "Compare the corporate segment scope at BAC and JPM for Q2 2025.",
     ["commercial & investment bank", "global banking", "global markets"]),
    ("peer-revenue", "What was consumer revenue at JPMorgan and Bank of America in Q2 2025?",
     ["18,847", "10,813"]),
]


def main():
    records = []
    for strategy, rerank in [("fixed", False), ("semantic", False), ("fixed", True), ("semantic", True)]:
        application = Application(strategy, rerank, False)
        for name, question, required in CASES:
            answer, trace = application.ask(question, save=False)
            text = "\n".join(h.chunk.text for h in answer.hits).casefold()
            banks = {h.chunk.bank for h in answer.hits}
            covered = all(term in text for term in required) and banks == {"JPM", "BAC"}
            records.append({"case": name, "question": question, "strategy": strategy, "reranking": rerank,
                            "required_terms": required, "coverage_pass": covered,
                            "evidence": [h.chunk.model_dump() for h in answer.hits],
                            "retrieval_queries": trace["retrieval_queries"]})
            print(f"{strategy} rerank={rerank} {name}: {'covered' if covered else 'missing evidence'}", flush=True)
    path = ROOT / "reports" / "peer-retrieval-development.json"
    path.write_text(json.dumps({"retrieval_policy": RETRIEVAL_POLICY,
                               "scope": "Three development regressions including a previously failed benchmark question and related paraphrase. Not held-out evaluation; term coverage does not prove correct column selection or generated-answer quality.",
                               "checks": records}, indent=2) + "\n", encoding="utf-8")
    return int(not all(r["coverage_pass"] for r in records))


if __name__ == "__main__":
    raise SystemExit(main())
