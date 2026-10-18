# Peer comparison improvement

The original peer failure is retained in [the first live validation](GENERATION_VALIDATION.md). Retrieval now finds source overviews from both banks. For the corporate-segment question, a source-backed summary lists JPMorgan's Commercial & Investment Bank and BAC's separately reported labels, including Global Banking and Global Markets. It states that labels alone do not establish comparable business scope.

## Changes

- Explicit questions about segment names or scope prefer tables of contents and business-segment overviews. Ordinary metric lookups retain their existing corpus scope.
- Structural queries expand to reporting terminology, including commercial/investment banking for corporate banking. The reranker uses the resolved structural query.
- Final selection reserves available evidence for each requested bank within the same five-chunk/2,200-token budget.
- Quantitative peer questions preserve retrieved total revenue/expense rows in the candidate pool and final selection. Empty headings, rates, and noninterest revenue cannot substitute for total revenue. This rule uses source row labels, not reviewed answers or gold evidence IDs.
- Literal segment labels are extracted from retrieved overview columns and named contents entries with their chunk citations. If the model omits labels, the application displays a source summary and records mode `source_summary`. It does not invent a missing bank or infer segment equivalence. Original model citation IDs are still validated before this fallback.

The model continued to omit Global Markets after several prompt revisions. That limitation is not hidden: the final complete overview uses the deterministic source-summary fallback. The source summary is a different output mode from model-written prose and is identified in the saved research record.

The final live check passed in `source_summary` mode. [The saved answer and review](peer-generation-validation.json) include citations, prompt fingerprint, retrieved excerpts, and the four earlier incomplete attempts. The five live peer attempts in this iteration used 11,040 tokens (9,616 input and 1,424 output); these are not total project usage. Earlier project requests are excluded, and actual billing should be checked in Nebius.

## Development checks

Three local regression questions cover segment names, a scope paraphrase, and consumer revenue at both banks. Required evidence terms are present under all four configurations: **12/12 checks**. This checks evidence presence, not exact column interpretation or generated-answer quality. The original failed question and related wording were used during development; these checks are not held out.

See [the retrieved excerpts](peer-retrieval-development.json) and rerun with:

```powershell
.\.venv\Scripts\python.exe scripts/check_peer_retrieval.py
```

## Repeated four-condition experiment

The original 20 questions were repeated with the new retrieval policy. This is development re-evaluation after tuning, not a fresh benchmark. The original report remains unchanged.

| Condition | Original recall @5 | Updated recall @5 | Change |
|---|---:|---:|---:|
| Fixed | 58.3% | 66.7% | +8.3 percentage points |
| Semantic | 58.3% | 66.7% | +8.3 percentage points |
| Fixed + reranking | 55.0% | 63.3% | +8.3 percentage points |
| Semantic + reranking | 55.0% | 63.3% | +8.3 percentage points |

Means use 15 answerable questions per condition; changes are computed from unrounded values. Candidate recall rises from 73.3% to 80.0%. All five clarification/refusal cases still behave correctly per condition. These improvements do not meet the proposed 90% recall target. Reranking still reduces mean recall, and the table-heavy corpus still shows no recall advantage for semantic chunking.

The [updated report](retrieval-v2-development/REPORT.md) includes all 80 records, failures, model revisions, retrieval policy, and source hashes. Its prompt fingerprint is the snapshot used when that retrieval-only run began; subsequent source-summary changes do not change those measured rankings. The live peer record carries the final prompt fingerprint separately.

## Validation and remaining limits

The full suite passes **53 tests**, plus 13 reported subtests. Added tests cover bank coverage and token limits, numeric-row selection, overview routing, literal segment extraction, missing labels, and missing-bank fallback refusal. Both existing indexes remain usable; no rebuild is needed.

Consolidated metrics, management commentary, and some multi-input operating-leverage requests still have retrieval gaps. Full generated-answer quality, an independent human review, a fresh held-out evaluation, and warmed end-to-end latency remain outstanding. A correct source summary for one development question does not establish general peer-comparison reliability.
