import unittest

from ir_assistant.models import Chunk, GeneratedAnswer, Hit
from ir_assistant.generation import complete_segment_answer, segment_context
from ir_assistant.retrieval import numeric_metric_row, prefer_segment_overviews, select_final_hits


def chunk(cid, bank, text="Detailed business line", tokens=100):
    return Chunk(chunk_id=cid, document_id="fixture", bank=bank, strategy="fixed", text=text,
                 location="fixture", url="https://example.com", periods=["2025Q2"],
                 evidence_ids=[cid], token_count=tokens)


class PeerRetrievalTests(unittest.TestCase):
    def test_structure_questions_prefer_overviews_for_each_bank_without_inventing_evidence(self):
        chunks = [chunk("a", "JPM", "TABLE OF CONTENTS"), chunk("b", "JPM"),
                  chunk("c", "BAC", "Quarterly Results by Business Segment"), chunk("d", "BAC")]
        result = prefer_segment_overviews(chunks, "Which corporate segment names do these banks report?")
        self.assertEqual([c.chunk_id for c in result], ["a", "c"])

    def test_a_bank_without_an_overview_retains_its_candidates(self):
        chunks = [chunk("a", "JPM", "TABLE OF CONTENTS"), chunk("b", "BAC")]
        self.assertEqual(prefer_segment_overviews(chunks, "Compare segment scope"), chunks)

    def test_numeric_segment_lookup_is_not_restricted_to_overviews(self):
        chunks = [chunk("a", "JPM", "TABLE OF CONTENTS"), chunk("b", "JPM")]
        self.assertEqual(prefer_segment_overviews(chunks, "What was consumer segment revenue in Q2 2025?"), chunks)

    def test_final_selection_reserves_available_evidence_per_bank(self):
        hits = [Hit(chunk=chunk(str(i), "JPM"), score=10-i) for i in range(6)]
        hits.append(Hit(chunk=chunk("peer", "BAC"), score=1))
        result = select_final_hits(hits, ["JPM", "BAC"])
        self.assertEqual(len(result), 5)
        self.assertEqual({h.chunk.bank for h in result}, {"JPM", "BAC"})
        self.assertEqual(len({h.chunk.chunk_id for h in result}), 5)

    def test_bank_coverage_never_exceeds_context_budget(self):
        hits = [Hit(chunk=chunk("large", "JPM", tokens=2300), score=3),
                Hit(chunk=chunk("small", "JPM", tokens=200), score=2),
                Hit(chunk=chunk("peer", "BAC", tokens=200), score=1)]
        result = select_final_hits(hits, ["JPM", "BAC"])
        self.assertEqual([h.chunk.chunk_id for h in result], ["small", "peer"])

    def test_numeric_metric_selection_rejects_empty_headings_and_submetrics(self):
        self.assertFalse(numeric_metric_row(chunk("a", "JPM", "header\nRow 1: c1=REVENUE"), "revenue"))
        self.assertFalse(numeric_metric_row(chunk("b", "JPM", "header\nRow 2: c1=Noninterest revenue | c4=42"), "revenue"))
        self.assertTrue(numeric_metric_row(chunk("c", "JPM", "header\nRow 3: c1=TOTAL NET REVENUE | c4=100"), "revenue"))

    def test_peer_metric_rows_are_preserved_without_using_reviewed_facts(self):
        hits = [Hit(chunk=chunk(str(i), "JPM"), score=10-i) for i in range(5)]
        hits.extend([Hit(chunk=chunk("jpm-value", "JPM", "header\nRow 1: c1=TOTAL NET REVENUE | c4=100"), score=0.2),
                     Hit(chunk=chunk("bac-value", "BAC", "header\nRow 1: c1=Total revenue, net of interest expense | c4=200"), score=0.1)])
        selected = select_final_hits(hits, ["JPM", "BAC"], "Compare consumer revenue at both banks")
        self.assertTrue({"jpm-value", "bac-value"}.issubset({h.chunk.chunk_id for h in selected}))
        self.assertLessEqual(len(selected), 5)

    def test_segment_context_preserves_literal_labels_and_source_citations(self):
        text = ('Table header context:\nQuarterly Results by Business Segment\n'
                'c1-3=Total Corporation | c4-6=Retail | c7-9=Markets | c10-12=All Other\n'
                'Row 1: c1=Revenue | c4=100')
        labels = segment_context([Hit(chunk=chunk("overview", "BAC", text), score=1)])
        self.assertEqual([item["label"] for item in labels], ["Retail", "Markets"])
        self.assertTrue(all(item["citations"] == ["overview"] for item in labels))

    def test_detailed_business_line_is_not_labeled_as_a_reported_segment(self):
        text = 'Table header context:\nFinancial Highlights\nRow 1: c1=Global Corporate Banking | c4=100'
        self.assertEqual(segment_context([Hit(chunk=chunk("detail", "JPM", text), score=1)]), [])

    def test_omitted_segment_uses_a_complete_source_summary_without_inventing_scope(self):
        answer = GeneratedAnswer(status="answered", claims=[{"text": "Alpha Bank and Beta Banking.", "citations": ["a", "b"]}])
        labels = [{"bank": "JPM", "label": "Alpha Bank", "citations": ["a"]},
                  {"bank": "BAC", "label": "Beta Banking", "citations": ["b"]},
                  {"bank": "BAC", "label": "Beta Markets", "citations": ["b"]}]
        result, fallback = complete_segment_answer(answer, labels, ["JPM", "BAC"])
        self.assertTrue(fallback)
        self.assertIn("Beta Markets", result.claims[1].text)
        self.assertEqual(result.claims[1].citations, ["b"])
        self.assertIn("do not establish equivalent", result.limitations[0])

    def test_source_summary_cannot_invent_a_missing_bank(self):
        answer = GeneratedAnswer(status="insufficient_evidence")
        result, fallback = complete_segment_answer(answer, [{"bank": "JPM", "label": "Alpha Bank", "citations": ["a"]}], ["JPM", "BAC"])
        self.assertFalse(fallback)
        self.assertEqual(result.status, "insufficient_evidence")


if __name__ == "__main__":
    unittest.main()
