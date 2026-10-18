"""Audit equivalent source rows; preserve the frozen set and raw scores."""
import csv
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
from ir_assistant.metrics import score_evidence


def main():
    source = ROOT / "eval/validation_questions.jsonl"
    freeze = json.loads((ROOT / "eval/validation_freeze.json").read_text(encoding="utf-8"))
    assert hashlib.sha256(source.read_bytes()).hexdigest() == freeze["question_hash"]
    questions = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
    blocks = {b["block_id"]: b for b in map(json.loads, (ROOT / "data/processed/blocks.jsonl").read_text(encoding="utf-8").splitlines())}
    soup = BeautifulSoup((ROOT / "data/raw/jpm-2025q2-supplement.html").read_bytes(), "html.parser")
    tables = [expand_table(t) if not t.find("table") else None for t in soup.find_all("table")]
    aliases = {"v01": ("jpm-2025q2-supplement:t4:r38", [(5, "14987"), (29, "18149")]),
               "v06": ("jpm-2025q2-supplement:t4:r46", [(4, "18"), (28, "23")])}
    checks = []
    for question in questions:
        if question["id"] not in aliases:
            continue
        eid, cells = aliases[question["id"]]
        _, table, row = eid.split(":")
        for column, expected in cells:
            actual = tables[int(table[1:])-1][int(row[1:])-1][column-1].replace(",", "")
            assert Decimal(actual) == Decimal(expected), (eid, column)
            checks.append({"question_id": question["id"], "evidence_id": eid, "column": column, "value": expected, "source_url": blocks[eid]["url"]})
        block = blocks[eid]
        assert "CONSOLIDATED STATEMENTS OF INCOME" in block["text"]
        question["evidence"][0].setdefault("alternatives", []).append({"document_id": block["document_id"],
            "evidence_id": eid, "quote": block["text"].rsplit("\nRow ", 1)[1].split(": ", 1)[1]})
    audited = ROOT / "eval/validation_questions.audited.jsonl"
    audited.write_text("\n".join(json.dumps(q, ensure_ascii=False) for q in questions)+"\n", encoding="utf-8")
    metadata = {"original_question_hash": freeze["question_hash"], "audited_question_hash": hashlib.sha256(audited.read_bytes()).hexdigest(),
                "reviewer": "coding assistant; not independent human audit", "source_cell_checks": checks,
                "reason": "Post-run annotation audit: equivalent consolidated net income and ROE rows were unannotated false negatives. Question text, expected values, retrieval code, rankings, and answers were not changed. Original labels and scores retained."}
    (ROOT / "eval/validation_annotation_audit.json").write_text(json.dumps(metadata, indent=2)+"\n", encoding="utf-8")
    original = next(p for p in (ROOT / "runs").glob("evaluation-*")
                    if json.loads((p / "configuration.json").read_text(encoding="utf-8"))["question_hash"] == freeze["question_hash"])
    directory = ROOT / "runs" / ("evaluation-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    directory.mkdir()
    config = json.loads((original / "configuration.json").read_text(encoding="utf-8"))
    config.update(question_hash=metadata["audited_question_hash"], original_run=original.name,
                  annotation_audit=metadata["reason"], scope="Prospective same-corpus validation; source-audited equivalent-row annotations. Original raw scores retained.")
    (directory / "configuration.json").write_text(json.dumps(config, indent=2)+"\n", encoding="utf-8")
    with (original / "scores.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    by_id = {q["id"]: q for q in questions}
    for row in rows:
        filename = f"{row['run']}-{row['question_id']}.json"
        trace = json.loads((original / filename).read_text(encoding="utf-8"))
        q = by_id[row["question_id"]]
        trace["gold"] = q
        (directory / filename).write_text(json.dumps(trace, indent=2)+"\n", encoding="utf-8")
        scores = score_evidence(q.get("evidence", []), [h["chunk"] for h in trace["answer"]["hits"]])
        candidates = score_evidence(q.get("evidence", []), [h["chunk"] for h in trace["candidate_hits"]])
        row.update(evidence_recall_at_5=scores["evidence_recall"], retrieval_precision_at_5=scores["precision"], candidate_recall_at_20=candidates["evidence_recall"])
        row["behavior_correct"] = None if row["behavior_correct"] == "" else row["behavior_correct"] == "True"
    with (directory / "scores.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    summaries = []
    for run in "ABCD":
        group = [r for r in rows if r["run"] == run]
        summary = {"run": run, "questions": len(group)}
        for key in ["evidence_recall_at_5", "retrieval_precision_at_5", "candidate_recall_at_20", "behavior_correct"]:
            values = [r[key] for r in group if r[key] is not None]
            summary[key] = sum(values)/len(values) if values else None
            summary[key+"_denominator"] = len(values)
        summaries.append(summary)
    (directory / "summary.json").write_text(json.dumps(summaries, indent=2)+"\n", encoding="utf-8")
    for label, run in [("raw", original), ("audited", directory)]:
        output = ROOT / "reports" / "prospective-validation" / label
        output.mkdir(parents=True, exist_ok=True)
        for name in ["configuration.json", "summary.json", "scores.csv"]:
            (output / name).write_bytes((run / name).read_bytes())
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
