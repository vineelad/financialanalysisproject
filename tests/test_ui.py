import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest
import streamlit as st

from ir_assistant.models import Answer, Chunk, Hit


class AnalystUITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        processed = root / "data" / "processed"
        processed.mkdir(parents=True)
        (processed / "source_manifest.json").write_text("[]", encoding="utf-8")
        for strategy in ("fixed", "semantic"):
            (processed / f"index-{strategy}.json").write_text("{}", encoding="utf-8")
            (processed / f"chunks-{strategy}.jsonl").write_text("", encoding="utf-8")
        self.engine = Mock()
        for target, value in [("ir_assistant.settings.DATA", root / "data"),
                              ("ir_assistant.settings.ROOT", root)]:
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch("ir_assistant.generation.provider_config", return_value=("", "", ""))
        self.provider = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch("ir_assistant.workflow.Application", return_value=self.engine)
        self.application_factory = patcher.start()
        self.addCleanup(patcher.stop)
        st.cache_resource.clear()
        self.addCleanup(st.cache_resource.clear)
        self.app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=20)

    def submit(self):
        if self.app.selectbox[0].value is None:
            self.app.selectbox[0].set_value("BAC")
        if not self.app.text_area[0].value:
            self.app.text_area[0].set_value("Compare consumer revenue in Q2 2025")
        next(button for button in self.app.button if button.label in {"Ask", "Search sources"}).click().run()

    def test_initial_page_does_not_query_or_generate(self):
        self.app.run()
        self.assertEqual(len(self.app.exception), 0)
        self.engine.ask.assert_not_called()
        self.assertTrue(any("answer service is not configured" in element.value for element in self.app.warning))
        self.assertEqual(len(self.app.tabs), 0)

    def test_submit_shows_brief_source_links_and_editing_does_not_repeat_query(self):
        chunk = Chunk(chunk_id="fixture-row", document_id="fixture", bank="BAC", strategy="fixed",
                      text="Fixture source evidence", location="Table 1 row 2", url="https://example.com/results",
                      periods=["2025Q2"], evidence_ids=["fixture:t1:r2"], token_count=4)
        answer = Answer(question="fixture", status="evidence_only", mode="evidence_only", text="Fixture",
                        hits=[Hit(chunk=chunk, score=1)], elapsed_seconds=0.1)
        self.engine.ask.return_value = (answer, {"calculations": []})
        self.app.run()
        self.submit()
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(self.engine.ask.call_count, 1)
        rendered = "\n".join(m.value for m in self.app.markdown)
        self.assertIn("[View source](<https://example.com/results>)", rendered)
        self.assertNotIn("Fixture source evidence", rendered)
        self.assertEqual(len(self.app.text), 0)
        self.app.text_area[0].set_value("Another question about BAC Q2 2025").run()
        self.assertEqual(self.engine.ask.call_count, 1)
        self.assertEqual(self.app.session_state["latest_result"]["configuration"], "semantic + reranking")

    def test_unavailable_period_is_displayed_as_a_limitation(self):
        answer = Answer(question="fixture", status="insufficient_evidence", mode="evidence_only",
                        text="The requested period is outside the corpus.")
        self.engine.ask.return_value = (answer, {"calculations": []})
        self.app.run()
        self.app.text_area[0].set_value("Give JPMorgan consumer revenue for Q2 2026.")
        self.assertIn("2026", self.app.text_area[0].value)
        self.engine.ask.assert_not_called()
        self.submit()
        self.assertEqual(len(self.app.exception), 0)
        self.assertTrue(any("outside the corpus" in element.value for element in self.app.warning))

    def test_backend_errors_are_not_echoed_into_the_page(self):
        self.engine.ask.side_effect = RuntimeError("sensitive-provider-error")
        self.app.run()
        self.submit()
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(len(self.app.error), 1)
        self.assertNotIn("sensitive-provider-error", self.app.error[0].value)

    def test_configured_app_answers_by_default_and_shows_readable_citations(self):
        self.provider.return_value = ("https://provider.invalid/v1", "test-placeholder", "fixture-model")
        chunk = Chunk(chunk_id="opaque-row-id", document_id="fixture", bank="BAC", strategy="semantic",
                      text="Verified evidence", location="Table 1", url="https://example.com/results",
                      periods=["2025Q2"], evidence_ids=["fixture:t1:r2"], token_count=4)
        answer = Answer(question="fixture", status="answered", mode="generated",
                        text="Consumer revenue was $10,813 million. [opaque-row-id]\n\n[opaque-row-id] Table 1: https://example.com/results",
                        hits=[Hit(chunk=chunk, score=1)], elapsed_seconds=0.1)
        self.engine.ask.return_value = (answer, {"calculations": []})
        self.app.run()
        self.engine.ask.assert_not_called()
        self.assertTrue(any(button.label == "Ask" for button in self.app.button))
        self.submit()
        self.assertEqual(len(self.app.exception), 0)
        self.assertTrue(self.application_factory.call_args.kwargs["generate"])
        text = "\n".join(m.value for m in self.app.markdown)
        self.assertIn("$10,813 million", text)
        self.assertIn("[1](<https://example.com/results>)", text)
        self.assertNotIn("opaque-row-id", text)
        self.assertEqual(len(self.app.metric), 0)
        self.assertFalse(any(e.label == "Technical run details" for e in self.app.expander))

    def test_analyst_view_contains_only_the_question_flow(self):
        self.app.run()
        self.assertTrue(any(s.value == "Ask a question" for s in self.app.subheader))
        self.assertEqual(len(self.app.tabs), 0)
        self.assertEqual(len(self.app.checkbox), 0)
        self.assertEqual(len(self.app.radio), 0)
        self.assertEqual(len(self.app.toggle), 0)
        self.assertEqual(self.app.selectbox[0].label, "Base bank")
        self.assertIsNone(self.app.selectbox[0].value)
        self.assertFalse(any(b.label in {"Consumer revenue", "Peer comparison", "Missing evidence"} for b in self.app.button))
        self.assertFalse(any(s.value == "Source documents" for s in self.app.subheader))
        self.engine.ask.assert_not_called()

    def test_base_selection_is_required_and_passed_with_submitted_question(self):
        self.engine.ask.return_value = (Answer(question="fixture", status="answered", mode="generated", text="Result"), {})
        self.app.run()
        self.app.text_area[0].set_value("Compare consumer revenue Q2 2025")
        next(b for b in self.app.button if b.label == "Search sources").click().run()
        self.engine.ask.assert_not_called()
        self.assertTrue(any("Select a base bank" in w.value for w in self.app.warning))
        self.app.selectbox[0].set_value("JPM")
        self.submit()
        self.engine.ask.assert_called_once_with("Compare consumer revenue Q2 2025", base_bank="JPM")
        self.assertEqual(self.app.session_state["latest_result"]["base_bank"], "JPM")
        self.app.selectbox[0].set_value("BAC").run()
        self.assertEqual(self.engine.ask.call_count, 1)
        self.assertTrue(any("Comparison base: JPMorgan Chase" in c.value for c in self.app.caption))

    def test_validated_calculation_is_presented_as_financial_results(self):
        self.provider.return_value = ("https://provider.invalid/v1", "test-placeholder", "fixture-model")
        answer = Answer(question="fixture", status="answered", mode="validated_calculation",
                        text="BAC consumer banking growth: 5.95%.")
        calculation = {"bank": "BAC", "value": "5.95", "formula": "(current / prior - 1) * 100",
                       "components": {}, "inputs": [{"period": "2025Q2", "metric": "revenue", "value": "10813",
                       "unit": "USD_millions", "basis": "FTE"}]}
        self.engine.ask.return_value = (answer, {"calculations": [calculation]})
        self.app.run()
        self.submit()
        self.assertEqual(len(self.app.exception), 0)
        result = self.app.dataframe[0].value
        self.assertEqual(result.iloc[0]["Bank"], "Bank of America")
        self.assertEqual(result.iloc[0]["Growth"], "5.95%")
        self.assertEqual(len(self.app.dataframe), 1)
        self.assertEqual(len(self.app.expander), 0)
        self.assertEqual(len(self.app.metric), 0)


if __name__ == "__main__":
    unittest.main()
