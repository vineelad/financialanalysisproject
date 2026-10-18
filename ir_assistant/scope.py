"""Conservative, deterministic scope resolution for the frozen demo corpus."""
import re
from dataclasses import dataclass, field
from .banks import bank_name, named_banks


@dataclass
class QueryScope:
    banks: list[str] = field(default_factory=list)
    periods: list[str] = field(default_factory=list)
    clarification: str | None = None
    unsupported: str | None = None


def consumer_only(question: str) -> bool:
    text = question.lower()
    return bool(re.search(r"\b(consumer|ccb|uspb)\b|personal banking", text)) and not any(
        word in text for word in ("wealth", "corporate", "commercial", "global banking", "global markets"))


def header_periods(text: str) -> set[str]:
    if "Table header context:\n" not in text:
        return set()
    header = text.split("Table header context:\n", 1)[1].split("\nRow ", 1)[0]
    quarters = set()
    numbers = {"first": "1", "second": "2", "third": "3", "fourth": "4"}
    for name, year in re.findall(r"\b(first|second|third|fourth) quarter\s+(20\d{2})", header, re.I):
        quarters.add(f"{year}Q{numbers[name.lower()]}")
    for quarter, year in re.findall(r"\b([1-4])Q[\u2019']?(\d{2})\b", header, re.I):
        quarters.add(f"20{year}Q{quarter}")
    # Match stacked year and quarter column headers (e.g. Capital One).
    year_columns, quarter_columns = {}, {}
    for start, end, year in re.findall(r"\bc(\d+)(?:-(\d+))?=(20\d{2})\b", header):
        for column in range(int(start), int(end or start) + 1):
            year_columns[column] = year
    for start, end, quarter in re.findall(r"\bc(\d+)(?:-(\d+))?=Q([1-4])\b", header, re.I):
        for column in range(int(start), int(end or start) + 1):
            quarter_columns[column] = quarter
    quarters.update(f"{year}Q{quarter_columns[col]}" for col, year in year_columns.items() if col in quarter_columns)
    months = {"march": "1", "june": "2", "september": "3", "december": "4"}
    if not quarters and not re.search(r"year.to.date|six months ended", header, re.I):
        for month, year in re.findall(r"\b(march|june|september|december)\s+\d{1,2},?\s+(20\d{2})", header, re.I):
            quarters.add(f"{year}Q{months[month.lower()]}")
    return quarters


def matches_quarter_context(text: str, periods: list[str], question: str) -> bool:
    if "Table header context:\n" not in text or not periods:
        return True
    header = text.split("Table header context:\n", 1)[1].split("\nRow ", 1)[0]
    quarters = header_periods(text)
    if quarters:
        return bool(quarters.intersection(periods))
    if not any(word in question.lower() for word in ("ytd", "year-to-date", "six months")):
        if "year-to-date" in header.lower() or "six months ended" in header.lower():
            return False
    return True


def peer_comparison_question(question: str, banks: list[str], periods: list[str]) -> bool:
    if len(banks) > 1 or re.search(r"\bpeers?\b|other banks|all banks|across banks|which bank", question, re.I):
        return True
    # A same-bank comparison across dates is not automatically a peer request.
    if len(periods) > 1 and banks:
        return False
    return bool(re.search(r"\b(compare[ds]?|comparing|comparison|versus|vs|against|gap|difference|outperform\w*|underperform\w*)\b|(?:higher|lower|larger|smaller) than", question, re.I))


def resolve(question: str, available_banks: set[str], available_periods: set[str], base_bank: str | None = None) -> QueryScope:
    text = question.lower()
    banks = named_banks(question)
    periods = set()
    for quarter, year in re.findall(r"\bq([1-4])\s*[,/-]?\s*(20\d{2})\b", text):
        periods.add(f"{year}Q{quarter}")
    for year, quarter in re.findall(r"\b(20\d{2})\s*q([1-4])\b", text):
        periods.add(f"{year}Q{quarter}")
    # Carry an explicit quarter into a second standalone comparison year.
    if periods and len({p[-1] for p in periods}) == 1:
        quarter = next(iter(periods))[-1]
        for year in re.findall(r"\b20\d{2}\b", text):
            periods.add(f"{year}Q{quarter}")
    if base_bank:
        if base_bank not in available_banks:
            raise ValueError("The selected base bank is not in the prepared corpus")
        if peer_comparison_question(question, banks, sorted(periods)):
            peers = [bank for bank in banks if bank != base_bank]
            banks = [base_bank, *peers] if peers else [base_bank, *sorted(available_banks - {base_bank})]
        elif not banks:
            banks = [base_bank]
    scope = QueryScope(banks=banks, periods=sorted(periods))
    if re.search(r"\b(forecast|predict|next quarter|private|internal targets)\b", text):
        scope.unsupported = "This public historical corpus does not establish forecasts or private targets."
    elif "roa" in text and "allocated capital" in text and any(word in text for word in ("using", "substitute", "as roa")):
        scope.unsupported = "Return on allocated capital cannot substitute for return on average assets (ROA)."
    elif banks and not set(banks).issubset(available_banks):
        missing = ", ".join(bank_name(bank) for bank in banks if bank not in available_banks)
        scope.unsupported = f"Requested bank documents are not in the prepared corpus: {missing}."
    elif periods and not periods.issubset(available_periods):
        scope.unsupported = "A requested period is not in the prepared corpus."
    elif not banks:
        scope.clarification = "Select a base bank or name a bank in the question."
    elif not periods:
        scope.clarification = "Specify the analysis quarter and year; the corpus is a historical snapshot."
    return scope
