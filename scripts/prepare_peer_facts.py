"""Check selected WFC/Citi/COF inputs against frozen originals; keep old labels.

Assistant-reviewed values, not an independent financial audit. This script never
rewrites gold evaluation questions or infers numbers from retrieved answers.
"""
import hashlib
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pdfplumber
from bs4 import BeautifulSoup
from ir_assistant.ingest import expand_table
from ir_assistant.metric_registry import validate_reviewed_fact
from ir_assistant.calculations import Fact


def main():
    data = ROOT / "data"
    blocks = {b["block_id"]: b for b in (json.loads(line) for line in (data / "processed/blocks.jsonl").read_text(encoding="utf-8").splitlines())}
    facts = [f for f in json.loads((data / "reviewed_facts.json").read_text(encoding="utf-8")) if f["bank"] not in {"WFC", "C", "COF"}]
    checks = []
    grids = {}
    for doc in ["c-2025q2-results", "cof-2025q2-results"]:
        soup = BeautifulSoup((data / "raw" / (doc + ".html")).read_bytes(), "html.parser")
        grids[doc] = [expand_table(t) if not t.find("table") else None for t in soup.find_all("table")]

    def add(bank, metric, eid, current, prior, basis, columns):
        assert eid in blocks, eid
        for period, value, column in [("2025Q2", current, columns[0]), ("2024Q2", prior, columns[1])]:
            item = dict(bank=bank, segment="consumer", metric=metric, period=period, value=value,
                        unit="USD_millions", basis=basis, evidence_id=eid, period_type="quarter", alternative_evidence_ids=[])
            validate_reviewed_fact(Fact(**{**item, "value": Decimal(value)}))
            facts.append(item)
            checks.append(dict(bank=bank, metric=metric, period=period, value=value, evidence_id=eid,
                               source_url=blocks[eid]["url"], original_column=column,
                               method="Original HTML expanded cell or original PDF text-line column checked against assistant-selected value"))

    specs = [
        ("C", "revenue", "c-2025q2-results", 7, 7, 4, 10, "5119", "4832", "reported"),
        ("C", "noninterest_expense", "c-2025q2-results", 7, 9, 4, 10, "2381", "2355", "reported"),
        ("COF", "revenue", "cof-2025q2-results", 19, 11, 4, 20, "2556", "2197", "GAAP"),
        ("COF", "noninterest_expense", "cof-2025q2-results", 19, 13, 4, 20, "1713", "1250", "GAAP"),
        ("COF", "net_interest_income", "cof-2025q2-results", 19, 9, 4, 20, "2162", "2025", "GAAP"),
        ("COF", "noninterest_income", "cof-2025q2-results", 19, 10, 4, 20, "394", "172", "GAAP"),
    ]
    for bank, metric, doc, table, row, ccol, pcol, current, prior, basis in specs:
        grid = grids[doc][table - 1]
        assert Decimal(grid[row - 1][ccol - 1].replace(",", "")) == Decimal(current)
        assert Decimal(grid[row - 1][pcol - 1].replace(",", "")) == Decimal(prior)
        assert ("USPB" in " ".join(grid[1])) if bank == "C" else ("Consumer Banking" in " ".join(grid[2]))
        add(bank, metric, f"{doc}:t{table}:r{row}", current, prior, basis, (ccol, pcol))
    with pdfplumber.open(data / "raw/wfc-2025q2-results.pdf") as pdf:
        lines = pdf.pages[3].extract_text().splitlines()
        assert lines[1].startswith("Consumer Banking and Lending")
        assert "2025 2025 2024 2025 2024" in lines
        for metric, label, current, prior in [("revenue", "Total revenue", "9228", "9006"),
                                                ("noninterest_expense", "Noninterest expense", "5799", "5701")]:
            matches = [(i, line) for i, line in enumerate(lines, 1) if line.startswith(label + " ")]
            assert len(matches) == 1
            number, line = matches[0]
            values = re.findall(r"\(?\d[\d,.]*\)?", line[len(label):])
            assert Decimal(values[0].replace(",", "")) == Decimal(current)
            assert Decimal(values[2].replace(",", "")) == Decimal(prior)
            add("WFC", metric, f"wfc-2025q2-results:page4:line{number}", current, prior, "reported", (1, 3))
    (data / "reviewed_facts.json").write_text(json.dumps(facts, indent=2) + "\n", encoding="utf-8")
    provenance = dict(reviewer="assistant", checks=checks,
                      basis_notes={"WFC": "Unadjusted reported segment table; not asserted to be FTE.", "C": "Unadjusted USPB table; not the All Other managed-basis table.", "COF": "Reported GAAP table, not adjusted non-GAAP results."},
                      caveats=["Capital One reports Credit Card separately from Consumer Banking.", "Discover results and statistics in this supplement cover May 18 through June 30, 2025; no acquisition normalization is computed."],
                      source_hashes={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (data / "raw").glob("*") if p.name.startswith(("wfc-", "c-", "cof-"))})
    (data / "peer_fact_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print(f"Checked {len(checks)} new source values; {len(facts)} reviewed facts available. Gold questions unchanged.")


if __name__ == "__main__":
    main()
