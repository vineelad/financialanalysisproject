"""Export a completed local evaluation as reviewable, credential-free assets."""
import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def report(run_directory: Path, destination: Path) -> Path:
    configuration = json.loads((run_directory / "configuration.json").read_text(encoding="utf-8"))
    summaries = json.loads((run_directory / "summary.json").read_text(encoding="utf-8"))
    with (run_directory / "scores.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if configuration["generation"]:
        raise ValueError("This report template describes retrieval-only runs; report generated-answer quality separately.")
    if {r["run"] for r in rows} != set("ABCD"):
        raise ValueError("All four experiment conditions must be complete")
    by_run = {s["run"]: s for s in summaries}
    names = {"A": "Fixed", "B": "Semantic", "C": "Fixed + reranking", "D": "Semantic + reranking"}
    destination.mkdir(parents=True, exist_ok=True)
    for filename in ("configuration.json", "summary.json", "scores.csv"):
        shutil.copyfile(run_directory / filename, destination / filename)
    manifest = ROOT / "data" / "processed" / "source_manifest.json"
    if manifest.is_file():
        shutil.copyfile(manifest, destination / "source_manifest.json")
    lines = [
        "# Retrieval experiment report", "",
        "This is a retrieval-only pilot, not a generated-answer quality benchmark. No hosted model calls were made for this experiment.", "",
        "## Method", "",
        "The same 20 source-reviewed questions were run against a frozen three-document corpus: Bank of America's Q2 2025 release and supplement, and JPMorgan's Q2 2025 supplement. Comparative columns supply Q2 2024 figures. Fifteen questions have gold evidence; five test clarification or refusal.", "",
        "Labels and financial cells were reviewed by the coding assistant against cached original HTML, not independently audited by a human. Some question types overlap development checks. Treat this as a development pilot; a fresh held-out set is needed for a generalization claim.", "",
        "Fixed chunking uses 400 tokens with 60 overlap; semantic narrative chunking uses sentence similarity and bounded lengths. Tables use identical atomic rows in both conditions. Index sizes are 2,196 fixed and 2,199 semantic chunks, so this table-heavy corpus provides a weak test of narrative chunking differences.", "",
        "All conditions use BGE-small embeddings, dense/BM25 reciprocal rank fusion, bank/quarter/consumer filters, 20 fused candidates, and up to five final chunks within 2,200 tokens. Operating-leverage requests expand into revenue and expense queries in every condition. C and D rerank with the same local cross-encoder. Exact revisions and framework versions are in configuration.json.", "",
        f"Retrieval policy: {configuration.get('retrieval_policy', 'v1 (before peer retrieval changes)')}. Repeating the original questions after tuning is development re-evaluation, not an unseen benchmark.", "",
        "## Results", "",
        "Recall is the mean fraction of required evidence units covered per answerable question. Precision counts returned chunks matching annotated evidence; unannotated but relevant passages may be scored irrelevant. Candidate recall diagnoses retrieval failures before reranking. Each percentage below includes its question denominator.", "",
        "| Condition | Evidence recall @5 | Annotated precision @5 | Candidate recall @20 | Clarification/refusal correctness |",
        "|---|---:|---:|---:|---:|",
    ]
    keys = ("evidence_recall_at_5", "retrieval_precision_at_5", "candidate_recall_at_20", "behavior_correct")
    for name in "ABCD":
        summary = by_run[name]
        values = [f"{100 * summary[key]:.1f}% (n={summary[key + '_denominator']})" for key in keys]
        lines.append(f"| {name}: {names[name]} | " + " | ".join(values) + " |")
    lines += ["", "### Changes in evidence recall", ""]
    for second, first, label in [("B", "A", "Semantic vs fixed without reranking"),
                                  ("D", "C", "Semantic vs fixed with reranking"),
                                  ("C", "A", "Reranking on fixed chunks"),
                                  ("D", "B", "Reranking on semantic chunks")]:
        delta = 100 * (by_run[second]["evidence_recall_at_5"] - by_run[first]["evidence_recall_at_5"])
        lines.append(f"- {label} ({second} minus {first}): {delta:+.1f} percentage points.")
    lines += ["", "## Failures and limitations", "",
              "The table below includes every answerable case with incomplete final gold coverage or a calculation refusal. Candidate coverage distinguishes missing candidates from evidence lost in final selection. An evidence-only status is not a successful generated answer.", "",
              "| Condition | Question | Final recall | Candidate recall | Status |",
              "|---|---|---:|---:|---|"]
    for row in rows:
        if row["evidence_recall_at_5"] and (float(row["evidence_recall_at_5"]) < 1 or row["status"] == "insufficient_evidence"):
            lines.append(f"| {row['run']} | {row['question_id']} | {float(row['evidence_recall_at_5']):.2f} | {float(row['candidate_recall_at_20']):.2f} | {row['status']} |")
    lines += ["", "### Selected source-level examples", ""]
    for name, question_id in [("A", "06"), ("C", "05"), ("C", "07")]:
        trace = json.loads((run_directory / f"{name}-{question_id}.json").read_text(encoding="utf-8"))
        answer = trace["answer"]
        reason = answer["text"].splitlines()[0] if answer["status"] == "insufficient_evidence" else "Inspect scores.csv and the retained local trace for evidence coverage."
        lines += [f"- **{name}/{question_id}: {trace['gold']['question']}** Status: {answer['status']}. {reason}"]
    lines += ["", "Arithmetic is guarded by source-reviewed facts, and every input row must actually be retrieved. A correct refusal is safer than manufacturing an operating-leverage answer, but refusals on answerable questions remain a coverage failure. Reranking can improve one metric while pushing another required input out of the final five.", "",
              "The extraction repeats initial table headers; some JPMorgan expense rows inherit a misleading revenue heading. Those rows are deliberately excluded from verified alternate calculation evidence. Source-specific header repair and formula-aware metric coverage are follow-up work, followed by a new frozen evaluation. Consult the configuration's retrieval policy when comparing runs; do not treat repeats after development changes as held-out evaluation.", "",
              "## What has not been measured", "",
              "Generated-answer faithfulness, numeric accuracy, semantic citation support, answer coverage, and hosted token cost are not measured here. The manual review columns in scores.csv remain blank. Citation-ID validation alone does not establish factual support.", "",
              "Per-query timings are retained in scores.csv but include model initialization and a fixed condition order. They do not establish warm p95 latency or the proposed 15-second target. Run warmed, repeated measurements including generation before making that claim.", "",
              "## Reproduce", "", "```powershell",
              ".\\.venv\\Scripts\\python.exe -m ir_assistant evaluate --questions eval/gold_questions.jsonl",
              ".\\.venv\\Scripts\\python.exe scripts/report_evaluation.py runs/<evaluation-directory>", "```", "",
              f"Question SHA-256: `{configuration['question_hash']}`.", "",
              "Source hashes are in data/processed/source_manifest.json after preparation; gold labels and source cell checks are in eval/gold_questions.jsonl and data/fact_provenance.json. Full per-query traces stay in the local ignored runs directory. This export contains configuration, summaries, and per-query scores."]
    corpus_path = ROOT / "data" / "processed" / "blocks.jsonl"
    if corpus_path.is_file():
        lines += ["", f"Cleaned corpus SHA-256: `{hashlib.sha256(corpus_path.read_bytes()).hexdigest()}`."]
    path = destination / "REPORT.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "retrieval-evaluation")
    arguments = parser.parse_args()
    print(report(arguments.run_directory, arguments.output))
