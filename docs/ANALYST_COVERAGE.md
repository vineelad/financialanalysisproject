# Analyst question coverage checklist

Assessment: 2026-10-18. Registry 1.0; checklist 1.1.

Five banks: Bank of America, JPMorgan Chase, Wells Fargo, Citi and Capital One. Six frozen Q2 2025 documents with selected Q2 2024 comparisons. Core reviewed consumer revenue/expense inputs cover all five banks. Q1 is not currently accepted by scope resolution.

Code and saved-artifact audit. These 28 compound questions have not been run as a new end-to-end evaluation. Partial checks are narrower than the family; counts are not answer accuracy.

**28 families: 0 fully validated, 7 with partial existing checks, 21 unvalidated.**

The registry defines 58 metrics. Only `revenue`, `noninterest_expense`, `net_interest_income`, `noninterest_income` are enabled in the reviewed consumer fact store. Existing source retrieval and calculation routes remain separately bounded.

These counts describe coverage, not answer accuracy. Relevant text in a source does not establish a correct answer. The registry does not enable a new calculation or make bank definitions equivalent.

## Implementation order

1. Week 2: finish narrow consumer performance and reported profitability cases; review definitions before extending to margin and card NCOs.
2. Next: review deposit, credit, capital and other segment inputs, then add matched-input calculations and independent cases.
3. Later: add dated guidance, rate-risk, regulatory and market data with their own provenance and assumptions.

## Family checklist

### Q01. How does ROTCE compare across peers this quarter, and how much is driven by one-time items?

**Profitability | Partial existing checks | Priority: week2**

Metrics: `rotce`, `net_income`.

Existing checks: JPM reported ROTCE has source-labelled retrieval checks only; no adjusted peer-answer validation.

Gaps: Both-bank coverage and notable-item reconciliation are not validated.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Verify reported and adjusted figures separately; require attributable income, average tangible equity and annualization before computing adjustments.

Next: Freeze both-bank reported ROTCE cases before adding adjusted returns.

Saved references: [validation_questions.audited.jsonl](../eval/validation_questions.audited.jsonl), [summary.json](../reports/prospective-validation/audited/summary.json).

### Q02. What is each bank's return on assets, and how much is driven by balance sheet mix rather than profitability?

**Profitability | Partial existing checks | Priority: week2**

Metrics: `roa`, `net_income`, `average_assets`.

Existing checks: JPM consolidated reported ROA was checked in the selected live-answer sample.

Gaps: Peer coverage and mix attribution are not validated.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Reject return on allocated capital as ROA; require disclosed evidence for mix attribution.

Next: Validate reported ROA for each bank; separate attribution into another case.

Saved references: [live-financial-validation.json](../reports/live-financial-validation.json).

### Q03. How much of the year-over-year change in earnings comes from revenue, expenses, and provisions?

**Profitability | Partial existing checks | Priority: next**

Metrics: `net_income`, `revenue`, `noninterest_expense`, `provision_expense`.

Existing checks: Selected net-income lookups have retrieval checks; these do not validate an earnings bridge.

Gaps: No reconciled earnings bridge or exceptional-item treatment.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Include tax and other reconciliation effects; separate reported and normalized changes.

Next: Define bridge inputs and notable-item reconciliations.

Saved references: [validation_questions.audited.jsonl](../eval/validation_questions.audited.jsonl), [summary.json](../reports/prospective-validation/audited/summary.json).

### Q04. What is each bank's net interest margin, and which way is it moving?

**Net interest income and margin | Unvalidated | Priority: week2**

Metrics: `net_interest_margin`, `net_interest_income`.

Existing checks: No family-specific end-to-end answer validation recorded.

Gaps: Bank-specific yield series and trend calculations are not validated.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Keep including/excluding Markets separate and verify matched periods and denominators.

Next: Review exact margin/yield labels and freeze bank-specific series.

### Q05. How sensitive is NII to a 100bp rate move?

**Net interest income and margin | Unvalidated | Priority: later**

Metrics: `nii_rate_sensitivity`.

Existing checks: No family-specific end-to-end answer validation recorded.

Gaps: No reviewed shock scenario, horizon or assumption mapping.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Display shock path, horizon and model assumptions; do not imply identical scenarios.

Next: Add and review rate-risk disclosures before enabling comparisons.

### Q06. What is full-year NII guidance, and has it been raised or cut since last quarter?

**Net interest income and margin | Unvalidated | Priority: later**

Metrics: `nii_guidance`.

Existing checks: No family-specific end-to-end answer validation recorded.

Gaps: No reviewed pair of dated guidance disclosures.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Compare issued-at dates and identical horizon and Markets scope; attribute forecasts to management.

Next: Add current and prior-quarter presentations or transcripts.

### Q07. What is deposit growth quarter over quarter, split by consumer and wholesale?

**Deposits and funding | Unvalidated | Priority: next**

Metrics: `deposits`.

Existing checks: No family-specific end-to-end answer validation recorded.

Gaps: Q1 is not currently accepted by scope resolution; no reviewed deposit series or QoQ route.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Match deposit populations and average/end balances; preserve segment definitions.

Next: Audit existing Q1 columns before expanding period metadata and calculation support.

### Q08. What share of deposits is noninterest-bearing, and is the mix shifting toward CDs and money market accounts?

**Deposits and funding | Unvalidated | Priority: next**

Metrics: `deposits`, `noninterest_bearing_deposits`.

Existing checks: No family-specific end-to-end answer validation recorded.

Gaps: No reviewed product mix series or share calculation.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Verify each deposit product definition and use the matching total deposit denominator.

Next: Label deposit product populations and review both-period mix inputs.

### Q09. What rate is each bank paying on interest-bearing deposits, and what is the cumulative deposit beta?

**Deposits and funding | Unvalidated | Priority: next**

Metrics: `deposit_rate`, `deposit_beta`.

Existing checks: No family-specific end-to-end answer validation recorded.

Gaps: No reviewed cost-of-deposits series, reference-rate cycle or beta implementation.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Distinguish interest-bearing from all deposits and cumulative from marginal beta.

Next: Review reported deposit rates before sourcing a consistent beta benchmark.

### Q10. What is the loan-to-deposit ratio?

**Deposits and funding | Unvalidated | Priority: next**

Metrics: `loans`, `deposits`, `loan_to_deposit_ratio`.

Existing checks: No family-specific end-to-end answer validation recorded.

Gaps: No reviewed matching balance inputs or ratio route.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Require same date, scope and balance conventions; reject zero/nonpositive deposit denominator.

Next: Review matched loans and deposits, then implement a validated ratio.

### Q11. What are net charge-off rates, especially on credit cards?

**Credit quality | Unvalidated | Priority: week2**

Metrics: `card_nco_rate`, `net_charge_offs`.

Existing checks: No family-specific end-to-end answer validation recorded.

Gaps: No reviewed portfolio-specific NCO answer route.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Compare card rates only with matching card rates, retaining annualization and loan denominator.

Next: Freeze both-bank card NCO source rows and reported-rate tests.

### Q12. What is the reserve build or release, and is provision expense above or below net charge-offs?

**Credit quality | Unvalidated | Priority: next**

Metrics: `reserve_change`, `provision_expense`, `net_charge_offs`, `allowance`.

Existing checks: No family-specific end-to-end answer validation recorded.

Gaps: No reviewed allowance movement reconciliation or comparison calculation.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Preserve allowance scope and explain other movements instead of assuming provision minus NCO equals the full change.

Next: Review allowance roll-forwards and provision/NCO populations.

### Q13. How large is commercial real estate exposure, and how are nonperforming loans in that book trending?

**Credit quality | Unvalidated | Priority: next**

Metrics: `cre_exposure`, `cre_npl`.

Existing checks: No family-specific end-to-end answer validation recorded.

Gaps: No reviewed matching CRE exposure and NPL trend series.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Preserve CRE/office/construction and funded/committed definitions.

Next: Audit portfolio definitions and select comparable dated disclosures.

### Q14. What is the allowance coverage ratio: allowance to loans, and allowance to nonperforming loans?

**Credit quality | Unvalidated | Priority: next**

Metrics: `allowance`, `allowance_to_loans`, `allowance_to_npl`, `loans`, `nonperforming_loans`.

Existing checks: No family-specific end-to-end answer validation recorded.

Gaps: No reviewed matching allowance/loan/NPL inputs or coverage formulas.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Use matching portfolio populations; reject unavailable or nonpositive denominators.

Next: Define allowance population and NPL convention before adding formulas.

### Q15. What is the CET1 ratio, and how much buffer is there above the regulatory requirement?

**Capital | Unvalidated | Priority: next**

Metrics: `cet1_ratio`, `capital_requirement`, `capital_buffer`.

Existing checks: No family-specific end-to-end answer validation recorded.

Gaps: No bank-specific requirement, approach or binding-constraint validation.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Match capital measure, regulatory approach and effective date; do not infer the binding constraint from CET1 alone.

Next: Review reported CET1 first, then requirements and other capital constraints.

### Q16. How much stock was repurchased this quarter, and what is the total payout ratio?

**Capital | Unvalidated | Priority: next**

Metrics: `share_repurchases`, `dividends`, `net_income`, `payout_ratio`.

Existing checks: No family-specific end-to-end answer validation recorded.

Gaps: No reviewed distribution convention or payout denominator.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Separate authorizations from execution; preserve common income and dividend conventions.

Next: Review actual buybacks, common dividends and the matching earnings measure.

### Q17. What is the expected impact of Basel III endgame or SLR changes?

**Capital | Unvalidated | Priority: later**

Metrics: `regulatory_change_impact`.

Existing checks: No family-specific end-to-end answer validation recorded.

Gaps: No dated rule-version and management-impact disclosure set.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Distinguish proposal from final rule, effective dates and management scenarios.

Next: Add versioned regulatory and management disclosures.

### Q18. What is the efficiency or overhead ratio, and is operating leverage positive?

**Efficiency | Partial existing checks | Priority: week2**

Metrics: `efficiency_ratio`, `operating_leverage`, `revenue`, `noninterest_expense`.

Existing checks: Five-bank consumer operating-leverage calculations and reported consumer performance have narrow source checks. Consolidated efficiency ratios and the complete family remain unvalidated.

Gaps: Existing checks are consumer scope; no full consolidated peer-family validation.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Match GAAP/FTE/managed bases; calculate leverage with validated inputs and state percentage-point units.

Next: Freeze separate consumer and consolidated acceptance cases.

Saved references: [REPORT.md](../reports/retrieval-v3-development/REPORT.md), [live-financial-validation.json](../reports/live-financial-validation.json), [five-bank-answer-validation.json](../reports/five-bank-answer-validation.json), [REPORT.md](../reports/five-bank-retrieval/REPORT.md).

### Q19. How fast are expenses growing compared with revenue, and how much of that growth is technology spending or headcount?

**Efficiency | Partial existing checks | Priority: week2**

Metrics: `revenue`, `noninterest_expense`, `technology_expense`, `headcount`.

Existing checks: Five-bank consumer revenue/expense YoY components are validated in narrow operating-leverage cases; technology/headcount attribution remains unvalidated.

Gaps: Technology/headcount attribution and consolidated coverage are unvalidated.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Use source-disclosed causal attribution; headcount change alone does not establish expense causality.

Next: Keep growth calculations and management-attributed explanations as separate cases.

Saved references: [live-financial-validation.json](../reports/live-financial-validation.json), [five-bank-answer-validation.json](../reports/five-bank-answer-validation.json), [REPORT.md](../reports/five-bank-retrieval/REPORT.md).

### Q20. How does consumer segment revenue and margin compare?

**Segment-level | Partial existing checks | Priority: week2**

Metrics: `revenue`, `consumer_margin`.

Existing checks: Reported consumer revenue is checked across all five banks, with selected-base comparisons and source/segment caveats. Margin is not defined or validated.

Gaps: Margin definition and input validation are missing.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Require an explicit margin definition; preserve reported segment scope and selected comparison denominator.

Next: Keep validated revenue comparison and clarify the requested margin before extending.

Saved references: [revenue-build-validation.json](../reports/revenue-build-validation.json), [selected-base-validation.json](../reports/selected-base-validation.json), [five-bank-answer-validation.json](../reports/five-bank-answer-validation.json), [REPORT.md](../reports/five-bank-retrieval/REPORT.md).

### Q21. How do investment banking fees and trading revenue (FICC and equities) compare, and what is each bank's market share?

**Segment-level | Unvalidated | Priority: next**

Metrics: `investment_banking_fees`, `ficc_revenue`, `equities_revenue`, `market_share`.

Existing checks: No family-specific end-to-end answer validation recorded.

Gaps: Product definitions are not reviewed; no market-total source is configured.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Compare matching product populations; market share requires an independently sourced market denominator.

Next: Validate reported fees/trading first, then source league-table or market totals.

### Q22. In wealth management, what are net new assets or client flows, and how is AUM growing?

**Segment-level | Unvalidated | Priority: next**

Metrics: `client_flows`, `aum`.

Existing checks: No family-specific end-to-end answer validation recorded.

Gaps: No reviewed flow definitions or AUM trend calculation.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Keep AUM, client assets and assets under supervision distinct; do not infer flows from total asset growth.

Next: Review wealth asset populations and source flow reconciliations.

### Q23. How much revenue comes from fees versus net interest income?

**Segment-level | Partial existing checks | Priority: week2**

Metrics: `noninterest_income`, `net_interest_income`, `revenue`, `noninterest_revenue_share`.

Existing checks: Consumer NII plus noninterest income reconciles to reported revenue for both banks; noninterest income is not verified as fees.

Gaps: No fee-only reconciliation or percentage-share calculation.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Label aggregate noninterest income correctly; require separate fee evidence for a fee-only share.

Next: Add validated noninterest share first; retain fee-only questions as separate cases.

Saved references: [revenue-build-validation.json](../reports/revenue-build-validation.json).

### Q24. How fast are card purchase volumes and debit volumes growing?

**Consumer and card activity | Unvalidated | Priority: next**

Metrics: `card_purchase_volume`, `debit_purchase_volume`.

Existing checks: No family-specific end-to-end answer validation recorded.

Gaps: No reviewed matching volume series or growth route.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Preserve credit/debit populations and the same sales/purchase volume conventions.

Next: Review each bank's volume definitions and period pairs.

### Q25. How many new card accounts were opened, and how fast are card loans growing?

**Consumer and card activity | Unvalidated | Priority: next**

Metrics: `new_card_accounts`, `card_loans`.

Existing checks: No family-specific end-to-end answer validation recorded.

Gaps: No reviewed account-opening and loan-balance series.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Do not substitute active accounts for openings or average card loans for period-end balances.

Next: Label account populations and matching loan balance conventions.

### Q26. How fast are digital and mobile active users growing?

**Consumer and card activity | Unvalidated | Priority: next**

Metrics: `digital_active_users`, `mobile_active_users`.

Existing checks: No family-specific end-to-end answer validation recorded.

Gaps: No reviewed active-user definitions or growth route.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Match activity windows and populations; do not add overlapping mobile and digital counts.

Next: Review activation definitions before calculating growth.

### Q27. What is price to tangible book value compared with ROTCE, and which banks look cheap or expensive relative to their returns?

**Valuation | Unvalidated | Priority: later**

Metrics: `price_to_tangible_book`, `stock_price`, `tangible_book_value_per_share`, `rotce`.

Existing checks: No family-specific end-to-end answer validation recorded.

Gaps: No dated market-price input, valuation route or defensible cheap/expensive assessment.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Align dates and ROTCE basis; distinguish relative multiples from a demonstrated mispricing conclusion.

Next: Add timestamped market data and a disclosed valuation methodology.

### Q28. What are dividend yield and tangible book value growth?

**Valuation | Unvalidated | Priority: later**

Metrics: `dividend_yield`, `dividends`, `stock_price`, `tangible_book_value_per_share`, `tangible_book_growth`.

Existing checks: No family-specific end-to-end answer validation recorded.

Gaps: No dated yield price input or reviewed TBV growth calculation.

Acceptance checks:

- [ ] Preserve bank, business scope, period, units and reporting basis; cite each material claim.
- [ ] Declare trailing/forward dividend convention and per-share/total TBV growth.

Next: Review TBV inputs and add dated prices for dividend yield.

## Maintaining this checklist

Edit `config/metric_registry.json` and `eval/analyst_coverage.json`, then run:

```powershell
.\.venv\Scripts\python.exe scripts/report_analyst_coverage.py
```

Promotion to fully validated requires saved source-backed answer checks for the complete family, including its calculations and traps. Review every acceptance item and retain failures. References must be existing repository files; a partial retrieval report alone does not justify promotion. Freeze new acceptance cases before inspecting their retrieval. This checklist is not a gold evaluation dataset.
