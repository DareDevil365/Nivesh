"""Four dated news editions, a separate lesson, then one closing research task."""

import hashlib
import html
import time
from datetime import date

from services import finance_teacher
from services import telegram_delivery as tg
from services.news_bot import BotError

EDITIONS = (
    ("world_finance", "World news & finance", {"world", "us", "policy", "commodities", "events"}),
    ("india_finance", "India news & finance", {"india"}),
    ("world_general", "World general news", {"world_general"}),
    ("india_general", "India general news", {"india_general"}),
)


def identifier(day, config, edition):
    return "universal-v1-" + edition + "-" + config.delivery_id(day)


def existing_delivery(day, config, ledger):
    # Missing/uncertain editions do not prevent other editions from being attempted.
    complete = []
    for edition, _, _ in EDITIONS:
        key = hashlib.sha256(identifier(day, config, edition).encode()).hexdigest()[:32]
        record = ledger.get(key)
        complete.append(bool(record and record.get("status") == "accepted"))
    return "already_accepted" if all(complete) else None


def edition_messages(digest, title, categories):
    day = date.fromisoformat(digest["date_ist"]).strftime("%A, %d %B %Y")
    sections = [section for section in digest["sections"] if section["id"] in categories]
    heading = f"<b>{html.escape(title)}</b>\n{day}"
    if not sections:
        body = "No validated summary was available for this edition in today's collection. This does not establish that nothing happened. Check original sources."
        return [heading, body]
    report = {**digest, "sections": sections, "glossary": []}
    content = tg.render_messages(report)
    # The dated heading is its own message, followed by complete numbered content.
    return [heading, *content]


def closing(day, config, ledger):
    text = (
        "<b>Your next step</b>\n"
        "Read in order: world finance → India finance → world headlines → India headlines → today's learning.\n\n"
        "Choose one source link and read the original. Write three lines: what changed, which business might be exposed, and what evidence would change your view. Then try today's lesson before revealing its answer.\n\n"
        "Headlines and AI summaries are starting points, not verified investment conclusions."
    )
    return tg.deliver_messages(day, [text], config, ledger, identifier(day, config, "closing"))


def deliver(digest, config, ledger, day=None):
    day = day or digest["date_ist"]
    results = {}
    # Render before any send, so invalid links/blocks fail without half a bundle.
    prepared = (
        [
            (edition, edition_messages(digest, title, categories))
            for edition, title, categories in EDITIONS
        ]
        if digest
        else []
    )
    if not digest:
        results.update({edition: "already_accepted" for edition, _, _ in EDITIONS})
    for edition, messages in prepared:
        try:
            time.sleep(1.1)
            results[edition] = tg.deliver_messages(
                day, messages, config, ledger, identifier(day, config, edition)
            )
        except BotError:
            results[edition] = "failed_or_pending"
    try:
        results["learning"] = finance_teacher.deliver(day, config, ledger, digest)
    except BotError:
        results["learning"] = "failed_or_pending"
    successful = {"telegram_accepted", "already_accepted"}
    if all(status in successful for status in results.values()):
        try:
            time.sleep(1.1)
            results["closing"] = closing(day, config, ledger)
        except BotError:
            results["closing"] = "failed_or_pending"
    else:
        results["closing"] = "withheld_incomplete_bundle"
    return {
        "status": "telegram_accepted"
        if all(status in successful for status in results.values())
        else "partial_delivery",
        "editions": results,
    }
