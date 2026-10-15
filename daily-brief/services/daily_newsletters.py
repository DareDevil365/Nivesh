"""Four dated news editions, a separate lesson, then one closing research task."""

import hashlib
import html
import time
from datetime import date

from services import ai_newsletter, finance_class, finance_teacher, news_memory, news_reader
from services import telegram_delivery as tg
from services.news_bot import BotError

EDITIONS = (
    ("world_finance", "World news & finance", {"world", "us", "policy", "commodities", "events"}),
    ("india_finance", "India news & finance", {"india"}),
    ("world_general", "World general news", {"world_general"}),
    ("india_general", "India general news", {"india_general"}),
)


def identifier(day, config, edition):
    return "universal-v2-" + edition + "-" + config.delivery_id(day)


def existing_delivery(day, config, ledger):
    # Missing/uncertain editions do not prevent other editions from being attempted.
    complete = []
    for edition in [entry[0] for entry in EDITIONS] + ["weekly"]:
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
        "Read the news and AI newsletter, check the seven-day follow-up, then try Finance Class and its case study. Stock Daddy is the separate company-research track.\n\n"
        "Open one original source. Explain one new finance concept in your own words, and name one fact you would check before believing an explanation. Try the lesson's question before revealing its answer.\n\n"
        "Headlines and AI summaries are starting points, not verified investment conclusions."
    )
    return tg.deliver_messages(day, [text], config, ledger, identifier(day, config, "closing"))


def weekly_messages(items, day):
    blocks = [
        "<b>7-day follow-up · New to your briefing</b>\n"
        + date.fromisoformat(day).strftime("%A, %d %B %Y")
    ]
    content = [
        "<b>Earlier developments worth revisiting</b>\nPublished between one and seven days ago; matching sent headlines from the last fourteen days are suppressed. Selection is a significance heuristic, not an exhaustive events calendar."
    ]
    for item in items:
        url = news_reader.safe_link(item["url"])
        if not url:
            raise BotError("Unsafe weekly citation URL.")
        content.append(
            f'<a href="{html.escape(url, quote=True)}">{html.escape(item["title"])}</a>\n{html.escape(item["publisher"])} · {html.escape(item["published_at"])}\nEvidence: {html.escape(item["read_status"].replace("_", " "))}. Read the source for the development and its event date.'
        )
        if item.get("previous_link_seen"):
            content.append(
                "<i>Updated headline at a link seen previously; check what actually changed.</i>"
            )
    if not items:
        content.append(
            "No additional qualifying unseen stories were found in this bounded scan. This does not establish that all major events have been covered."
        )
    return [*blocks, *finance_class.pack_blocks(content)]


def deliver(
    digest,
    config,
    ledger,
    day=None,
    weekly_pack=None,
    include_ai=False,
    ai_use_ai=True,
    ai_offline=False,
):
    day = day or digest["date_ist"]
    results = {}
    memory_key = news_memory.history_key(config)
    history = news_memory.load(ledger, memory_key, day)
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
                day,
                messages,
                config,
                ledger,
                identifier(day, config, edition),
                story_entries=news_memory.entries_for(
                    news_memory.sources_in(
                        digest, next(entry[2] for entry in EDITIONS if entry[0] == edition)
                    ),
                    day,
                ),
            )
        except BotError:
            results[edition] = "failed_or_pending"
    # Reconciliation heals a history write failure without replaying accepted messages.
    for edition, _, _ in EDITIONS:
        try:
            news_memory.reconcile(ledger, memory_key, day, identifier(day, config, edition))
        except BotError:
            results[edition] = "history_update_failed"
    history = news_memory.load(ledger, memory_key, day)
    weekly = news_memory.weekly_candidates(weekly_pack, history) if weekly_pack else []
    try:
        time.sleep(1.1)
        results["weekly"] = tg.deliver_messages(
            day,
            weekly_messages(weekly, day),
            config,
            ledger,
            identifier(day, config, "weekly"),
            story_entries=news_memory.entries_for(weekly, day),
        )
        news_memory.reconcile(ledger, memory_key, day, identifier(day, config, "weekly"))
    except BotError:
        results["weekly"] = "failed_or_pending"
    teaching = digest.get("finance_teaching") if digest else None
    teaching = teaching or finance_class.prepare(day, use_ai=False)
    try:
        results["finance_class"] = finance_class.deliver(day, config, ledger, teaching)
    except BotError:
        results["finance_class"] = "failed_or_pending"
    try:
        results["finance_context"] = finance_class.deliver(
            day, config, ledger, teaching, context=True
        )
    except BotError:
        results["finance_context"] = "failed_or_pending"
    try:
        results["stock_daddy"] = finance_teacher.deliver(day, config, ledger, digest)
    except BotError:
        results["stock_daddy"] = "failed_or_pending"
    if include_ai:
        try:
            results["ai_newsletter"] = ai_newsletter.deliver(
                day, config, ledger, use_ai=ai_use_ai, offline=ai_offline
            )
        except BotError:
            results["ai_newsletter"] = "failed_or_pending"
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
