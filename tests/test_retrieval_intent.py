import unittest

from ir_assistant.models import Chunk, Hit
from ir_assistant.retrieval import explanation_hits, numeric_metric_row, retrieval_queries, select_final_hits
from ir_assistant.scope import header_periods
from ir_assistant.metrics import score_evidence


def hit(cid, header, label, score=1):
    return Hit(chunk=Chunk(chunk_id=cid, document_id="fixture", bank="BAC", strategy="fixed",
                          text=f"Table header context:\n{header}\nRow 1: c1={label} | c4=123",
                          location="fixture", url="https://example.com", periods=["2024Q2", "2025Q2"],
                          evidence_ids=[cid], token_count=50), score=score)


class RetrievalIntentTests(unittest.TestCase):
    def test_single_bank_calculation_preserves_both_metrics_and_period_coverage(self):
        hits = [hit("rev", "Consumer Banking\nSecond Quarter 2025 | Second Quarter 2024", "Total net revenue", 10),
                hit("expense-one-period", "Consumer Banking\nSecond Quarter 2025", "Noninterest expense", 9),
                hit("expense-both-periods", "Consumer Banking\nSecond Quarter 2025 | Second Quarter 2024", "Noninterest expense", 1)]
        selected = select_final_hits(hits, ["BAC"], "consumer operating leverage", ["2024Q2", "2025Q2"])
        self.assertEqual([h.chunk.chunk_id for h in selected[:2]], ["rev", "expense-both-periods"])

    def test_assets_are_not_interest_earning_assets_or_the_wrong_balance_basis(self):
        self.assertFalse(numeric_metric_row(hit("earning", "Average balances", "Total interest-earning assets").chunk, "assets"))
        hits = [hit("end", "Consolidated balance sheet", "Total assets", 10),
                hit("avg", "Condensed average balance sheets", "Total assets", 1)]
        selected = select_final_hits(hits, ["BAC"], "consolidated average total assets")
        self.assertEqual(selected[0].chunk.chunk_id, "avg")

    def test_roa_abbreviation_expands_to_the_reported_metric(self):
        self.assertIn("return on assets", retrieval_queries("BAC consolidated ROA Q2 2025")[0])
        self.assertTrue(numeric_metric_row(hit("roa", "Consolidated ratios", "Return on assets (b)").chunk, "roa"))

    def test_calendar_dates_are_periods_but_ytd_is_not_a_quarter(self):
        self.assertEqual(header_periods("Table header context:\nJune 30 2025 | June 30 2024\nRow 1:"), {"2025Q2", "2024Q2"})
        self.assertEqual(header_periods("Table header context:\nSix Months Ended June 30, 2025\nRow 1:"), set())

    def test_explanation_requires_a_causal_narrative_not_a_revenue_table(self):
        table = hit("table", "Consumer", "Total net revenue")
        narrative = table.model_copy(deep=True)
        narrative.chunk.chunk_id = "narrative"
        narrative.chunk.text = "Consumer Banking revenue increased, driven primarily by higher net interest income."
        selected = explanation_hits([table, narrative], ["BAC"], "What drove consumer revenue?")
        self.assertEqual([h.chunk.chunk_id for h in selected], ["narrative"])

    def test_current_period_alternative_cannot_cover_a_prior_period_unit(self):
        units = [{"document_id": "source", "quote": "both periods", "period": "2025Q2",
                  "alternatives": [{"document_id": "source", "quote": "current only"}]},
                 {"document_id": "source", "quote": "both periods", "period": "2024Q2",
                  "alternatives": [{"document_id": "source", "quote": "prior only"}]}]
        score = score_evidence(units, [{"document_id": "source", "text": "current only"}])
        self.assertEqual(score["evidence_recall"], 0.5)


if __name__ == "__main__":
    unittest.main()
