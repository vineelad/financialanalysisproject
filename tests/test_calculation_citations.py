import copy
import unittest

from ir_assistant.generation import calculation_context
from ir_assistant.models import Chunk, Hit


class CalculationCitationTests(unittest.TestCase):
    def setUp(self):
        self.hits = [Hit(chunk=Chunk(chunk_id="allowed-chunk", document_id="source", bank="BAC",
                                    strategy="fixed", text="verified source row", location="Table 1 row 2",
                                    url="https://example.com", periods=["2025Q2"],
                                    evidence_ids=["source:t1:r2"], token_count=5), score=1)]
        self.calculations = [{"value": "5.95", "unit": "percent", "inputs": [
            {"value": "10813", "evidence_id": "source:t1:r2", "alternative_evidence_ids": ["other-row"]}]}]

    def test_model_receives_allowed_chunk_ids_and_original_provenance_is_retained(self):
        original = copy.deepcopy(self.calculations)
        context = calculation_context(self.calculations, self.hits)
        self.assertEqual(context[0]["citations"], ["allowed-chunk"])
        self.assertEqual(context[0]["inputs"][0]["citations"], ["allowed-chunk"])
        self.assertNotIn("evidence_id", context[0]["inputs"][0])
        self.assertNotIn("alternative_evidence_ids", context[0]["inputs"][0])
        self.assertEqual(self.calculations, original)

    def test_missing_retrieved_input_cannot_receive_a_citation(self):
        with self.assertRaisesRegex(ValueError, "no retrieved chunk"):
            calculation_context(self.calculations, [])


if __name__ == "__main__":
    unittest.main()
