"""Rolling 14-day fingerprints of acknowledged stories; no message bodies or chat IDs."""

import hashlib
import re
import unicodedata
from datetime import date, timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from services import news_reader
from services.news_bot import BotError

_UNSET = object()


def title_key(source):
    title = unicodedata.normalize("NFKC", source["title"]).casefold()
    publisher = source.get("publisher", "").casefold()
    if publisher and title.endswith(" - " + publisher):
        title = title[: -(len(publisher) + 3)]
    return news_reader.headline_fingerprint(title)


def url_key(source):
    safe = news_reader.safe_link(source["url"])
    if not safe:
        raise BotError("Unsafe story URL in news memory.")
    parsed = urlsplit(safe)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query)
        if not key.casefold().startswith("utm_") and key.casefold() not in {"ref", "referrer"}
    ]
    canonical = urlunsplit(
        (parsed.scheme, parsed.netloc.casefold(), parsed.path, urlencode(query), "")
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def history_key(config):
    identity = config.token.split(":")[0] + ":" + config.chat_id
    return "story-history-v1-" + hashlib.sha256(identity.encode()).hexdigest()[:24]


def load(ledger, key, day, record=_UNSET):
    raw = ledger.get(key) if record is _UNSET else record
    if raw is None:
        return {"version": 1, "entries": {}}
    if (
        not isinstance(raw, dict)
        or raw.get("version") != 1
        or not isinstance(raw.get("entries"), dict)
    ):
        raise BotError("Story history is invalid; refusing to forget sent stories silently.")
    today = date.fromisoformat(day)
    entries = {}
    for fingerprint, entry in raw["entries"].items():
        try:
            sent = date.fromisoformat(entry["sent_on"])
            valid = re.fullmatch(r"[a-f0-9]{64}", fingerprint)
        except (ValueError, TypeError, KeyError):
            raise BotError("Story history contains an invalid record.") from None
        if not valid:
            raise BotError("Story history contains an invalid fingerprint.")
        if today - timedelta(days=13) <= sent <= today:
            entries[fingerprint] = entry
    return {"version": 1, "entries": entries}


def entries_for(sources, day):
    entries = {}
    for source in sources:
        entry = {"sent_on": day, "published_on": source["published_at"][:10]}
        entries[title_key(source)] = {**entry, "kind": "title"}
        entries[url_key(source)] = {**entry, "kind": "url"}
    return entries


def sources_in(digest, categories=None):
    return [
        source
        for section in digest["sections"]
        if categories is None or section["id"] in categories
        for bullet in section["bullets"]
        for source in bullet["sources"]
    ]


def unseen(source, history):
    # A changed headline at an existing URL can be a genuine developing update.
    return title_key(source) not in history["entries"]


def filter_pack(pack, history):
    items = [item for item in pack["items"] if unseen(item, history)]
    return {
        **pack,
        "items": items,
        "coverage": {
            "headlines": len(items),
            "article_excerpts": sum(item["read_status"] == "article_excerpt" for item in items),
            "feed_excerpts": sum(item["read_status"] == "publisher_feed_excerpt" for item in items),
            "headline_only": sum(item["read_status"] == "headline_only" for item in items),
        },
        "suppressed_seen": len(pack["items"]) - len(items),
    }


def empty_digest(pack):
    return {
        **{
            key: pack[key]
            for key in ("date_ist", "generated_at", "coverage", "feeds", "limitations")
        },
        "subject": "Nivesh brief · " + pack["date_ist"],
        "sections": [],
        "glossary": [],
        "summary_status": "no_unseen_stories",
        "summary_modes": {},
    }


def reconcile(ledger, key, day, delivery_id):
    record = ledger.get(hashlib.sha256(delivery_id.encode()).hexdigest()[:32])
    if not record or record.get("status") != "accepted":
        return
    previous = ledger.get(key)
    history = load(ledger, key, day, record=previous)
    history["entries"].update(record.get("story_entries", {}))
    # Prune again: recovering an older receipt must not revive expired stories.
    today = date.fromisoformat(day)
    history["entries"] = {
        fingerprint: entry
        for fingerprint, entry in history["entries"].items()
        if today - timedelta(days=13) <= date.fromisoformat(entry["sent_on"]) <= today
    }
    if previous == history:
        return
    if previous is None:
        ledger.reserve(key, history)
    else:
        ledger.accepted(key, history)


def persist(ledger, key, history):
    if ledger.get(key) is None:
        ledger.reserve(key, history)
    else:
        ledger.accepted(key, history)


def weekly_candidates(pack, history, limit=4):
    candidates = []
    for item in pack["items"]:
        score = news_reader.priority(item)
        if not unseen(item, history) or score["headline_form"] == "stock_picks":
            continue
        major = bool(
            re.search(
                r"crisis|crash|recession|central bank|inflation|tariff|war|ceasefire|election|earthquake|hurricane|flood|court|epidemic|pandemic|major|historic",
                item["title"],
                re.I,
            )
        )
        if major or score["reading_score"] >= 4:
            candidates.append((major, score["reading_score"], item["published_at"], item))
    candidates.sort(key=lambda entry: entry[:3], reverse=True)
    chosen, seen = [], set()
    for *_, item in candidates:
        fingerprint = title_key(item)
        if fingerprint not in seen:
            chosen.append({**item, "previous_link_seen": url_key(item) in history["entries"]})
            seen.add(fingerprint)
        if len(chosen) == limit:
            break
    return chosen


def cleanup_local(folder, day):
    """Remove only this bot's dated report artifacts; never dossiers or claims."""
    cutoff = date.fromisoformat(day) - timedelta(days=13)
    removed = 0
    for path in folder.glob("*"):
        match = re.fullmatch(
            r"(\d{4}-\d{2}-\d{2})-(?:(?:input|weekly-input|digest|summary)\.json|email\.(?:txt|html))",
            path.name,
        )
        if not match or path.is_symlink() or not path.is_file():
            continue
        try:
            artifact_day = date.fromisoformat(match[1])
        except ValueError:
            continue
        if artifact_day < cutoff:
            path.unlink()
            removed += 1
    return removed
