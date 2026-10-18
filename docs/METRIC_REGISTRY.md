# Financial metric registry

The editable catalog is [config/metric_registry.json](../config/metric_registry.json). It defines 58 metrics used by the [28-family coverage checklist](ANALYST_COVERAGE.md). These definitions are application contracts and review requirements, not independently sourced financial observations.

Each definition records its canonical ID, definition, units, time convention, required comparison context, comparability traps, and any numerator, denominator or formula. Existing source-row labels are bank-labelled. Planned metrics require further source review; their presence here does not establish support.

## What is connected to the application

- Table-row matching in `retrieval.py` reads canonical labels from the registry. Labels alone do not establish the correct period, segment or balance convention; existing scope and period filters still apply.
- Loading `data/reviewed_facts.json` validates each fact against an enabled metric, reviewed scope, allowed units and reporting basis, explicit quarter, finite value and evidence ID. Actual retrieved-source support is still required downstream.
- Only revenue, noninterest expense, NII and noninterest income are enabled in the reviewed consumer fact store. Existing consumer growth, revenue build-up, peer comparison and operating-leverage routes continue to perform their own input and arithmetic checks. This flag describes stored source facts, not all retrieval or calculation capabilities.
- New query traces and evaluation configurations include the registry version and SHA-256. The registry reloads when its file timestamp or size changes. Earlier saved evaluations retain their original configurations.
- `validate_metric_context()` checks that a future route has supplied required conventions such as card portfolio, rate-sensitivity horizon or regulatory approach. This helper checks presence only; it does not verify the conventions against evidence, reconcile differences, or execute a formula. It is not a general comparison gate wired into every model-generated answer.

`metrics.py` continues to score retrieval evidence. Financial metric definitions live in `metric_registry.py` and the JSON catalog.

## Adding support for a metric

1. Review source definitions for both banks and the exact analysis periods. Record the unit, scope, reporting basis, numerator, denominator, adjustments and required conventions.
2. Freeze source-labelled acceptance cases, including incompatible inputs and missing evidence, before tuning retrieval against them.
3. Add reviewed source facts and provenance where appropriate. Extend the allowed fact contract only with reviewed scopes and bases. The current fact contract is deliberately limited to quarterly consumer inputs; broader observations will need additional metadata.
4. Implement the answer or calculation route explicitly. A formula in the catalog is documentation; it does not execute or enable a calculation. Keep derived values in Python and require actual retrieved evidence for every input.
5. Verify complete answers and comparability handling, then record the results in the checklist. Preserve original failures and evaluation snapshots.

Do not map aggregate noninterest income to pure fees, average assets to period-end assets, or return on allocated capital to ROA. Preserve reported figures with appropriate caveats when definitions differ; do not invent a normalized figure to force comparability.

## Coverage maintenance

The editable checklist is [eval/analyst_coverage.json](../eval/analyst_coverage.json). Each family has metric references, current evidence, open gaps, acceptance checks, priority and a next step. References must resolve to repository files. Full validation requires closed gaps, all listed acceptance checks marked completed, and saved evidence. These consistency checks do not replace source or answer review.

Regenerate the report after editing:

```powershell
.\.venv\Scripts\python.exe scripts/report_analyst_coverage.py
```

This command validates the catalog and checklist and writes `docs/ANALYST_COVERAGE.md`. It makes no retrieval or provider requests. The checklist is a development inventory, separate from frozen gold evaluation questions. Its current 0 full / 7 partial / 21 unvalidated counts are not an answer-accuracy score.
