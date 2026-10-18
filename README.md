# Bank IR Assistant

An investor relations research tool for comparing consumer banking performance across Bank of America, JPMorgan Chase, Wells Fargo, Citi and Capital One.

Bank earnings reports often put similar numbers under different names, in different tables, and on different reporting bases. I built this app to make those comparisons easier: select a base bank, ask a question, and get an answer with links back to the reports. Supported financial calculations run in Python using source-reviewed figures and retrieved evidence.

This is my Gen Academy Week 2 project, built with LangChain, LangGraph and Streamlit.

## What you can ask

The current dataset covers Q2 2025, with selected Q2 2024 figures for year-over-year comparisons. The strongest coverage is consumer revenue, expenses, growth and operating leverage.

A few questions to try:

- Compare consumer banking revenue across peers for Q2 2025.
- How does consumer revenue compare with Wells Fargo in Q2 2025?
- Compare consumer revenue growth from Q2 2024 to Q2 2025 across peers.
- Which bank had the strongest consumer operating leverage in Q2 2025?
- Break down Bank of America's Q2 2025 consumer revenue into net interest income and noninterest income.
- What did Bank of America management say drove consumer revenue changes in Q2 2025?

A general peer comparison includes all supported banks. Naming a peer narrows the comparison, and a single-bank question stays with that bank. Percentage comparisons use the selected base bank as the denominator.

There are real limits to these comparisons. The banks' consumer segments have different scopes and reporting bases. Capital One reports Credit Card separately from Consumer Banking, and its Discover acquisition affects year-over-year results. The app reports those caveats; it does not produce acquisition-adjusted or fully normalized peer figures.

## Run it locally

These instructions use Windows PowerShell. Python 3.13 was used for development.

```powershell
git clone https://github.com/vineelad/financialanalysisproject.git
cd financialanalysisproject
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
```

Create your local settings file once:

```powershell
Copy-Item .env.example .env
```

If you already have a `.env`, keep it. Edit the file locally and add your provider key:

```dotenv
LLM_BASE_URL=https://api.tokenfactory.nebius.com/v1
LLM_API_KEY=your_api_key
LLM_MODEL=Qwen/Qwen3-30B-A3B-Instruct-2507
LANGSMITH_TRACING=false
```

The project uses Nebius for generated explanations. Embeddings, reranking and supported financial calculations run locally. Without a configured provider, the UI offers source retrieval rather than written answers. No Pinecone account is needed.

Download the source documents, extract their contents and build both indexes:

```powershell
.\.venv\Scripts\python.exe -m ir_assistant prepare
.\.venv\Scripts\python.exe -m ir_assistant index --strategy both
```

The first build downloads the embedding model, and the first reranked query may download the reranker. Internet access is needed for those downloads and the official reports. Raw documents, model caches and vector indexes are generated locally and are excluded from Git.

Start the app:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open <http://localhost:8501>, select a base bank and enter a question. Keep the terminal open while using the app; press Ctrl+C to stop it.

## How it works

Six official earnings documents supply the evidence: two from Bank of America and one each from the other four banks. Their URLs are in [config/sources.json](config/sources.json). This is a historical snapshot, refreshed manually.

HTML and PDF extraction preserve source locations, table headers and period context. The pipeline compares fixed 400-token windows with 60-token overlap against semantic narrative chunks, while applying the same financial-row preservation rules to both. Local BGE-small embeddings are stored in Chroma; BM25 adds keyword matching, and reciprocal rank fusion combines the results. An optional MiniLM cross-encoder reranks candidates.

LangGraph connects scope resolution, retrieval, calculations and answering. LangChain provides document, embedding and retriever interfaces, Chroma integration, and the prompt/model/parser chain for generated answers. The UI defaults to semantic chunking with reranking.

The 32 reviewed financial facts are checked against the evidence retrieved for each question before use. Python performs supported arithmetic, and generated claims must cite retrieved evidence IDs. These checks help catch missing inputs and invalid citations, but a valid citation alone does not prove that an explanation is correct.

## What has been checked

The final five-bank evaluation compares four configurations: fixed and semantic chunking, each with and without reranking. It contains 18 answerable development cases and two scope checks.

All four configurations reached 100% audited evidence recall on those 18 cases. Before the annotation audit, recall ranged from 97.8% to 98.9%; the audit added equivalent source rows already recorded in the reviewed-fact snapshot and rescored unchanged traces. Raw results and the audit are retained in the repository.

Separate narrow answer checks passed 20/20 with audited labels, the automated test suite passed 100 tests, and a final hosted explanation smoke check passed. These are development checks, not an independent accuracy benchmark. General faithfulness, answer relevance and production latency have not been established. The final table-heavy set also showed no recall advantage for semantic chunking or reranking.

For the evidence and limitations, see the [retrieval report](reports/five-bank-retrieval/REPORT.md) and [answer-check results](reports/five-bank-answer-validation.json). The metric registry is broader than the implemented calculations; a listed metric does not mean the app can answer every question about it.

## Tests and command-line use

Run the tests in the project environment:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

You can also ask questions without opening Streamlit:

```powershell
.\.venv\Scripts\python.exe -m ir_assistant ask "Compare consumer revenue across peers for Q2 2025" --base-bank BAC --strategy semantic --rerank --generate
```

Omit `--generate` for evidence-only output. Generated explanations may incur provider charges; covered deterministic numeric answers use the local calculation path.

To rerun the four retrieval configurations without hosted generation:

```powershell
.\.venv\Scripts\python.exe -m ir_assistant evaluate --questions eval/five_bank_questions.audited.jsonl
```

API keys belong in your local `.env`, which Git ignores. The committed `.env.example` is a blank setup template. LangSmith tracing is optional and disabled by default.
