import unittest
from decimal import Decimal
from unittest.mock import patch

from ir_assistant.calculations import Fact
from ir_assistant.facts import calculate
from ir_assistant.models import Chunk, GeneratedAnswer, Hit
from ir_assistant.workflow import Application


class AnswerRouteTests(unittest.TestCase):
    def application(self):
        app = object.__new__(Application)
        app.generate = True
        return app

    def hit(self, text):
        return Hit(chunk=Chunk(chunk_id="allowed", document_id="source", bank="BAC", strategy="fixed",
                              text=text, location="source", url="https://example.com",
                              periods=["2024Q2", "2025Q2"], evidence_ids=["row"], token_count=50), score=1)

    def test_computed_results_and_components_are_rendered_without_a_model_call(self):
        facts = [Fact(bank="BAC", segment="consumer", metric=metric, period=period, value=Decimal(value),
                      unit="USD_millions", basis="FTE", evidence_id="row")
                 for metric, period, value in [("revenue", "2025Q2", "120"), ("revenue", "2024Q2", "100"),
                                               ("noninterest_expense", "2025Q2", "110"), ("noninterest_expense", "2024Q2", "100")]]
        hits = [self.hit("source-backed inputs")]
        with patch("ir_assistant.facts.load_reviewed_facts", return_value=facts):
            calculations = calculate("consumer operating leverage", ["BAC"], ["2024Q2", "2025Q2"], hits)
        with patch("ir_assistant.workflow.generate_answer", side_effect=AssertionError("must not call model")):
            result = self.application().answer({"question": "consumer operating leverage", "scope": {"banks": ["BAC"]},
                                               "hits": hits, "calculations": calculations})
        self.assertEqual(result["answer_mode"], "validated_calculation")
        self.assertIn("Revenue growth 20.00%", result["text"])
        self.assertIn("expense growth 10.00% = 10.00 percentage points", result["text"])
        self.assertEqual(result["usage"], {})
        self.assertIn("[allowed]", result["text"])

    def test_explicit_reported_cause_can_be_quoted_if_model_refuses(self):
        text = "Consumer revenue was driven primarily by higher net interest income."
        with patch("ir_assistant.workflow.generate_answer", return_value=(GeneratedAnswer(status="insufficient_evidence"), {})):
            result = self.application().answer({"question": "What drove BAC consumer revenue?", "scope": {"banks": ["BAC"]},
                                               "hits": [self.hit(text)], "calculations": []})
        self.assertEqual(result["answer_mode"], "source_excerpt")
        self.assertEqual(result["status"], "answered")
        self.assertIn("revenue was driven primarily by higher net interest income", result["text"])

    def test_numeric_table_without_explanation_cannot_be_given_an_invented_cause(self):
        text = "Table header context:\nConsumer\nRow 1: c1=Revenue | c4=120"
        with patch("ir_assistant.workflow.generate_answer", return_value=(GeneratedAnswer(status="insufficient_evidence"), {})):
            result = self.application().answer({"question": "What drove BAC consumer revenue?", "scope": {"banks": ["BAC"]},
                                               "hits": [self.hit(text)], "calculations": []})
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(result["answer_mode"], "generated")


if __name__ == "__main__":
    unittest.main()
