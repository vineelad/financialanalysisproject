"""Run these source-layout checks once dependencies are installed."""
import importlib.util
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path


@unittest.skipUnless(importlib.util.find_spec("bs4") and importlib.util.find_spec("httpx") and
                     importlib.util.find_spec("pdfplumber") and importlib.util.find_spec("pydantic") and
                     importlib.util.find_spec("dotenv"), "Ingestion dependencies are not installed")
class IngestionTests(unittest.TestCase):
    def test_pdf_rows_keep_the_source_quarter_order_and_page_provenance(self):
        from ir_assistant.ingest import extract_pdf
        from ir_assistant.models import Source
        source = Source(document_id="fixture", bank="WFC", title="Test", url="https://example.com/results.pdf",
                        format="pdf", periods=["2025Q2", "2024Q2"], publication_date="2025-07-15")
        page = MagicMock()
        page.extract_text.return_value = "Consumer Banking\nQuarter ended\nJun 30, Mar 31, Jun 30,\n2025 2025 2024\nEarnings (in millions)\nTotal revenue 110 105 100\nAverage balances (in billions)\nLoans 20 19 18"
        pdf = MagicMock()
        pdf.__enter__.return_value.pages = [page]
        with patch("ir_assistant.ingest.pdfplumber.open", return_value=pdf):
            blocks = extract_pdf(source, Path("fixture.pdf"))
        row = next(b for b in blocks if b.kind == "table")
        self.assertIn("c2=2Q25 | c3=1Q25 | c4=2Q24", row.text)
        self.assertIn("c1=Total revenue | c2=110 | c3=105 | c4=100", row.text)
        self.assertEqual(row.url, "https://example.com/results.pdf#page=1")
        self.assertEqual(row.evidence_ids, ["fixture:page1:line6"])
        self.assertFalse(any("c1=Loans" in b.text for b in blocks if b.kind == "table"))

    def test_pdf_ambiguous_date_headers_do_not_create_approved_looking_rows(self):
        from ir_assistant.ingest import extract_pdf
        from ir_assistant.models import Source
        source = Source(document_id="fixture", bank="WFC", title="Test", url="https://example.com/results.pdf",
                        format="pdf", periods=["2025Q2"], publication_date="2025-07-15")
        page = MagicMock()
        page.extract_text.return_value = "Consumer Banking\nEarnings (in millions)\nTotal revenue 110 105 100"
        pdf = MagicMock()
        pdf.__enter__.return_value.pages = [page]
        with patch("ir_assistant.ingest.pdfplumber.open", return_value=pdf):
            blocks = extract_pdf(source, Path("fixture.pdf"))
        self.assertEqual([b.kind for b in blocks], ["narrative"])

    def test_stacked_quarter_panels_update_the_active_header(self):
        from ir_assistant.ingest import extract_html
        from ir_assistant.models import Source
        source = Source(document_id="fixture", bank="BAC", title="Test", url="https://example.com/results",
                        format="html", periods=["2025Q2", "2024Q2"], publication_date="2025-07-16")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "panels.html"
            path.write_text('<table><tr><td>Consumer Banking</td></tr><tr><td>Second Quarter 2025</td></tr>'
                            '<tr><td>Revenue</td><td>110</td></tr><tr><td>Second Quarter 2024</td></tr>'
                            '<tr><td>Revenue</td><td>100</td></tr></table>', encoding="utf-8")
            row = extract_html(source, path)[-1]
            self.assertIn("Second Quarter 2024", row.text)
            self.assertNotIn("Second Quarter 2025", row.text)

    def test_colspan_compression_keeps_column_ranges(self):
        from ir_assistant.ingest import format_row
        self.assertEqual(format_row(["Metric", "Metric", "", "2025", "2024"]),
                         "c1-2=Metric | c4=2025 | c5=2024")

    def test_period_headers_after_title_and_units_are_retained(self):
        from ir_assistant.ingest import extract_html
        from ir_assistant.models import Source
        source = Source(document_id="fixture", bank="JPM", title="Test", url="https://example.com/results",
                        format="html", periods=["2025Q2", "2024Q2"], publication_date="2025-07-15")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "long-headers.html"
            path.write_text('<table><tr><td>JPMorgan Chase</td></tr><tr><td>Consumer Banking</td></tr>'
                            '<tr><td>USD millions</td></tr><tr><td>Quarterly trends</td></tr>'
                            '<tr><td>Metric</td><td>2Q25</td><td>2Q24</td></tr>'
                            '<tr><td>Revenue</td><td>110</td><td>100</td></tr></table>', encoding="utf-8")
            row = extract_html(source, path)[-1]
            self.assertIn("c2=2Q25", row.text)
            self.assertIn("c3=2Q24", row.text)

    def test_image_exhibit_text_layer_is_kept_as_narrative(self):
        from ir_assistant.ingest import extract_html
        from ir_assistant.models import Source
        source = Source(document_id="fixture", bank="BAC", title="Test", url="https://example.com/results",
                        format="html", periods=["2025Q2"], publication_date="2025-07-16")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "image-exhibit.html"
            text = "Consumer Banking Q2 2025 revenue and noninterest expense are reported in the following financial results. "
            path.write_text(f'<html><body><img src="page.png"><font>{text}</font></body></html>', encoding="utf-8")
            blocks = extract_html(source, path)
            self.assertEqual(len(blocks), 1)
            self.assertEqual(blocks[0].kind, "narrative")
            self.assertIn("not a parsed table", blocks[0].location)
            self.assertIn("Consumer Banking", blocks[0].text)

    def test_spans_preserve_year_column_alignment(self):
        from bs4 import BeautifulSoup
        from ir_assistant.ingest import expand_table
        table = BeautifulSoup('<table><tr><th rowspan="2">Metric</th><th colspan="2">Quarter</th></tr>'
                              '<tr><th>2025</th><th>2024</th></tr>'
                              '<tr><td>Revenue</td><td>110</td><td>100</td></tr></table>', 'html.parser').table
        rows = expand_table(table)
        self.assertEqual(rows[1], ["Metric", "2025", "2024"])
        self.assertEqual(rows[2], ["Revenue", "110", "100"])

    def test_negative_values_and_source_rows_survive_extraction(self):
        from ir_assistant.ingest import extract_html
        from ir_assistant.models import Source
        source = Source(document_id="fixture", bank="BAC", title="Test", url="https://example.com/results",
                        format="html", periods=["2025Q2", "2024Q2"], publication_date="2025-07-16")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "table.html"
            path.write_text('<h2>Consumer Banking</h2><table><tr><th>USD millions</th><th>2025</th><th>2024</th></tr>'
                            '<tr><td>Noninterest expense</td><td>(25)</td><td>30</td></tr></table>', encoding="utf-8")
            blocks = extract_html(source, path)
            row = next(b for b in blocks if "Row 2:" in b.text)
            self.assertIn("c2=(25)", row.text)
            self.assertIn("c3=30", row.text)
            self.assertEqual(row.evidence_ids, ["fixture:t1:r2"])
            self.assertEqual(row.location, "HTML table 1, row 2")


if __name__ == "__main__":
    unittest.main()
