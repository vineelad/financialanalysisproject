import unittest
from dataclasses import replace
from decimal import Decimal
from unittest.mock import patch

from ir_assistant.calculations import Fact
from ir_assistant.models import Chunk, Hit
from ir_assistant.reported import reported_metric_answer
from ir_assistant.retrieval import retrieval_budget, retrieval_queries, scope_matches, select_final_hits
from ir_assistant.scope import header_periods, resolve


BANKS = {"BAC", "JPM", "WFC", "C", "COF"}


class PeerDefaultTests(unittest.TestCase):
    def test_general_comparison_and_base_only_name_use_all_supported_peers(self):
        for q in ["Compare consumer revenue Q2 2025", "How does BAC consumer revenue compare Q2 2025?", "Compare BAC with its peers Q2 2025"]:
            with self.subTest(q=q):
                result = resolve(q, BANKS, {"2025Q2"}, base_bank="BAC")
                self.assertEqual(set(result.banks), BANKS)
                self.assertEqual(result.banks[0], "BAC")
                self.assertIsNone(result.unsupported)

    def test_named_peers_narrow_the_comparison(self):
        result = resolve("Compare consumer revenue with Wells Fargo and Citi Q2 2025", BANKS, {"2025Q2"}, base_bank="JPM")
        self.assertEqual(set(result.banks), {"JPM", "WFC", "C"})
        self.assertEqual(result.banks[0], "JPM")
        self.assertEqual(resolve("Compare consumer revenue with C in Q2 2025", BANKS, {"2025Q2"}, base_bank="JPM").banks, ["JPM", "C"])

    def test_lookup_and_financial_ratio_do_not_expand_to_other_banks(self):
        for q in ["What was Wells Fargo consumer revenue Q2 2025?", "What is Wells Fargo's consumer efficiency ratio Q2 2025?"]:
            with self.subTest(q=q):
                self.assertEqual(resolve(q, BANKS, {"2025Q2"}, base_bank="BAC").banks, ["WFC"])
        self.assertEqual(resolve("What was consumer revenue Q2 2025?", BANKS, {"2025Q2"}, base_bank="BAC").banks, ["BAC"])

    def test_time_comparison_stays_with_the_named_bank(self):
        self.assertEqual(resolve("Compare Wells Fargo consumer revenue Q2 2025 and Q2 2024", BANKS,
                                 {"2025Q2", "2024Q2"}, base_bank="BAC").banks, ["WFC"])
        self.assertEqual(set(resolve("Compare consumer operating leverage Q2 2025 and Q2 2024", BANKS,
                                     {"2025Q2", "2024Q2"}, base_bank="BAC").banks), BANKS)

    def test_missing_bank_is_not_silently_replaced_with_all_available_peers(self):
        result = resolve("Compare with Wells Fargo consumer revenue Q2 2025", {"BAC", "JPM"}, {"2025Q2"}, base_bank="BAC")
        self.assertIn("Wells Fargo", result.unsupported)

    def inputs(self):
        facts, hits = [], []
        for bank, value in [("BAC", "100"), ("JPM", "250"), ("WFC", "80"), ("C", "40"), ("COF", "20")]:
            facts.append(Fact(bank=bank, segment="consumer", metric="revenue", period="2025Q2", value=Decimal(value),
                              unit="USD_millions", basis="reported", evidence_id=bank))
            hits.append(Hit(chunk=Chunk(chunk_id=bank, document_id="fixture", bank=bank, strategy="fixed",
                text="Consumer Banking\nRow 1: c1=Total net revenue | c2="+value, location="fixture", url="https://example.com",
                periods=["2025Q2"], evidence_ids=[bank], token_count=350), score=1))
        return facts, hits

    def test_each_peer_uses_selected_base_and_its_own_citations(self):
        facts, hits = self.inputs()
        with patch("ir_assistant.reported.load_reviewed_facts", return_value=facts):
            result = reported_metric_answer("Compare consumer revenue Q2 2025", sorted(BANKS), ["2025Q2"], hits, base_bank="BAC")
        self.assertEqual(result.status, "answered")
        pairs = [c for c in result.claims if "using Bank of America as the base" in c.text]
        self.assertEqual(len(pairs), 4)
        self.assertTrue(any("150.0% higher" in c.text for c in pairs))
        self.assertTrue(any("20.0% lower" in c.text for c in pairs))
        self.assertTrue(all("BAC" in c.citations and len(c.citations) == 2 for c in pairs))
        self.assertTrue(any("Acquisition effects are not removed" in note for note in result.limitations))

    def test_missing_peer_preserves_available_figures_without_inventing_its_amount(self):
        facts, hits = self.inputs()
        with patch("ir_assistant.reported.load_reviewed_facts", return_value=facts):
            result = reported_metric_answer("Compare consumer revenue Q2 2025", sorted(BANKS), ["2025Q2"], [h for h in hits if h.chunk.bank != "C"], base_bank="BAC")
        self.assertEqual(result.status, "answered")
        self.assertTrue(any("Citi 2025Q2" in note and "unavailable" in note for note in result.limitations))
        self.assertFalse(any("Citi's" in c.text for c in result.claims))
        self.assertTrue(any("JPMorgan Chase" in c.text for c in result.claims))

    def test_missing_base_never_uses_another_bank_as_the_denominator(self):
        facts, hits = self.inputs()
        with patch("ir_assistant.reported.load_reviewed_facts", return_value=facts):
            result = reported_metric_answer("Compare consumer revenue Q2 2025", sorted(BANKS), ["2025Q2"], [h for h in hits if h.chunk.bank != "BAC"], base_bank="BAC")
        self.assertEqual(result.status, "insufficient_evidence")
        self.assertFalse(any("as the base" in c.text for c in result.claims))

    def test_bank_scaled_budgets_preserve_the_original_two_bank_limits(self):
        self.assertEqual(retrieval_budget("consumer revenue", ["BAC", "JPM"]), {"candidate_k": 20, "final_k": 5, "context_tokens": 2200})
        budget = retrieval_budget("consumer operating leverage", sorted(BANKS))
        self.assertEqual(budget, {"candidate_k": 50, "final_k": 10, "context_tokens": 5500})
        _, hits = self.inputs()
        final = select_final_hits(hits, sorted(BANKS), "consumer revenue", ["2025Q2"])
        self.assertEqual({h.chunk.bank for h in final}, BANKS)

    def test_new_source_period_headers_preserve_citi_and_capital_one_quarters(self):
        self.assertEqual(header_periods("Table header context:\nc3=2Q\u201925 | c6=1Q\u201925 | c9=2Q\u201924\nRow 1: x"), {"2025Q2", "2025Q1", "2024Q2"})
        self.assertEqual(header_periods("Table header context:\nc3-5=2025 | c19-21=2024\nc3-5=Q2 | c19-21=Q2\nRow 1: x"), {"2025Q2", "2024Q2"})

    def test_card_question_does_not_substitute_capital_one_consumer_banking(self):
        facts, hits = self.inputs()
        with patch("ir_assistant.reported.load_reviewed_facts", return_value=facts):
            self.assertIsNone(reported_metric_answer("Compare consumer credit card revenue Q2 2025", sorted(BANKS), ["2025Q2"], hits, base_bank="BAC"))

    def test_citi_acronym_query_expansion_uses_source_labels_without_source_amounts(self):
        queries = retrieval_queries("What was consumer revenue in Q2 2025?", ["C"])
        self.assertTrue(any("USPB" in q and "total revenues, net of interest expense" in q for q in queries))
        self.assertFalse(any("5119" in q for q in queries))

    def test_ceo_mention_does_not_make_a_consolidated_table_consumer_evidence(self):
        _, hits = self.inputs()
        chunk = hits[3].chunk.model_copy(update={"bank": "C", "text":
            "C | CEO mentions USPB\nTable header context:\nc1=Citigroup consolidated results | c2=CEO comments on USPB\nRow 1: c1=Total revenues, net of interest expense | c2=100"})
        self.assertFalse(scope_matches(chunk, "Citi consumer revenue Q2 2025"))
        chunk.text = "C | source\nTable header context:\nc1=USPB ($ in millions) | c2=2Q25\nRow 1: c1=Total revenues, net of interest expense | c2=100"
        self.assertTrue(scope_matches(chunk, "Citi consumer revenue Q2 2025"))


if __name__ == "__main__":
    unittest.main()
