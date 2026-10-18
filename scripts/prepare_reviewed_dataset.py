"""Reproduce assistant-reviewed labels with assertions against original HTML cells.

Run from the project root after prepare. The row/column choices below were
inspected in the original frozen documents; this script does not infer labels
from search results. It refuses source-cell mismatches rather than guessing.
"""
import argparse
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bs4 import BeautifulSoup
from ir_assistant.ingest import expand_table
from ir_assistant.models import Block
from ir_assistant.settings import DATA
from ir_assistant.storage import read_jsonl, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facts-only", action="store_true", help="Refresh checked facts without rewriting evaluation questions")
    args = parser.parse_args()
    blocks = {b.block_id: b for b in read_jsonl(DATA / "processed" / "blocks.jsonl", Block)}
    grids = {}
    for document in ("bac-2025q2-supplement", "jpm-2025q2-supplement"):
        soup = BeautifulSoup((DATA / "raw" / f"{document}.html").read_bytes(), "html.parser")
        grids[document] = [expand_table(table) if not table.find("table") else None for table in soup.find_all("table")]
    provenance = []

    def check(row_id, column, expected):
        document, table, row = re.fullmatch(r"(.+):t(\d+):r(\d+)", row_id).groups()
        actual = grids[document][int(table) - 1][int(row) - 1][column - 1].replace(",", "")
        assert Decimal(actual) == Decimal(str(expected)), (row_id, column, actual, expected)
        assert row_id in blocks
        provenance.append({"evidence_id": row_id, "column": column, "value": str(expected),
                           "source_url": blocks[row_id].url, "review_method": "original HTML expanded cell checked against selected value"})

    specs = [
        ("BAC", "revenue", "bac-2025q2-supplement:t27:r14", 19, 43, "10813", "10206",
         ["bac-2025q2-supplement:t21:r18"], ["bac-2025q2-supplement:t23:r18"], "FTE"),
        ("BAC", "noninterest_expense", "bac-2025q2-supplement:t27:r18", 19, 43, "5567", "5464",
         ["bac-2025q2-supplement:t21:r20"], ["bac-2025q2-supplement:t23:r20"], "FTE"),
        ("JPM", "revenue", "jpm-2025q2-supplement:t13:r19", 4, 28, "18847", "17701",
         ["jpm-2025q2-supplement:t9:r11"], ["jpm-2025q2-supplement:t9:r11"], "managed_FTE"),
        ("JPM", "noninterest_expense", "jpm-2025q2-supplement:t13:r26", 4, 28, "9858", "9425", [], [], "managed_FTE"),
        ("BAC", "net_interest_income", "bac-2025q2-supplement:t27:r7", 20, 44, "8726", "8118", [], [], "FTE"),
        ("BAC", "noninterest_income", "bac-2025q2-supplement:t27:r13", 19, 43, "2087", "2088", [], [], "FTE"),
        ("JPM", "net_interest_income", "jpm-2025q2-supplement:t13:r18", 4, 28, "14395", "13705", [], [], "managed_FTE"),
        ("JPM", "noninterest_income", "jpm-2025q2-supplement:t13:r17", 4, 28, "4452", "3996", [], [], "managed_FTE"),
    ]
    facts = []
    for bank, metric, eid, current_col, prior_col, current, prior, current_alias, prior_alias, basis in specs:
        for period, column, value, aliases in [("2025Q2", current_col, current, current_alias),
                                                ("2024Q2", prior_col, prior, prior_alias)]:
            check(eid, column, value)
            for alias in aliases:
                alias_column = (5 if period == "2025Q2" else 29) if bank == "JPM" else 16
                check(alias, alias_column, value)
            facts.append({"bank": bank, "segment": "consumer", "metric": metric, "period": period,
                          "value": value, "unit": "USD_millions", "basis": basis, "evidence_id": eid,
                          "period_type": "quarter", "alternative_evidence_ids": aliases})

    if args.facts_only:
        existing_path = DATA / "reviewed_facts.json"
        if existing_path.exists():
            facts.extend(f for f in json.loads(existing_path.read_text(encoding="utf-8")) if f["bank"] not in {"BAC", "JPM"})
        write_json(DATA / "reviewed_facts.json", facts)
        write_json(DATA / "fact_provenance.json", {"reviewer": "assistant", "checks": provenance,
            "basis_evidence": ["bac-2025q2-supplement:t1:r59", "jpm-2025q2-supplement:t9:r3", "jpm-2025q2-supplement:t9:r10"]})
        print(f"Prepared {len(facts)} financial facts with {len(provenance)} original-cell checks; evaluation questions unchanged.")
        return

    def unit(eid, aliases=(), quote=None):
        block = blocks[eid]
        value = quote if quote is not None else "Row " + block.text.rsplit("\nRow ", 1)[1]
        assert value in block.text
        return {"document_id": block.document_id, "quote": value, "evidence_id": eid,
                "alternatives": [unit(alias) for alias in aliases]}

    jrev = unit("jpm-2025q2-supplement:t13:r19", ["jpm-2025q2-supplement:t9:r11"])
    jexpense = unit("jpm-2025q2-supplement:t13:r26")
    brev = unit("bac-2025q2-supplement:t27:r14", ["bac-2025q2-supplement:t21:r18", "bac-2025q2-supplement:t23:r18"])
    bexpense = unit("bac-2025q2-supplement:t27:r18", ["bac-2025q2-supplement:t21:r20", "bac-2025q2-supplement:t23:r20"])
    def rate(now, prior):
        return (Decimal(now) / Decimal(prior) - 1) * 100
    jgrowth = rate("18847", "17701")
    jegrowth = rate("9858", "9425")
    bgrowth = rate("10813", "10206")
    begrowth = rate("5567", "5464")
    jl, bl = jgrowth - jegrowth, bgrowth - begrowth
    def rounded(value):
        return str(value.quantize(Decimal("0.01")))

    # Extra numeric labels are checked against original cells as well.
    for eid, column, value in [
        ("bac-2025q2-supplement:t27:r24", 19, "51.48"), ("bac-2025q2-supplement:t27:r24", 43, "53.54"),
        ("jpm-2025q2-supplement:t13:r44", 4, "52"), ("jpm-2025q2-supplement:t13:r44", 28, "53"),
        ("jpm-2025q2-supplement:t6:r22", 5, "4437618"), ("jpm-2025q2-supplement:t6:r22", 29, "4071443"),
        ("bac-2025q2-supplement:t9:r26", 8, "3441142"), ("bac-2025q2-supplement:t9:r26", 20, "3257996"),
        ("jpm-2025q2-supplement:t2:r40", 4, "1.35"), ("jpm-2025q2-supplement:t2:r40", 28, "1.79")]:
        check(eid, column, value)

    questions = [json.loads(line) for line in (ROOT / "eval" / "questions.draft.jsonl").read_text(encoding="utf-8").splitlines()]
    labels = [
        ([jrev], "JPM CCB Q2 2025 net revenue: USD 18,847 million, managed/FTE presentation."),
        ([bexpense], "BAC Consumer Banking Q2 2025 noninterest expense: USD 5,567 million."),
        ([jrev], "JPM CCB Q2 2024 net revenue: USD 17,701 million."),
        ([brev], f"BAC consumer revenue YoY growth: {rounded(bgrowth)}%; inputs 10,813 and 10,206 million."),
        ([jexpense], f"JPM consumer expense YoY growth: {rounded(jegrowth)}%; inputs 9,858 and 9,425 million."),
        ([jrev, jexpense], f"JPM consumer operating leverage: {rounded(jl)} percentage points; revenue growth {rounded(jgrowth)}% minus expense growth {rounded(jegrowth)}%."),
        ([brev, bexpense], f"BAC consumer operating leverage: {rounded(bl)} percentage points; revenue growth {rounded(bgrowth)}% minus expense growth {rounded(begrowth)}%."),
        ([jrev, jexpense, brev, bexpense], f"BAC {rounded(bl)} pp exceeds JPM {rounded(jl)} pp under the project formula; segment composition and reporting definitions differ, so this is a qualified comparison."),
        ([unit("bac-2025q2-supplement:t27:r24")], "BAC reported consumer efficiency ratio: 51.48% in Q2 2025 and 53.54% in Q2 2024."),
        ([unit("jpm-2025q2-supplement:t13:r44")], "JPM reported CCB overhead ratio: 52% in Q2 2025 and 53% in Q2 2024."),
        ([unit("jpm-2025q2-supplement:t6:r22")], "JPM consolidated average assets: USD 4,437,618 million in Q2 2025 and 4,071,443 million in Q2 2024; not period-end balances."),
        ([unit("bac-2025q2-supplement:t9:r26")], "BAC consolidated period-end assets: USD 3,441,142 million at June 30, 2025 and 3,257,996 million at June 30, 2024."),
        ([unit("jpm-2025q2-supplement:t2:r40", ["jpm-2025q2-supplement:t4:r48"])], "JPM reported consolidated ROA: 1.35% in Q2 2025 and 1.79% in Q2 2024; no unsupported annualization convention is inferred."),
        ([unit("bac-2025q2-results:textlayer3", quote="Revenue of $10.8 billion,2 up 6%, driven primarily by higher NII")], "BAC attributes the consumer revenue increase primarily to higher net interest income; attribute this explanation to management."),
        ([unit("jpm-2025q2-supplement:t1:r18", quote="Commercial & Investment Bank"), unit("bac-2025q2-supplement:t21:r17", quote="Global Banking | c34-36=Global Markets")], "JPM reports Commercial & Investment Bank; BAC separates Global Banking and Global Markets. Do not assert identical segment scope or invent a combined reported BAC segment."),
    ]
    # Tighten three broad draft prompts to what the frozen corpus explicitly reports.
    questions[8]["question"] = "What consumer efficiency ratios does Bank of America report for Q2 2025 and Q2 2024?"
    questions[9]["question"] = "What consumer overhead ratios does JPMorgan report for Q2 2025 and Q2 2024?"
    questions[12]["question"] = "What consolidated ROA does JPMorgan report for Q2 2025 and Q2 2024?"
    questions[14]["question"] = "Which corporate banking segment names do JPMorgan and Bank of America report in Q2 2025, and why should comparisons be qualified?"
    for question, (evidence, expected) in zip(questions, labels):
        question.update(evidence=evidence, expected_answer=expected)
    for question in questions:
        question["annotation_status"] = "reviewed"
        question["review_method"] = "Assistant checked frozen original HTML rows/cells or public-corpus scope; not an independent human financial audit."
    write_json(DATA / "reviewed_facts.json", facts)
    write_json(DATA / "fact_provenance.json", {"reviewer": "assistant", "checks": provenance,
        "basis_evidence": ["bac-2025q2-supplement:t1:r59", "jpm-2025q2-supplement:t9:r3", "jpm-2025q2-supplement:t9:r10"]})
    target = ROOT / "eval" / "gold_questions.jsonl"
    target.write_text("\n".join(json.dumps(q, ensure_ascii=False) for q in questions) + "\n", encoding="utf-8")
    print(f"Prepared {len(facts)} financial facts, {len(provenance)} original-cell checks, and {len(questions)} reviewed questions.")


if __name__ == "__main__":
    main()
