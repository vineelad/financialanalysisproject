import unittest
from dataclasses import replace
from decimal import Decimal
from unittest.mock import patch

from ir_assistant.calculations import Fact
from ir_assistant.models import Chunk, Hit
from ir_assistant.reported import reported_metric_answer
from ir_assistant.scope import resolve
from ir_assistant.retrieval import revenue_build_question, required_peer_metrics, select_final_hits
from ir_assistant.workflow import Application


QUESTION = "How does bank of America consumer revenue compare with jp morgan chase for q2 2025"


class ReportedMetricTests(unittest.TestCase):
    def setUp(self):
        self.facts = [Fact(bank=bank, segment="consumer", metric="revenue", period="2025Q2", value=Decimal(value),
                           unit="USD_millions", basis="FTE", evidence_id=bank + "-row")
                      for bank, value in [("BAC", "100"), ("JPM", "250")]]
        self.hits = [Hit(chunk=Chunk(chunk_id=bank+"-chunk", document_id="source", bank=bank, strategy="semantic",
                                    text="Consumer segment revenue", location="Table", url="https://example.com",
                                    periods=["2025Q2"], evidence_ids=[bank+"-row"], token_count=20), score=1)
                     for bank in ["BAC", "JPM"]]

    def test_exact_user_wording_resolves_both_banks_and_period(self):
        scope = resolve(QUESTION, {"BAC", "JPM"}, {"2025Q2"})
        self.assertEqual(set(scope.banks), {"BAC", "JPM"})
        self.assertEqual(scope.periods, ["2025Q2"])
        self.assertEqual(resolve("JP Morgan consumer revenue Q2 2025", {"JPM"}, {"2025Q2"}).banks, ["JPM"])

    def test_comparison_uses_retrieved_values_not_fixed_answers_or_model_guesses(self):
        app = object.__new__(Application)
        app.generate = True
        with patch("ir_assistant.reported.load_reviewed_facts", return_value=self.facts), \
             patch("ir_assistant.workflow.generate_answer", side_effect=AssertionError("must not call model")):
            result = app.answer({"question": QUESTION, "scope": {"banks": ["BAC", "JPM"], "periods": ["2025Q2"]},
                                 "hits": self.hits, "calculations": []})
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["answer_mode"], "verified_reported_metrics")
        self.assertIn("Consumer & Community Banking", result["text"])
        self.assertIn("$150 million higher", result["text"])
        self.assertIn("150.0%", result["text"])
        self.assertIn("60.0% smaller (base: JPMorgan Chase)", result["text"])
        self.assertIn("150.0% larger (base: Bank of America)", result["text"])
        self.assertIn("2.50\u00d7", result["text"])
        self.assertIn("[BAC-chunk]", result["text"])
        self.assertIn("[JPM-chunk]", result["text"])
        self.assertEqual(result["usage"], {})

    def test_missing_bank_evidence_cannot_be_filled_from_the_fact_store(self):
        with patch("ir_assistant.reported.load_reviewed_facts", return_value=self.facts):
            result = reported_metric_answer(QUESTION, ["BAC", "JPM"], ["2025Q2"], self.hits[:1])
        self.assertIsNone(result)

    def test_other_period_or_metric_cannot_supply_requested_revenue(self):
        with patch("ir_assistant.reported.load_reviewed_facts", return_value=self.facts):
            self.assertIsNone(reported_metric_answer(QUESTION, ["BAC", "JPM"], ["2024Q2"], self.hits))
            self.assertIsNone(reported_metric_answer("Compare consumer expense Q2 2025", ["BAC", "JPM"], ["2025Q2"], self.hits))
            self.assertIsNone(reported_metric_answer("Compare consumer revenue per employee Q2 2025", ["BAC", "JPM"], ["2025Q2"], self.hits))

    def build_inputs(self):
        facts, hits = self.facts[:], self.hits[:]
        for base in self.facts:
            for metric, fraction in [("net_interest_income", Decimal("0.8")), ("noninterest_income", Decimal("0.2"))]:
                eid = base.bank + metric
                facts.append(replace(base, metric=metric, value=base.value * fraction, evidence_id=eid))
                hit = next(h for h in self.hits if h.chunk.bank == base.bank)
                hits.append(Hit(chunk=hit.chunk.model_copy(update={"chunk_id": eid, "evidence_ids": [eid]}), score=1))
        return facts, hits

    def test_revenue_build_reconciles_retrieved_components_and_compares_peers(self):
        facts, hits = self.build_inputs()
        question = "Explain the consumer revenue build-up for BAC and JPM Q2 2025 and compare them"
        with patch("ir_assistant.reported.load_reviewed_facts", return_value=facts):
            answer = reported_metric_answer(question, ["BAC", "JPM"], ["2025Q2"], hits)
        self.assertEqual(answer.status, "answered")
        text = " ".join(c.text for c in answer.claims)
        self.assertIn("$80 million + noninterest income/revenue $20 million = segment revenue $100 million", text)
        self.assertIn("$200 million + noninterest income/revenue $50 million = segment revenue $250 million", text)
        self.assertTrue(any("BACnet_interest_income" in c.citations for c in answer.claims))

    def test_build_refuses_missing_component_wrong_basis_or_nonreconciling_sum(self):
        facts, hits = self.build_inputs()
        question = "How is BAC consumer revenue calculated Q2 2025?"
        for values, evidence in [(facts, self.hits),
                                 ([replace(f, basis="GAAP") if f.metric == "net_interest_income" else f for f in facts], hits),
                                 ([replace(f, value=Decimal("999")) if f.metric == "net_interest_income" else f for f in facts], hits)]:
            with self.subTest(values=values, evidence=evidence), patch("ir_assistant.reported.load_reviewed_facts", return_value=values):
                answer = reported_metric_answer(question, ["BAC"], ["2025Q2"], evidence)
                self.assertEqual(answer.status, "insufficient_evidence")
                self.assertFalse(any("= segment revenue" in c.text for c in answer.claims))

    def test_peer_build_reserves_all_six_input_rows_within_token_budget(self):
        _, hits = self.build_inputs()
        labels = {"revenue": "Total net revenue", "net_interest_income": "Net interest income", "noninterest_income": "Noninterest revenue"}
        for hit in hits:
            metric = next((m for m in labels if m in hit.chunk.chunk_id), "revenue")
            hit.chunk.text = "Consumer Banking\nRow 1: c1=" + labels[metric] + " | c2=100"
        question = "Compare BAC and JPM consumer revenue components Q2 2025"
        self.assertEqual(len(select_final_hits(hits, ["BAC", "JPM"], question, ["2025Q2"])), 6)
        self.assertEqual(required_peer_metrics(question), ["revenue", "net_interest_income", "noninterest_income"])
        self.assertFalse(revenue_build_question("How is the gap in consumer revenue calculated?"))

    def test_zero_negative_and_equal_values_do_not_produce_invalid_ratios(self):
        for value in ["0", "-100", "250"]:
            with self.subTest(value=value), patch("ir_assistant.reported.load_reviewed_facts", return_value=[replace(self.facts[0], value=Decimal(value)), self.facts[1]]):
                answer = reported_metric_answer(QUESTION, ["BAC", "JPM"], ["2025Q2"], self.hits)
                self.assertFalse(any("ratio:" in c.text for c in answer.claims))

    def test_accounting_explanations_are_not_replaced_with_numeric_lookup(self):
        self.assertIsNone(reported_metric_answer("Explain FTE allocations in BAC consumer revenue Q2 2025", ["BAC"], ["2025Q2"], self.hits))

    def test_selected_bank_controls_percentage_denominator_and_ratio(self):
        with patch("ir_assistant.reported.load_reviewed_facts", return_value=self.facts):
            bac = reported_metric_answer(QUESTION, ["BAC", "JPM"], ["2025Q2"], self.hits, base_bank="BAC")
            jpm = reported_metric_answer(QUESTION, ["BAC", "JPM"], ["2025Q2"], self.hits, base_bank="JPM")
        bac_text = " ".join(c.text for c in bac.claims)
        jpm_text = " ".join(c.text for c in jpm.claims)
        self.assertIn("150.0% higher using Bank of America as the base", bac_text)
        self.assertIn("2.50\u00d7", bac_text)
        self.assertIn("60.0% lower using JPMorgan Chase as the base", jpm_text)
        self.assertIn("0.40\u00d7", jpm_text)
        self.assertNotIn("150.0%", jpm_text)

    def test_base_selection_supplies_scope_without_overriding_explicit_lookup(self):
        app = object.__new__(Application)
        app.banks, app.periods = {"BAC", "JPM"}, {"2025Q2"}
        scope = app.resolve_scope({"question": "Compare consumer revenue Q2 2025", "base_bank": "BAC"})["scope"]
        self.assertEqual(set(scope["banks"]), {"BAC", "JPM"})
        self.assertIsNone(scope["clarification"])
        lookup = app.resolve_scope({"question": "What was JPM consumer revenue Q2 2025?", "base_bank": "BAC"})["scope"]
        self.assertEqual(lookup["banks"], ["JPM"])
        self.assertEqual(app.resolve_scope({"question": "Compare consumer revenue", "base_bank": "BAC"})["status"], "clarification")
        self.assertEqual(app.resolve_scope({"question": "Compare consumer revenue Q2 2026", "base_bank": "BAC"})["status"], "insufficient_evidence")


if __name__ == "__main__":
    unittest.main()
