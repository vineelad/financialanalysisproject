"""Publish the expanded evaluation with actual query budgets and denominators."""
import argparse
import csv
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/five-bank-retrieval")
    args = parser.parse_args()
    source = args.run.resolve()
    summary = json.loads((source / "summary.json").read_text(encoding="utf-8"))
    scores = list(csv.DictReader((source / "scores.csv").open(encoding="utf-8")))
    target = args.output
    target.mkdir(parents=True, exist_ok=True)
    for path in source.glob("*.json"):
        shutil.copy2(path, target / path.name)
    shutil.copy2(source / "scores.csv", target / "scores.csv")
    sources = json.loads((ROOT / "data/processed/source_manifest.json").read_text(encoding="utf-8"))
    (target / "source_manifest.json").write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")
    lines = ["# Five-bank retrieval experiment", "",
             "Expanded corpus: six official documents, five banks. Twenty frozen narrow cases: 18 answerable and two scope checks. "
             "Assistant-authored and source-reviewed; these topics overlap development and are not independent answer-accuracy validation.", "",
             "| Run | Chunking / reranking | Evidence recall | Annotated precision | Candidate recall | Scope checks | Calculation inputs |", "|---|---|---:|---:|---:|---:|---:|"]
    names = {"A": "Fixed", "B": "Semantic", "C": "Fixed + reranking", "D": "Semantic + reranking"}
    for item in summary:
        run = item["run"]
        cases = [json.loads(p.read_text(encoding="utf-8")) for p in target.glob(f"{run}-F*.json")]
        calculations = [case for case in cases if "operating leverage" in case["gold"]["question"].lower()]
        scope_rows = [row for row in scores if row["run"] == run and row["question_id"] in {"F19", "F20"}]
        ready = sum(case["answer"]["status"] == "evidence_only" and bool(case["calculations"]) for case in calculations)
        scope_ok = sum(row["behavior_correct"] == "True" for row in scope_rows)
        lines.append(f"| {run} | {names[run]} | {item['evidence_recall']:.1%} ({item['evidence_recall_denominator']} cases) | "
                     f"{item['retrieval_precision']:.1%} | {item['candidate_recall']:.1%} | {scope_ok}/{len(scope_rows)} | {ready}/{len(calculations)} |")
    config = json.loads((source / "configuration.json").read_text(encoding="utf-8"))
    if config.get("annotation_audit"):
        audit = json.loads((ROOT / "eval/five_bank_annotation_audit.json").read_text(encoding="utf-8"))
        raw_summary = json.loads((ROOT / audit["raw_retrieval_run"] / "summary.json").read_text(encoding="utf-8"))
        lines += ["", "## Annotation audit: raw and rescored results", "",
                  "The frozen original labels omitted equivalent BofA/JPM rows already recorded in the pre-evaluation reviewed fact snapshot. "
                  "A separate audited label file adds those verified alternatives. No questions, expected values, answers, candidates or rankings changed; "
                  "these are rescored saved traces, not a fresh independent validation.", "",
                  "| Run | Raw recall | Audited recall |", "|---|---:|---:|"]
        for raw, final in zip(raw_summary, summary):
            lines.append(f"| {raw['run']} | {raw['evidence_recall']:.1%} | {final['evidence_recall']:.1%} |")
        lines += ["", "Raw v6 results: `reports/five-bank-retrieval-raw-v6/`. Initial pre-fix results: `reports/five-bank-retrieval-initial/`. "
                  "Audit proof: `eval/five_bank_annotation_audit.json`. The answer checks likewise retain the initial 16/20 and post-fix raw 18/20 records "
                  "alongside their audited score. Apparent remaining failures after the retrieval fix were missing equivalent-row labels, not incorrect amounts.", ""]
    if len({round(item["evidence_recall"], 8) for item in summary}) == 1:
        lines += ["", "## Observed chunking and reranking impact", "",
                  "Evidence recall is equal across the four configurations on this narrow table-heavy set. The chunkers share atomic income rows, "
                  "and typed metric/period coverage already preserves the inputs. This experiment does not demonstrate a recall advantage for semantic "
                  "chunking or reranking on these cases. Annotated precision scores exact reviewed rows, including audited equivalents, rather than every "
                  "potentially useful contextual passage. The earlier two-bank narrative-containing experiment remains a separate comparison.", ""]
    lines += ["", "## Budgets and interpretation", "",
              "All four configurations use the same query-dependent budgets. One/two-bank cases retain 20 candidates and a 2,200-token context. "
              "Five-bank cases use 50 candidates and 5,500 context tokens. Final evidence limits are at least five, with enough slots for the "
              "requested metrics per bank: five for revenue/expense, ten for five-bank operating leverage. Two-bank revenue build-up can use six rows.", "",
              "The table reports evidence recall under each query's actual budget, not a blanket recall@5. CSV rows record candidate, final-hit and context limits. "
              "Legacy @5/@20 fields are populated only where their names match the actual limits. These results are separate from the earlier three-document/two-bank experiment.", "",
              "Calculation readiness means the local reviewed inputs were retrieved and Python completed the calculation. Retrieval-only runs do not establish generated-answer accuracy. "
              "See `reports/five-bank-answer-validation.json` for the separate narrow deterministic-answer checks. No hosted calls are made by the retrieval experiment.", ""]
    (target / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(target / "REPORT.md")


if __name__ == "__main__":
    main()
