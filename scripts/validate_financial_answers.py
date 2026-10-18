"""Six live source-review cases using the selected quality configuration.

Makes at most six hosted requests. Review the saved answers against the sources;
an answered status is not automatically a correctness label.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ir_assistant.generation import ANSWER_POLICY, prompt_fingerprint, provider_config
from ir_assistant.retrieval import RETRIEVAL_POLICY
from ir_assistant.workflow import Application


def main():
    if not all(provider_config()):
        raise ValueError("Configure the private .env first")
    questions = {q["id"]: q for q in map(json.loads, (ROOT / "eval/gold_questions.strict.jsonl").read_text(encoding="utf-8").splitlines())}
    questions.update({q["id"]: q for q in map(json.loads, (ROOT / "eval/validation_questions.jsonl").read_text(encoding="utf-8").splitlines())})
    directory = ROOT / "runs" / ("financial-validation-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    directory.mkdir(parents=True)
    result = {"model": provider_config()[2], "retrieval_policy": RETRIEVAL_POLICY,
              "answer_policy": ANSWER_POLICY,
              "prompt_hash": prompt_fingerprint(), "strategy": "semantic", "reranking": True,
              "scope": "Six live development/source-review cases; one comes from the prospective validation set. Not a representative answer-accuracy benchmark.", "cases": []}
    application = Application("semantic", True, True)
    for qid in ["08", "11", "12", "13", "14", "v02"]:
        q = questions[qid]
        try:
            answer, trace = application.ask(q["question"])
        except (RuntimeError, ValueError) as exc:
            result["cases"].append({"id": qid, "question": q["question"], "error_type": type(exc).__name__})
            print(f"{qid}: failed; details suppressed", flush=True)
        else:
            result["cases"].append({"id": qid, "gold": q, "answer": answer.model_dump(), "calculations": trace["calculations"]})
            print(f"{qid}: {answer.status}; tokens={answer.usage.get('total_tokens', 0)}", flush=True)
        (directory / "results.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(directory, flush=True)
    return int(any("error_type" in case for case in result["cases"]))


if __name__ == "__main__":
    raise SystemExit(main())
