"""Freeze prospective checks on new metrics before inspecting their retrieval."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bs4 import BeautifulSoup
from ir_assistant.ingest import expand_table


def main():
    target = ROOT / "eval/validation_questions.jsonl"
    if target.exists():
        raise ValueError("Validation set already frozen; do not overwrite after seeing results")
    blocks = {b["block_id"]: b for b in map(json.loads, (ROOT / "data/processed/blocks.jsonl").read_text(encoding="utf-8").splitlines())}
    grids = {}
    for doc in ["jpm-2025q2-supplement", "bac-2025q2-supplement"]:
        soup = BeautifulSoup((ROOT / f"data/raw/{doc}.html").read_bytes(), "html.parser")
        grids[doc] = [expand_table(t) if not t.find("table") else None for t in soup.find_all("table")]
    specifications = [
        ("v01", "What consolidated net income did JPMorgan report for Q2 2025 and Q2 2024?", "jpm-2025q2-supplement:t2:r15", [(4, "14987"), (28, "18149")], "USD 14,987 million and USD 18,149 million."),
        ("v02", "What net income did Bank of America Consumer Banking report in Q2 2025 and Q2 2024?", "bac-2025q2-supplement:t27:r21", [(20, "2973"), (44, "2595")], "USD 2,973 million and USD 2,595 million."),
        ("v03", "Give JPMorgan consumer banking net income for Q2 2024.", "jpm-2025q2-supplement:t13:r30", [(29, "4210")], "USD 4,210 million."),
        ("v04", "What was Bank of America consumer net interest income in Q2 2025 and Q2 2024?", "bac-2025q2-supplement:t27:r7", [(20, "8726"), (44, "8118")], "USD 8,726 million and USD 8,118 million."),
        ("v05", "What net interest income did JPMorgan Consumer and Community Banking report for Q2 2025 and Q2 2024?", "jpm-2025q2-supplement:t13:r18", [(4, "14395"), (28, "13705")], "USD 14,395 million and USD 13,705 million."),
        ("v06", "What consolidated return on common equity did JPMorgan report in Q2 2025 and Q2 2024?", "jpm-2025q2-supplement:t2:r38", [(4, "18"), (28, "23")], "18% and 23%; this is common equity, not tangible common equity."),
        ("v07", "What consolidated return on tangible common equity did JPMorgan report for Q2 2025 and Q2 2024?", "jpm-2025q2-supplement:t2:r39", [(4, "21"), (28, "28")], "21% and 28%; preserve the tangible common equity measure."),
        ("v08", "Give the reported Consumer and Community Banking total net revenue at JPM for Q2 2024.", "jpm-2025q2-supplement:t13:r19", [(28, "17701")], "USD 17,701 million."),
    ]
    questions, checks = [], []
    for qid, question, eid, values, answer in specifications:
        doc, table, row = eid.split(":")
        for column, expected in values:
            actual = grids[doc][int(table[1:])-1][int(row[1:])-1][column-1].replace(",", "")
            assert Decimal(actual) == Decimal(expected), (eid, column)
            checks.append({"evidence_id": eid, "column": column, "value": expected})
        block = blocks[eid]
        # Row numbers are locators, not part of the underlying evidence unit.
        quote = block["text"].rsplit("\nRow ", 1)[1].split(": ", 1)[1]
        questions.append({"id": qid, "question": question, "expected_behavior": "answered",
                          "annotation_status": "reviewed", "expected_answer": answer,
                          "evidence": [{"document_id": doc, "evidence_id": eid, "quote": quote}],
                          "review_method": "Assistant checked original HTML cells before validation retrieval; not an independent human audit."})
    questions.extend([
        {"id": "v09", "question": "Predict Bank of America consumer revenue in Q2 2027.", "expected_behavior": "insufficient_evidence", "annotation_status": "reviewed", "evidence": [], "expected_answer": "Historical corpus cannot establish forecasts."},
        {"id": "v10", "question": "How profitable was the bank in the latest quarter?", "expected_behavior": "clarification", "annotation_status": "reviewed", "evidence": [], "expected_answer": "Clarify bank, period, and profitability measure."},
    ])
    target.write_text("\n".join(json.dumps(q, ensure_ascii=False) for q in questions)+"\n", encoding="utf-8")
    (ROOT / "eval/validation_freeze.json").write_text(json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(),
        "question_hash": hashlib.sha256(target.read_bytes()).hexdigest(), "source_checks": checks,
        "scope": "Prospective same-corpus validation: new metrics plus a revenue paraphrase, frozen after v3 implementation and before running these questions. Assistant-authored, not independent external evaluation. Do not tune to the results and retain the held-out label."}, indent=2)+"\n", encoding="utf-8")
    print("Frozen 10 prospective validation questions with original-cell checks.")


if __name__ == "__main__":
    main()
