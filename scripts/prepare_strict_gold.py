"""Correct period-specific gold alternatives without modifying the original set."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    questions = [json.loads(line) for line in (ROOT / "eval/gold_questions.jsonl").read_text(encoding="utf-8").splitlines()]
    facts = json.loads((ROOT / "data/reviewed_facts.json").read_text(encoding="utf-8"))
    blocks = {b["block_id"]: b for b in map(json.loads, (ROOT / "data/processed/blocks.jsonl").read_text(encoding="utf-8").splitlines())}

    def unit(eid):
        block = blocks[eid]
        return {"document_id": block["document_id"], "evidence_id": eid,
                "quote": "Row " + block["text"].rsplit("\nRow ", 1)[1]}

    # Gold annotation rules belong here, never in the retriever. Each input's
    # alternatives are already checked against original HTML for that period.
    specifications = {"01": (["JPM"], ["revenue"], ["2025Q2"]),
                      "02": (["BAC"], ["noninterest_expense"], ["2025Q2"]),
                      "03": (["JPM"], ["revenue"], ["2024Q2"]),
                      "04": (["BAC"], ["revenue"], ["2024Q2", "2025Q2"]),
                      "05": (["JPM"], ["noninterest_expense"], ["2024Q2", "2025Q2"]),
                      "06": (["JPM"], ["revenue", "noninterest_expense"], ["2024Q2", "2025Q2"]),
                      "07": (["BAC"], ["revenue", "noninterest_expense"], ["2024Q2", "2025Q2"]),
                      "08": (["JPM", "BAC"], ["revenue", "noninterest_expense"], ["2024Q2", "2025Q2"])}
    for question in questions:
        question["gold_version"] = "v2-period-specific-inputs"
        if question["id"] in specifications:
            banks, metrics, periods = specifications[question["id"]]
            inputs = [f for f in facts if f["bank"] in banks and f["metric"] in metrics and f["period"] in periods]
            question["evidence"] = [{**unit(f["evidence_id"]), "bank": f["bank"], "metric": f["metric"],
                                     "period": f["period"], "alternatives": [unit(eid) for eid in f.get("alternative_evidence_ids", [])]}
                                    for f in inputs]
        question["label_correction"] = "Numeric facts use separate period units; a one-period alternative cannot satisfy the other period. Original question wording and reference answers retained."
    target = ROOT / "eval/gold_questions.strict.jsonl"
    target.write_text("\n".join(json.dumps(q, ensure_ascii=False) for q in questions) + "\n", encoding="utf-8")
    print(f"Wrote {len(questions)} strict questions; original gold unchanged.")


if __name__ == "__main__":
    main()
