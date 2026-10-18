# Investor Relations Document Intelligence Assistant

Content for the required Google Doc. Fill the submission links and review the recorded limitations before sharing. Creating this local file does not create a Google Doc or submit the project.

## Problem and scope

Investor relations analysts compare financial performance across banks, but earnings documents use complex tables, different segment names, and different reporting bases. This application retrieves cited evidence for Bank of America, JPMorgan Chase, Wells Fargo, Citi and Capital One. Reviewed consumer revenue/expense, growth and operating leverage form its calculation path; selected consolidated metrics remain narrower lookup checks.

The final build uses six Q2 2025 documents with selected Q2 2024 comparison figures. It is a historical snapshot. The original controlled experiment used three documents and two banks; the expansion has a separate frozen evaluation. Wealth and broader corporate analysis remain extensions.

## Dataset and provenance

- Bank of America Q2 2025 earnings release.
- Bank of America Q2 2025 supplemental information.
- JPMorgan Chase Q2 2025 earnings supplement.
- Wells Fargo Q2 2025 earnings release PDF.
- Citi Q2 2025 earnings release and segment tables.
- Capital One Q2 2025 earnings release and financial supplement.

Official URLs are in `config/sources.json`. The report export includes source hashes. Final ingestion produced 3,470 blocks; the fixed index contains 3,422 chunks and the semantic index 3,426. Earlier two-bank counts and source hashes remain in their saved reports.

Thirty-two reviewed consumer facts are recorded in `data/reviewed_facts.json`, with original and expanded provenance in `data/fact_provenance.json` and `data/peer_fact_provenance.json`. Selected PDF text rows retain original page and column order, and their values are checked before being approved. The coding assistant reviewed these against the original cached HTML; they have not received an independent human financial audit. Gold evidence annotations include verified equivalent source rows where available.

## Architecture and tools

The local Python application uses LangChain Documents, embedding and retriever interfaces, Chroma integration, and an LCEL prompt/model/parser chain. LangGraph connects scope resolution, hybrid retrieval, deterministic calculations, and cited answering or refusal. Streamlit supplies the optional analyst interface.

Local BGE-small embeddings and BM25 are fused with reciprocal rank fusion. The cross-encoder reranker is optional. Fixed and semantic chunking share identical table-row treatment; only narrative boundaries differ. A local embedding cache avoids recomputing unchanged document vectors. Exact model revisions and dependency versions are recorded.

Nebius supplies generation using `Qwen/Qwen3-30B-A3B-Instruct-2507`. One live lookup passed: the model returned BAC consumer revenue of $10,813 million for Q2 2025 with citations, matching the source-reviewed amount. The result and token usage are in `reports/live-generation-smoke.json`. **Pending:** broader generated-answer review, cost review, and warm end-to-end timings. LangSmith tracing is optional and disabled for the local experiment. Pinecone is not needed for this Chroma implementation.

## Prompt and calculation contract

The system prompt in `ir_assistant/generation.py` requires the model to use only retrieved evidence and validated calculations, preserve bank/segment/period/units/basis, cite factual claims, and state missing evidence. It treats retrieved text as untrusted evidence and requests structured JSON. The report records the prompt fingerprint.

Python calculates year-over-year growth and operating leverage (revenue growth minus expense growth, in percentage points). Every reviewed input must be supported by an actually retrieved row. The pipeline rejects incompatible periods, units, bases, missing facts, and substituting return on allocated capital for ROA. It does not compute unsupported asset growth or infer management explanations.

## Iterations and AI coding assistance

The coding assistant helped interpret the assignment, draft the project plan, implement the pipeline and interface, inspect financial tables, and run checks. Validation uncovered hidden text layers in image-like exhibits, duplicated column spans, quarter/YTD ambiguity, Windows Unicode issues, and the need for conservative financial calculations.

The local embedding model was reduced from the initial base-model proposal to BGE-small for this CPU machine. Custom table handling retains row provenance. Operating-leverage queries expand into revenue and expense queries, but this does not guarantee complete final evidence. Experiments retain original failures and labels; any source-supported annotation corrections are versioned and explicitly disclosed.

## Experiments and measured results

The earlier two-bank experiment evaluated twenty questions across fixed, semantic, fixed with reranking, and semantic with reranking. Fifteen have gold evidence and five test scope handling. The following recorded v3 results use that earlier snapshot and identical budgets in all conditions; they are not measurements of the final five-bank corpus.

| Configuration | Mean evidence recall @5 | Mean annotated precision @5 | Mean candidate recall @20 | Correct scope handling |
|---|---:|---:|---:|---:|
| Fixed | 93.3% | 32.0% | 100% | 5/5 |
| Semantic | 93.3% | 33.3% | 100% | 5/5 |
| Fixed + reranking | 93.3% | 30.7% | 100% | 5/5 |
| Semantic + reranking | 100% | 32.0% | 100% | 5/5 |

Retrieval means use 15 answerable questions per condition. Annotated precision is conservative: it scores exact gold evidence and may miss other relevant passages. Table treatment is identical across chunkers; the remaining difference is the management-explanation case, whose evidence D retains. All five arithmetic questions now retrieve their required inputs. These questions informed development, so this is not an unseen benchmark.

The earlier 66.7% result was below target. Fixes increased the weight of row labels, expanded metric terms, distinguished consolidated and segment scope, separated average from period-end assets, prioritized both periods and all required metrics, and improved narrative retrieval. No gold evidence IDs or amounts were placed in retrieval logic. The same indexes and budgets were retained during that earlier tuning phase. The five-bank expansion uses new indexes and recorded query-dependent budgets.

A scoring defect also needed correction: one-period alternative rows could satisfy a two-period calculation unit. The versioned strict gold assigns separate input-period units. Original files remain intact. Rescoring the v2 saved traces with the identical strict labels gives 65.8% recall for A/B and 60.8% for C/D; current results are 93.3% and 100% as above. Calculation readiness improves from 2/5 to 5/5 per condition. See reports/strict-baseline-comparison.json and reports/retrieval-v3-development/REPORT.md.

### Prospective validation and annotation audit

Ten additional questions were frozen before inspecting their retrieval: eight answerable questions cover new metrics and wording, and two cover scope handling. They use the same corpus and assistant-reviewed original HTML cells. Semantic plus reranking was selected from development results before the prospective scores were inspected.

Raw recall was 87.5% without reranking and 75% with reranking. The apparent misses retrieved equivalent consolidated net-income and ROE rows absent from the original annotations. A post-run audit verified the original HTML cells and added those alternatives in a separately versioned file, without changing questions, expected values, retrieval code, or rankings. All eight answerable cases then have their required evidence in every condition; both scope cases pass. Both raw and audited scores are preserved. This small same-corpus sample with an annotation audit is not a clean independent 100% accuracy benchmark.

### Live answer review and safeguards

Retrieval recall did not prevent answer errors. An initial live check caught invented JPM intermediate growth rates and a refusal despite a supporting narrative quote. Those answers remain preserved as failures. Calculations now render the actual Python-validated inputs, component growth rates, result, and citations directly, without calling the model. Explicit reported explanations are highlighted for the model, with a cited source-excerpt fallback if it refuses despite that evidence. Segment-name omissions retain the earlier source-summary fallback.

The repeated six-case live check passed assistant source review for peer operating leverage, JPM average assets, BAC period-end assets, JPM ROA, BAC management's stated revenue driver, and BAC consumer net income. JPM leverage is 6.47% revenue growth minus 4.59% expense growth, yielding 1.88 percentage points. BAC is 5.95% minus 1.89%, yielding 4.06 percentage points. The comparison preserves reporting bases and does not assume identical segment scope.

The final batch used 15,012 tokens across five hosted calls; the calculation used zero model tokens. The initial failed batch used 19,318 tokens and is retained separately. These figures are not the full project bill. The suite passes 100 tests. Full responses, citation excerpts, review notes, and limits are in reports/live-financial-validation.json and reports/ACCURACY_IMPROVEMENT.md.

The selected-case results meet the proposed retrieval target on the measured sets, but general 95% faithfulness/accuracy and 15-second warm p95 remain unproven. A larger independently reviewed evaluation is still needed. Empty manual quality columns in retrieval-only CSV files are unmeasured values.

A subsequent real-user revenue-comparison question revealed a false refusal outside the selected live sample: the model incorrectly questioned whether the retrieved consumer-segment totals were consumer revenue. Covered reported revenue/expense lookups now render source-reviewed facts only when their supporting rows are retrieved, and compute comparisons with Decimal rather than relying on the model to reconcile labels. The exact question returns JPM $18,847 million versus BAC $10,813 million, an $8,034 million difference (74.3% relative to BAC), with reported segment names, bases, citations, and an unadjusted-comparison caveat. This regression is saved in reports/reported-revenue-regression.json. Missing evidence still cannot be supplied from the fact store alone. This failure reinforces the limits of the earlier small sample; it does not retroactively make that sample representative.

## Final five-bank behavior and validation

The analyst selects a base bank. General comparison questions include supported peers, named peers narrow the result, and single-bank lookups and explicit same-bank time comparisons stay focused. Each peer percentage uses the selected base as its denominator. Missing peer evidence is stated explicitly and cannot be replaced with a different segment. Bank identity and aliases are centralized in `config/banks.json`.

Capital One Consumer Banking is separate from its Credit Card business; calculations do not remove acquisition effects. Wells Fargo and Citi figures are labelled as reported rather than silently asserted to be FTE. The registry contains 58 metric definitions and a 28-family coverage checklist. Adding a definition does not enable an unreviewed calculation.

The expansion freezes 20 narrow cases before retrieval inspection: 18 answerable and two scope checks. These are assistant-authored on overlapping financial topics, not an independent benchmark. All four configurations use identical query-dependent budgets; five-bank questions receive more candidates/context and enough final evidence slots for their inputs. The report records actual limits rather than calling every score recall@5. See `reports/five-bank-retrieval/REPORT.md` and `reports/five-bank-answer-validation.json`. Original two-bank reports and corpus/index metadata remain retained.

The initial expanded answer checks passed 16/20 and exposed Citi acronym/segment retrieval misses. Those failures are retained in `reports/five-bank-initial-answer-validation.json`. Source-segment heading checks and USPB query aliases correct the retrieval path; the frozen questions and expected source values remain unchanged. Subsequent results are development regressions, not unseen validation. The post-fix exact-ID answer check passed 18/20; two remaining flags were omitted equivalent BofA overview rows already reviewed before the freeze. A separate audited label file rescores the identical saved answers and retrieval. Raw and audited records remain retained. With audited labels, all 20 narrow saved checks pass, and all four configurations have full required evidence on the 18 answerable cases. Raw recall is 98.9% for A/B and 97.8% for C/D. Equal audited recall on this table-heavy set does not demonstrate a chunking or reranking advantage. These are not general answer-accuracy scores.

## Learnings and remaining work

The table-heavy corpus produces almost identical fixed and semantic indexes, limiting conclusions about semantic narrative chunking. Reranking can improve one result while removing a different required input. An explicit calculation refusal prevents an unsupported answer but still counts as an answer-coverage failure.

Some extracted expense rows inherit initial revenue headers; these rows are excluded from verified alternate calculation evidence. Future work should repair subsection headers, improve metric coverage for multi-input questions, expand narrative sources, and evaluate on newly frozen questions. Warm end-to-end latency and hosted token costs remain to be measured with generated answers.

A final BofA management-explanation request exercised the configured Nebius/Qwen generation chain and passed source review: consumer revenue increased 6% to $10.8 billion, primarily driven by higher NII. It used 3,604 tokens in one request; these are not total project usage figures. The full trace is in `reports/final-provider-check.json`.

## Submission links to fill

- GitHub repository: pending publication.
- Live demonstration video (under five minutes): pending recording.
- This content in a Google Doc: pending creation and sharing.
- Comparison report: `reports/retrieval-v3-development/REPORT.md`; methodology and audits: `reports/ACCURACY_IMPROVEMENT.md`.

The repository includes the README, implementation, version lock, reviewed questions, source/fact provenance, exported experiment results, and a recording script in `docs/DEMO_SCRIPT.md`. Raw documents and generated indexes are reproducible local artifacts excluded from version control; credentials must remain excluded.
