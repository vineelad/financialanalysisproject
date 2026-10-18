"""Validate and render the coverage checklist; does not run queries or models."""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ir_assistant.metric_registry import load_coverage, load_registry


def render() -> Path:
    registry, checklist = load_registry(), load_coverage()
    counts = Counter(item.status for item in checklist.items)
    statuses = {"partial_existing_checks": "Partial existing checks", "unvalidated": "Unvalidated", "fully_validated": "Fully validated"}
    lines = ["# Analyst question coverage checklist", "",
             f"Assessment: {checklist.assessment_date}. Registry {registry.version}; checklist {checklist.version}.", "",
             checklist.analysis_scope, "", checklist.assessment_method, "",
             f"**{len(checklist.items)} families: {counts['fully_validated']} fully validated, "
             f"{counts['partial_existing_checks']} with partial existing checks, {counts['unvalidated']} unvalidated.**", "",
             f"The registry defines {len(registry.metrics)} metrics. Only "
             + ", ".join(f"`{m.id}`" for m in registry.metrics if m.reviewed_fact_enabled)
             + " are enabled in the reviewed consumer fact store. Existing source retrieval and calculation routes remain separately bounded.", "",
             "These counts describe coverage, not answer accuracy. Relevant text in a source does not establish a correct answer. "
             "The registry does not enable a new calculation or make bank definitions equivalent.", "",
             "## Implementation order", "",
             "1. Week 2: finish narrow consumer performance and reported profitability cases; review definitions before extending to margin and card NCOs.",
             "2. Next: review deposit, credit, capital and other segment inputs, then add matched-input calculations and independent cases.",
             "3. Later: add dated guidance, rate-risk, regulatory and market data with their own provenance and assumptions.", "",
             "## Family checklist", ""]
    for item in checklist.items:
        lines += [f"### {item.id}. {item.question}", "",
                  f"**{item.category} | {statuses[item.status]} | Priority: {item.priority}**", "",
                  "Metrics: " + ", ".join(f"`{mid}`" for mid in item.metric_ids) + ".", "",
                  "Existing checks: " + item.existing_checks, "",
                  "Gaps: " + " ".join(item.gaps), "", "Acceptance checks:", ""]
        lines.extend(f"- [{'x' if check in item.completed_acceptance_checks else ' '}] {check}" for check in item.acceptance_checks)
        lines += ["", "Next: " + item.next_step, ""]
        if item.evidence_refs:
            lines += ["Saved references: " + ", ".join(f"[{Path(ref).name}](../{ref})" for ref in item.evidence_refs) + ".", ""]
    lines += ["## Maintaining this checklist", "",
              "Edit `config/metric_registry.json` and `eval/analyst_coverage.json`, then run:", "",
              "```powershell", ".\\.venv\\Scripts\\python.exe scripts/report_analyst_coverage.py", "```", "",
              "Promotion to fully validated requires saved source-backed answer checks for the complete family, including "
              "its calculations and traps. Review every acceptance item and retain failures. References must be existing "
              "repository files; a partial retrieval report alone does not justify promotion. Freeze new acceptance cases "
              "before inspecting their retrieval. This checklist is not a gold evaluation dataset.", ""]
    path = ROOT / "docs" / "ANALYST_COVERAGE.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"metrics": len(registry.metrics), "families": len(checklist.items),
                      "coverage": {status: counts[status] for status in statuses}, "report": str(path)}))
    return path


if __name__ == "__main__":
    render()
