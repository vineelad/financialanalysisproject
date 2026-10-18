# Investor Relations Document Intelligence Assistant

A local financial-document RAG project for Gen Academy Week 2. It compares fixed-size and semantic chunking, with and without reranking, while retaining source citations and explicit financial calculation rules.

## Current status

The final narrow five-bank answer checks pass 20/20 with audited evidence labels, retaining the initial 16/20 and post-fix raw 18/20 records. No saved answers or rankings changed in the annotation audit. A separate final model-written explanation passed in one Nebius request (3,604 tokens). These checks do not establish general accuracy.

For the final build, run and submission steps, see [WEEK_2_HANDOFF.md](docs/WEEK_2_HANDOFF.md). Expanded experiment results are in [the five-bank report](reports/five-bank-retrieval/REPORT.md), with separate [narrow answer checks](reports/five-bank-answer-validation.json).

The [financial metric registry](docs/METRIC_REGISTRY.md) defines 58 metrics and supplies existing retrieval labels and reviewed-fact validation. The [28-family analyst coverage checklist](docs/ANALYST_COVERAGE.md) records 0 fully validated families, 7 with partial existing checks and 21 unvalidated; these are coverage counts, not answer accuracy. Definitions and planned formulas do not enable new calculations. Refresh the checklist with `python scripts/report_analyst_coverage.py`; this performs no provider calls.

Dependencies are installed and `prepare` has successfully extracted **3,470 blocks from six official documents across five banks**. Both local indexes are built: **3,422 fixed-size chunks and 3,426 semantic chunks**. A local Streamlit analyst UI is available, and all **100 tests pass**, including default answer generation, readable citations, financial result tables, metric/period coverage, deterministic arithmetic, and a mocked chat-provider request.

The recorded v3 two-bank retrieval experiment reached **93.3% evidence recall in A/B/C and 100% in D (semantic + reranking)** on 15 answerable development questions, with all five scope cases correct per condition. A versioned label correction requires both periods for numeric calculations; saved v2 traces were rescored with the same strict labels for a fair comparison. All five calculation questions now have their required inputs. See the [accuracy report](reports/ACCURACY_IMPROVEMENT.md) for the comparison, retained earlier results, and limitations. The UI defaults to semantic chunking with reranking.

Ten prospective same-corpus checks were also frozen before inspecting retrieval. After a source audit added two unannotated equivalent rows, all eight answerable cases have required evidence in every condition and both scope cases pass. **Raw scores and audited scores are both retained**; this small assistant-authored sample is not an independent 100% answer-accuracy benchmark.

A six-case live source review passed after catching and fixing model-written arithmetic and an unnecessary refusal. Calculations now render Python-validated inputs, components, results, and citations without a model call. Narrative answers can fall back to a cited excerpt when an explicit reported cause is present. [The live review](reports/live-financial-validation.json) retains the earlier failed answers as well. Broader generated-answer faithfulness and warm p95 remain unmeasured.

A later user-reported consumer-revenue comparison exposed another model refusal despite correct retrieved evidence. Covered consumer revenue/expense lookups now use reviewed facts only when their actual supporting rows are retrieved, preserving segment names, periods, units, and bases. Cross-bank differences use Decimal arithmetic, with a comparability caveat. [The exact-question regression](reports/reported-revenue-regression.json) verifies this route; the four added tests use independent fixture values and reject missing-bank, wrong-period, and unsupported-metric substitutions. Cached UI workflows are refreshed after backend edits.

Consumer-revenue build-up questions now retrieve net interest income, noninterest income/revenue and reported total revenue for each bank. Python checks matching bank, segment, quarter, units and basis, then verifies the sum before stating an equation. Peer comparisons name the denominator for both percentage directions and show the ratio; zero or negative bases do not produce misleading percentage/ratio claims. Build-up questions can retain six source rows for two banks within the existing token budget. The reviewed store now contains 32 facts across five banks. Reproduce them with `python scripts/prepare_reviewed_dataset.py --facts-only` followed by `python scripts/prepare_peer_facts.py`, without changing evaluation questions. [Three end-to-end source checks](reports/revenue-build-validation.json) cover the original comparison, the peer build-up and BAC Q2 2024, with zero hosted-model tokens. The earlier evaluation reports remain snapshots of their recorded policies; no new aggregate recall claim is made for v4.

Try: **Explain the consumer revenue build-up for Bank of America and JPMorgan Chase in Q2 2025 and compare them.** Routine comparison answers stay concise. Accounting questions use the generation path and may explain funding allocations, FTE or managed basis only from retrieved disclosures. The policy prohibits inferring internal transfer rates from asset-allocation notes, equating managed basis with FTE alone, or calling a consumer FTE impact immaterial from a firmwide adjustment. These rules do not add missing accounting disclosures to the corpus or independently validate a model's explanation.

Real-document inspection led to fixes for image-exhibit text layers, column-span duplication, period headers, Windows Unicode output, and consumer/quarter retrieval scope. The initial two-bank review recorded eight revenue/expense facts and original HTML cell checks; later build-up and peer reviews expanded the fact store to 32 entries. New-bank original-cell/PDF checks are in `data/peer_fact_provenance.json`. One live Nebius/Qwen lookup succeeded and returned the source-verified BAC consumer revenue of $10,813 million with citations. Its usage and result are saved in [the smoke-test record](reports/live-generation-smoke.json). Full generated-answer review remains pending. Keep credentials private and out of editor context and submissions.

The [live generation development checks](reports/GENERATION_VALIDATION.md) additionally verified BAC revenue growth (5.95%), JPM operating leverage (1.88 percentage points with reranking), unsupported-period refusal, and ambiguity handling. The peer segment comparison failed and remains documented. A calculation citation-mapping bug was fixed without relaxing validation. These checks do not establish full answer-quality targets.

The later [peer improvement](reports/PEER_IMPROVEMENT.md) fixes overview retrieval and preserves available bank/metric coverage. All 12 local peer evidence checks pass. Incomplete model-written segment answers use a cited source summary listing the retrieved reported labels, including BAC Global Markets; saved records identify this mode as `source_summary`. The original failures remain available for comparison.

The final source inventory adds the Wells Fargo Q2 2025 earnings PDF, Citi earnings release with segment tables, and Capital One release with financial supplement to the original three documents. Calculations retain Consumer Banking, Consumer & Community Banking, Consumer Banking and Lending, and US Personal Banking as reported names. Capital One Credit Card is a separate segment; acquisition effects are not normalized.

## Run the local demo UI

From the project folder in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open <http://localhost:8501> in your browser. Keep the terminal running; press Ctrl+C there to stop the app. The server binds to this machine's loopback interface.

- **Ask a question:** select a base bank, enter a question and reporting quarter, then click **Ask**. Peer percentage comparisons use the selected bank as the denominator, with the peer/base ratio shown in the same direction. Lookups without a named bank use the selected bank; a general comparison uses all available peers by default; naming a peer narrows the comparison. Explicit single-bank lookups retain the requested bank. The example buttons are removed. Each result records its submitted base bank; editing the form does not run another query. Answers appear by default when a provider is configured; calculations appear as financial result tables. Download the answer as Markdown.
- **Supporting sources:** each source has a one-line description and an original-document link. Raw excerpts, calculation input tables, technical settings, document inventories, and experiment screens are excluded from the analyst view.
- **Project evaluation:** run controlled experiments through the CLI and use the exported reports for the assignment and demo. The analyst UI uses semantic chunking plus reranking.

Answers are the default when `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` are configured in `.env`. Without a provider, the app explains that written answers are unavailable and returns supporting-source links only. Old source-only results require resubmitting the question to produce an answer; editing a question does not silently make paid calls. The first query may download the local reranker. Each question is independent; previous questions are not passed as chat history. Ordinary lookups and explanations may use the provider; validated calculations run locally.

For the video, follow [the recording script](docs/DEMO_SCRIPT.md): demonstrate a lookup with a source link, a validated calculation, a peer question, an unavailable-period refusal, and actual experiment results. The [Google Doc content draft](docs/SUBMISSION_DRAFT.md) is ready for completion after generated-answer review. Use the separate final five-bank reports for the expanded corpus and the retained earlier reports for development history.

## LangChain + LangGraph implementation

| Layer | Component | Code |
|---|---|---|
| Source documents | LangChain `Document` objects with stable row IDs and scalar-encoded provenance | `ir_assistant/documents.py` |
| Embeddings | Custom LangChain `Embeddings` adapter retaining local BGE weights and SQLite caching | `ir_assistant/embedding.py` |
| Dense indexing and retrieval | `langchain_chroma.Chroma` using the existing persistent collections | `ir_assistant/retrieval.py` |
| Hybrid candidates | Custom LangChain `BaseRetriever` fusing dense and BM25 rankings | `ir_assistant/retrieval.py` |
| Answer generation | `ChatPromptTemplate` → configured `ChatOpenAI` adapter → `PydanticOutputParser`, composed with LCEL runnables | `ir_assistant/generation.py` |
| Workflow | LangGraph `StateGraph` for scope, retrieval, calculation, answering, and abstention branches | `ir_assistant/workflow.py` |

The `ChatOpenAI` class is the configurable protocol adapter: it sends requests to `LLM_BASE_URL`, which can be a compatible provider such as Nebius. It does not require an OpenAI account when another provider is configured. Selected Nebius/Qwen responses were previously source-reviewed; the final covered numeric routes run locally. This does not establish arbitrary generated-answer accuracy.

Table-aware chunking, reciprocal rank fusion, financial validation, and arithmetic remain custom Python because these implement the project experiment and financial rules. The earlier framework refactor retained the original index conventions. The final five-bank expansion rebuilt both indexes; original two-bank snapshots and reports remain retained.

## Optional LangSmith

LangSmith is the hosted tracing/evaluation service; LangChain and LangGraph run locally without buying credits. Hosted tracing is disabled by default. To enable it deliberately, add these values to your ignored `.env`:

```dotenv
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_PROJECT=ir-assistant-week2
```

Traces can include questions, retrieved financial excerpts, prompts, and answers. The graph, custom retriever, and answer chain have LangChain/LangGraph tracing hooks; end-to-end hosted tracing has not been exercised. Local JSON traces remain available with tracing off.

LangSmith credit types matter: its pricing distinguishes service usage from **LLM Gateway Credits**, which can fund model usage through the gateway. A LangSmith balance does not establish which credits you have or pay a separate Nebius account automatically. Check the balance label and applicable terms before choosing the generation route: [official LangSmith pricing](https://www.langchain.com/pricing). No Nebius requests or hosted LangSmith uploads were made during the refactor tests.

## Setup on Windows PowerShell

Python 3.13 is available in the workspace. A project `.venv` has been created; install dependencies when network access is approved:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`requirements.lock.txt` records the versions installed on this Windows/Python 3.13 environment. `pip check` passes. The locked environment is covered by recorded tests and narrow source-backed checks; a dependency snapshot alone does not establish model-provider compatibility.

The first index build downloads Hugging Face embedding model weights; the first reranked query also downloads reranker weights. These require network access and disk space. Model caches are kept in `.cache/huggingface` by default.

## Prepare and inspect the corpus

```powershell
.\.venv\Scripts\python.exe -m ir_assistant prepare
.\.venv\Scripts\python.exe -m ir_assistant inspect --bank BAC --contains "consumer" --limit 12
.\.venv\Scripts\python.exe -m ir_assistant inspect --bank JPM --contains "consumer" --limit 12
```

Raw documents, file hashes, and extracted blocks are saved locally. Inspect original source tables alongside extracted blocks before trusting amounts, column years, units, segment scope, or calculation inputs. Downloads use an explicit source allowlist. If a site denies access, obtain its official IR equivalent and update the manifest; do not substitute unofficial figures or silently skip a bank.

HTML tables retain row/column coordinates and repeated initial header context. Complex tables may still need source-specific extraction corrections. PDF extraction preserves page-level text and citations, plus income text rows when split date headers can be aligned. Selected Wells Fargo values are checked against original PDF columns; general PDF table extraction is not automatically trusted. Image-only PDFs need an additional OCR path.

## Build the two indexes

```powershell
.\.venv\Scripts\python.exe -m ir_assistant index --strategy both
```

- Fixed: 400 embedding-token windows with 60-token overlap.
- Semantic: sentence-similarity boundaries on packed narrative paragraphs, bounded to approximately 150–400 tokens.
- Tables: atomic row records are handled identically in both conditions. Oversized rows are marked as fragments and cannot automatically supply reviewed numeric facts.
- Dense embeddings: `BAAI/bge-small-en-v1.5`, normalized, with its retrieval instruction applied to queries. The smaller model replaces the original base-model proposal because this machine has two PyTorch CPU threads and no CUDA GPU.
- Database: persistent Chroma; keyword search: local BM25; fusion: reciprocal rank fusion.
- Reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2`.

Table preprocessing is intentionally held constant. Report narrative and table performance separately; much of the table-only evaluation may show no chunking difference. A revision-aware SQLite cache reuses document embeddings across strategies; query embeddings are not cached. The embedding model is pinned to the downloaded revision in `settings.py`, and both index manifests record it.

## Query and generation

Start in evidence-only mode, which displays excerpts and citations without calling a hosted model:

```powershell
.\.venv\Scripts\python.exe -m ir_assistant ask "What was Bank of America consumer revenue in Q2 2025?"
.\.venv\Scripts\python.exe -m ir_assistant ask "What was JPMorgan consumer revenue in Q2 2025?" --strategy semantic --rerank
```

For generated answers, copy `.env.example` to `.env` and configure `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` for a provider exposing a chat-completions endpoint. The base URL includes the provider's API version path when required, but excludes `/chat/completions`. No specific provider or paid model is assumed.

```powershell
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m ir_assistant ask "What was Bank of America consumer revenue in Q2 2025?" --generate
```

Use `Copy-Item` only when `.env` does not already exist, and edit its values locally. The application loads only `.env`; it never opens `pineconekey` or `pineconekey.env`. Git ignore rules exclude these credential paths and other `.env` files while allowing `.env.example`.

Generation uses a LangChain prompt/model/parser chain and returns structured claims citing retrieved chunk IDs. Invalid citation IDs and uncited claim records are rejected. This checks reference validity, not semantic faithfulness; reviewers must still verify claim support. A mocked compatible endpoint verifies routing, schema parsing, and usage metadata locally. A live Nebius request using `Qwen/Qwen3-30B-A3B-Instruct-2507` also passed one cited lookup; this is a smoke test, not a full generated-answer evaluation.

## Reviewed calculations

`data/reviewed_facts.json` now contains eight assistant-source-reviewed consumer revenue and expense facts. `data/fact_provenance.json` records 24 checks against original HTML cells and supporting basis references. These labels are not an independent human audit. To reproduce the reviewed dataset from the prepared corpus, run `./.venv/Scripts/python.exe scripts/prepare_reviewed_dataset.py`. Add new facts only after source verification, using actual row IDs from `inspect`:

```text
bank: JPM or BAC
segment: consumer
metric: revenue or noninterest_expense
period: YYYYQn
value: exact decimal as a JSON string
unit: explicit currency and scale, e.g. USD_millions
basis: actual source reporting basis
evidence_id: exact source row ID
period_type: quarter
```

The file is a JSON array of objects with those fields. Never invent values to make a demo work. Calculations require every input's row to be present in the selected retrieval results; missing, fragmented, or conflicting inputs produce an explicit limitation. Quarter/YTD, segment, reporting basis, and unit mismatches are rejected. Growth uses Decimal arithmetic, and operating leverage is reported in percentage points.

```powershell
.\.venv\Scripts\python.exe -m ir_assistant ask "What was Bank of America consumer revenue growth from Q2 2024 to Q2 2025?"
```

Reviewed asset-growth and ROA calculations are future extensions; do not present those as implemented. Questions requiring additional arithmetic must be added as validated calculation paths before claiming support.

## Evaluation

`eval/questions.draft.jsonl` preserves the original unreviewed proposals. `eval/gold_questions.jsonl` contains 20 assistant-reviewed questions, including revised wording where the original request exceeded available evidence. Fifteen have source evidence and five test scope handling. Some question types overlap development checks; the completed experiment is a pilot rather than a strict held-out benchmark. For each new answerable question add an `expected_answer` and evidence units:

```json
{"document_id":"actual-source-id","quote":"exact supporting text from the shared cleaned representation"}
```

Use sufficiently specific quotes containing metric and period context, not a bare number. Gold units are independent of chunk boundaries. Check each quote against the original document as well as the cleaned extraction, and set `annotation_status` to `reviewed` only after validation. Keep separate development questions for tuning; do not tune on the frozen test set.

```powershell
.\.venv\Scripts\python.exe -m ir_assistant evaluate --questions eval/gold_questions.jsonl
.\.venv\Scripts\python.exe -m ir_assistant evaluate --questions eval/gold_questions.jsonl --generate
```

The runner refuses unreviewed gold questions. It executes A=fixed, B=semantic, C=fixed+reranking, D=semantic+reranking, with the same corpus and retrieval budgets. It saves per-query traces, `scores.csv`, and `summary.json` under `runs/evaluation-*`.

Export a completed retrieval-only run into submission assets with:

```powershell
.\.venv\Scripts\python.exe scripts/report_evaluation.py runs/<evaluation-directory>
```

The exporter saves the report, scores, configuration, summary, and source manifest in `reports/retrieval-evaluation/`. The current report retains the measured baseline failures. Do not tune to these questions and then describe a repeat as an unseen test; freeze a fresh set for subsequent generalization claims.

Automatic metrics cover gold evidence recall@5, precision@5, candidate recall@20, and response status. Evidence-only responses are never scored as successful generated answers. Faithfulness, numeric correctness, and citation support require manual labels in the results CSV; the automatic summary does not pretend to calculate these.

Initial timing includes model initialization and uses a fixed configuration order. It is diagnostic only, not the plan's warm p95 benchmark. Final reporting still requires warmup, randomized/repeated timing, cost review, model/version recording, and failure analysis.

## Checks

Dependency-free rules and scoring tests:

```powershell
python -m unittest discover -s tests -v
```

The suite also includes HTML span/alignment and negative-value extraction checks, which skip until ingestion dependencies are installed. Full validation must additionally run actual ingestion, both indexes, reranked retrieval, and provider generation before submission.

## Remaining milestones

1. Keep `.env` private; live lookup, financial-answer, and source-summary checks have passed on the selected cases.
2. Obtain independent human review and broader validation; record provider costs and warmed end-to-end latency.
3. Repair remaining table subsection headers and expand the corpus, retaining current benchmarks and freezing new questions before tuning further.
4. Complete the Google Doc from `docs/SUBMISSION_DRAFT.md`, record the five-minute demo, and publish the reviewed repository assets.

See [WEEK_2_PROJECT_PLAN.md](WEEK_2_PROJECT_PLAN.md) for assignment mapping and acceptance targets. Pinecone can replace the vector-store adapter later; no Pinecone account or credits are needed for this implementation.
