"""Auditable arithmetic using reviewed, retrieved facts only."""
from dataclasses import dataclass
from decimal import Decimal
import re


@dataclass(frozen=True)
class Fact:
    bank: str
    segment: str
    metric: str
    period: str
    value: Decimal
    unit: str
    basis: str
    evidence_id: str
    period_type: str = "quarter"
    alternative_evidence_ids: tuple[str, ...] = ()


def growth(current: Fact, prior: Fact, retrieved_evidence: set[str]) -> Decimal:
    for fact in (current, prior):
        if fact.evidence_id not in retrieved_evidence:
            raise ValueError("Calculation input was not present in retrieved evidence")
        if not fact.basis or not fact.unit:
            raise ValueError("Missing reporting basis or units")
        if not fact.value.is_finite():
            raise ValueError("Financial values must be finite")
    for attribute in ("bank", "segment", "metric", "unit", "basis", "period_type"):
        if getattr(current, attribute) != getattr(prior, attribute):
            raise ValueError(f"Incompatible {attribute}")
    if current.period_type != "quarter":
        raise ValueError("Only quarterly growth is supported")
    if not re.fullmatch(r"20\d{2}Q[1-4]", current.period) or not re.fullmatch(r"20\d{2}Q[1-4]", prior.period):
        raise ValueError("Expected YYYYQn periods")
    if current.period[4:] != prior.period[4:] or int(current.period[:4]) != int(prior.period[:4]) + 1:
        raise ValueError("Expected the same quarter in consecutive years")
    if prior.value <= 0:
        raise ValueError("Growth with a nonpositive prior value requires manual interpretation")
    return (current.value / prior.value - 1) * 100


def operating_leverage(revenue_current: Fact, revenue_prior: Fact,
                       expense_current: Fact, expense_prior: Fact,
                       retrieved_evidence: set[str]) -> Decimal:
    if revenue_current.metric != "revenue" or expense_current.metric != "noninterest_expense":
        raise ValueError("Expected revenue and noninterest expense")
    for attribute in ("bank", "segment", "period", "basis", "period_type", "unit"):
        if getattr(revenue_current, attribute) != getattr(expense_current, attribute):
            raise ValueError(f"Incompatible revenue and expense {attribute}")
    return growth(revenue_current, revenue_prior, retrieved_evidence) - growth(expense_current, expense_prior, retrieved_evidence)
