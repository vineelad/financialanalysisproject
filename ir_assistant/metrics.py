"""Dependency-free scoring against chunk-independent source evidence."""
import re


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def evidence_covered(unit: dict, chunks: list[dict]) -> bool:
    quote = normalize(unit["quote"])
    if not quote:
        raise ValueError("Gold evidence quotes must not be empty")
    variants = [unit, *unit.get("alternatives", [])]
    for variant in variants:
        variant_quote = normalize(variant["quote"])
        if not variant_quote:
            raise ValueError("Alternative evidence quotes must not be empty")
        if any(chunk["document_id"] == variant["document_id"] and variant_quote in normalize(chunk["text"]) for chunk in chunks):
            return True
    return False


def score_evidence(units: list[dict], chunks: list[dict]) -> dict:
    if not units:
        return {"evidence_recall": None, "precision": None}
    covered = sum(evidence_covered(unit, chunks) for unit in units)
    relevant = sum(any(evidence_covered(unit, [chunk]) for unit in units) for chunk in chunks)
    return {"evidence_recall": covered / len(units), "precision": relevant / len(chunks) if chunks else 0.0}
