"""Immutable raw downloads and inspectable, source-linked text/table blocks."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pdfplumber
from bs4 import BeautifulSoup

from .models import Block, Source
from .settings import DATA, ROOT
from .storage import write_json, write_jsonl


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def expand_table(table) -> list[list[str]]:
    """Expand HTML spans without shifting values into another period's column."""
    grid: dict[tuple[int, int], str] = {}
    rows = [row for row in table.find_all("tr") if row.find_parent("table") is table]
    for row_index, row in enumerate(rows):
        column = 0
        for cell in row.find_all(["td", "th"], recursive=False):
            while (row_index, column) in grid:
                column += 1
            value = clean(cell.get_text(" ", strip=True))
            rowspan = min(int(cell.get("rowspan", 1)), 100)
            colspan = min(int(cell.get("colspan", 1)), 100)
            for dr in range(rowspan):
                for dc in range(colspan):
                    grid[row_index + dr, column + dc] = value
            column += colspan
    width = max((c for _, c in grid), default=-1) + 1
    return [[grid.get((r, c), "") for c in range(width)] for r in range(len(rows))]


def format_row(row: list[str]) -> str:
    """Compress repeated colspan values while retaining original column ranges."""
    values, index = [], 0
    while index < len(row):
        value = row[index]
        end = index + 1
        while end < len(row) and row[end] == value:
            end += 1
        if value:
            columns = f"c{index + 1}" if end == index + 1 else f"c{index + 1}-{end}"
            values.append(f"{columns}={value}")
        index = end
    return " | ".join(values)


def extract_html(source: Source, path: Path) -> list[Block]:
    soup = BeautifulSoup(path.read_bytes(), "html.parser")
    for node in soup(["script", "style", "nav", "footer", "header"]):
        node.decompose()
    blocks = []
    # Leaf tables avoid duplicating entire nested SEC document layouts.
    for table_number, table in enumerate(soup.find_all("table"), 1):
        if table.find("table"):
            continue
        rows = expand_table(table)
        if not rows:
            continue
        anchor = table.get("id") or table.find_previous(attrs={"id": True})
        anchor_id = anchor if isinstance(anchor, str) else (anchor.get("id") if anchor else None)
        location = f"HTML table {table_number}"
        url = source.url + (f"#{anchor_id}" if anchor_id else "")
        previous = table.find_previous(["h1", "h2", "h3", "h4", "p"])
        context = clean(previous.get_text(" "))[:500] if previous else source.title
        # Preserve explicit column positions, including blank currency/spacer cells.
        headers = []
        for row in rows[:20]:
            line = format_row(row)
            # Quarter labels (2Q25), year columns, and captions are headers,
            # not financial data. Stop at the first actual amount row.
            has_amount = any(re.fullmatch(r"[-\u2212]?\(?[\d,]+(?:\.\d+)?\)?%?", v)
                             and not re.fullmatch(r"20\d{2}", v) for v in row if v)
            if has_amount and headers:
                break
            if line:
                headers.append(line)
        header_text = "\n".join(headers)
        panel_pattern = re.compile(r"(?:First|Second|Third|Fourth) Quarter\s+20\d{2}", re.I)
        for row_number, row in enumerate(rows, 1):
            if not any(row):
                continue
            row_id = f"{source.document_id}:t{table_number}:r{row_number}"
            line = format_row(row)
            # Some BAC tables stack quarters vertically. Replace the active
            # period header when a later panel begins, rather than labelling
            # every row with the first panel's quarter.
            if panel_pattern.search(line):
                updated = [line if panel_pattern.search(header) else header for header in headers]
                if not any(panel_pattern.search(header) for header in headers):
                    updated.append(line)
                header_text = "\n".join(updated)
            text = f"{source.bank} | {context}\nTable header context:\n{header_text}\nRow {row_number}: {line}"
            blocks.append(Block(block_id=row_id, document_id=source.document_id, bank=source.bank,
                                kind="table", text=text, location=f"{location}, row {row_number}",
                                url=url, periods=source.periods, evidence_ids=[row_id]))
    for number, node in enumerate(soup.find_all(["p", "h1", "h2", "h3", "h4", "li"]), 1):
        if node.find_parent("table") or node.find_parent(["p", "li"]):
            continue
        text = clean(node.get_text(" "))
        if len(text) < 50:
            continue
        block_id = f"{source.document_id}:p{number}"
        anchor = node.get("id")
        blocks.append(Block(block_id=block_id, document_id=source.document_id, bank=source.bank,
                            kind="narrative", text=text, location=f"HTML paragraph {number}",
                            url=source.url + (f"#{anchor}" if anchor else ""),
                            periods=source.periods, evidence_ids=[block_id]))
    # Some official exhibits render each financial page as an image and supply
    # its accessible text in leaf <font> elements, rather than HTML paragraphs.
    # Preserve that text as narrative; do not pretend it is a parsed table.
    if not blocks:
        for number, node in enumerate(soup.find_all("font"), 1):
            if node.find("font") or node.find_parent("table"):
                continue
            text = clean(node.get_text(" "))
            if len(text) < 100:
                continue
            block_id = f"{source.document_id}:textlayer{number}"
            blocks.append(Block(block_id=block_id, document_id=source.document_id, bank=source.bank,
                                kind="narrative", text=text,
                                location=f"HTML image text layer {number} (not a parsed table)",
                                url=source.url, periods=source.periods, evidence_ids=[block_id]))
    return blocks


def extract_pdf(source: Source, path: Path) -> list[Block]:
    blocks = []
    with pdfplumber.open(path) as pdf:
        for number, page in enumerate(pdf.pages, 1):
            # PDF text preserves page provenance. Layout-sensitive table extraction
            # requires manual inspection; no PDF values are auto-approved as facts.
            text = page.extract_text(layout=False) or ""
            if not text.strip():
                continue
            block_id = f"{source.document_id}:page{number}"
            blocks.append(Block(block_id=block_id, document_id=source.document_id, bank=source.bank,
                                kind="narrative", text=text, location=f"PDF page {number}",
                                url=f"{source.url}#page={number}", periods=source.periods,
                                evidence_ids=[block_id]))
            # Some earnings PDFs provide simple income rows beneath a split
            # month/year header. Preserve those rows separately with their exact
            # source text. Only manually reviewed values may become facts.
            lines = text.splitlines()
            start = next((i for i, line in enumerate(lines) if re.search(r"^Earnings\s+\(.*millions", line, re.I)), None)
            if start is None:
                continue
            header = lines[:start + 1]
            normalized = []
            months = {"Mar": 1, "Jun": 2, "Sep": 3, "Dec": 4}
            for i, line in enumerate(header[:-1]):
                names = re.findall(r"\b(Mar|Jun|Sep|Dec)\s+\d{1,2},", line)
                years = re.findall(r"\b20\d{2}\b", header[i + 1])
                if len(names) >= 3 and len(names) == len(years):
                    normalized = [f"c{j + 2}={months[month]}Q{year[-2:]}" for j, (month, year) in enumerate(zip(names, years))]
            if not normalized:
                continue
            for line_number, line in enumerate(lines[start + 1:], start + 2):
                if re.search(r"^Average balances|^Balance Sheet|^Second Quarter", line):
                    break
                match = re.match(r"^(.+?)\s+\$?\s*(\(?\d[\d,.]*\)?(?:\s+.*)?)$", line)
                if not match:
                    continue
                values = re.findall(r"\(?-?\d[\d,.]*\)?|\u2014", match[2])
                if len(values) < 3:
                    continue
                row_id = f"{block_id}:line{line_number}"
                row_text = (f"{source.bank} | {source.title}\nTable header context:\n" + "\n".join(header)
                            + "\n" + " | ".join(normalized) + f"\nRow {line_number}: c1={match[1]} | "
                            + " | ".join(f"c{i + 2}={value}" for i, value in enumerate(values)))
                blocks.append(Block(block_id=row_id, document_id=source.document_id, bank=source.bank,
                                    kind="table", text=row_text, location=f"PDF page {number}, text line {line_number} (reviewed values only)",
                                    url=f"{source.url}#page={number}", periods=source.periods, evidence_ids=[row_id]))
    return blocks


def prepare(manifest_path: Path = ROOT / "config" / "sources.json") -> dict:
    sources = [Source.model_validate(item) for item in json.loads(manifest_path.read_text(encoding="utf-8"))]
    all_blocks, manifest, failures = [], [], []
    raw = DATA / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        for source in sources:
            path = raw / f"{source.document_id}.{source.format}"
            try:
                if not path.exists():
                    response = client.get(source.url, headers={"User-Agent": "IRResearchPrototype/0.1 (educational public document analysis)"})
                    response.raise_for_status()
                    if source.format == "pdf" and not response.content.startswith(b"%PDF"):
                        raise ValueError("Expected a PDF, received another content type")
                    if source.format == "html" and "<" not in response.text[:1000]:
                        raise ValueError("Expected an HTML document")
                    path.write_bytes(response.content)
                blocks = extract_html(source, path) if source.format == "html" else extract_pdf(source, path)
                if not blocks:
                    raise ValueError("No text blocks extracted")
                all_blocks.extend(blocks)
                manifest.append({**source.model_dump(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                 "local_path": str(path.relative_to(ROOT)), "blocks": len(blocks),
                                 "ingested_at": datetime.now(timezone.utc).isoformat()})
                print(f"Prepared {source.document_id}: {len(blocks)} blocks")
            except (httpx.HTTPError, ValueError) as exc:
                failures.append({"document_id": source.document_id, "error": str(exc)})
                print(f"Could not prepare {source.document_id}: {exc}")
    # Do not publish a partial corpus that looks like the requested full snapshot.
    if failures:
        write_json(DATA / "processed" / "ingestion_failures.json", failures)
        raise RuntimeError("Ingestion incomplete; see data/processed/ingestion_failures.json. Existing processed snapshot was retained.")
    write_jsonl(DATA / "processed" / "blocks.jsonl", all_blocks)
    write_json(DATA / "processed" / "source_manifest.json", manifest)
    write_json(DATA / "processed" / "ingestion_failures.json", [])
    return {"documents": len(manifest), "blocks": len(all_blocks)}
