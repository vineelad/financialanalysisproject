"""Version omitted, previously reviewed aliases; rescore saved traces unchanged."""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ir_assistant.metrics import score_evidence


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    original_path = ROOT / "eval/five_bank_questions.jsonl"
    questions = [json.loads(line) for line in original_path.read_text(encoding="utf-8").splitlines()]
    snapshot = ROOT / "data/snapshots/two-bank-v1"
    old_facts = json.loads((snapshot / "reviewed_facts.json").read_text(encoding="utf-8"))
    old_checks = json.loads((snapshot / "fact_provenance.json").read_text(encoding="utf-8"))["checks"]
    blocks = {b["block_id"]: b for b in map(json.loads, (ROOT / "data/processed/blocks.jsonl").read_text(encoding="utf-8").splitlines())}
    additions = []
    for question in questions:
        question["annotation_version"] = "v2-preexisting-reviewed-alternatives"
        for unit in question["evidence"]:
            matches = [f for f in old_facts if f["bank"] == unit["bank"] and f["period"] == unit["period"] and f["metric"] == unit["metric"]]
            if not matches:
                continue
            assert len(matches) == 1
            fact = matches[0]
            alternatives = []
            for eid in fact.get("alternative_evidence_ids", []):
                # The alias and its amount were already reviewed before the
                # new evaluation was frozen, not selected from a model answer.
                checks = [check for check in old_checks if check["evidence_id"] == eid and str(check["value"]) == str(fact["value"])]
                assert checks, (eid, fact["value"])
                block = blocks[eid]
                alternatives.append(dict(document_id=block["document_id"], evidence_id=eid,
                                         quote="Row " + block["text"].rsplit("\nRow ", 1)[1], period=unit["period"]))
                additions.append(dict(question_id=question["id"], bank=unit["bank"], metric=unit["metric"],
                                      period=unit["period"], evidence_id=eid, preexisting_original_cell_checks=checks))
            if alternatives:
                unit["alternatives"] = alternatives
    audited_path = ROOT / "eval/five_bank_questions.audited.jsonl"
    content = "\n".join(json.dumps(q) for q in questions) + "\n"
    if audited_path.exists() and audited_path.read_text(encoding="utf-8") != content:
        raise ValueError("Refusing to overwrite a different audited label version")
    audited_path.write_text(content, encoding="utf-8")
    by_id = {q["id"]: q for q in questions}
    run = args.run.resolve()
    target = ROOT / "runs" / (run.name + "-audited")
    target.mkdir(exist_ok=True)
    rows = list(csv.DictReader((run / "scores.csv").open(encoding="utf-8")))
    for row in rows:
        name = f"{row['run']}-{row['question_id']}.json"
        trace = json.loads((run / name).read_text(encoding="utf-8"))
        question = by_id[row["question_id"]]
        final = score_evidence(question["evidence"], [h["chunk"] for h in trace["answer"]["hits"]])
        candidates = score_evidence(question["evidence"], [h["chunk"] for h in trace["candidate_hits"]])
        row.update(evidence_recall=final["evidence_recall"], retrieval_precision=final["precision"], candidate_recall=candidates["evidence_recall"])
        row["evidence_recall_at_5"] = final["evidence_recall"] if int(row["final_hit_limit"]) == 5 else None
        row["retrieval_precision_at_5"] = final["precision"] if int(row["final_hit_limit"]) == 5 else None
        row["candidate_recall_at_20"] = candidates["evidence_recall"] if int(row["candidate_limit"]) == 20 else None
        trace["gold"] = question
        (target / name).write_text(json.dumps(trace, indent=2), encoding="utf-8")
    with (target / "scores.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summaries = []
    for name in "ABCD":
        group = [row for row in rows if row["run"] == name]
        result = dict(run=name, questions=len(group))
        for key in ["evidence_recall", "retrieval_precision", "candidate_recall", "evidence_recall_at_5", "retrieval_precision_at_5", "candidate_recall_at_20", "behavior_correct"]:
            vals = [float(value) if value not in {"True", "False"} else float(value == "True") for row in group
                    if (value := row[key]) not in (None, "")]
            result[key] = sum(vals) / len(vals) if vals else None
            result[key + "_denominator"] = len(vals)
        summaries.append(result)
    (target / "summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    config = json.loads((run / "configuration.json").read_text(encoding="utf-8"))
    config["annotation_audit"] = dict(original_question_hash=sha(original_path), audited_label_hash=sha(audited_path), rescore_only=True)
    (target / "configuration.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    raw_answer_path = ROOT / "reports/five-bank-answer-validation.raw-v6.json"
    answer_report = json.loads(raw_answer_path.read_text(encoding="utf-8"))
    for record in answer_report["records"]:
        trace = record.get("trace")
        if trace and "retrieved_inputs" in record["checks"]:
            ids = {eid for hit in trace["answer"]["hits"] for eid in hit["chunk"]["evidence_ids"]}
            record["checks"]["retrieved_inputs"] = all(any(v["evidence_id"] in ids for v in [unit, *unit.get("alternatives", [])])
                                                       for unit in by_id[record["id"]]["evidence"])
            record["passed"] = all(record["checks"].values())
    answer_report["passed"] = sum(r["passed"] for r in answer_report["records"])
    answer_report["annotation_audit"] = dict(raw_report="reports/five-bank-answer-validation.raw-v6.json", rescore_only=True,
                                             note="Exact saved answers and retrieval retained; only omitted pre-reviewed aliases accepted.")
    (ROOT / "reports/five-bank-answer-validation.json").write_text(json.dumps(answer_report, indent=2), encoding="utf-8")
    audit = dict(original_question_hash=sha(original_path), audited_label_hash=sha(audited_path),
                 snapshot_facts_hash=sha(snapshot / "reviewed_facts.json"), additions=additions,
                 method="Aliases checked against pre-evaluation fact snapshot and its original-cell checks. Questions, expected values, answers, candidates and ranks unchanged.",
                 raw_retrieval_run=str(run.relative_to(ROOT)), audited_retrieval_run=str(target.relative_to(ROOT)))
    (ROOT / "eval/five_bank_annotation_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(dict(audited_run=str(target), saved_answers_passed=answer_report["passed"], total=answer_report["total"], aliases=len(additions))))


if __name__ == "__main__":
    main()
