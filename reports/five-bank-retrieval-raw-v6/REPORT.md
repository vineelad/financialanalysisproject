# Five-bank retrieval experiment

Expanded corpus: six official documents, five banks. Twenty frozen narrow cases: 18 answerable and two scope checks. Assistant-authored and source-reviewed; these topics overlap development and are not independent answer-accuracy validation.

| Run | Chunking / reranking | Evidence recall | Candidate recall | Scope checks | Calculation inputs |
|---|---|---:|---:|---:|---:|
| A | Fixed | 98.9% (18 cases) | 100.0% | 2/2 | 4/4 |
| B | Semantic | 98.9% (18 cases) | 100.0% | 2/2 | 4/4 |
| C | Fixed + reranking | 97.8% (18 cases) | 100.0% | 2/2 | 4/4 |
| D | Semantic + reranking | 97.8% (18 cases) | 100.0% | 2/2 | 4/4 |

## Budgets and interpretation

All four configurations use the same query-dependent budgets. One/two-bank cases retain 20 candidates and a 2,200-token context. Five-bank cases use 50 candidates and 5,500 context tokens. Final evidence limits are at least five, with enough slots for the requested metrics per bank: five for revenue/expense, ten for five-bank operating leverage. Two-bank revenue build-up can use six rows.

The table reports evidence recall under each query's actual budget, not a blanket recall@5. CSV rows record candidate, final-hit and context limits. Legacy @5/@20 fields are populated only where their names match the actual limits. These results are separate from the earlier three-document/two-bank experiment.

Calculation readiness means the local reviewed inputs were retrieved and Python completed the calculation. Retrieval-only runs do not establish generated-answer accuracy. See `reports/five-bank-answer-validation.json` for the separate narrow deterministic-answer checks. No hosted calls are made by the retrieval experiment.
