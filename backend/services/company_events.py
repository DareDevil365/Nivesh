"""Source-linked developments and private, append-only project research histories."""

import hashlib
import io
import json
import re
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import HTTPException
from pypdf import PdfReader

from services.data_fetcher import now_iso
from services.filing_reader import _pdfs, identity_matches, normalize_text
from services.filing_sources import fetch_public
from services.local_store import connection

EVENT_VERSION = 2
MAX_EVENT_DOCUMENTS = 4
LIFECYCLES = {
    "tender": [
        "not_established",
        "participation_disclosed",
        "bid_submitted",
        "qualified",
        "preferred_bidder",
        "awarded",
        "contract_signed",
        "executing",
        "revenue_recognized",
        "cash_received",
        "lost",
        "withdrawn",
        "cancelled",
    ],
    "expansion": [
        "not_established",
        "announced",
        "permissions_pending",
        "approved",
        "funding_pending",
        "construction",
        "trial_production",
        "commercial_operations",
        "cancelled",
        "paused",
    ],
    "approval": [
        "not_established",
        "application_submitted",
        "under_review",
        "conditional_approval",
        "approved",
        "rejected",
        "withdrawn",
    ],
    "acquisition": [
        "not_established",
        "proposed",
        "agreement_signed",
        "approvals_pending",
        "approved",
        "closed",
        "integration",
        "withdrawn",
        "cancelled",
    ],
    "other": [
        "not_established",
        "announced",
        "pending",
        "in_progress",
        "completed",
        "cancelled",
        "paused",
    ],
}
TERMINAL = {"cash_received", "lost", "withdrawn", "cancelled", "rejected", "completed"}
EVENT_PATTERNS = (
    ("clarification", r"rumou?r|clarification|denial|deny|media report"),
    (
        "management",
        r"\b(?:ceo|cfo|managing director|chief executive|chief financial|auditor|resignation|appointment)\b",
    ),
    (
        "project",
        r"\b(?:tender|bid|contract|order award|orders received|order received|letter of (?:award|acceptance)|acquisition|divestment|expansion|incorporation|incorporated|commissioning|commissioned|commercial production|commercial operations|capacity addition|clearance)\b",
    ),
    (
        "financing",
        r"\b(?:fund raising|raising of funds|raising funds|rights issue|preferential issue|buyback|debt issue)\b",
    ),
    (
        "reports",
        r"annual report|prospectus|financial results|quarterly results|presentation|transcript",
    ),
)


def event_kind(title):
    # A reference to takeover regulations is not an acquisition announcement.
    if re.search(r"substantial acquisition of shares|regulation\s+(?:29|31)\s*\(", title, re.I):
        return "ownership"
    if re.search(r"preferential issue|monitoring agency|rights issue|fund.?raising", title, re.I):
        return "financing"
    for kind, pattern in EVENT_PATTERNS:
        if re.search(pattern, title, re.I):
            return kind
    return None


def today_india():
    return datetime.now(timezone(timedelta(hours=5, minutes=30))).date()


def public_link(url):
    try:
        parsed = urlsplit(str(url))
        return (
            parsed.scheme == "https"
            and bool(parsed.hostname)
            and not parsed.username
            and not parsed.password
        )
    except ValueError:
        return False


def _schema(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS development_observations (
            ticker TEXT NOT NULL, id TEXT NOT NULL, payload TEXT NOT NULL, first_seen TEXT NOT NULL,
            PRIMARY KEY(ticker,id)
        );
        CREATE TABLE IF NOT EXISTS pending_projects (
            owner TEXT NOT NULL, ticker TEXT NOT NULL, id TEXT PRIMARY KEY,
            payload TEXT NOT NULL, version INTEGER NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS pending_projects_owner ON pending_projects(owner,ticker);
    """)


def collect_event_documents(profile, candidates, documents):
    """Read up to four additional short issuer filings; no AI or arbitrary news crawl."""
    used = {item["url"] for item in documents}
    selected = [
        item
        for item in candidates
        if item.get("url") not in used
        and event_kind(item.get("title", ""))
        in {"project", "management", "financing", "clarification"}
        and not re.search(r"newspaper|trading.window|audio", item.get("title", ""), re.I)
        and (not item.get("date") or item["date"][:10] <= today_india().isoformat())
    ]
    selected.sort(key=lambda item: item.get("date") or "", reverse=True)
    result, attempts = [], []
    seen = set()
    for candidate in selected:
        if candidate["url"] in seen:
            continue
        seen.add(candidate["url"])
        if len(attempts) >= MAX_EVENT_DOCUMENTS:
            break
        try:
            content, final_url, _ = fetch_public(candidate["url"], profile.get("website") or "")
            if not content.startswith((b"%PDF", b"PK\x03\x04")):
                raise ValueError("Event attachment is not a readable PDF/ZIP.")
            extracted = None
            for filename, pdf in _pdfs(content)[:3]:
                reader = PdfReader(io.BytesIO(pdf), strict=False)
                if reader.is_encrypted and not reader.decrypt(""):
                    continue
                cover = " ".join(
                    normalize_text(page.extract_text() or "") for page in reader.pages[:3]
                )
                if not identity_matches(profile, cover):
                    continue
                if re.search(
                    r"newspaper\s+(?:publication|advertisement)|copy of newspaper", cover, re.I
                ):
                    raise ValueError("Newspaper clippings are excluded.")
                identifier = hashlib.sha256(pdf).hexdigest()[:20]
                passages = []
                for index, page in enumerate(reader.pages[:12]):
                    text = normalize_text(page.extract_text() or "")[:80000]
                    # A passage is a bounded preview, not an automatically established status.
                    match = re.search(
                        r"incorporat|commission|commercial|acquisition|tender|bid|contract|order|appoint|resign|clarif|denial|fund|clearance|approval",
                        text,
                        re.I,
                    )
                    if match:
                        excerpt = text[max(0, match.start() - 180) : match.start() + 1420]
                        passages.append(
                            {
                                "id": f"{identifier}:event:p{index + 1}",
                                "page": index + 1,
                                "text": excerpt,
                                "category": "governance",
                                "score": 25,
                                "issuer_terms": [profile["name"], profile["ticker"].split(".")[0]],
                            }
                        )
                if not passages:
                    continue
                extracted = {
                    "id": identifier,
                    "url": final_url,
                    "original_url": candidate["url"],
                    "title": candidate["title"],
                    "date": candidate.get("date"),
                    "archive_member": None if filename == "document.pdf" else filename,
                    "extraction_version": f"event-{EVENT_VERSION}",
                    "passages": passages[:4],
                    "relationships": [],
                    "total_pages": len(reader.pages),
                    "pages_read": min(12, len(reader.pages)),
                    "partial": len(reader.pages) > 12,
                }
                break
            if not extracted:
                raise ValueError("No issuer-matched readable event evidence found.")
            extracted["duplicate_content"] = extracted["id"] in {
                doc["id"] for doc in documents + result
            }
            if extracted["url"] not in {doc["url"] for doc in result}:
                result.append(extracted)
            attempts.append({"url": candidate["url"], "status": "read"})
        except Exception as error:
            attempts.append(
                {
                    "url": candidate["url"],
                    "status": "unavailable",
                    "message": str(error)[:250]
                    if isinstance(error, ValueError)
                    else "Event attachment could not be read.",
                }
            )
    return {"documents": result, "attempts": attempts, "version": EVENT_VERSION}


def _observations(state):
    docs = state.get("documents", []) + state.get("event_documents", [])
    by_url = {url: doc for doc in docs for url in {doc["url"], doc.get("original_url", doc["url"])}}
    candidates = list(state.get("candidates", []))
    candidates.extend(
        doc for doc in docs if doc["url"] not in {item.get("url") for item in candidates}
    )
    for candidate in candidates:
        title, url = candidate.get("title", ""), candidate.get("url", "")
        kind = event_kind(title)
        if (
            not kind
            or not public_link(url)
            or re.search(r"newspaper|trading.window|audio", title, re.I)
        ):
            continue
        published = candidate.get("date")
        if published and published[:10] > today_india().isoformat():
            continue
        doc = by_url.get(url)
        if doc is None:
            # A redirect can change the URL; content IDs, when supplied, are a stronger join.
            doc = next(
                (d for d in docs if d.get("id") and d.get("id") == candidate.get("id")), None
            )
        passages = doc.get("passages", []) if doc else []
        evidence = passages[:2]
        version = (
            (
                doc["id"]
                + str(doc.get("extraction_version"))
                + json.dumps(
                    {"evidence": evidence, "archive_member": doc.get("archive_member")},
                    sort_keys=True,
                )
            )
            if doc
            else "headline"
        )
        identity = hashlib.sha256(
            (url + version + title + str(published) + str(EVENT_VERSION)).encode()
        ).hexdigest()[:24]
        yield {
            "id": identity,
            "title": title,
            "url": url,
            "published_date": published,
            "kind": kind,
            "evidence_status": "document_excerpt" if evidence else "headline_lead",
            "document_id": doc.get("id") if doc else None,
            "archive_member": (
                None if doc.get("archive_member") == "document.pdf" else doc.get("archive_member")
            )
            if doc
            else None,
            "duplicate_content": bool(doc and doc.get("duplicate_content")),
            "evidence": [
                {"id": p["id"], "text": p["text"], "page": p.get("page")} for p in evidence
            ],
            "interpretation": "Read the original disclosure; excerpts do not independently verify management claims or establish a project outcome.",
        }


def developments(ticker, state):
    # Idempotent migration of existing collected sources; never downloads or calls AI.
    with connection() as db:
        _schema(db)
        for observation in _observations(state):
            db.execute(
                "INSERT OR IGNORE INTO development_observations VALUES(?,?,?,?)",
                (ticker, observation["id"], json.dumps(observation), now_iso()),
            )
        rows = db.execute(
            "SELECT payload,first_seen FROM development_observations WHERE ticker=? ORDER BY first_seen DESC LIMIT 300",
            (ticker,),
        ).fetchall()
    items = [{**json.loads(row["payload"]), "first_seen": row["first_seen"]} for row in rows]
    # Display the strongest version per URL; immutable older versions remain stored.
    best = {}
    for item in items:
        old = best.get(item["url"])
        if old is None or (
            item["evidence_status"] == "document_excerpt"
            and old["evidence_status"] == "headline_lead"
        ):
            best[item["url"]] = item
    items = sorted(
        best.values(),
        key=lambda item: (item.get("published_date") or "", item["first_seen"]),
        reverse=True,
    )[:100]
    current = {doc["id"] for doc in state.get("documents", []) + state.get("event_documents", [])}
    for item in items:
        item["in_current_collection"] = (
            item.get("document_id") in current if item.get("document_id") else False
        )
    leads, seen = [], set()
    for doc in state.get("documents", []) + state.get("event_documents", []):
        for passage in doc.get("passages", []):
            text = passage["text"]
            if (
                re.search(r"\b(?:we|our|company)\b", text, re.I)
                and re.search(
                    r"\b(?:plan|propos|expect|intend|await|applied|application|pending|will commission|will commence)\w*\b",
                    text,
                    re.I,
                )
                and re.search(
                    r"\b(?:plant|project|expansion|capacity|tender|bid|approval|acquisition|commission|qualification)\w*\b",
                    text,
                    re.I,
                )
                and not re.search(
                    r"forward.looking statements|table of contents|may adversely affect", text, re.I
                )
                and text not in seen
                and public_link(doc["url"])
            ):
                seen.add(text)
                leads.append(
                    {
                        "id": passage["id"],
                        "title": doc["title"],
                        "url": doc["url"],
                        "page": passage.get("page"),
                        "archive_member": None
                        if doc.get("archive_member") == "document.pdf"
                        else doc.get("archive_member"),
                        "text": text,
                        "published_date": doc.get("date"),
                        "status": "potential_follow_up",
                        "category": passage.get("category", "business"),
                        "note": "Historical or conditional language may appear here. Review scope and newer filings before tracking.",
                    }
                )
    leads.sort(
        key=lambda item: (
            {"guidance": 5, "operations": 4, "business": 3, "governance": 2, "risks": 0}.get(
                item["category"], 1
            ),
            item.get("published_date") or "",
        ),
        reverse=True,
    )
    return {
        "ticker": ticker,
        "items": items,
        "follow_up_leads": leads[:12],
        "lifecycles": LIFECYCLES,
        "collection_status": state.get("status"),
        "last_collection_at": state.get("finished_at"),
        "event_attempts": state.get("event_attempts", []),
        "limitations": "Bounded issuer disclosures only. Broad news, rumour feeds, public-tender matching and scheduled monitoring are not connected. First seen is not publication date; no later outcome found is not evidence of loss or cancellation.",
    }


def _decorate(payload, today=None):
    result = dict(payload)
    today = today or today_india()
    due = result.get("expected_date")
    result["review_due"] = bool(
        due and date.fromisoformat(due) < today and result["stage"] not in TERMINAL
    )
    result["evidence_status"] = "user_research_entry"
    return result


def list_projects(owner, ticker):
    with connection() as db:
        _schema(db)
        rows = db.execute(
            "SELECT payload FROM pending_projects WHERE owner=? AND ticker=? ORDER BY updated_at DESC",
            (owner, ticker),
        ).fetchall()
    return {
        "items": [_decorate(json.loads(row["payload"])) for row in rows],
        "lifecycles": LIFECYCLES,
        "privacy": "Saved only in this browser workspace. Entries and quotes are researcher-supplied, not independently verified or sent to AI.",
    }


def create_project(owner, ticker, payload):
    timestamp, identifier = now_iso(), uuid4().hex
    item = {
        **payload,
        "id": identifier,
        "ticker": ticker,
        "version": 1,
        "created_at": timestamp,
        "updated_at": timestamp,
        "history": [{**payload, "recorded_at": timestamp, "version": 1}],
    }
    with connection() as db:
        _schema(db)
        db.execute("BEGIN IMMEDIATE")
        if (
            db.execute("SELECT COUNT(*) FROM pending_projects WHERE owner=?", (owner,)).fetchone()[
                0
            ]
            >= 200
        ):
            raise HTTPException(409, "Workspace project limit reached (200).")
        db.execute(
            "INSERT INTO pending_projects VALUES(?,?,?,?,?,?)",
            (owner, ticker, identifier, json.dumps(item), 1, timestamp),
        )
    return _decorate(item)


def update_project(owner, ticker, identifier, payload):
    with connection() as db:
        _schema(db)
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT payload,version FROM pending_projects WHERE owner=? AND ticker=? AND id=?",
            (owner, ticker, identifier),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Project not found in this workspace.")
        if row["version"] != payload.pop("expected_version"):
            raise HTTPException(409, "Project changed. Reload before saving another observation.")
        item = json.loads(row["payload"])
        if payload["stage"] not in LIFECYCLES[item["kind"]]:
            raise HTTPException(422, "Stage does not belong to this project type.")
        if len(item["history"]) >= 100:
            raise HTTPException(409, "Project observation limit reached (100).")
        timestamp, version = now_iso(), row["version"] + 1
        item.update(payload, updated_at=timestamp, version=version)
        item["history"].append({**payload, "recorded_at": timestamp, "version": version})
        db.execute(
            "UPDATE pending_projects SET payload=?,version=?,updated_at=? WHERE id=? AND owner=?",
            (json.dumps(item), version, timestamp, identifier, owner),
        )
    return _decorate(item)


def delete_project(owner, ticker, identifier, version):
    with connection() as db:
        _schema(db)
        row = db.execute(
            "SELECT version FROM pending_projects WHERE owner=? AND ticker=? AND id=?",
            (owner, ticker, identifier),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Project not found in this workspace.")
        if row["version"] != version:
            raise HTTPException(409, "Project changed. Reload before deleting.")
        cursor = db.execute(
            "DELETE FROM pending_projects WHERE owner=? AND ticker=? AND id=? AND version=?",
            (owner, ticker, identifier, version),
        )
        if cursor.rowcount != 1:
            raise HTTPException(409, "Project changed. Reload before deleting.")
    return {"deleted": True}
