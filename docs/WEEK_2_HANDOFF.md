# Week 2 handoff

## Final build scope

- Five banks: Bank of America, JPMorgan Chase, Wells Fargo, Citi and Capital One.
- Six official Q2 2025 documents, with selected Q2 2024 comparison figures. This is a historical snapshot.
- Reviewed consumer revenue and noninterest/operating expense, peer gaps and ratios, year-over-year growth and operating leverage. NII and noninterest-income build-ups are available only where reviewed component rows exist.
- A selected base bank sets the denominator. General comparison questions include supported peers; named peers narrow the comparison. Single-bank lookups and explicit same-bank time comparisons stay focused.
- Reported segment names and bases are retained. Capital One Consumer Banking is separate from Credit Card; calculations do not remove acquisition effects.
- LangChain/LangGraph pipeline, fixed and semantic chunking, optional reranking, local Chroma, and a question-only Streamlit interface with brief supporting links.

The 58-metric registry is a review and implementation catalog. The [28-family checklist](ANALYST_COVERAGE.md) distinguishes partial checks from complete support. This build does not implement all 58 metrics or fully validate all 28 compound analyst questions.

## Run the app

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open http://localhost:8501. Select a base bank and ask:

> Compare consumer banking revenue in Q2 2025.

Then try:

- Compare consumer revenue with Wells Fargo in Q2 2025.
- What was Wells Fargo consumer revenue in Q2 2025?
- Compare consumer operating leverage across peers from Q2 2024 to Q2 2025.
- Compare consumer revenue in Q2 2026.

The selected base supplies context; it does not automatically turn an ordinary lookup into a peer comparison. Missing figures must remain unavailable rather than being substituted from another segment.

## Reproduce the reviewed dataset

Install the locked dependencies in a Python virtual environment. Configure the provider using `.env.example` if model-written explanations are needed; the covered reported figures and calculations use local validated routes.

```powershell
.\.venv\Scripts\python.exe -m ir_assistant prepare
.\.venv\Scripts\python.exe scripts/prepare_reviewed_dataset.py --facts-only
.\.venv\Scripts\python.exe scripts/prepare_peer_facts.py
.\.venv\Scripts\python.exe -m ir_assistant index --strategy both
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/validate_five_bank.py
```

`--facts-only` preserves evaluation labels. The peer fact script checks frozen original HTML cells and PDF text-line columns before writing the reviewed values. Local models may download on first setup; index building does not use Nebius credits.

## Evaluation and provenance

- Earlier two-bank results remain in their original report folders. Original corpus/index metadata and reviewed facts were copied to `data/snapshots/two-bank-v1`; its source list is also in `config/sources.two-bank.json`.
- The expanded 20-case set is frozen in `eval/five_bank_questions.jsonl`, with its protocol in `eval/five_bank_freeze.json`.
- The expanded four-condition experiment is exported to `reports/five-bank-retrieval/REPORT.md`.
- Narrow final-answer checks and full traces are in `reports/five-bank-answer-validation.json`. These cases use real retrieval with provider calls blocked, so an unintended model fallback is a recorded failure.
- Initial checks passed 16/20 before the Citi retrieval correction. Post-fix exact-ID checks passed 18/20; the remaining two flags were omitted, previously reviewed equivalent BofA rows. Separate audited labels rescore the identical saved answers and rankings. Raw and audited reports remain available. All 20 saved narrow cases pass with the audited labels; this is development validation, not general answer accuracy.
- A final model-written BofA explanation passed source review in `reports/final-provider-check.json`, using one Nebius request and 3,604 tokens. This is separate from the local numeric checks and is not the project's total token usage.
- New source checks are in `data/peer_fact_provenance.json`. Review is by the coding assistant, not an independent human financial audit.

To rerun and export the expanded experiment:

```powershell
.\.venv\Scripts\python.exe -m ir_assistant evaluate --questions eval/five_bank_questions.audited.jsonl
.\.venv\Scripts\python.exe scripts/report_five_bank_evaluation.py runs/<evaluation-directory>
```

Budgets are recorded per query and applied identically to all four configurations. Five-bank questions get enough evidence slots for their inputs; the report must not label every result recall@5 when the final limit is larger. Retrieval recall and a small deterministic-answer sample do not establish general model-answer accuracy.

The original frozen labels remain in `eval/five_bank_questions.jsonl`. The audited file and `eval/five_bank_annotation_audit.json` document the omitted pre-reviewed alternatives. Audit rescoring changes no queries, amounts, answers or rankings. The package retains the original fact snapshot needed to reproduce this audit against the exported raw report folder.

## Submission steps

- [ ] Paste the final [submission draft](SUBMISSION_DRAFT.md) into a Google Doc and add its shareable link.
- [ ] Record the demonstration using [DEMO_SCRIPT.md](DEMO_SCRIPT.md), under five minutes, and add its link.
- [ ] Publish the source repository to GitHub and add the link. A local submission zip can be created with `python scripts/package_week2.py` after validation reports are complete.
- [ ] Check shared links and submit through the handout's form: https://forms.gle/Cxad8AnPHBB4sNzw5.

These external submission steps are not completed by generating local files. Private env/key files, model caches and vector indexes are excluded from the submission zip.
