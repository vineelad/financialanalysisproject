"""Financial definitions and capability boundaries; no model or network calls.

Cataloguing a metric does not enable its calculation. Current reviewed fact
routes and retrieval selectors explicitly opt in to registry definitions.
"""
import json
import hashlib
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .settings import ROOT
from .banks import bank_registry


class MetricDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str
    definition: str
    unit: str
    time_basis: Literal["flow", "period_end", "average", "reported_ratio", "scenario", "guidance", "market_snapshot", "count", "disclosure"]
    required_dimensions: tuple[str, ...]
    comparison_traps: tuple[str, ...]
    formula: str | None = None
    numerator: str | None = None
    denominator: str | None = None
    # This is an existing implementation, not a promise inferred from a formula.
    reviewed_fact_enabled: bool = False
    reviewed_scopes: tuple[str, ...] = ()
    allowed_reviewed_bases: tuple[str, ...] = ()
    retrieval_labels: dict[str, tuple[str, ...]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_reviewed_contract(self):
        if self.reviewed_fact_enabled and not (self.reviewed_scopes and self.allowed_reviewed_bases):
            raise ValueError("Enabled reviewed facts require explicit scopes and bases")
        return self


class MetricRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    scope: str
    metrics: tuple[MetricDefinition, ...]

    @model_validator(mode="after")
    def unique_ids(self):
        ids = [m.id for m in self.metrics]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate metric IDs")
        return self


@lru_cache(maxsize=4)
def _read_registry(path: str, stamp: int, size: int) -> MetricRegistry:
    return MetricRegistry.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def load_registry() -> MetricRegistry:
    path = ROOT / "config" / "metric_registry.json"
    stat = path.stat()
    return _read_registry(str(path), stat.st_mtime_ns, stat.st_size)


def registry_metadata() -> dict:
    return {"version": load_registry().version,
            "sha256": hashlib.sha256((ROOT / "config" / "metric_registry.json").read_bytes()).hexdigest()}


def validate_metric_context(metric_id: str, context: dict) -> None:
    """Require source-defined conventions before future metric routes use them.

    This validates metadata presence, not financial correctness or source support.
    It neither supplies missing conventions nor enables a calculation.
    """
    definition = metric_definition(metric_id)
    missing = [name for name in definition.required_dimensions
               if context.get(name) is None or (isinstance(context.get(name), str) and not context[name].strip())]
    if missing:
        raise ValueError(f"{metric_id}: missing comparability context: {', '.join(missing)}")


def metric_definition(metric_id: str) -> MetricDefinition:
    for metric in load_registry().metrics:
        if metric.id == metric_id:
            return metric
    raise ValueError(f"Unknown financial metric: {metric_id}")


def matches_metric_label(label: str, metric_id: str) -> bool:
    definition = metric_definition(metric_id)
    return label.casefold() in {v.casefold() for values in definition.retrieval_labels.values() for v in values}


def validate_reviewed_fact(fact) -> None:
    """Reject unsupported stored facts before they reach answer/calculation routes."""
    definition = metric_definition(fact.metric)
    if not definition.reviewed_fact_enabled:
        raise ValueError(f"Reviewed facts are not enabled for {fact.metric}")
    if fact.segment not in definition.reviewed_scopes:
        raise ValueError(f"Unreviewed scope for {fact.metric}: {fact.segment}")
    if fact.unit != definition.unit or fact.basis not in definition.allowed_reviewed_bases:
        raise ValueError(f"Unreviewed units or reporting basis for {fact.metric}")
    bank = bank_registry().get(fact.bank)
    if not bank or fact.basis != bank.get("reviewed_basis"):
        raise ValueError(f"Unreviewed units or reporting basis for {fact.bank}")
    if fact.period_type != "quarter" or not re.fullmatch(r"20\d{2}Q[1-4]", fact.period):
        raise ValueError("Reviewed facts currently require explicit quarterly periods")
    if not fact.value.is_finite() or not fact.evidence_id:
        raise ValueError("Reviewed facts require a finite value and a source evidence ID")


class CoverageItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^Q\d{2}$")
    category: str
    question: str
    metric_ids: tuple[str, ...]
    status: Literal["partial_existing_checks", "unvalidated", "fully_validated"]
    existing_checks: str
    evidence_refs: tuple[str, ...] = ()
    gaps: tuple[str, ...] = ()
    acceptance_checks: tuple[str, ...] = Field(min_length=1)
    completed_acceptance_checks: tuple[str, ...] = ()
    next_step: str
    priority: Literal["week2", "next", "later"]


class CoverageChecklist(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    assessment_date: str
    assessment_method: str
    analysis_scope: str
    items: tuple[CoverageItem, ...]


def load_coverage(path: Path | None = None) -> CoverageChecklist:
    checklist = CoverageChecklist.model_validate(json.loads((path or ROOT / "eval" / "analyst_coverage.json").read_text(encoding="utf-8")))
    if {item.id for item in checklist.items} != {f"Q{i:02d}" for i in range(1, 29)} or len(checklist.items) != 28:
        raise ValueError("Coverage checklist must contain 28 unique question families")
    for item in checklist.items:
        if not set(item.completed_acceptance_checks).issubset(item.acceptance_checks):
            raise ValueError(f"{item.id}: unknown completed acceptance check")
        if item.status == "fully_validated" and (item.gaps or set(item.completed_acceptance_checks) != set(item.acceptance_checks)):
            raise ValueError(f"{item.id}: full validation requires closed gaps and all acceptance checks completed")
        if item.status != "fully_validated" and not item.gaps:
            raise ValueError(f"{item.id}: incomplete families require explicit gaps")
        for metric_id in item.metric_ids:
            metric_definition(metric_id)
        if item.status != "unvalidated" and not item.evidence_refs:
            raise ValueError(f"{item.id}: coverage claims require saved evidence references")
        for reference in item.evidence_refs:
            target = (ROOT / reference).resolve()
            if not target.is_relative_to(ROOT.resolve()) or not target.is_file():
                raise ValueError(f"{item.id}: missing or invalid evidence reference: {reference}")
    return checklist
