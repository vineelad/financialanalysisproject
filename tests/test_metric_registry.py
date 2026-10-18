import json
import tempfile
import unittest
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from ir_assistant.calculations import Fact
from ir_assistant.facts import load_reviewed_facts
from ir_assistant.metric_registry import (MetricRegistry, load_coverage, load_registry,
    matches_metric_label, metric_definition, registry_metadata, validate_metric_context, validate_reviewed_fact)
from ir_assistant.retrieval import numeric_metric_row
from ir_assistant.models import Chunk


class MetricRegistryTests(unittest.TestCase):
    def test_all_current_reviewed_facts_pass_the_registry_contract(self):
        facts = load_reviewed_facts()
        self.assertTrue(facts)
        self.assertEqual({f.metric for f in facts}, {m.id for m in load_registry().metrics if m.reviewed_fact_enabled})
        for fact in facts:
            validate_reviewed_fact(fact)
        self.assertEqual(len(registry_metadata()["sha256"]), 64)

    def test_unreviewed_metrics_or_changed_scope_basis_units_period_are_rejected(self):
        fact = Fact(bank="BAC", segment="consumer", metric="revenue", period="2025Q2", value=Decimal("10"),
                    unit="USD_millions", basis="FTE", evidence_id="source-row")
        for changes in [{"metric": "not_a_metric"}, {"metric": "roa", "unit": "percent"},
                        {"segment": "consolidated"}, {"basis": "GAAP"}, {"unit": "USD_billions"},
                        {"period_type": "annual"}, {"period": "2025"}, {"value": Decimal("NaN")}, {"evidence_id": ""}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_reviewed_fact(replace(fact, **changes))

    def test_fact_loader_checks_registry_before_exposing_invalid_stored_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "reviewed_facts.json").write_text(json.dumps([dict(bank="BAC", segment="consumer", metric="revenue",
                period="2025Q2", value="10", unit="USD_billions", basis="FTE", evidence_id="source-row")]), encoding="utf-8")
            with patch("ir_assistant.facts.DATA", path), self.assertRaisesRegex(ValueError, "units or reporting basis"):
                load_reviewed_facts()

    def test_numeric_row_selection_uses_the_canonical_registry_labels(self):
        chunk = Chunk(chunk_id="row", document_id="fixture", bank="BAC", strategy="fixed", text="\nRow 1: c1=Total noninterest expense | c2=10",
                      location="fixture", url="https://example.com", periods=["2025Q2"], evidence_ids=["row"], token_count=10)
        self.assertTrue(numeric_metric_row(chunk, "expense"))
        self.assertFalse(numeric_metric_row(chunk, "revenue"))
        self.assertTrue(matches_metric_label("total net revenue", "revenue"))
        self.assertFalse(matches_metric_label("Card income", "noninterest_income"))

    def test_context_validation_requires_portfolio_and_rate_conventions(self):
        common = {"reporting_basis": "reported", "segment_definition": "source-defined"}
        with self.assertRaisesRegex(ValueError, "portfolio"):
            validate_metric_context("card_nco_rate", common)
        with self.assertRaisesRegex(ValueError, "annualization"):
            validate_metric_context("card_nco_rate", {**common, "portfolio": "card", "annualization": " ", "loan_denominator": "average card loans"})
        validate_metric_context("card_nco_rate", {**common, "portfolio": "card", "annualization": "as disclosed", "loan_denominator": "average card loans"})
        self.assertFalse(metric_definition("card_nco_rate").reviewed_fact_enabled)

    def test_registry_rejects_duplicate_ids_and_incomplete_enabled_contract(self):
        raw = load_registry().model_dump()
        raw["metrics"] = [raw["metrics"][0], raw["metrics"][0]]
        with self.assertRaisesRegex(ValidationError, "Duplicate"):
            MetricRegistry.model_validate(raw)
        metric = load_registry().metrics[0].model_dump()
        metric["reviewed_scopes"] = []
        with self.assertRaisesRegex(ValidationError, "explicit scopes and bases"):
            MetricRegistry.model_validate({"version": "test", "scope": "fixture", "metrics": [metric]})

    def test_coverage_has_all_families_without_claiming_full_answer_accuracy(self):
        coverage = load_coverage()
        self.assertEqual({item.id for item in coverage.items}, {f"Q{i:02d}" for i in range(1, 29)})
        self.assertEqual(sum(i.status == "partial_existing_checks" for i in coverage.items), 7)
        self.assertEqual(sum(i.status == "fully_validated" for i in coverage.items), 0)
        self.assertTrue(all(item.acceptance_checks and item.gaps for item in coverage.items))

    def test_coverage_rejects_unknown_metrics_and_missing_or_escaping_references(self):
        for change in [{"metric_ids": ["made_up"]}, {"evidence_refs": ["no-such-evidence.json"]},
                       {"evidence_refs": ["../outside-workspace.txt"]}, {"evidence_refs": []},
                       {"status": "fully_validated"}, {"completed_acceptance_checks": ["Unlisted check"]}]:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                raw = load_coverage().model_dump(mode="json")
                raw["items"][0].update(change)
                path = Path(directory) / "coverage.json"
                path.write_text(json.dumps(raw), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_coverage(path)


if __name__ == "__main__":
    unittest.main()
