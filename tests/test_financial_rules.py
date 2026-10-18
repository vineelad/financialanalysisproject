import unittest
from dataclasses import replace
from decimal import Decimal

from ir_assistant.calculations import Fact, growth, operating_leverage
from ir_assistant.metrics import score_evidence
from ir_assistant.scope import consumer_only, matches_quarter_context, resolve


class FinancialRulesTests(unittest.TestCase):
    def setUp(self):
        self.current = Fact("BAC", "consumer", "revenue", "2025Q2", Decimal("110"), "USD_millions", "GAAP", "current")
        self.prior = replace(self.current, period="2024Q2", value=Decimal("100"), evidence_id="prior")
        self.ids = {"current", "prior", "expense-current", "expense-prior"}

    def test_growth_uses_exact_decimal_inputs(self):
        self.assertEqual(growth(self.current, self.prior, self.ids), Decimal("10"))

    def test_calculation_cannot_bypass_retrieval(self):
        with self.assertRaisesRegex(ValueError, "retrieved evidence"):
            growth(self.current, self.prior, {"current"})

    def test_rejects_incompatible_financial_inputs(self):
        for changes in [{"bank": "JPM"}, {"segment": "wealth"}, {"metric": "assets"},
                        {"unit": "USD_billions"}, {"basis": "managed"}, {"period_type": "year_to_date"}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                growth(self.current, replace(self.prior, **changes), self.ids)

    def test_zero_or_negative_prior_is_not_reported_as_growth(self):
        for value in [Decimal("0"), Decimal("-100")]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                growth(self.current, replace(self.prior, value=value), self.ids)

    def test_mixed_quarters_and_year_gaps_are_rejected(self):
        for period in ["2024Q1", "2023Q2", "2025Q2"]:
            with self.subTest(period=period), self.assertRaises(ValueError):
                growth(self.current, replace(self.prior, period=period), self.ids)

    def test_missing_basis_blocks_calculation(self):
        with self.assertRaises(ValueError):
            growth(replace(self.current, basis=""), self.prior, self.ids)

    def test_nonfinite_amounts_are_rejected(self):
        for value in [Decimal("NaN"), Decimal("Infinity")]:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "finite"):
                growth(replace(self.current, value=value), self.prior, self.ids)

    def test_operating_leverage_is_percentage_point_difference(self):
        expense_current = replace(self.current, metric="noninterest_expense", value=Decimal("52.5"), evidence_id="expense-current")
        expense_prior = replace(self.prior, metric="noninterest_expense", value=Decimal("50"), evidence_id="expense-prior")
        self.assertEqual(operating_leverage(self.current, self.prior, expense_current, expense_prior, self.ids), Decimal("5"))

    def test_operating_leverage_rejects_cross_segment_inputs(self):
        expense_current = replace(self.current, segment="wealth", metric="noninterest_expense")
        expense_prior = replace(self.prior, segment="wealth", metric="noninterest_expense")
        with self.assertRaises(ValueError):
            operating_leverage(self.current, self.prior, expense_current, expense_prior, self.ids)


class ScopeTests(unittest.TestCase):
    def test_quarter_lookup_excludes_ytd_only_and_other_quarter_panels(self):
        def table(header):
            return "BAC | Published July 2025\nTable header context:\n" + header + "\nRow 18: Revenue"
        self.assertFalse(matches_quarter_context(table("Year-to-Date Results; Six Months Ended June 30, 2025"),
                                                ["2025Q2"], "revenue Q2 2025"))
        self.assertFalse(matches_quarter_context(table("Second Quarter 2024"), ["2025Q2"], "revenue Q2 2025"))
        self.assertTrue(matches_quarter_context(table("2Q25 | 2Q24"), ["2025Q2"], "revenue Q2 2025"))
        self.assertTrue(matches_quarter_context(table("Second Quarter 2025 | Six Months Ended"),
                                               ["2025Q2"], "revenue Q2 2025"))

    def test_consumer_filter_does_not_hide_cross_segment_comparisons(self):
        self.assertTrue(consumer_only("BAC consumer revenue Q2 2025"))
        self.assertFalse(consumer_only("Compare consumer and wealth performance"))
        self.assertFalse(consumer_only("BAC consolidated revenue Q2 2025"))

    def check(self, question):
        return resolve(question, {"JPM", "BAC"}, {"2025Q2", "2024Q2"})

    def test_multi_bank_multi_period_request(self):
        scope = self.check("Compare JPMorgan and Bank of America for Q2 2025 versus 2024")
        self.assertEqual(set(scope.banks), {"JPM", "BAC"})
        self.assertEqual(scope.periods, ["2024Q2", "2025Q2"])
        self.assertIsNone(scope.clarification)

    def test_unsupported_period(self):
        self.assertIsNotNone(self.check("JPM revenue Q2 2026").unsupported)

    def test_ambiguous_latest_requires_clarification(self):
        self.assertIsNotNone(self.check("What was the latest efficiency ratio?").clarification)

    def test_bank_without_period_requires_clarification(self):
        self.assertIsNotNone(self.check("Bank of America consumer revenue").clarification)

    def test_forecast_is_out_of_scope(self):
        self.assertIsNotNone(self.check("JPM revenue next quarter").unsupported)

    def test_allocated_capital_cannot_substitute_for_assets(self):
        self.assertIsNotNone(self.check("Calculate JPM consumer ROA in Q2 2025 using return on allocated capital as ROA").unsupported)


class EvidenceScoringTests(unittest.TestCase):
    def test_equivalent_reviewed_source_is_accepted(self):
        units = [{"document_id": "bac", "quote": "canonical revenue row",
                  "alternatives": [{"document_id": "bac-release", "quote": "equivalent revenue row"}]}]
        score = score_evidence(units, [{"document_id": "bac-release", "text": "Equivalent revenue row"}])
        self.assertEqual(score["evidence_recall"], 1)
        self.assertEqual(score["precision"], 1)

    def test_same_quote_in_wrong_document_does_not_count(self):
        score = score_evidence([{"document_id": "bac", "quote": "revenue 110"}],
                               [{"document_id": "jpm", "text": "Revenue 110"}])
        self.assertEqual(score["evidence_recall"], 0)

    def test_partial_evidence_does_not_receive_full_credit(self):
        units = [{"document_id": "bac", "quote": "revenue 110"}, {"document_id": "bac", "quote": "expense 52.5"}]
        score = score_evidence(units, [{"document_id": "bac", "text": "Revenue 110"}])
        self.assertEqual(score["evidence_recall"], 0.5)

    def test_unanswerable_questions_have_no_retrieval_score(self):
        self.assertIsNone(score_evidence([], [])["evidence_recall"])

    def test_empty_quote_is_rejected(self):
        with self.assertRaises(ValueError):
            score_evidence([{"document_id": "bac", "quote": ""}], [])


if __name__ == "__main__":
    unittest.main()
