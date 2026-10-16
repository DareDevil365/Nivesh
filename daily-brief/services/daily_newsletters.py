"""Four dated news editions, a separate lesson, then one closing research task."""

import hashlib
import html
import time
from datetime import date

from services import (
    ai_newsletter,
    brief_format,
    detailed_report,
    finance_class,
    finance_teacher,
    news_memory,
    news_reader,
)
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


def existing_delivery(day, config, ledger, include_report=False):
    # Missing/uncertain editions do not prevent other editions from being attempted.
    complete = []
    for edition in [entry[0] for entry in EDITIONS] + ["weekly"]:
        key = hashlib.sha256(identifier(day, config, edition).encode()).hexdigest()[:32]
        record = ledger.get(key)
        complete.append(bool(record and record.get("status") == "accepted"))
    if all(complete) and include_report and not detailed_report.existing(day, ledger):
        return None
    return "already_accepted" if all(complete) else None


def edition_messages(digest, title, categories, compact=False):
    day = date.fromisoformat(digest["date_ist"]).strftime("%A, %d %B %Y")
    sections = [section for section in digest["sections"] if section["id"] in categories]
    heading = f"<b>{html.escape(title)}</b>\n{day}"
    if compact:
        try:
            content = brief_format.news_blocks(brief_format.select(digest, categories))
        except ValueError as error:
            raise BotError("Unsafe compact newsletter citation.") from error
        return [
            heading
            + "\n\n"
            + ("\n\n".join(content) or "No usable summary was available in this scan.")
        ]
    if not sections:
        body = "No validated summary was available for this edition in today's collection. This does not establish that nothing happened. Check original sources."
        return [heading, body]
    scope = next((edition for edition, label, _ in EDITIONS if label == title), None)
    report = {
        **digest,
        "sections": sections,
        "glossary": [],
        "research_cards": [c for c in digest.get("research_cards", []) if c["scope"] == scope],
    }
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


def weekly_messages(items, day, compact=False):
    if compact:
        lines = []
        for item in items[:2]:
            url = news_reader.safe_link(item["url"])
            if not url:
                raise BotError("Unsafe weekly citation URL.")
            label = brief_format.sentence(item["title"], 22, "Earlier report — open source")
            lines.append(
                '<a href="' + html.escape(url, quote=True) + '">' + html.escape(label) + "</a>"
            )
        return [
            "<b>7-day follow-up</b>\n"
            + ("\n".join(lines) or "No additional unseen reports in this scan.")
        ]
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
    include_report=False,
):
    day = day or digest["date_ist"]
    results = {}
    compact = brief_format.enabled()
    report_prior, report_error = None, False
    if include_report:
        try:
            report_prior = detailed_report.existing(day, ledger)
        except BotError:
            report_error = True
            results["detailed_email"] = "failed_or_pending"
    need_report = include_report and not report_prior and not report_error
    captured_ai = []
    if need_report and not digest:
        raise BotError("Full news data is required before preparing the detailed email report.")
    memory_key = news_memory.history_key(config)
    history = news_memory.load(ledger, memory_key, day)
    # Render before any send, so invalid links/blocks fail without half a bundle.
    prepared = (
        [
            (edition, edition_messages(digest, title, categories, compact=compact))
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
                    (brief_format.sources_in if compact else news_memory.sources_in)(
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
            weekly_messages(weekly, day, compact=compact),
            config,
            ledger,
            identifier(day, config, "weekly"),
            story_entries=news_memory.entries_for(weekly[:2] if compact else weekly, day),
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
                day,
                config,
                ledger,
                use_ai=ai_use_ai,
                offline=ai_offline,
                capture=captured_ai.append if need_report else None,
            )
        except BotError:
            results["ai_newsletter"] = "failed_or_pending"
    if include_report and not report_error:
        try:
            if report_prior:
                results["detailed_email"] = report_prior
            elif include_ai and not captured_ai:
                results["detailed_email"] = "withheld_missing_ai_report"
            else:
                report = detailed_report.build(
                    day, digest, weekly, captured_ai[0] if captured_ai else None
                )
                results["detailed_email"] = detailed_report.deliver(day, report, ledger)
        except BotError:
            results["detailed_email"] = "failed_or_pending"
    successful = {"telegram_accepted", "already_accepted", "smtp_accepted", "already_in_sent"}
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
