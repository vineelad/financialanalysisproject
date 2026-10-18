# Five-bank retrieval experiment

Expanded corpus: six official documents, five banks. Twenty frozen narrow cases: 18 answerable and two scope checks. Assistant-authored and source-reviewed; these topics overlap development and are not independent answer-accuracy validation.

| Run | Chunking / reranking | Evidence recall | Annotated precision | Candidate recall | Scope checks | Calculation inputs |
|---|---|---:|---:|---:|---:|---:|
| A | Fixed | 100.0% (18 cases) | 41.1% | 100.0% | 2/2 | 4/4 |
| B | Semantic | 100.0% (18 cases) | 41.1% | 100.0% | 2/2 | 4/4 |
| C | Fixed + reranking | 100.0% (18 cases) | 40.0% | 100.0% | 2/2 | 4/4 |
| D | Semantic + reranking | 100.0% (18 cases) | 40.0% | 100.0% | 2/2 | 4/4 |

## Annotation audit: raw and rescored results

The frozen original labels omitted equivalent BofA/JPM rows already recorded in the pre-evaluation reviewed fact snapshot. A separate audited label file adds those verified alternatives. No questions, expected values, answers, candidates or rankings changed; these are rescored saved traces, not a fresh independent validation.

| Run | Raw recall | Audited recall |
|---|---:|---:|
| A | 98.9% | 100.0% |
| B | 98.9% | 100.0% |
| C | 97.8% | 100.0% |
| D | 97.8% | 100.0% |

Raw v6 results: `reports/five-bank-retrieval-raw-v6/`. Initial pre-fix results: `reports/five-bank-retrieval-initial/`. Audit proof: `eval/five_bank_annotation_audit.json`. The answer checks likewise retain the initial 16/20 and post-fix raw 18/20 records alongside their audited score. Apparent remaining failures after the retrieval fix were missing equivalent-row labels, not incorrect amounts.


## Observed chunking and reranking impact

Evidence recall is equal across the four configurations on this narrow table-heavy set. The chunkers share atomic income rows, and typed metric/period coverage already preserves the inputs. This experiment does not demonstrate a recall advantage for semantic chunking or reranking on these cases. Annotated precision scores exact reviewed rows, including audited equivalents, rather than every potentially useful contextual passage. The earlier two-bank narrative-containing experiment remains a separate comparison.


## Budgets and interpretation

All four configurations use the same query-dependent budgets. One/two-bank cases retain 20 candidates and a 2,200-token context. Five-bank cases use 50 candidates and 5,500 context tokens. Final evidence limits are at least five, with enough slots for the requested metrics per bank: five for revenue/expense, ten for five-bank operating leverage. Two-bank revenue build-up can use six rows.

The table reports evidence recall under each query's actual budget, not a blanket recall@5. CSV rows record candidate, final-hit and context limits. Legacy @5/@20 fields are populated only where their names match the actual limits. These results are separate from the earlier three-document/two-bank experiment.

Calculation readiness means the local reviewed inputs were retrieved and Python completed the calculation. Retrieval-only runs do not establish generated-answer accuracy. See `reports/five-bank-answer-validation.json` for the separate narrow deterministic-answer checks. No hosted calls are made by the retrieval experiment.
