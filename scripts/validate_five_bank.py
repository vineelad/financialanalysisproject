"""Run frozen narrow answer checks through real retrieval, without model calls."""
import json
import argparse
import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ir_assistant.banks import bank_name
from ir_assistant.facts import load_reviewed_facts
from ir_assistant.workflow import Application
from ir_assistant.storage import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    audited = ROOT / "eval/five_bank_questions.audited.jsonl"
    parser.add_argument("--questions", type=Path, default=audited if audited.exists() else ROOT / "eval/five_bank_questions.jsonl")
    args = parser.parse_args()
    questions = [json.loads(line) for line in args.questions.read_text(encoding="utf-8").splitlines()]
    facts = load_reviewed_facts()
    app = Application("semantic", rerank=True, generate=True)
    records = []
    with patch("ir_assistant.workflow.generate_answer", side_effect=ValueError("Case left the expected validated answer route; no model request made")):
        for item in questions:
            checks, trace = {}, None
            try:
                answer, trace = app.ask(item["question"], save=False, base_bank=item.get("base_bank"))
                checks["status"] = answer.status == item["expected_behavior"]
                checks["no_provider_usage"] = not answer.usage
                if item["expected_behavior"] == "answered":
                    expected_banks = {unit["bank"] for unit in item["evidence"]}
                    checks["scope"] = set(trace["scope"]["banks"]) == expected_banks
                    supported = {eid for hit in answer.hits for eid in hit.chunk.evidence_ids}
                    checks["retrieved_inputs"] = all(any(variant["evidence_id"] in supported for variant in [unit, *unit.get("alternatives", [])]) for unit in item["evidence"])
                    if answer.mode == "validated_calculation":
                        expected = {}
                        for bank in expected_banks:
                            values = {(f.metric, f.period): f.value for f in facts if f.bank == bank}
                            revenue = (values['revenue','2025Q2']/values['revenue','2024Q2']-1)*100
                            expense = (values['noninterest_expense','2025Q2']/values['noninterest_expense','2024Q2']-1)*100
                            expected[bank] = str((revenue-expense).quantize(Decimal('0.01')))
                        checks["numeric_results"] = {c["bank"]: c["value"] for c in trace["calculations"]} == expected
                    elif answer.mode == "verified_reported_metrics":
                        lines = answer.text.split("\n\n")
                        checks["reported_amounts"] = all(any(bank_name(unit["bank"]) in line and f"${next(f.value for f in facts if f.bank==unit['bank'] and f.metric==unit['metric'] and f.period==unit['period']):,f} million" in line for line in lines) for unit in item["evidence"])
                    else:
                        checks["validated_answer_route"] = False
                record = {"id": item["id"], "checks": checks, "passed": all(checks.values()), "trace": trace}
            except Exception as exc:
                record = {"id": item["id"], "checks": checks, "passed": False, "error_type": type(exc).__name__, "error": str(exc)}
            records.append(record)
            print(item["id"], "PASS" if record["passed"] else "FAIL", flush=True)
    report = {"scope": "20 frozen narrow five-bank cases; assistant source checks, not independent human review or general 28-family accuracy.",
              "strategy": "semantic + reranking", "provider_calls": 0,
              "question_file": str(args.questions.relative_to(ROOT)),
              "passed": sum(r["passed"] for r in records), "total": len(records), "records": records}
    write_json(ROOT / "reports/five-bank-answer-validation.json", report)
    print(f"{report['passed']}/{report['total']} passed; no hosted model calls.")
    if report["passed"] != report["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
