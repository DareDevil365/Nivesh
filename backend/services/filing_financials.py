"""Conservative income-table extraction; ambiguous layouts remain unparsed."""

import calendar
import re
from datetime import date

from services.document_text import repair_pdf_text

NUMBER = r"(?:\(?-?\d[\d,]*(?:\.\d+)?\)?|[-–—])"
METRICS = {
    "revenue_cr": r"(?:net\s+)?revenue\s+from\s+operations",
    "net_income_cr": r"(?:profit\s+(?:for\s+the\s+(?:year|period)|after\s+tax)|PAT)(?!\s+margin)",
}


def _periods(header):
    if re.search(r"\bFY\s*\d{2,4}\s*[-–/]\s*\d{2,4}\b", header, re.I):
        # Do not silently read FY2025-26 as the year ending March 2025.
        return []
    tokens = re.findall(r"\bQ[1-4]\s*FY\s*\d{2,4}\b|\bFY\s*\d{2,4}\b", header, re.I)
    periods = []
    if tokens:
        for token in tokens:
            match = re.fullmatch(r"(?:Q([1-4])\s*)?FY\s*(\d{2,4})", token, re.I)
            year = int(match[2]) + (2000 if len(match[2]) == 2 else 0)
            quarter = int(match[1]) if match[1] else None
            month = (6, 9, 12, 3)[quarter - 1] if quarter else 3
            end_year = year - (1 if quarter and quarter < 4 else 0)
            periods.append(
                {
                    "period": date(
                        end_year, month, calendar.monthrange(end_year, month)[1]
                    ).isoformat(),
                    "period_kind": "quarter" if quarter else "annual",
                }
            )
    elif re.search(r"year\s+ended", header, re.I):
        for match in re.finditer(r"(?:March\s+31\s*,?\s*|31\s+March\s*)(20\d{2})", header, re.I):
            periods.append({"period": match[1] + "-03-31", "period_kind": "annual"})
    return periods if len({p["period"] for p in periods}) == len(periods) else []


def extract_income_table(raw, source):
    text = repair_pdf_text(raw)
    if not re.search(r"(?:statement\s+of\s+)?profit\s*(?:and|&)\s*loss", text, re.I):
        return []
    bases = set(re.findall(r"\b(?:standalone|consolidated)\b", text, re.I))
    bases = {basis.lower() for basis in bases}
    if len(bases) != 1:
        return []
    basis = bases.pop()
    unit = re.search(
        r"(?:₹|INR|Indian Rupees|Rs\.?)\s*\(?\s*(crores?|cr|millions?|mn|lakhs?|lacs?)\b",
        text,
        re.I,
    )
    if not unit:
        return []
    scale = unit[1].lower()
    factor = 1 if scale.startswith("cr") else 0.1 if scale.startswith(("mi", "mn")) else 0.01
    lines = text.splitlines()
    first_revenue = next(
        (i for i, line in enumerate(lines) if re.search(METRICS["revenue_cr"], line, re.I)), None
    )
    if first_revenue is None:
        return []
    header_start = max(
        (
            i
            for i, line in enumerate(lines[:first_revenue])
            if re.search(r"\bparticulars\b", line, re.I)
        ),
        default=0,
    )
    header = " ".join(lines[header_start:first_revenue])
    # A statement title repeated at the bottom is not another column header.
    periods = _periods(header)
    if not 1 <= len(periods) <= 6:
        return []
    records = []
    for metric, pattern in METRICS.items():
        matched = []
        for line in lines:
            match = re.search(pattern, line, re.I)
            if not match:
                continue
            if metric == "net_income_cr" and re.search(
                r"\b(?:cash|adjusted|normalised|normalized)\s*$", line[: match.start()], re.I
            ):
                continue
            # Ignore notes and arithmetic references such as (21), (3-4), (VII-VIII).
            tail = line[match.end() :].strip()
            tail = re.sub(r"^\((?:\d+\s*-\s*\d+|[IVX]+\s*-\s*[IVX]+)\)\s*", "", tail)
            tokens = re.findall(NUMBER, tail)
            if (
                len(tokens) == len(periods) + 1
                and re.search(r"\bnote\b", header, re.I)
                and re.fullmatch(r"\(?\d{1,2}\)?", tokens[0])
            ):
                tokens = tokens[1:]
            # Skip percentages, comparisons, multiline/misaligned rows and duplicates.
            residue = re.sub(NUMBER, "", tail).strip(" :")
            if residue or len(tokens) != len(periods):
                continue
            values = []
            for token in tokens:
                if token in {"-", "–", "—"}:
                    values.append(None)
                else:
                    value = float(token.strip("()").replace(",", ""))
                    values.append(-abs(value) * factor if token.startswith("(") else value * factor)
            matched.append((line, values))
        if len(matched) != 1:
            continue
        line, values = matched[0]
        records.extend(
            {
                **source,
                **period,
                "metric": metric,
                "value_cr": round(value, 6),
                "basis": basis,
                "reported_unit": unit.group(),
                "evidence_quote": " ".join(line.split()),
                "table_header": header[:800],
                "extraction": "explicit_income_table",
            }
            for period, value in zip(periods, values, strict=True)
            if value is not None and period["period"] <= date.today().isoformat()
        )
    return records


def reconcile_financials(inputs, documents):
    """Keep the provider baseline intact; expose independently extracted alternatives."""
    records = [row for document in documents for row in document.get("financial_metrics", [])]
    current = [
        row
        for row in records
        if row["period"] == inputs.get("period") and row["period_kind"] == "annual"
    ]
    comparisons = []
    for row in current:
        provider = inputs.get(row["metric"])
        if provider is None:
            status = "provider_missing"
            difference = None
        else:
            difference = row["value_cr"] - provider
            # Presentation tables round values; retain the actual difference too.
            tolerance = max(0.06, abs(row["value_cr"]) * 0.001)
            status = (
                "close_value_unconfirmed_basis"
                if abs(difference) <= tolerance
                else "review_difference"
            )
        comparisons.append(
            {
                **row,
                "provider_value_cr": provider,
                "difference_cr": round(difference, 6) if difference is not None else None,
                "status": status,
            }
        )
    return {
        "records": records,
        "comparisons": comparisons,
        "note": "Filing tables preserve stated basis, periods and units. Provider basis is unknown; close numbers do not establish the same accounting definition. Choose a consistent basis before modelling. Cash PAT is not operating cash flow.",
    }
