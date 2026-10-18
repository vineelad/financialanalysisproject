"""Answer covered reported-metric lookups from verified, retrieved facts.

Comparability caveats do not invalidate the banks' explicitly reported figures.
No amount is supplied unless its reviewed source row was actually retrieved.
"""
import re
from dataclasses import replace
from decimal import Decimal

from .facts import load_reviewed_facts
from .models import Claim, GeneratedAnswer, Hit
from .retrieval import narrative_question, required_peer_metrics, revenue_build_question, segment_structure_question
from .scope import consumer_only
from .banks import bank_registry


NAMES = {bank: (item["name"], item["consumer_segment"]) for bank, item in bank_registry().items()}


def reported_metric_answer(question: str, banks: list[str], periods: list[str], hits: list[Hit], base_bank: str | None = None) -> GeneratedAnswer | None:
    build = revenue_build_question(question)
    if (not consumer_only(question) or (narrative_question(question) and not build) or segment_structure_question(question)
            or re.search(r"\b(growth|grew|leverage|margin|share|adjusted|forecast|predict|definition|defined|mix|card|mortgage|auto)\b|\bper\s+(employee|branch|customer)", question, re.I)
            or re.search(r"funds transfer|\bFTE\b|taxable.equivalent|allocations?|managed basis", question, re.I)):
        return None
    metrics = required_peer_metrics(question)
    if (not build and (len(metrics) != 1 or metrics[0] not in {"revenue", "expense"})) or not banks or not periods:
        return None
    metric_question = re.sub(r"net of interest expense", "", question, flags=re.I).lower()
    if "revenue" in metric_question and "expense" in metric_question:
        return None
    metric = "noninterest_expense" if metrics[0] == "expense" else "revenue"
    retrieved = {eid: h.chunk.chunk_id for h in hits for eid in h.chunk.evidence_ids}
    available = []
    for fact in load_reviewed_facts():
        supporting = [eid for eid in (fact.evidence_id, *fact.alternative_evidence_ids) if eid in retrieved]
        if supporting:
            available.append(replace(fact, evidence_id=supporting[0]))
    facts, missing = [], []
    for bank in banks:
        for period in periods:
            matches = [f for f in available if f.bank == bank and f.period == period and f.segment == "consumer"
                       and f.metric == metric and f.period_type == "quarter" and f.value.is_finite()]
            if len(matches) != 1 or bank not in NAMES:
                if base_bank and bank in NAMES:
                    missing.append(f"{NAMES[bank][0]} {period}: reviewed {metric.replace('_', ' ')} is unavailable in the retrieved evidence.")
                    continue
                return None
            facts.append(matches[0])

    def amount(value, unit):
        display = format(value, ',f').rstrip('0').rstrip('.') if value.as_tuple().exponent < 0 else format(value, ',f')
        return f"${display} million" if unit == "USD_millions" else f"{display} {unit.replace('_', ' ')}"

    claims = []
    for fact in facts:
        bank_name, segment_name = NAMES[fact.bank]
        period = f"Q{fact.period[-1]} {fact.period[:4]}"
        claims.append(Claim(text=f"{bank_name}'s {segment_name} reported {metric.replace('_', ' ')} of "
                            f"{amount(fact.value, fact.unit)} in {period} ({fact.basis.replace('_', '/')} basis).",
                            citations=[retrieved[fact.evidence_id]]))
    limitations = missing[:]
    if build:
        for fact in facts:
            inputs = [[f for f in available if f.bank == fact.bank and f.period == fact.period
                       and f.segment == fact.segment and f.metric == metric_name and f.period_type == "quarter"
                       and f.unit == fact.unit and f.basis == fact.basis and f.value.is_finite()]
                      for metric_name in ("net_interest_income", "noninterest_income")]
            if any(len(group) != 1 for group in inputs):
                limitations.append(f"{NAMES[fact.bank][0]}'s revenue build-up requires retrieved, reviewed net interest income and noninterest income rows on the same basis and period.")
                continue
            nii, noninterest = (group[0] for group in inputs)
            if nii.value + noninterest.value != fact.value:
                limitations.append(f"{NAMES[fact.bank][0]}'s retrieved components do not reconcile to reported revenue; no build-up is asserted.")
                continue
            claims.append(Claim(text=f"{NAMES[fact.bank][0]}, Q{fact.period[-1]} {fact.period[:4]}: "
                                f"net interest income {amount(nii.value, fact.unit)} + noninterest income/revenue "
                                f"{amount(noninterest.value, fact.unit)} = segment revenue {amount(fact.value, fact.unit)}.",
                                citations=list(dict.fromkeys(retrieved[f.evidence_id] for f in (nii, noninterest, fact)))))
    base = next((fact for fact in facts if fact.bank == base_bank), None)
    if base_bank and len(banks) > 1 and len(periods) == 1:
        if base is not None:
            for peer in facts:
                if peer.bank == base_bank:
                    continue
                if peer.unit != base.unit:
                    limitations.append(f"{NAMES[peer.bank][0]} cannot be compared arithmetically with the base because its units differ.")
                    continue
                gap = peer.value - base.value
                base_name, peer_name = NAMES[base.bank][0], NAMES[peer.bank][0]
                direction = "higher" if gap > 0 else "lower"
                statement = (f"{peer_name}'s reported figure was {amount(abs(gap), base.unit)} {direction} than {base_name}."
                             if gap else f"{peer_name} and {base_name} reported equal figures.")
                if base.value > 0 and peer.value >= 0:
                    percent = (abs(gap) / base.value * 100).quantize(Decimal('0.1'))
                    ratio = (peer.value / base.value).quantize(Decimal('0.01'))
                    statement += (f" That is {percent}% {direction} using {base_name} as the base; "
                                  f"{peer_name}/{base_name} {metric.replace('_', ' ')} ratio: {ratio}\u00d7." if gap else
                                  f" Base bank: {base_name}; {peer_name}/{base_name} ratio: {ratio}\u00d7.")
                else:
                    statement += f" Percentage and ratio require a positive base and nonnegative peer figure. Base bank: {base_name}."
                claims.append(Claim(text=statement, citations=list(dict.fromkeys(retrieved[f.evidence_id] for f in (base, peer)))))
    elif len(banks) == 2 and len(periods) == 1 and len({f.unit for f in facts}) == 1:
        higher, lower = sorted(facts, key=lambda f: f.value, reverse=True)
        difference = higher.value - lower.value
        high_name, low_name = NAMES[higher.bank][0], NAMES[lower.bank][0]
        relative = ""
        if lower.value > 0 and difference:
            above = (difference / lower.value * 100).quantize(Decimal('0.1'))
            below = (difference / higher.value * 100).quantize(Decimal('0.1'))
            ratio = (higher.value / lower.value).quantize(Decimal('0.01'))
            relative = (f" {high_name} was {above}% larger (base: {low_name}); "
                        f"{low_name} was {below}% smaller (base: {high_name}). "
                        f"{high_name}/{low_name} {metric.replace('_', ' ')} ratio: {ratio}\u00d7.")
        statement = (f"{high_name}'s reported figure was {amount(difference, higher.unit)} higher."
                     if difference else "The reported figures were equal.")
        claims.append(Claim(text=statement + relative, citations=list(dict.fromkeys(retrieved[f.evidence_id] for f in facts))))
    if len(banks) > 1:
        limitations.append("These are reported segment figures without peer adjustments; segment scope, reporting conventions and internal allocations may differ.")
    if "COF" in banks:
        limitations.append("Capital One comparisons use the reported Consumer Banking segment. Acquisition effects are not removed; combined Consumer Banking/Credit Card comparisons are not supported by this calculation.")
    return GeneratedAnswer(status="insufficient_evidence" if not facts or (base_bank and len(banks) > 1 and base is None) or
                           (build and any("build-up" in line or "reconcile" in line for line in limitations)) else "answered",
                           claims=claims, limitations=limitations)
