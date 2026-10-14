"""Private-chat Telegram delivery; no token, chat ID or response body is logged."""

import hashlib
import os
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from services import news_digest
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
        return "telegram-" + day + "-" + hashlib.sha256(destination.encode()).hexdigest()[:20]


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


def shorten(text, units):
    """Bound UTF-16 units conservatively, preserving Unicode code points."""
    text = " ".join(str(text).split())
    if len(text.encode("utf-16-le")) // 2 <= units:
        return text
    output, used = [], 0
    for character in text:
        width = len(character.encode("utf-16-le")) // 2
        if used + width > units - 1:
            break
        output.append(character)
        used += width
    return "".join(output).rstrip() + "…"


def caption(digest):
    lines = [
        f"Nivesh morning brief · {digest['date_ist']}",
        "Section previews (full text attached):",
    ]
    for section in digest["sections"][:6]:
        fallback = digest.get("summary_modes", {}).get(section["id"]) == "headline_fallback"
        label = shorten(section["label"], 26) + (" [headlines]" if fallback else "")
        lines.append(label + ": " + shorten(section["bullets"][0]["text"], 72))
    if digest.get("glossary"):
        term = digest["glossary"][0]
        lines.append("Learn: " + shorten(term["term"] + " — " + term["meaning"], 110))
    lines.append(
        "Sources, context and coverage gaps are in the attached report. AI interpretation is unverified."
    )
    return shorten_lines(lines, 1024)


def shorten_lines(lines, limit):
    text = "\n\n".join(lines)
    if len(text.encode("utf-16-le")) // 2 > limit:
        raise BotError("Telegram preview exceeds the caption limit; refusing an incomplete send.")
    return text


def existing_delivery(day, config, ledger):
    key = hashlib.sha256(config.delivery_id(day).encode()).hexdigest()[:32]
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
    day = digest["date_ist"]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise BotError("Invalid Telegram report date.")
    text = news_digest.email_text(digest).encode("utf-8")
    preview = caption(digest)
    delivery_id = config.delivery_id(day)
    key = hashlib.sha256(delivery_id.encode()).hexdigest()[:32]
    ledger.reserve(
        key,
        {
            "status": "pending",
            "delivery_id": delivery_id,
            "claimed_at": datetime.now(timezone.utc).isoformat(),
            "attempt": secrets.token_hex(8),
        },
    )
    result = api(
        config,
        "sendDocument",
        data={"chat_id": config.chat_id, "caption": preview},
        files={"document": (f"nivesh-{day}.txt", text, "text/plain; charset=utf-8")},
    )
    if (
        not isinstance(result, dict)
        or type(result.get("message_id")) is not int
        or result["message_id"] <= 0
        or not isinstance(result.get("chat"), dict)
        or str(result["chat"].get("id")) != config.chat_id
        or result["chat"].get("type") != "private"
        or not result.get("document")
    ):
        raise BotError("Telegram returned an unexpected receipt; review the pending delivery.")
    ledger.accepted(
        key,
        {
            "status": "accepted",
            "delivery_id": delivery_id,
            "accepted_at": datetime.now(timezone.utc).isoformat(),
            "basis": "telegram_api_acceptance",
        },
    )
    return "telegram_accepted"
