"""Run five development cases, including at most three hosted answer requests.

This is a small live development check, separate from the four-condition
retrieval experiment. Run from the project root; requires a private .env.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ir_assistant import settings
from ir_assistant.generation import provider_config, prompt_fingerprint
from ir_assistant.workflow import Application
from ir_assistant.retrieval import RETRIEVAL_POLICY


CASES = [
    ("bac-growth", False, "What was Bank of America consumer revenue growth from Q2 2024 to Q2 2025?"),
    ("jpm-leverage", True, "What was JPMorgan consumer banking operating leverage from Q2 2024 to Q2 2025?"),
    ("peer-segments", False, "Which corporate banking segment names do JPMorgan and Bank of America report in Q2 2025, and why should comparisons be qualified?"),
    ("unsupported-period", False, "Give JPMorgan consumer revenue for Q2 2026."),
    ("ambiguous", False, "What was the latest quarter's efficiency ratio?"),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", choices=[c[0] for c in CASES], help="Run only the named case(s)")
    arguments = parser.parse_args()
    if not all(provider_config()):
        print("Save LLM_BASE_URL, LLM_API_KEY, and LLM_MODEL in .env first.")
        return 2
    directory = ROOT / "runs" / ("generation-check-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    directory.mkdir(parents=True)
    record = {"model": provider_config()[2], "prompt_hash": prompt_fingerprint(),
              "retrieval_policy": RETRIEVAL_POLICY,
              "scope": "Five development checks with mixed retrieval configurations; not a comparative answer-quality benchmark.",
              "timing_note": "First query includes embedding initialization; first reranked query includes reranker initialization. No warm p95 claim.",
              "cases": []}
    applications = {}
    for case_id, rerank, question in CASES:
        if arguments.case and case_id not in arguments.case:
            continue
        if rerank not in applications:
            applications[rerank] = Application("fixed", rerank, generate=True)
        try:
            answer, trace = applications[rerank].ask(question)
        except (RuntimeError, ValueError) as exc:
            # Do not print provider exception bodies or configuration values.
            error_types = []
            cause = exc
            while cause is not None and len(error_types) < 6:
                error_types.append({"type": type(cause).__name__, "status_code": getattr(cause, "status_code", None)})
                cause = cause.__cause__
            known = {"Generated answer cited evidence that was not retrieved", "Answered response contained no cited claims"}
            reason = str(exc) if str(exc) in known else "Generation or validation failed; raw provider error suppressed."
            record["cases"].append({"id": case_id, "question": question, "error": reason, "error_types": error_types})
            print(f"{case_id}: {reason}; types={error_types}", flush=True)
        else:
            item = {"id": case_id, "strategy": "fixed", "reranking": rerank,
                    "answer": answer.model_dump(), "calculations": trace["calculations"]}
            record["cases"].append(item)
            print(f"{case_id}: {answer.status}; tokens={answer.usage.get('total_tokens', 0)}; {answer.elapsed_seconds}s", flush=True)
        (directory / "results.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(directory, flush=True)
    return int(any("error" in case for case in record["cases"]))


if __name__ == "__main__":
    raise SystemExit(main())
