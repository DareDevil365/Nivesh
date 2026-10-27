"""Repeatable evidence/data checks. Passing checks do not certify an investment thesis."""

import hashlib
import io
import math
from datetime import date, datetime, timezone
from urllib.parse import urlsplit

from pypdf import PdfReader

from services.filing_reader import CATEGORIES, _pdfs, normalize_text, read_company_page
from services.filing_sources import allowed_host, fetch_public
from services.research_workflow import corpus_fingerprint


def audit_research(state, financials=None):
    checks = []

    def add(name, status, detail):
        checks.append({"check": name, "status": status, "detail": detail})

    documents = state.get("documents", [])
    add(
        "source_collection",
        "pass" if documents else "warning",
        f"{len(documents)} current issuer documents; collection status {state.get('status', 'unknown')}.",
    )
    for category in CATEGORIES:
        found = sum(
            p.get("category") == category for doc in documents for p in doc.get("passages", [])
        )
        add(
            "coverage:" + category,
            "pass" if found else "warning",
            f"{found} retrieved passages. Retrieval does not establish that the topic is answered.",
        )
    for doc in documents:
        for node in doc.get("relationships", []):
            valid = (
                node.get("source_url") == doc.get("url")
                and (
                    (doc.get("source_kind") == "company_page" and node.get("source_page") is None)
                    or (
                        isinstance(node.get("source_page"), int)
                        and 1 <= node["source_page"] <= (doc.get("total_pages") or 0)
                    )
                )
                and bool(node.get("evidence_quote"))
            )
            add(
                "relationship_citation:" + node.get("name", "unknown"),
                "pass" if valid else "fail",
                "Document URL, physical page and quotation must be present and agree.",
            )
    for row in state.get("financial_reconciliation", {}).get("comparisons", []):
        add(
            "filing_comparison:" + row["metric"] + ":" + row["basis"],
            "warning",
            f"{row['basis']} {row['period']}: filing {row['value_cr']} Cr; provider {row['provider_value_cr']} Cr; {row['status']}. Provider basis/definition needs confirmation.",
        )
    if state.get("ai_relationships"):
        same = state.get("ai_corpus_fingerprint") == corpus_fingerprint(state)
        add(
            "ai_corpus",
            "pass" if same else "fail",
            "AI relationships must belong to the current extracted evidence version.",
        )
    inputs = state.get("financial_inputs") or {}
    for field in ("revenue_cr", "net_income_cr", "operating_cf_cr", "shares_outstanding"):
        value = inputs.get(field)
        if value is None:
            add("input:" + field, "warning", "Missing provider input; no number is inferred.")
        else:
            valid = (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
            )
            add(
                "input:" + field,
                "pass" if valid else "fail",
                "Provided financial input must be finite and numerical.",
            )
    if financials is None:
        add(
            "statement_alignment",
            "warning",
            "Full structured statements were not supplied for this audit.",
        )
    else:
        periods = financials.get("period_dates", [])
        valid_dates = True
        try:
            parsed = [date.fromisoformat(period) for period in periods]
            valid_dates = parsed == sorted(set(parsed)) and all(
                period <= datetime.now(timezone.utc).date() for period in parsed
            )
        except (ValueError, TypeError):
            valid_dates = False
        add(
            "statement_periods",
            "pass" if periods and valid_dates else "fail" if periods else "warning",
            "Periods must be unique, ordered, valid dates and not in the future.",
        )
        for section in ("income_statement", "balance_sheet", "cash_flow"):
            for row in financials.get(section, []):
                metric, values = row["metric"], row.get("values", [])
                expected_unit = (
                    "₹ / share"
                    if metric == "Diluted EPS"
                    else "shares"
                    if metric == "Shares Outstanding"
                    else "₹ Cr"
                )
                aligned = len(values) == len(periods) and row.get("unit") == expected_unit
                finite = all(
                    value is None
                    or isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                    for value in values
                )
                add(
                    "statement_row:" + metric,
                    "pass" if aligned and finite else "fail",
                    f"Expect one finite/missing value per period and unit {expected_unit}.",
                )
        # Compare collection-time baselines only when the statement period agrees;
        # a provider refresh may legitimately supersede the saved collection.
        if periods and inputs.get("period") == periods[-1]:
            for field, metric, section in (
                ("revenue_cr", "Total Revenue", "income_statement"),
                ("net_income_cr", "Net Income", "income_statement"),
                ("operating_cf_cr", "Operating Cash Flow", "cash_flow"),
            ):
                row = next(
                    (row for row in financials.get(section, []) if row["metric"] == metric), None
                )
                actual = row["values"][-1] if row and row.get("values") else None
                recorded = inputs.get(field)
                same = (
                    actual == recorded
                    or isinstance(actual, (int, float))
                    and isinstance(recorded, (int, float))
                    and math.isclose(actual, recorded, rel_tol=1e-7, abs_tol=1e-7)
                )
                add(
                    "baseline_comparison:" + field,
                    "pass" if same else "warning",
                    "Collection baseline compared with latest provider table for the same period; differences may be restatements and require review.",
                )
    add(
        "semantic_review",
        "warning",
        "These checks validate data contracts and citations, not interpretation, source completeness, accounting judgments or price predictions.",
    )
    return {
        "ticker": state.get("ticker"),
        "status": "fail"
        if any(c["status"] == "fail" for c in checks)
        else "review_required"
        if any(c["status"] == "warning" for c in checks)
        else "pass",
        "checks": checks,
    }


def verify_originals(profile, state, limit=6):
    """Re-download originals and independently compare cited page text and PDF hashes."""
    checks = []
    for doc in state.get("documents", [])[:limit]:
        try:
            if not allowed_host(urlsplit(doc["url"]).hostname, profile.get("website", "")):
                raise ValueError("Original source is outside the issuer/regulator allowlist.")
            raw, _, _ = fetch_public(doc["url"], profile.get("website", ""))
            if doc.get("source_kind") == "company_page":
                original = read_company_page(profile, doc, raw, doc["url"])
                for node in doc.get("relationships", []):
                    checks.append(
                        {
                            "check": "original_quote:" + node["name"],
                            "status": "pass"
                            if normalize_text(node["evidence_quote"]) in original["body_text"]
                            else "fail",
                            "detail": "Re-downloaded issuer HTML: " + doc["url"],
                        }
                    )
                checks.append(
                    {
                        "check": "original_hash:" + doc["id"],
                        "status": "pass" if original["id"] == doc["id"] else "warning",
                        "detail": "Compared normalized issuer HTML body hash; live pages may change.",
                    }
                )
                continue
            matches = [
                (name, pdf)
                for name, pdf in _pdfs(raw)
                if hashlib.sha256(pdf).hexdigest()[:20] == doc["id"]
            ]
            if not matches:
                raise ValueError(
                    "Downloaded PDF hash differs from the collected report; recollect before reviewing citations."
                )
            reader = PdfReader(io.BytesIO(matches[0][1]))
            pages = {}
            for node in doc.get("relationships", []):
                page = node["source_page"]
                if page not in pages:
                    pages[page] = normalize_text(reader.pages[page - 1].extract_text() or "")
                valid = normalize_text(node["evidence_quote"]) in pages[page]
                checks.append(
                    {
                        "check": "original_quote:" + node["name"],
                        "status": "pass" if valid else "fail",
                        "detail": f"Re-downloaded PDF, physical page {page}: {doc['url']}",
                    }
                )
            checks.append(
                {
                    "check": "original_hash:" + doc["id"],
                    "status": "pass",
                    "detail": "Original PDF bytes match the collected document hash.",
                }
            )
        except Exception as error:
            checks.append(
                {
                    "check": "original_source:" + doc.get("id", "unknown"),
                    "status": "warning",
                    "detail": str(error)[:300]
                    if isinstance(error, ValueError)
                    else type(error).__name__ + ": original could not be checked.",
                }
            )
    return checks
