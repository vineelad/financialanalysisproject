# Accuracy improvement: retrieval and answer validation

The 66.7% development result was below the project's target. This iteration fixes evidence selection and separately checks whether the final answers use that evidence correctly. Retrieval scores are not answer accuracy scores.

## Retrieval changes

The retriever now gives table row labels more weight than repeated headers, expands metric terms such as ROA to return on assets, distinguishes consolidated from segment evidence, and recognizes calendar-date columns. Numeric selections require the requested metric: total assets cannot be replaced by interest-earning assets, and average balances cannot be replaced by period-end balances.

Metric coverage applies to single-bank and peer questions. For multi-period calculations it prefers rows spanning all requested quarters, while retaining the same 20-candidate/five-final-chunk/2,200-token budgets. Explanation questions prioritize causal narrative passages. No gold IDs, reviewed amounts, or reference answers are used by the retriever. Existing indexes are reused.

## Corrected labels and a fair baseline

The original gold labels incorrectly allowed a BAC row containing one year to satisfy an evidence unit intended to support a two-year calculation. The versioned `eval/gold_questions.strict.jsonl` assigns each numeric input its own period-specific alternatives. Original questions, reference values, labels, and published results are retained.

Both the v2 saved traces and v3 traces were scored with these identical strict labels. This correction makes the previous baseline slightly lower; it is not a relaxation to improve the new result. The [comparison data](strict-baseline-comparison.json) includes calculation readiness independently of evidence recall.

| Configuration | v2 recall, strict labels | v3 recall, strict labels | Valid calculation inputs, v2 → v3 |
|---|---:|---:|---:|
| Fixed | 65.8% | 93.3% | 2/5 → 5/5 |
| Semantic | 65.8% | 93.3% | 2/5 → 5/5 |
| Fixed + reranking | 60.8% | 93.3% | 2/5 → 5/5 |
| Semantic + reranking | 60.8% | 100.0% | 2/5 → 5/5 |

Recall means use 15 answerable questions per condition. All five designated scope cases remain correct. These questions informed development; the scores do not establish unseen performance. Candidate recall is 100% in all conditions. The remaining miss in A/B/C is the annotated management-explanation passage; D retains it. The [full v3 report](retrieval-v3-development/REPORT.md) preserves all 80 per-question records.

Semantic plus reranking is the selected UI default. This selection was made from development results before inspecting the prospective validation scores; the protocol is in `eval/validation_protocol.json`.

## Prospective checks and annotation audit

Ten additional questions were frozen before their retrieval was inspected: eight answerable questions, including net income, net interest income, ROE, ROTCE, and a revenue paraphrase, plus two scope cases. Original HTML cell assertions support the labels. These are assistant-authored checks on the same corpus, not an independent external assessment.

Initial raw recall was 87.5% without reranking and 75.0% with reranking. Inspection showed that the supposed misses retrieved the correct consolidated net-income and common-equity-return figures from equivalent income-statement rows absent from the annotations. The alternate cells were checked against the original HTML: net income 14,987/18,149 million and ROE 18%/23% for the requested quarters.

The immutable original set and raw results remain available. A separately versioned annotation audit adds those equivalent rows, without changing question text, expected values, retrieval, rankings, or answers. With audited annotations, **8/8 answerable questions have their required evidence in every condition**, and both scope cases pass per condition. This small result and post-run audit should not be represented as a clean independent 100% accuracy benchmark.

- [Raw prospective results](prospective-validation/raw/summary.json)
- [Audited prospective results](prospective-validation/audited/summary.json)
- Original freeze and cell checks: `eval/validation_freeze.json`
- Alternate-row audit: `eval/validation_annotation_audit.json`

## Answer safeguards

A live six-case check caught errors that retrieval recall alone would miss. The model invented JPMorgan intermediate growth rates, even though its final leverage value matched, and refused a management explanation despite a supporting quote being present. Those initial answers remain retained as failures.

The application now renders validated calculations directly from Python, including the actual inputs, reporting bases, component growth rates, and citations. It compares leverage using validated values and does not call the model for this path. This prevents the model from replacing a valid computation with invented arithmetic. Records use mode `validated_calculation`.

For explicit reported causal explanations, the model receives the supporting excerpt separately. If it refuses despite that excerpt, a source-backed fallback quotes the retrieved statement with citations, without inventing causes or attributing it to a named executive. Records identify this mode as `source_excerpt`. Ordinary lookups still use the configured model; incomplete segment summaries retain the earlier source-summary safeguard.

These guards have regression tests for incorrect/missing numeric support and refusal to invent a narrative cause from a numeric table. They do not establish that arbitrary model-written statements are faithful. Human review and a larger independent evaluation remain necessary.

The repeated live check passed source review for **all six selected answers**: peer operating leverage, JPM average assets, BAC period-end assets, JPM ROA, BAC management's reported revenue driver, and BAC consumer net income. Arithmetic now reports JPM revenue growth 6.47% and expense growth 4.59%, giving 1.88 percentage points; BAC is 5.95% minus 1.89%, giving 4.06 percentage points. The narrative answer cites the explicit higher-NII explanation. See [the reviewed answers](live-financial-validation.json), including the original failed answers and usage totals. This is assistant review, not an independent human audit.

The final batch used 15,012 tokens across five hosted calls; the peer calculation used zero model tokens. The previous six-call batch is retained separately and also incurred usage. These are not total project billing figures. The full suite passes **62 tests**, plus 13 reported subtests, including the UI defaults and no-model arithmetic path.

## Reproduce

```powershell
.\.venv\Scripts\python.exe scripts/prepare_strict_gold.py
.\.venv\Scripts\python.exe -m ir_assistant evaluate --questions eval/gold_questions.strict.jsonl
.\.venv\Scripts\python.exe -m ir_assistant evaluate --questions eval/validation_questions.jsonl
.\.venv\Scripts\python.exe scripts/validate_financial_answers.py
```

The first two evaluation commands are local. The live answer check makes at most five hosted calls because its peer calculation runs locally. Frozen validation labels should not be overwritten after viewing results. Full generated-answer accuracy percentages, warm p95 latency, and general performance on other filings remain unproven.
