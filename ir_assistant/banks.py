"""Bank identity is separate from whether its documents are indexed/reviewed."""
import json
import re
from functools import lru_cache
from pathlib import Path


_PATH = Path(__file__).resolve().parents[1] / "config" / "banks.json"


@lru_cache(maxsize=4)
def _read_banks(stamp: int) -> dict[str, dict]:
    rows = json.loads(_PATH.read_text(encoding="utf-8"))
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate bank IDs")
    return {row["id"]: row for row in rows}


def bank_registry() -> dict[str, dict]:
    return _read_banks(_PATH.stat().st_mtime_ns)


def bank_name(bank: str) -> str:
    return bank_registry().get(bank, {}).get("name", bank)


def named_banks(question: str) -> list[str]:
    return [bank for bank, item in bank_registry().items()
            if any(re.search(r"\b" + re.escape(alias) + r"\b", question, 0 if len(alias) == 1 else re.I)
                   for alias in [*item["aliases"], bank])]
