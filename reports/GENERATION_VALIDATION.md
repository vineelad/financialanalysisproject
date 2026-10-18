# Live generation development checks

Five cases were exercised with Nebius `Qwen/Qwen3-30B-A3B-Instruct-2507`. Two calculations returned correct cited answers; two scope checks behaved correctly without model requests. The corporate segment comparison remains unsuccessful. This is a small development check with mixed retrieval settings, not the four-condition answer-quality benchmark.

## Results after the citation fix

| Case | Retrieval | Result | Assistant source review |
|---|---|---|---|
| BAC consumer revenue growth, Q2 2024 to Q2 2025 | Fixed, no reranking | Answered: 5.95% | Correct; the cited row contains $10,813 million and $10,206 million in the correct quarter columns. |
| JPM consumer operating leverage, Q2 2024 to Q2 2025 | Fixed, reranking | Answered: 1.88 percentage points | Correct under the project definition; citations cover revenue and expense rows for both periods. |
| Corporate segment names at both banks | Fixed, no reranking | Insufficient evidence | Incomplete peer coverage. The selected BAC passage is a risk disclosure. The response also treats a JPM business-line label as a segment name in uncited limitation text; do not use it as a reliable segment explanation. |
| JPM consumer revenue, Q2 2026 | Fixed, no reranking | Insufficient evidence | Correct: unavailable period; zero model tokens. |
| Latest quarter's efficiency ratio | Fixed, no reranking | Clarification | Correct first step: requests the bank; no model call. A period must also be established before retrieval. |

The coding assistant checked the numeric results and citation excerpts against the previously reviewed source cells. This is not an independent human audit. Two correct numeric answers out of two attempted post-fix numeric cases does not establish the proposed 95% accuracy target on a representative set.

## Failure found and fixed

Initial calculation attempts were rejected. A diagnostic retry confirmed that the BAC answer cited source row IDs outside the allowed chunk-ID namespace. The calculation payload exposed row provenance while the answer validator expected chunk IDs.

`calculation_context` now maps every verified input row to its retrieved chunk IDs before sending it to the model. It removes alternative row IDs from that payload and retains the original provenance in local traces. Missing input citations still fail explicitly; the validator has not been relaxed. The prompt also requests that factual statements appear in cited claims.

The post-fix BAC and JPM calculations both passed. Two regression tests cover citation mapping/provenance preservation and refusal to map an input without a retrieved chunk. The full suite passes: **42 tests**, plus 13 reported subtests.

The prompt fingerprint changed. The original retrieval report retains its original configuration and was not replaced; retrieval rankings and arithmetic were not modified by this fix. The peer response shows that prompt instructions alone do not prevent factual statements appearing in limitations.

## Usage and timing

The completed post-fix batch made three model requests, using **9,779 input tokens and 344 output tokens (10,123 total)**. The other two cases made no model request. Provider-reported usage and full source excerpts are saved in [generation-validation.json](generation-validation.json).

These totals exclude the earlier lookup smoke test and failed calculation attempts. Rejected responses may still be billed; the application did not retain their token usage. Do not present the recorded batch tokens as the total project bill. Confirm actual spending in Nebius.

Recorded end-to-end times were 21.018 seconds for the first BAC calculation, 8.234 seconds for JPM, and 8.261 seconds for the peer request. Initialization and different retrieval settings confound comparisons. These five cases do not measure warm p95 or demonstrate the proposed 15-second p95 target.

## Reproduce

Run from the project folder with a privately saved `.env`:

```powershell
.\.venv\Scripts\python.exe scripts/validate_generation.py
```

This makes up to three hosted requests. To rerun a single case:

```powershell
.\.venv\Scripts\python.exe scripts/validate_generation.py --case bac-growth
```

Each invocation saves a new local `runs/generation-check-*` directory. The reviewed export above refers to the completed post-fix batch; later runs do not silently overwrite that reviewed export.

## Next improvement

Improve bank and metric coverage in the selected evidence, repair misleading subsection headers, and distinguish reported segments from business lines. Keep these failures visible, then freeze fresh questions before evaluating changes. Broader generated-answer review, human verification, warm timing, and a successful peer demonstration remain outstanding.
