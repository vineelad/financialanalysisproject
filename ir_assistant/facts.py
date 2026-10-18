"""Manually reviewed facts supplement extraction, but never bypass retrieval."""
import json
from dataclasses import asdict, replace
from decimal import Decimal

from .calculations import Fact, growth, operating_leverage
from .models import Hit
from .metric_registry import validate_reviewed_fact
from .settings import DATA


def load_reviewed_facts() -> list[Fact]:
    path = DATA / "reviewed_facts.json"
    if not path.exists():
        return []
    values = json.loads(path.read_text(encoding="utf-8"))
    facts = [Fact(**{**item, "value": Decimal(str(item["value"])),
                    "alternative_evidence_ids": tuple(item.get("alternative_evidence_ids", []))}) for item in values]
    for fact in facts:
        validate_reviewed_fact(fact)
    return facts


def calculate(question: str, banks: list[str], periods: list[str], hits: list[Hit]) -> list[dict]:
    text = question.lower()
    if not any(word in text for word in ("growth", "grew", "leverage")):
        return []
    if not any(word in text for word in ("revenue", "expense", "leverage")):
        raise ValueError("Reviewed growth calculations currently support revenue and noninterest expense only")
    if not any(word in text for word in ("consumer", "ccb")):
        raise ValueError("Reviewed calculations currently support consumer banking only")
    if any(word in text for word in ("credit card", "branded card", "mortgage", "auto loan")):
        raise ValueError("Reviewed growth calculations cover reported consumer segments, not their individual product lines")
    if len(periods) != 2:
        raise ValueError("A year-over-year calculation requires two explicit quarters")
    retrieved = {eid for hit in hits for eid in hit.chunk.evidence_ids}
    facts = []
    for fact in load_reviewed_facts():
        supported = [eid for eid in (fact.evidence_id, *fact.alternative_evidence_ids) if eid in retrieved]
        if supported:
            # Cite the equivalent reviewed row that was actually retrieved.
            facts.append(replace(fact, evidence_id=supported[0]))
    if not facts:
        raise ValueError("Required reviewed financial inputs are absent from the selected evidence")
    results = []
    for bank in banks:
        def get(metric: str, period: str) -> Fact:
            matching = [f for f in facts if f.bank == bank and f.segment == "consumer" and f.metric == metric and f.period == period]
            if len(matching) != 1:
                raise ValueError(f"Missing or conflicting retrieved {bank} {period} {metric} inputs")
            return matching[0]
        prior, current = sorted(periods)
        if "leverage" in text:
            inputs = [get("revenue", current), get("revenue", prior),
                      get("noninterest_expense", current), get("noninterest_expense", prior)]
            value = operating_leverage(*inputs, retrieved_evidence=retrieved)
            formula = "revenue YoY growth minus noninterest expense YoY growth"
            unit = "percentage points"
            components = {"revenue_growth": str(growth(inputs[0], inputs[1], retrieved_evidence=retrieved).quantize(Decimal("0.01"))),
                          "expense_growth": str(growth(inputs[2], inputs[3], retrieved_evidence=retrieved).quantize(Decimal("0.01")))}
        else:
            metric = "noninterest_expense" if "expense" in text else "revenue"
            inputs = [get(metric, current), get(metric, prior)]
            value = growth(*inputs, retrieved_evidence=retrieved)
            formula = "(current / prior - 1) * 100"
            unit = "percent"
            components = {}
        results.append({"bank": bank, "value": str(value.quantize(Decimal("0.01"))), "unit": unit,
                        "formula": formula, "components": components,
                        "inputs": [{**asdict(f), "value": str(f.value)} for f in inputs]})
    return results
