"""A bounded, persistent, issuer-independent evidence collection workflow."""

import hashlib
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException

from services.company_events import EVENT_VERSION, collect_event_documents, developments
from services.data_fetcher import financial_value, get_company_financials, now_iso
from services.filing_financials import reconcile_financials
from services.filing_reader import CATEGORIES, EXTRACTION_VERSION, read_document
from services.filing_sources import discover_documents, document_kind, validate_source_url
from services.local_store import connection
from services.research_context import collect_context, context_url
from services.research_plan import build_research_plan

MAX_DOCUMENTS = 6
MAX_ATTEMPTS = 12

STAGES = [
    {
        "id": "identity",
        "title": "Resolve the business",
        "method": "Provider identity and official issuer documents",
        "questions": [
            "Which listed legal entity, subsidiaries and business segments are included?",
            "Which financial periods and consolidated/standalone basis are available?",
        ],
        "evidence": [
            "Issuer name and exchange symbol",
            "Annual report or prospectus",
            "Latest quarterly results",
        ],
    },
    {
        "id": "business",
        "title": "Map how money moves",
        "method": "Document passages, explicit relationship extraction; optional AI interpretation",
        "questions": [
            "Who pays for which product or service, through which channel?",
            "Who supplies critical inputs? Are names disclosed or just brands/customer groups?",
            "What are the concentration, replacement and bargaining-power risks?",
        ],
        "evidence": [
            "Business and segment notes",
            "Procurement and customer disclosures",
            "Related-party and concentration notes",
        ],
    },
    {
        "id": "financials",
        "title": "Check financial quality",
        "method": "Code for period-aligned calculations; original statements for accounting context",
        "questions": [
            "Do operating cash flows support reported profits?",
            "What drives margin changes, working capital, debt and returns on capital?",
            "Are one-off items, dilution or accounting changes distorting the trend?",
        ],
        "evidence": [
            "3–5 years of income, balance sheet and cash flow statements",
            "Auditor opinion and accounting notes",
            "Peer disclosures on a comparable basis",
        ],
    },
    {
        "id": "drivers",
        "title": "Model demand and constraints",
        "method": "Researcher assumptions supported by operating evidence",
        "questions": [
            "Which measurable drivers explain revenue: customers, usage, volume, price, stores or utilisation?",
            "Can capacity, supply, finance or competition limit growth?",
            "What contrary evidence would invalidate the demand forecast?",
        ],
        "evidence": [
            "Operating KPIs and segment history",
            "Customer/industry data",
            "Capacity, pricing and inventory disclosures",
        ],
    },
    {
        "id": "events",
        "title": "Trace policy and world events",
        "method": "Event → exposure → sales/cost/cash impact → timing → valuation",
        "questions": [
            "Is a policy proposed, notified, funded, awarded or actually implemented?",
            "What are the net exposures to interest rates, currencies, commodities and logistics?",
            "What are the duration, hedging, pass-through and second-order effects?",
        ],
        "evidence": [
            "Original policy/regulator notice",
            "Company exposure and hedging notes",
            "Official industry and economic data",
        ],
    },
    {
        "id": "valuation",
        "title": "Test valuation and the thesis",
        "method": "Code for scenarios; AI for synthesis; researcher for judgment",
        "questions": [
            "What operating and valuation assumptions justify today's price?",
            "How do bear/base/bull outcomes change with those assumptions?",
            "What catalyst, downside and falsification condition support the pitch?",
        ],
        "evidence": [
            "Explicit scenario inputs and sensitivity analysis",
            "Comparable peer economics and valuation",
            "Dated evidence, counter-evidence and review triggers",
        ],
    },
]
_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="issuer-research")
_active, _lock = set(), threading.Lock()


def _read(symbol):
    with connection() as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS company_research (ticker TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at REAL NOT NULL)"
        )
        row = db.execute(
            "SELECT payload FROM company_research WHERE ticker=?", (symbol,)
        ).fetchone()
    return json.loads(row["payload"]) if row else None


def _write(symbol, payload):
    with connection() as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS company_research (ticker TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at REAL NOT NULL)"
        )
        db.execute(
            "INSERT OR REPLACE INTO company_research VALUES(?,?,?)",
            (symbol, json.dumps(payload, allow_nan=False), time.time()),
        )


def cached_research(symbol):
    result = _read(symbol) or {
        "ticker": symbol,
        "status": "not_started",
        "documents": [],
        "attempts": [],
        "candidates": [],
        "errors": [],
    }
    with _lock:
        active = symbol in _active
    if result["status"] in {"queued", "running"} and not active:
        result.update(
            status="interrupted",
            progress="The server restarted before collection completed. Run research again.",
        )
    result["stages"] = STAGES
    if result.get("research_plan"):
        result["research_plan"] = build_research_plan(
            {}, result["documents"], kind_override=result["research_plan"].get("business_template")
        )
    result["material_updates"] = sorted(
        [
            {**item, "collected": any(doc.get("url") == item["url"] for doc in result["documents"])}
            for item in result.get("candidates", [])
            if re.search(
                r"incorporation|capacity addition|commercial production|acquisition|divestment|raising.*fund|expansion|environment.*clearance",
                item.get("title", ""),
                re.I,
            )
        ],
        key=lambda item: item.get("date") or "",
        reverse=True,
    )[:12]
    result["corpus_fingerprint"] = corpus_fingerprint(result)
    ai_nodes = (
        result.get("ai_relationships", [])
        if result.get("ai_corpus_fingerprint") == result["corpus_fingerprint"]
        else []
    )
    result["relationship_count"] = len(
        {
            (node["direction"], node["name"].casefold())
            for node in [node for doc in result["documents"] for node in doc["relationships"]]
            + ai_nodes
        }
    )
    result["coverage"] = [
        {
            "category": category,
            "passages": sum(
                p.get("category") == category
                for doc in result["documents"]
                for p in doc["passages"]
            ),
            "status": "passages_found"
            if any(
                p.get("category") == category
                for doc in result["documents"]
                for p in doc["passages"]
            )
            else "not_found",
        }
        for category in CATEGORIES
    ]
    return result


def corpus_fingerprint(state):
    # Include extracted text, dates and parser version: identical PDF bytes do not
    # imply identical evidence after an extraction fix or source-date correction.
    evidence = [
        {k: doc.get(k) for k in ("id", "url", "date", "extraction_version", "passages")}
        for doc in state.get("documents", []) + state.get("event_documents", [])
    ]
    content = {"documents": evidence, "context": state.get("context", {}).get("articles", [])}
    return hashlib.sha256(
        json.dumps(content, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:20]


def _select(candidates):
    selected, kinds = [], set()
    for item in candidates:
        kind = document_kind(item)
        if kind == "administrative":
            continue
        if kind not in kinds:
            selected.append(item)
            kinds.add(kind)
        if len(selected) == MAX_DOCUMENTS:
            break
    for item in candidates:
        if len(selected) == MAX_DOCUMENTS:
            break
        if item not in selected and document_kind(item) != "administrative":
            selected.append(item)
    return selected


def _run(profile, source_urls, payload):
    symbol = profile["ticker"]
    try:
        payload["previous_documents"] = payload.get("previous_documents") or payload.get(
            "documents", []
        )
        payload["documents"] = []
        payload.pop("ai_relationships", None)
        payload.pop("ai_corpus_fingerprint", None)
        payload.update(
            status="running",
            progress="Discovering issuer filings, annual reports and investor documents…",
        )
        _write(symbol, payload)
        candidates, attempts = discover_documents(profile)
        manual = [
            {
                "url": url,
                "title": "User-supplied official company report",
                "date": None,
                "discovered_via": "User-supplied official URL",
            }
            for url in source_urls
        ]
        payload.update(candidates=candidates, attempts=attempts)
        preferred = _select(candidates)
        targets = manual + [
            item
            for item in preferred
            + [
                item
                for item in candidates
                if item not in preferred and document_kind(item) != "administrative"
            ]
            if item["url"] not in source_urls
        ]
        documents, errors = [], []
        for index, candidate in enumerate(targets[:MAX_ATTEMPTS]):
            if len(documents) == MAX_DOCUMENTS:
                break
            payload["progress"] = (
                f"Checking source {index + 1}/{min(MAX_ATTEMPTS, len(targets))}; {len(documents)}/{MAX_DOCUMENTS} documents read: {candidate['title']}"
            )
            _write(symbol, payload)
            try:
                document = read_document(profile, candidate)
                if document["id"] not in {d["id"] for d in documents}:
                    documents.append(document)
                payload["documents"] = documents
            except Exception as error:
                errors.append(
                    {
                        "url": candidate["url"],
                        "message": str(error)[:300]
                        if isinstance(error, ValueError)
                        else f"{type(error).__name__}: document could not be read.",
                    }
                )
            payload["errors"] = errors
            _write(symbol, payload)
        try:
            financials = get_company_financials(symbol)
            payload["financial_inputs"] = {
                "period": (financials.get("period_dates") or [None])[-1],
                "basis": financials.get("basis"),
                "source_url": profile.get("source_url"),
                "collected_at": now_iso(),
                "revenue_cr": financial_value(financials, "income_statement", "Total Revenue"),
                "net_income_cr": financial_value(financials, "income_statement", "Net Income"),
                "operating_cf_cr": financial_value(financials, "cash_flow", "Operating Cash Flow"),
                "shares_outstanding": profile.get("shares_outstanding"),
                "current_price": profile.get("current_price"),
                "instrument_type": profile.get("instrument_type"),
                "sector": profile.get("sector"),
            }
        except Exception:
            payload["financial_inputs"] = None
        payload["progress"] = "Reading additional short event disclosures…"
        _write(symbol, payload)
        event_result = collect_event_documents(profile, candidates, documents)
        payload.update(
            event_documents=event_result["documents"],
            event_attempts=event_result["attempts"],
            event_version=EVENT_VERSION,
        )
        developments(symbol, payload)
        payload["financial_reconciliation"] = reconcile_financials(
            payload.get("financial_inputs") or {}, documents
        )
        payload["research_plan"] = build_research_plan(profile, documents)
        payload["progress"] = "Checking official policy feeds and contextual sources…"
        _write(symbol, payload)
        payload["context"] = collect_context(profile, payload.get("context_urls", []))
        payload.update(
            status="complete" if documents else "complete_with_gaps",
            extraction_version=EXTRACTION_VERSION,
            finished_at=now_iso(),
            progress=f"Read {len(documents)} documents. Source coverage and extraction limits are shown below.",
            limitations=[
                "Discovery is bounded to public NSE feeds and company investor pages; it is not a complete search of the web.",
                "Try up to twelve issuer sources to read six reports, plus up to four additional event attachments. Main reports read at most 700 pages; event attachments read twelve pages and retain up to four previews. Up to three PDFs per archive are checked. Scanned text requires OCR, which is not implemented.",
                "A source-backed mention does not establish financial materiality, a current contract or a complete supplier/customer list.",
                "Policy, competitor and industry conclusions require the additional evidence in the research checklist.",
            ],
        )
        _write(symbol, payload)
    except Exception as error:
        payload.update(
            status="failed",
            finished_at=now_iso(),
            progress="Collection stopped. Retry or provide an official report URL.",
        )
        payload.setdefault("errors", []).append(
            {"message": type(error).__name__ + ": research collection failed."}
        )
        _write(symbol, payload)
    finally:
        with _lock:
            _active.discard(symbol)


def start_research(profile, source_urls=None, force=False, context_urls=None):
    symbol = profile["ticker"]
    existing = cached_research(symbol)
    requested = bool(source_urls or context_urls)
    source_urls = list(dict.fromkeys(source_urls or existing.get("requested_source_urls", [])))
    context_urls = list(dict.fromkeys(context_urls or existing.get("context_urls", [])))
    for url in source_urls:
        validate_source_url(url, profile.get("website") or "")
    for url in context_urls:
        context_url(url)
    with _lock:
        if symbol in _active:
            if requested:
                raise HTTPException(
                    409, "Collection is already running. Add your source after it finishes."
                )
            return existing
        elapsed = time.time() - existing.get("started_epoch", 0)
        if (
            not force
            and existing["status"] in {"complete", "complete_with_gaps"}
            and elapsed < 21600
            and existing.get("extraction_version") == EXTRACTION_VERSION
            and existing.get("event_version") == EVENT_VERSION
        ):
            return existing
        if force and elapsed < 60:
            raise HTTPException(429, "Wait a minute between collection runs.")
        if len(_active) >= 8:
            raise HTTPException(429, "The research queue is full. Try again shortly.")
        _active.add(symbol)
    payload = {
        "ticker": symbol,
        "name": profile["name"],
        "status": "queued",
        "progress": "Waiting for a research worker…",
        "started_at": now_iso(),
        "started_epoch": time.time(),
        "documents": [],
        "previous_documents": existing["documents"] or existing.get("previous_documents", []),
        "requested_source_urls": source_urls,
        "context_urls": context_urls,
        "attempts": [],
        "candidates": [],
        "errors": [],
    }
    try:
        _write(symbol, payload)
        _pool.submit(_run, profile, source_urls, payload)
    except Exception:
        with _lock:
            _active.discard(symbol)
        raise
    return {**payload, "stages": STAGES}


def ensure_research(profile):
    state = cached_research(profile["ticker"])
    stale = (
        time.time() - state.get("started_epoch", 0) > 21600
        or state.get("extraction_version") != EXTRACTION_VERSION
        or state.get("event_version") != EVENT_VERSION
    )
    if state["status"] in {"not_started", "interrupted"} or (
        stale and state["status"] in {"complete", "complete_with_gaps"}
    ):
        try:
            return start_research(profile)
        except HTTPException:
            return {**state, "progress": "Research queue is busy. Run collection again shortly."}
    return state


def filing_sources_for_ai(symbol, state=None):
    sources, remaining, buckets = [], 28000, {category: [] for category in CATEGORIES}
    state = state if state is not None else cached_research(symbol)
    groups = {}
    for row in state.get("financial_reconciliation", {}).get("records", []):
        groups.setdefault(row["id"], []).append(row)
    for identifier, rows in sorted(
        groups.items(), key=lambda item: max(row["period"] for row in item[1]), reverse=True
    )[:4]:
        text = json.dumps(rows[:16], ensure_ascii=False)
        if len(text) > 5000 or remaining < 22000:
            continue
        sources.append(
            {
                "id": "parsed_table:" + identifier,
                "title": "Parsed issuer income table · verify basis and original row",
                "url": rows[0]["url"],
                "page": rows[0]["page"],
                "source_kind": "parsed_filing_table",
                "text": text,
            }
        )
        remaining -= len(text)
    for article in state.get("context", {}).get("articles", [])[:3]:
        text = article["text"][:2000]
        sources.append(
            {
                **{
                    key: article.get(key)
                    for key in ("id", "title", "url", "date", "date_note", "date_warning")
                },
                "text": text,
                "source_kind": "external_context",
                "impact_status": "unverified",
            }
        )
        remaining -= len(text)
    for document in state["documents"] + state.get("event_documents", []):
        for passage in document["passages"]:
            buckets.setdefault(passage.get("category", "business"), []).append((document, passage))
    for bucket in buckets.values():
        bucket.sort(key=lambda item: -item[1]["score"])
    # Round-robin categories to preserve contrary and non-financial evidence.
    seen_text = set()
    for index in range(20):
        for bucket in buckets.values():
            if index >= len(bucket):
                continue
            document, passage = bucket[index]
            if passage["text"] in seen_text:
                continue
            seen_text.add(passage["text"])
            if remaining < 300:
                return sources
            text = passage["text"][:remaining]
            sources.append(
                {
                    "id": passage["id"],
                    "title": f"{document['title']} · PDF page {passage['page']}"
                    if passage.get("page")
                    else document["title"],
                    "url": document["url"],
                    "page": passage["page"],
                    "date": document.get("date"),
                    "issuer_terms": passage.get("issuer_terms", []),
                    "text": text,
                }
            )
            remaining -= len(text)
    return sources


def save_ai_relationships(symbol, relationships, expected_corpus):
    # One write transaction prevents a late AI result from overwriting a newer
    # refresh or attaching relationships extracted from the previous corpus.
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT payload FROM company_research WHERE ticker=?", (symbol,)
        ).fetchone()
        state = json.loads(row["payload"]) if row else None
        if (
            state
            and state["status"] in {"complete", "complete_with_gaps"}
            and corpus_fingerprint(state) == expected_corpus
        ):
            state.update(ai_relationships=relationships, ai_corpus_fingerprint=expected_corpus)
            db.execute(
                "UPDATE company_research SET payload=?, updated_at=? WHERE ticker=?",
                (json.dumps(state, allow_nan=False), time.time(), symbol),
            )
