"""Private-chat Telegram delivery; no token, chat ID or response body is logged."""

import hashlib
import html
import json
import os
import re
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from services import news_reader
from services.news_bot import BotError


@dataclass
class TelegramConfig:
    token: str = field(repr=False)
    chat_id: str = field(default="", repr=False)

    @classmethod
    def load(cls, require_chat=True):
        config = cls(
            os.getenv("NEWS_TELEGRAM_BOT_TOKEN", "").strip(),
            os.getenv("NEWS_TELEGRAM_CHAT_ID", "").strip(),
        )
        if not re.fullmatch(r"[1-9][0-9]*:[A-Za-z0-9_-]{20,}", config.token):
            raise BotError("Add your BotFather token to NEWS_TELEGRAM_BOT_TOKEN privately.")
        if (require_chat or config.chat_id) and not re.fullmatch(r"[1-9][0-9]*", config.chat_id):
            raise BotError("Pair your private chat using scripts/setup_telegram.py first.")
        return config

    def delivery_id(self, day):
        destination = self.token.split(":", 1)[0] + ":" + self.chat_id
        return (
            "telegram-messages-v2-"
            + day
            + "-"
            + hashlib.sha256(destination.encode()).hexdigest()[:20]
        )


def api(config, method, *, data=None, files=None):
    """One verified HTTPS request, no redirects or automatic send retries."""
    try:
        with httpx.Client(timeout=35, trust_env=False, follow_redirects=False) as client:
            response = client.post(
                f"https://api.telegram.org/bot{config.token}/{method}",
                data=data or {},
                files=files,
            )
        if response.status_code != 200:
            hints = {
                401: "Check the BotFather token.",
                403: "Start/unblock the bot in Telegram.",
                409: "Another update reader or webhook is active; review bot setup.",
                429: "Telegram rate limited this attempt; no automatic resend was made.",
            }
            raise BotError(
                f"Telegram request failed ({response.status_code}). "
                + hints.get(response.status_code, "Check the private bot setup.")
            )
        payload = response.json()
        if not isinstance(payload, dict) or payload.get("ok") is not True:
            raise BotError("Telegram did not confirm success; inspect delivery before retrying.")
        return payload.get("result")
    except (httpx.HTTPError, ValueError):
        # httpx exceptions contain the token-bearing URL. Never chain or print them.
        raise BotError(
            "Telegram could not confirm the request; no automatic retry was made."
        ) from None


def check(config):
    me = api(config, "getMe")
    if (
        not isinstance(me, dict)
        or me.get("is_bot") is not True
        or str(me.get("id")) != config.token.split(":")[0]
    ):
        raise BotError("Telegram bot identity did not match the configured token.")
    chat = api(config, "getChat", data={"chat_id": config.chat_id})
    if (
        not isinstance(chat, dict)
        or chat.get("type") != "private"
        or str(chat.get("id")) != config.chat_id
    ):
        raise BotError("Telegram destination must match the paired private chat.")


def render_messages(digest):
    """Keep complete HTML blocks/links together, conservatively below 4096 units."""
    esc = html.escape
    coverage = digest["coverage"]
    blocks = [
        f"Prepared: {esc(digest['generated_at'])}. News window: last 24 hours.\n"
        f"Coverage: {coverage['headlines']} headlines; {coverage['article_excerpts']} article excerpts, "
        f"{coverage['feed_excerpts']} feed excerpts, {coverage['headline_only']} headline-only.\n"
        "AI interpretation is unverified. Headline fallbacks are labelled below."
    ]
    for section in digest["sections"]:
        mode = digest.get("summary_modes", {}).get(section["id"], "unverified")
        blocks.append(
            f"<b>{esc(section['label'])}</b>\nSummary mode: {esc(mode.replace('_', ' '))}"
        )
        for bullet in section["bullets"]:
            blocks.append(esc(bullet["text"]))
            blocks.append("<b>Why it may matter:</b> " + esc(bullet["why_it_matters"]))
            for source in bullet["sources"]:
                url = news_reader.safe_link(source["url"])
                if not url:
                    raise BotError("Unsafe Telegram citation URL; nothing was sent.")
                blocks.append(
                    f'<a href="{esc(url, quote=True)}">{esc(source["publisher"])} — {esc(source["title"])}</a>\n'
                    f"{esc(source['published_at'])} | {esc(source['read_status'].replace('_', ' '))}"
                )
    blocks.append("<b>Finance terms to learn</b>")
    blocks.extend(
        f"<b>{esc(term['term'])}:</b> {esc(term['meaning'])}" for term in digest["glossary"]
    )
    blocks.append("<b>Source coverage and limitations</b>")
    blocks.extend(
        f"{esc(feed['id'])}: {esc(feed['status'])}" + (" (stale)" if feed.get("stale") else "")
        for feed in digest["feeds"]
    )
    blocks.append(esc(digest["limitations"]))
    chunks, current = [], ""
    for block in blocks:
        if len(block.encode("utf-16-le")) // 2 > 3500:
            raise BotError("A Telegram report block exceeds the safe limit; nothing was sent.")
        candidate = current + ("\n\n" if current else "") + block
        if len(candidate.encode("utf-16-le")) // 2 > 3500:
            chunks.append(current)
            current = block
        else:
            current = candidate
    if current:
        chunks.append(current)
    if not chunks or len(chunks) > 20:
        raise BotError("Unexpected Telegram report size; nothing was sent.")
    return [
        f"<b>Nivesh · {esc(digest['date_ist'])} · {index}/{len(chunks)}</b>\n\n" + chunk
        for index, chunk in enumerate(chunks, 1)
    ]


def existing_delivery(day, config, ledger):
    return existing_id(config.delivery_id(day), ledger)


def existing_id(delivery_id, ledger):
    key = hashlib.sha256(delivery_id.encode()).hexdigest()[:32]
    previous = ledger.get(key)
    if previous and previous.get("status") == "accepted":
        return "already_accepted"
    if previous:
        raise BotError(
            "An earlier Telegram attempt is pending. Check your chat and the claim before retrying; "
            "Telegram has no Sent lookup or idempotency key."
        )
    return None


def deliver(digest, config, ledger):
    existing = existing_delivery(digest["date_ist"], config, ledger)
    if existing:
        return existing
    return deliver_messages(
        digest["date_ist"],
        render_messages(digest),
        config,
        ledger,
        config.delivery_id(digest["date_ist"]),
    )


def deliver_messages(day, messages, config, ledger, delivery_id):
    existing = existing_id(delivery_id, ledger)
    if existing:
        return existing
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise BotError("Invalid Telegram report date.")
    if (
        not messages
        or len(messages) > 20
        or any(len(message.encode("utf-16-le")) // 2 > 4096 for message in messages)
    ):
        raise BotError("Telegram message size is invalid; nothing was sent.")
    key = hashlib.sha256(delivery_id.encode()).hexdigest()[:32]
    record = {
        "status": "pending",
        "delivery_id": delivery_id,
        "claimed_at": datetime.now(timezone.utc).isoformat(),
        "attempt": secrets.token_hex(8),
        "total_parts": len(messages),
        "confirmed_parts": 0,
        "body_sha256": hashlib.sha256(
            json.dumps(messages, ensure_ascii=False).encode()
        ).hexdigest(),
    }
    ledger.reserve(key, record)
    for index, text in enumerate(messages, 1):
        if index > 1:
            time.sleep(1.1)
        result = api(
            config,
            "sendMessage",
            data={
                "chat_id": config.chat_id,
                "text": text,
                "parse_mode": "HTML",
                "link_preview_options": '{"is_disabled":true}',
            },
        )
        if (
            not isinstance(result, dict)
            or type(result.get("message_id")) is not int
            or result["message_id"] <= 0
            or not isinstance(result.get("chat"), dict)
            or str(result["chat"].get("id")) != config.chat_id
            or result["chat"].get("type") != "private"
        ):
            raise BotError("Telegram returned an unexpected receipt; review the pending delivery.")
        record = {**record, "confirmed_parts": index}
        if index == len(messages):
            record.update(
                status="accepted",
                accepted_at=datetime.now(timezone.utc).isoformat(),
                basis="telegram_api_acceptance",
            )
        ledger.accepted(key, record)
    return "telegram_accepted"
