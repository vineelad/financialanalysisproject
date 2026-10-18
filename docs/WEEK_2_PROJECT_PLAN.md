# Week 2 Project Plan: Investor Relations Document Intelligence Assistant

Status: LangChain/LangGraph pipeline, both indexes, and Streamlit UI are available; all 100 tests pass. Recorded v3 strict-label development recall is 93.3% for A/B/C and 100% for D, with 5/5 calculation questions supported. Ten prospective checks and a six-case live source review are recorded in the [accuracy report](reports/ACCURACY_IMPROVEMENT.md), including raw/audited labels and retained model failures. The UI defaults to semantic plus reranking; calculations use validated Python output. The v4 revenue build-up and peer-comparison changes have separate source checks in reports/revenue-build-validation.json; aggregate recall has not been rerun for v4. These small assistant-reviewed results do not establish general answer accuracy or warm latency targets. Independent review and submission steps remain. See the [submission draft](docs/SUBMISSION_DRAFT.md), [demo script](docs/DEMO_SCRIPT.md), and [README.md](README.md).  
Final Week 2 scope: five banks, six official documents, 32 reviewed consumer facts and rebuilt fixed/semantic indexes. See [the handoff](docs/WEEK_2_HANDOFF.md) and separate expanded-corpus reports. Original two-bank results remain historical snapshots.

Prepared: October 18, 2026.

## 1. Recommendation

Build a financial RAG assistant that helps an investor relations analyst compare a focus bank with a peer using cited earnings documents. Start with **JPMorgan Chase versus Bank of America, Q2 2025 versus Q2 2024**, with consumer banking as the required end-to-end demonstration and wealth and corporate banking added after the core pipeline and experiments work.

Choose **Financial Document Intelligence Pipeline RAG (suggested use case 2)** and implement it using **Track 2: Python, LangChain, and a small LangGraph workflow**. The handout distinguishes the use case from the implementation track; selecting financial document intelligence does not itself select code or n8n.

The central project question is: **Can table-aware retrieval produce reliable, cited bank performance comparisons, and how do semantic chunking and reranking change retrieval quality?** This makes your IR idea a focused Week 2 RAG project with measurable results.

### One-line project statement

My RAG app helps investor relations analysts answer year-over-year bank performance and peer comparison questions from a frozen collection of JPMorgan Chase and Bank of America Q2 2025 and Q2 2024 earnings releases, financial supplements, and selected 10-Q disclosures in a local analyst interface, targeting at least 95% claim faithfulness and 90% evidence recall@5, with warm answer latency at or below 15 seconds at p95.

These percentages and latency limits are proposed acceptance targets, not measured results or handout-mandated thresholds.

## 2. What the handout requires

| Expectation | Planned implementation | Evidence to submit |
|---|---|---|
| Define a specific corpus, user, surface, quality target, and latency ceiling | One-liner above and completed framework below | Project documentation |
| Ingest, chunk, embed, store, retrieve, and generate cited answers | Reproducible Python ingestion and query pipeline | Working application, source code, live demo |
| Compare fixed-size and semantic chunking on the same queries | Two independently indexed chunk collections from the same cleaned source snapshot | Chunking comparison report and per-query results |
| Add reranking and measure its impact | Run each chunking strategy with and without a reranker | Four-condition experiment and reranking impact analysis |
| Explain the project and workflow | Record datasets, prompts, iterations, AI coding tool usage, and observations | Google Doc project write-up |
| Demonstrate the final application | Show an answer, a cross-document comparison, source inspection, and an unsupported question | Video no longer than five minutes |
| Share project assets | Repository with setup instructions, evaluation data, configurations, and reports | GitHub link; the use-case section also permits a zip |

The general submission instructions request GitHub, so use GitHub as the primary asset destination. The final write-up must be a **Google Doc**; this Markdown plan is our starting artifact, not the complete submission.

**Optional:** the handout describes a chatbot UI as a bonus. A polished interface, many banks, real-time ingestion, and complex agent autonomy are not prerequisites for completing this use case. The financial use case does not specify an evaluation question count; the 20-question set below is our proposed scope, not a requirement borrowed from another use case.

### Deadline and submission

The supplied handout lists Sunday, October 18, 2026 at **11:59 p.m. Pacific**, equivalent to **Monday, October 19 at 1:59 a.m. Chicago time**, for Builder of the Week eligibility. It permits later submissions for project completion, without Builder of the Week consideration.

Submission form from the handout: <https://forms.gle/Cxad8AnPHBB4sNzw5>.

Prioritize the required pipeline, experiments, report, and recording before optional features. Do not claim completion or quality scores until they have been measured.

## 3. How this develops your original idea

Your Investor Relations Assistant document proposes automating manual peer analysis across consumer, corporate/business, and wealth management, covering operating leverage, efficiency ratios, asset growth, revenue, expenses, and ROA. Keep that business objective, but deliver it in two increments:

| Increment | Scope | Completion criterion |
|---|---|---|
| Required Week 2 core | Two banks; one historical quarter and its prior-year comparison; consumer banking plus consolidated metrics; cited retrieval and calculations | Working pipeline, both chunkers, reranking experiment, evaluation, report, and demo |
| Extension after the core | Wealth and corporate segment comparisons; additional peer; charts and saved briefs | Add only after source definitions and comparability checks pass |

Use a historical snapshot deliberately so the experiment is reproducible. The interface must label Q2 2025 as the selected analysis period and must not describe it as the latest available quarter.

### Important corrections to the original scope

- Earnings releases and financial supplements are separate documents from Forms 10-Q and 10-K. Use quarterly releases and supplements for accessible segment tables, with selected 10-Q disclosures for definitions and reconciliation; a 10-K is optional here.
- Banks do not organize their businesses identically. Preserve each reported segment name and provide a comparison caveat rather than assuming the three business categories are equivalent across banks.
- Keep reported amounts separate from computed ratios and interpretive commentary. Python performs arithmetic; the language model explains evidence and results.
- Revenue, assets, client assets, AUM, loans, and deposits are distinct measures. Never substitute one for another to complete a comparison.
- Return on allocated capital is not ROA. Segment ROA may be unavailable; return an explicit limitation when segment net income or average segment assets are missing.

## 4. Completed RAG framework

Each entry below follows the handout's one-to-two-sentence format.

| Field | Decision |
|---|---|
| Use case | An IR analyst asks a local application for cited bank performance explanations and year-over-year peer comparisons. The first supported path covers consumer banking and consolidated performance. |
| Corpus | Freeze approximately 6–10 English-language releases, supplements, and selected 10-Q documents for JPMorgan Chase and Bank of America covering Q2 2025 and Q2 2024, deduplicating combined release/supplement packages. Official bank IR publications and SEC filings are the source of truth; the project maintains a source manifest. |
| Ingestion + cleaning | Download approved public HTML/PDF sources into a local snapshot, preserve source locations and table structure, and remove repeated navigation, page headers, and footers. Normalize whitespace and units while retaining original values, footnotes, period labels, and reported segment names. |
| Ingestion + freshness | Run ingestion manually for the submitted snapshot and check document hashes on reruns. For a future quarterly refresh, propose ingestion within two business days of publication; freshness is visible through period and ingestion timestamps. |
| Chunking + embedding | Compare fixed 400-token chunks with 60-token overlap against sentence-embedding semantic boundaries with a roughly 150–400-token budget, using `BAAI/bge-small-en-v1.5` in both after the base model proved slow on this CPU-only machine. Preserve table headers and row provenance under both strategies and retain document embedding caches across builds. |
| Retrieve | Use local persistent Chroma collections plus BM25, apply bank/period/segment filters, and fuse dense and lexical rankings using reciprocal rank fusion. Retrieve up to 20 candidates per method, fuse to 20 unique candidates, and return five evidence chunks with or without reranking. |

### Additional operational decisions

- Generation: use one configurable instruction model through the available model provider, keeping the exact model identifier, prompt, temperature, and context budget constant across experiments. Nebius credits are an option mentioned by the handout; verify account access and available model IDs during setup.
- Reranking: start with local `cross-encoder/ms-marco-MiniLM-L-6-v2`; validate model availability, input limits, and runtime on this machine before committing dependencies. Record truncated inputs and never silently drop the table headers needed to interpret a row.
- Implementation: pin tested dependency versions, cache embeddings and downloaded models, and record exact model revisions. If the proposed local models are unavailable, choose compatible alternatives before freezing the evaluation configuration and document the substitution.
- Interface: start with a CLI for the core pipeline; add a small Streamlit analyst screen if time permits. A UI does not block evaluation or submission.
- Tracing: save local JSON run records with configuration, retrieved chunk IDs, citations, timing, and calculated inputs. Hosted tracing is optional.

## 5. Corpus and financial comparability

### Initial source collection

1. Obtain each bank's Q2 2025 earnings release and financial supplement or equivalent results package.
2. Obtain Q2 2024 counterparts to establish prior-year provenance and test cross-document retrieval.
3. Add the Q2 2025 10-Q for each bank where needed for definitions, basis differences, or segment disclosures.
4. Count actual source documents after checking packaging; do not manufacture separate documents when one official package contains both release and supplement.
5. Identify a small gold evidence subset manually before building retrieval. Check revenue and noninterest expense for consumer banking first, then consolidated average assets and net income.

Use a current document's comparative prior-year column when appropriate, and retain older documents to reveal changes in presentation. If prior-year amounts were recast, prefer explicitly comparable recast figures and cite the recast source; do not mix original and recast amounts silently.

### Segment mapping

| Analytical category | JPMorgan Chase reported segment | Bank of America reported segment | Rule |
|---|---|---|---|
| Consumer | Consumer & Community Banking | Consumer Banking | Core comparison with disclosed scope caveat |
| Wealth | Asset & Wealth Management | Global Wealth & Investment Management | Extension; AUM and client-asset definitions need review |
| Corporate/business | Commercial & Investment Bank | Global Banking; Global Markets reported separately | Extension; no automatic one-to-one equivalence or invented combined segment |

These names are supported by the official [JPMorgan Q2 2025 financial supplement](https://www.sec.gov/Archives/edgar/data/19617/000001961725000518/a2q25erfex992supplement.htm) and [Bank of America Q2 2025 results package](https://investor.bankofamerica.com/regulatory-and-other-filings/select-sec-filings/content/0000070858-25-000254/bac063025ex991.htm). Their differences motivate the mapping rules above; the mapping is our analytical design, not a claim of identical business scope.

### Source and fact metadata

For every source: `document_id`, bank, title, document type, official URL, publication date, reporting periods, local path, file hash, and ingestion timestamp.

For every chunk: source document ID, chunk strategy, stable chunk ID, page or HTML section anchor, table and row IDs where applicable, reported segment, period labels, and units. Give multi-period tables all relevant period tags so filters do not exclude valid prior-year evidence.

For extracted numeric facts: metric name, raw value, normalized value, currency/scale, quarter versus year-to-date, average versus period-end, reported/adjusted/managed basis, source location, and footnote references. Missing metadata must block incompatible calculations.

### Calculation policy

These are explicit project calculation conventions, to be checked against each bank's reported definitions before use:

| Metric | Calculation | Evidence and limitation |
|---|---|---|
| Revenue or expense YoY growth | `(current / prior - 1) × 100` | Same metric, segment scope, period length, units, and reporting basis; zero prior values make the calculation undefined |
| Operating leverage | Revenue YoY growth minus expense YoY growth | Express in percentage points; label as project-calculated unless a matching bank definition is cited |
| Efficiency ratio | Noninterest expense / applicable net revenue × 100 | Prefer a reported ratio; distinguish a derived ratio if bank-specific adjustments differ |
| Asset growth | `(current assets / prior assets - 1) × 100` | Compare average with average or period-end with period-end; keep consolidated and segment measures separate |
| Quarterly ROA | Quarter net income / average total assets × an explicit annualization factor × 100 | Prefer reported ROA; any derived value states the convention, such as simple ×4, and is not assumed to match the bank's day-count method |

For percentage metrics, show year-over-year movement in percentage points or basis points, not as dollar growth. Show input citations, formula, rounding, and result for every derived metric. Refuse calculations with missing or incompatible inputs and qualify comparisons with nonpositive prior values rather than presenting misleading growth percentages.

## 6. Pipeline and answer behavior

```text
Official documents -> frozen source manifest -> text/table extraction + validation
                                              |
                              shared cleaned source representation
                                  /                         \
                        fixed-size chunks             semantic chunks
                        Chroma + BM25                 Chroma + BM25
                                  \                         /
Question -> bank/period/metric scope -> chosen index -> hybrid candidate retrieval
         -> optional reranking -> evidence sufficiency and compatibility checks
         -> supported calculations -> cited answer or explicit evidence limitation
         -> saved retrieval trace and evaluation record
```

Keep LangGraph small: resolve scope, retrieve, optionally rerank, check evidence, calculate when needed, and answer or abstain. Avoid autonomous browsing and open-ended agent loops during evaluation.

### Table-aware ingestion

- Prefer official HTML tables where available; use text-based PDF extraction when HTML is unavailable.
- Preserve row/column relationships and emit readable records such as bank, segment, metric, period, value, unit, and source location.
- Repeat table title and column headers for row groups, keeping relevant footnotes attached or retrievable.
- Apply the same table serialization and provenance rules to both chunking conditions. Differences in table preprocessing must not be mistaken for a chunking improvement.
- Use sentence-embedding similarity to decide semantic boundaries in narrative text. Heading-only splitting is not the semantic experiment.
- Split large tables into bounded row groups with repeated headers; inspect samples manually to catch shifted columns, lost negative signs, and quarter/YTD confusion.

### Answer contract

Every response provides a direct answer, supporting figures with units and periods, source links with page/section references, and relevant limitations. Each quantitative claim has supporting citations; computed claims cite all input facts and show the calculation.

Separate reported explanations from our interpretation. An observation such as expenses growing faster than revenue does not prove a cause; attribute management explanations to the source.

When the bank, period, or metric is ambiguous, ask for clarification or state a visible supported assumption. When evidence is absent, incompatible, or insufficient, say what is missing instead of inventing an answer; treat document contents as evidence, never as instructions to change application behavior.

Example proposed instruction:

> Answer only from the retrieved financial evidence and validated calculation outputs. Preserve each bank's reporting basis, segment scope, period, and units. Cite every material financial claim. Explain missing inputs and comparability limits, and do not infer unavailable metrics or causal explanations.

## 7. Controlled evaluation

### Four configurations

| Run | Chunking | Retrieval | Reranking | Final evidence budget |
|---|---|---|---|---|
| A | Fixed-size | Hybrid | Off | Top 5, same token cap |
| B | Semantic | Hybrid | Off | Top 5, same token cap |
| C | Fixed-size | Hybrid | On | Top 5, same token cap |
| D | Semantic | Hybrid | On | Top 5, same token cap |

Compare B−A and D−C for chunking effects, and C−A and D−B for reranking effects. Freeze corpus, queries, embedding model, generator, prompt, filters, fusion settings, candidate budget, and final evidence token cap; avoid changing several factors at once.

Use four development questions to tune extraction, semantic thresholds, and reranker settings, then freeze the configurations before running a separate 20-question evaluation set. Review gold labels before inspecting experiment outcomes; disclose any later corrections and rerun all affected conditions.

### Proposed 20-question evaluation set

Fill in gold values and exact evidence locations from the source documents before running the benchmark. These are question templates, not claims that all requested facts are available.

| ID | Question | Main behavior tested |
|---|---|---|
| 01 | What was JPMorgan consumer banking revenue in Q2 2025? | Single-table lookup |
| 02 | What was Bank of America consumer banking noninterest expense in Q2 2025? | Metric and segment matching |
| 03 | What was JPMorgan consumer banking revenue in Q2 2024? | Prior-year retrieval |
| 04 | What was Bank of America consumer banking revenue growth from Q2 2024 to Q2 2025? | Cited arithmetic |
| 05 | What was JPMorgan consumer banking expense growth over the same period? | Expense extraction and arithmetic |
| 06 | What was JPMorgan consumer banking operating leverage under the project definition? | Multiple inputs |
| 07 | What was Bank of America consumer banking operating leverage under that definition? | Multiple inputs |
| 08 | Which consumer segment had stronger operating leverage, and what limits the comparison? | Cross-bank reasoning |
| 09 | What consumer efficiency ratio does Bank of America report, and how is it defined? | Ratio and definition evidence |
| 10 | What consumer efficiency or overhead ratio does JPMorgan report, and on what basis? | Terminology and basis |
| 11 | What were JPMorgan's consolidated average total assets in Q2 2025 and Q2 2024? | Average versus period-end |
| 12 | How did Bank of America's consolidated total assets change year over year on a consistent basis? | Asset comparability |
| 13 | What consolidated ROA is reported for JPMorgan, and is it annualized? | Reported ratio provenance |
| 14 | What does management say drove consumer revenue or expense changes at either bank? | Grounded narrative explanation |
| 15 | How does JPMorgan's commercial segment scope differ from Bank of America's? | Cross-document comparability caveat |
| 16 | What was the latest quarter's efficiency ratio? | Ambiguous bank and period; clarify |
| 17 | Give Q2 2026 consumer revenue from this Q2 2025/2024 corpus. | Unsupported period; abstain |
| 18 | What will JPMorgan consumer revenue be next quarter? | Unsupported forecast; abstain |
| 19 | Calculate segment ROA using return on allocated capital as ROA. | Reject incompatible metric substitution |
| 20 | What were the CEO's private internal targets for the consumer business? | Unavailable evidence; abstain |

If a presumed answerable question lacks source evidence, label it unanswerable before freezing the set and preserve adequate coverage of actual lookups and calculations. Do not invent a gold answer to preserve the initial question wording.

Each gold record includes question, expected behavior, relevant bank/period, required evidence units, acceptable answer or formula, units, tolerance, and a reason for refusal where relevant. Define evidence units as source table rows/cells or narrative spans independent of chunk boundaries so the two chunkers can be scored fairly.

### Metrics and acceptance targets

| Metric | Measurement | Proposed target |
|---|---|---|
| Evidence recall@5 | Required gold evidence units covered by the five retrieved chunks, averaged over answerable questions | At least 90% |
| Retrieval precision@5 | Relevant chunks / returned chunks, with relevance labels defined before scoring | Report for all four runs |
| Claim faithfulness | Supported factual claims / all factual claims in substantive answers, manually reviewed against citations | At least 95% |
| Numeric accuracy | Correct numeric answers under predeclared rounding tolerances / expected numeric answers | At least 95%, with counts |
| Citation coverage | Material factual claims with a citation to supporting evidence / all material factual claims | 100% |
| Unsupported-question handling | Correct abstentions on gold unanswerable questions | All designated cases |
| Ambiguity handling | Correct clarification or explicit supported assumption for ambiguous cases | All designated cases |
| Answer coverage | Answerable questions receiving substantive supported answers / answerable questions | At least 90% |
| Latency | End-to-end warm query time, including reranking and generation | p95 at or below 15 seconds |
| Cost and resource use | Token use and provider cost where available; local model load time and memory observations | Report actual values |

Report denominators and raw counts alongside percentages; this is a small evaluation. Abstentions do not count as faithful substantive answers, and answer coverage prevents an always-refuse system from appearing successful. Score retrieval only where gold evidence exists, and report abstention behavior separately.

Record candidate evidence recall@20 as a diagnostic: a reranker cannot recover facts absent from its candidate pool. Measure baseline and reranked answers as well as retrieval, since a ranking improvement may not improve answer quality.

Run each of the four configurations on all 20 questions for 80 initial outputs. Warm model caches first, randomize configuration order, and repeat timed queries three times if feasible; report cold-start time separately and treat p95 from a small sample as preliminary.

### Comparison report

Include a results table for A–D, per-question scores, absolute metric changes in percentage points, latency/cost tradeoffs, and at least three inspected successes or failures. Save actual traces showing whether errors came from extraction, chunk boundaries, filtering, candidate retrieval, reranking, calculations, or generation.

Do not promise semantic chunking or reranking will win. A negative result with controlled evidence and a useful explanation still satisfies the experimental objective.

## 8. Build sequence and checkpoints

| Order | Work | Exit condition |
|---|---|---|
| 1 | Freeze core bank/period scope and source inventory | Official sources saved, manifest complete, consumer evidence verified |
| 2 | Build and inspect shared text/table extraction | Hand-checked sample values, units, periods, negatives, headers, and citations match originals |
| 3 | Implement fixed-size ingestion, hybrid retrieval, and grounded answering | One lookup, one derived result, and one unsupported question work end to end |
| 4 | Implement semantic ingestion and reranking toggle | Both chunk collections searchable; A–D selectable by configuration |
| 5 | Finalize gold set and run evaluation | Saved 80 outputs, labels, traces, scores, and timing observations |
| 6 | Review failures and select demo configuration | Comparison report explains results and remaining limitations |
| 7 | Package documentation and assets | Clean setup instructions, prompts, configurations, report, Google Doc draft content |
| 8 | Record and submit | Video under five minutes, accessible GitHub link, Google Doc, and submission form |

If time is tight, keep the corpus small, defer extra segments, and demonstrate through the CLI. Preserve both chunking strategies, the reranking experiment, citations, and the report because those are central requirements. Any bug fix after evaluation must trigger reruns of affected configurations; do not mix results from different code versions.

### Proposed repository layout

```text
WEEK_2_PROJECT_PLAN.md
README.md
.env.example
requirements.txt
config/
  experiment.yaml
data/
  source_manifest.csv
  raw/
  processed/
src/
  ingest.py
  chunking.py
  retrieval.py
  calculations.py
  workflow.py
  cli.py
eval/
  dev_questions.jsonl
  gold_questions.jsonl
  run_evaluation.py
  results/
reports/
  chunking_and_reranking_comparison.md
  project_writeup.md
  demo_script.md
```

Keep credentials out of code and committed artifacts. Store index rebuild instructions and source hashes; large raw downloads and generated indexes can remain local with reproducible download steps.

## 9. Submission story and demonstration

### Google Doc outline

1. Business problem and your IR assistant idea.
2. One-liner and completed RAG framework.
3. Dataset inventory, period selection, and segment comparability decisions.
4. Pipeline, table handling, chunking implementations, and retrieval settings.
5. Actual prompts, graph instructions, and AI coding tools used, with your review and validation steps.
6. Four-condition experiment, gold questions, metric definitions, and measured results.
7. Iterations, failure analysis, lessons, and limitations.
8. Demo link, code link, and next steps.

### Suggested video sequence: about 4 minutes 45 seconds

| Time | Demonstration |
|---|---|
| 0:00–0:35 | Describe the manual IR workflow, target user, and frozen corpus |
| 0:35–1:25 | Ask a consumer revenue/expense question and inspect its source evidence |
| 1:25–2:15 | Run a year-over-year peer comparison; show input citations, formula, and scope caveat |
| 2:15–2:50 | Ask an unavailable-period question and show the evidence limitation |
| 2:50–4:00 | Show A–D results, one retrieval example, and the measured tradeoff |
| 4:00–4:45 | Explain AI coding tool usage, validation, remaining limitations, and repository setup |

### Final completion checklist

- [ ] Core financial RAG pipeline runs from documented setup instructions.
- [ ] Corpus provenance and exact bank/period scope are visible.
- [ ] Fixed-size and semantic chunking are both implemented and compared.
- [ ] Reranking impact is measured against matching baselines.
- [ ] Gold questions, results, failure analysis, and configuration details are saved.
- [ ] Financial claims and calculation inputs have verifiable source citations.
- [ ] Unsupported and incompatible requests produce explicit limitations.
- [ ] Google Doc includes datasets, prompts, iterations, learnings, and AI coding workflow.
- [ ] Demo video is five minutes or less and shows the working application live.
- [ ] GitHub assets and submission links are accessible to reviewers.

## 10. Reference material

Primary assignment and idea sources, read from this workspace:

- [Week 2 Project Handout ( Oct 2026 ).docx](./Week%202%20Project%20Handout%20%28%20Oct%202026%20%29.docx)
- [Investor Relations Assistant.docx](./Investor%20Relations%20Assistant.docx)

Official corpus starting points:

- [JPMorgan Chase quarterly earnings archive](https://www.jpmorganchase.com/ir/quarterly-earnings)
- [JPMorgan Chase Q2 2025 financial supplement](https://www.sec.gov/Archives/edgar/data/19617/000001961725000518/a2q25erfex992supplement.htm)
- [Bank of America Q2 2025 results and supplement](https://investor.bankofamerica.com/regulatory-and-other-filings/select-sec-filings/content/0000070858-25-000254/bac063025ex991.htm)
- [Bank of America Q2 2025 Form 10-Q](https://investor.bankofamerica.com/regulatory-and-other-filings/select-sec-filings/content/0000070858-25-000268/bac-20250630.htm)
- [LangChain learning documentation](https://docs.langchain.com/oss/python/learn)
- [LangChain embedding integration documentation](https://docs.langchain.com/oss/python/integrations/embeddings)

The handout's linked solution folders were not consulted. This plan is based on your idea, the assignment requirements, and the official sources above.

## Metric registry and analyst coverage

The registry and checklist foundation is implemented. See [metric contracts](docs/METRIC_REGISTRY.md) and the [28-family coverage checklist](docs/ANALYST_COVERAGE.md). The registry defines 58 metrics; existing source-row matching and reviewed consumer fact loading use it. New calculation routes remain separate implementation work. Next, freeze narrow source-labelled cases for both-bank reported profitability before attempting adjusted returns, then extend deposits, credit and capital. The coverage checklist is separate from frozen evaluation labels.
