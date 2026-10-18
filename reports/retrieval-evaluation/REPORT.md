# Retrieval experiment report

This is a retrieval-only pilot, not a generated-answer quality benchmark. No hosted model calls were made for this experiment.

## Method

The same 20 source-reviewed questions were run against a frozen three-document corpus: Bank of America's Q2 2025 release and supplement, and JPMorgan's Q2 2025 supplement. Comparative columns supply Q2 2024 figures. Fifteen questions have gold evidence; five test clarification or refusal.

Labels and financial cells were reviewed by the coding assistant against cached original HTML, not independently audited by a human. Some question types overlap development checks. Treat this as a development pilot; a fresh held-out set is needed for a generalization claim.

Fixed chunking uses 400 tokens with 60 overlap; semantic narrative chunking uses sentence similarity and bounded lengths. Tables use identical atomic rows in both conditions. Index sizes are 2,196 fixed and 2,199 semantic chunks, so this table-heavy corpus provides a weak test of narrative chunking differences.

All conditions use BGE-small embeddings, dense/BM25 reciprocal rank fusion, bank/quarter/consumer filters, 20 fused candidates, and up to five final chunks within 2,200 tokens. Operating-leverage requests expand into revenue and expense queries in every condition. C and D rerank with the same local cross-encoder. Exact revisions and framework versions are in configuration.json.

## Results

Recall is the mean fraction of required evidence units covered per answerable question. Precision counts returned chunks matching annotated evidence; unannotated but relevant passages may be scored irrelevant. Candidate recall diagnoses retrieval failures before reranking. Each percentage below includes its question denominator.

| Condition | Evidence recall @5 | Annotated precision @5 | Candidate recall @20 | Clarification/refusal correctness |
|---|---:|---:|---:|---:|
| A: Fixed | 58.3% (n=15) | 22.7% (n=15) | 73.3% (n=15) | 100.0% (n=5) |
| B: Semantic | 58.3% (n=15) | 21.3% (n=15) | 73.3% (n=15) | 100.0% (n=5) |
| C: Fixed + reranking | 55.0% (n=15) | 17.3% (n=15) | 73.3% (n=15) | 100.0% (n=5) |
| D: Semantic + reranking | 55.0% (n=15) | 17.3% (n=15) | 73.3% (n=15) | 100.0% (n=5) |

### Changes in evidence recall

- Semantic vs fixed without reranking (B minus A): +0.0 percentage points.
- Semantic vs fixed with reranking (D minus C): +0.0 percentage points.
- Reranking on fixed chunks (C minus A): -3.3 percentage points.
- Reranking on semantic chunks (D minus B): -3.3 percentage points.

## Failures and limitations

The table below includes every answerable case with incomplete final gold coverage or a calculation refusal. Candidate coverage distinguishes missing candidates from evidence lost in final selection. An evidence-only status is not a successful generated answer.

| Condition | Question | Final recall | Candidate recall | Status |
|---|---|---:|---:|---|
| A | 06 | 0.50 | 1.00 | insufficient_evidence |
| A | 07 | 0.50 | 1.00 | insufficient_evidence |
| A | 08 | 0.25 | 0.50 | insufficient_evidence |
| A | 11 | 0.00 | 0.00 | evidence_only |
| A | 12 | 0.00 | 0.00 | evidence_only |
| A | 13 | 0.00 | 0.00 | evidence_only |
| A | 14 | 0.00 | 1.00 | evidence_only |
| A | 15 | 0.50 | 0.50 | evidence_only |
| B | 06 | 0.50 | 1.00 | insufficient_evidence |
| B | 07 | 0.50 | 1.00 | insufficient_evidence |
| B | 08 | 0.25 | 0.50 | insufficient_evidence |
| B | 11 | 0.00 | 0.00 | evidence_only |
| B | 12 | 0.00 | 0.00 | evidence_only |
| B | 13 | 0.00 | 0.00 | evidence_only |
| B | 14 | 0.00 | 1.00 | evidence_only |
| B | 15 | 0.50 | 0.50 | evidence_only |
| C | 05 | 0.00 | 1.00 | insufficient_evidence |
| C | 07 | 0.50 | 1.00 | insufficient_evidence |
| C | 08 | 0.25 | 0.50 | insufficient_evidence |
| C | 11 | 0.00 | 0.00 | evidence_only |
| C | 12 | 0.00 | 0.00 | evidence_only |
| C | 13 | 0.00 | 0.00 | evidence_only |
| C | 14 | 0.00 | 1.00 | evidence_only |
| C | 15 | 0.50 | 0.50 | evidence_only |
| D | 05 | 0.00 | 1.00 | insufficient_evidence |
| D | 07 | 0.50 | 1.00 | insufficient_evidence |
| D | 08 | 0.25 | 0.50 | insufficient_evidence |
| D | 11 | 0.00 | 0.00 | evidence_only |
| D | 12 | 0.00 | 0.00 | evidence_only |
| D | 13 | 0.00 | 0.00 | evidence_only |
| D | 14 | 0.00 | 1.00 | evidence_only |
| D | 15 | 0.50 | 0.50 | evidence_only |

### Selected source-level examples

- **A/06: What was JPMorgan consumer banking operating leverage from Q2 2024 to Q2 2025?** Status: insufficient_evidence. Missing or conflicting retrieved JPM 2025Q2 noninterest_expense inputs
- **C/05: What was JPMorgan consumer banking expense growth from Q2 2024 to Q2 2025?** Status: insufficient_evidence. Required reviewed financial inputs are absent from the selected evidence
- **C/07: What was Bank of America consumer banking operating leverage from Q2 2024 to Q2 2025?** Status: insufficient_evidence. Missing or conflicting retrieved BAC 2025Q2 revenue inputs

Arithmetic is guarded by source-reviewed facts, and every input row must actually be retrieved. A correct refusal is safer than manufacturing an operating-leverage answer, but refusals on answerable questions remain a coverage failure. Reranking can improve one metric while pushing another required input out of the final five.

The extraction repeats initial table headers; some JPMorgan expense rows inherit a misleading revenue heading. Those rows are deliberately excluded from verified alternate calculation evidence. Source-specific header repair and formula-aware metric coverage are follow-up work, followed by a new frozen evaluation; these results were not tuned after inspection.

## What has not been measured

Generated-answer faithfulness, numeric accuracy, semantic citation support, answer coverage, and hosted token cost are not measured here. The manual review columns in scores.csv remain blank. Citation-ID validation alone does not establish factual support.

Per-query timings are retained in scores.csv but include model initialization and a fixed condition order. They do not establish warm p95 latency or the proposed 15-second target. Run warmed, repeated measurements including generation before making that claim.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -m ir_assistant evaluate --questions eval/gold_questions.jsonl
.\.venv\Scripts\python.exe scripts/report_evaluation.py runs/<evaluation-directory>
```

Question SHA-256: `0629ca762947693add75977693a5cee4bd0253dcf9b86e4bdbd1f5fdcc335a3c`.

Source hashes are in data/processed/source_manifest.json after preparation; gold labels and source cell checks are in eval/gold_questions.jsonl and data/fact_provenance.json. Full per-query traces stay in the local ignored runs directory. This export contains configuration, summaries, and per-query scores.

Cleaned corpus SHA-256: `a4f3a5be8f0706572bcbe30f49885a8c5c92663f486c7e149942de9903a9402b`.
