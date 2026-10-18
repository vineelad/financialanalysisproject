"""Build a local submission zip from explicit public/project files only."""
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    validation = json.loads((ROOT / "reports/five-bank-answer-validation.json").read_text(encoding="utf-8"))
    if validation["passed"] != validation["total"]:
        raise ValueError("Resolve the recorded answer-check failures before packaging")
    if not json.loads((ROOT / "reports/final-provider-check.json").read_text(encoding="utf-8"))["passed"]:
        raise ValueError("Resolve the final provider explanation check before packaging")
    if not (ROOT / "reports/five-bank-retrieval/REPORT.md").is_file():
        raise ValueError("Export the completed four-condition experiment before packaging")
    files = []
    for name in ["ir_assistant", "scripts", "tests", "config", "eval", "docs", "reports"]:
        files.extend(p for p in (ROOT / name).rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix in {".py", ".json", ".jsonl", ".md", ".txt", ".csv"})
    files.extend(ROOT / name for name in ["app.py", "README.md", "WEEK_2_PROJECT_PLAN.md", "requirements.txt", "requirements.lock.txt", ".env.example", ".gitignore"])
    files.extend(ROOT / "data" / name for name in ["reviewed_facts.json", "fact_provenance.json", "peer_fact_provenance.json"])
    files.extend(ROOT / "data/snapshots/two-bank-v1" / name for name in ["reviewed_facts.json", "fact_provenance.json", "snapshot.json"])
    for source in json.loads((ROOT / "config/sources.json").read_text(encoding="utf-8")):
        files.append(ROOT / "data/raw" / f"{source['document_id']}.{source['format']}")
    files = sorted(set(files))
    for path in files:
        if not path.resolve().is_relative_to(ROOT) or not path.is_file():
            raise ValueError(f"Missing or unsafe package member: {path.name}")
        if path.name != ".env.example" and (path.name.startswith(".env") or path.suffix == ".env" or "pineconekey" in path.name.lower()):
            raise ValueError("Credential file excluded from package")
        if path.suffix not in {".pdf", ".html"}:
            value = path.read_text(encoding="utf-8")
            if re.search(r"\bv1\.[A-Za-z0-9_-]{60,}\.[A-Za-z0-9_-]{60,}", value) or re.search(r"\bsk-[A-Za-z0-9_-]{32,}", value):
                raise ValueError(f"Potential credential in {path.relative_to(ROOT)}; inspect locally before packaging")
    target = ROOT / "artifacts"
    target.mkdir(exist_ok=True)
    archive = target / "week2-ir-assistant.zip"
    manifest = [{"path": p.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for path in files:
            output.write(path, path.relative_to(ROOT).as_posix())
        output.writestr("PACKAGE_MANIFEST.json", json.dumps(manifest, indent=2))
    print(json.dumps({"archive": str(archive), "files": len(files), "bytes": archive.stat().st_size,
                      "excludes": ["private env/key files", "model caches", "vector indexes", "runtime sessions"]}))


if __name__ == "__main__":
    main()
