import unittest
from decimal import Decimal
from unittest.mock import patch

from ir_assistant.calculations import Fact
from ir_assistant.facts import calculate
from ir_assistant.models import Chunk, Hit


class ReviewedFactTests(unittest.TestCase):
    def facts(self):
        return [Fact(bank="BAC", segment="consumer", metric="revenue", period=period,
                     value=Decimal(value), unit="USD_millions", basis="FTE", evidence_id="canonical",
                     alternative_evidence_ids=("equivalent",))
                for period, value in [("2025Q2", "110"), ("2024Q2", "100")]]

    def hit(self, evidence_id):
        chunk = Chunk(chunk_id="fixture", document_id="fixture", bank="BAC", strategy="fixed",
                      text="fixture", location="fixture", url="https://example.com", periods=["2025Q2", "2024Q2"],
                      evidence_ids=[evidence_id], token_count=1)
        return Hit(chunk=chunk, score=1)

    def test_calculation_cites_the_equivalent_row_that_was_actually_retrieved(self):
        with patch("ir_assistant.facts.load_reviewed_facts", return_value=self.facts()):
            result = calculate("consumer revenue growth", ["BAC"], ["2024Q2", "2025Q2"], [self.hit("equivalent")])
        self.assertEqual(result[0]["value"], "10.00")
        self.assertTrue(all(f["evidence_id"] == "equivalent" for f in result[0]["inputs"]))

    def test_a_stored_fact_without_retrieved_support_still_cannot_be_used(self):
        with patch("ir_assistant.facts.load_reviewed_facts", return_value=self.facts()):
            with self.assertRaisesRegex(ValueError, "absent"):
                calculate("consumer revenue growth", ["BAC"], ["2024Q2", "2025Q2"], [self.hit("unrelated")])


if __name__ == "__main__":
    unittest.main()
