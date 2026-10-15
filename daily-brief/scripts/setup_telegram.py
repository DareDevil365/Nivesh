"""Pair one private Telegram chat using a one-time Start link; never print secrets."""

import argparse
import json
import os
import re
import secrets
import sys
import time
from pathlib import Path

from dotenv import set_key

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.news_bot import BotError  # noqa: E402
from services.telegram_delivery import TelegramConfig, api, check  # noqa: E402

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def pairing_chat(updates, code, now):
    if not re.fullmatch(r"[A-Za-z0-9_-]{20,64}", code or ""):
        raise BotError("Generate a private Start link with --link first.")
    if not isinstance(updates, list):
        raise BotError("Unexpected Telegram update response.")
    matches = set()
    for update in updates:
        message = update.get("message", {}) if isinstance(update, dict) else {}
        chat, sender = message.get("chat", {}), message.get("from", {})
        date = message.get("date")
        if (
            message.get("text") == "/start " + code
            and chat.get("type") == "private"
            and type(chat.get("id")) is int
            and chat["id"] > 0
            and sender.get("id") == chat["id"]
            and not sender.get("is_bot", False)
            and type(date) is int
            and -60 <= now - date <= 1800
        ):
            matches.add(str(chat["id"]))
    if len(matches) != 1:
        raise BotError(
            "No unique recent pairing found. Open the generated link and press Start, then retry."
        )
    return matches.pop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--link", action="store_true")
    group.add_argument("--bind", action="store_true")
    args = parser.parse_args()
    config = TelegramConfig.load(require_chat=False)
    if args.link:
        me = api(config, "getMe")
        username = me.get("username", "") if isinstance(me, dict) else ""
        if not re.fullmatch(r"[A-Za-z0-9_]{5,32}", username) or me.get("is_bot") is not True:
            raise BotError("Telegram did not return a valid bot username.")
        code = secrets.token_urlsafe(24)
        set_key(str(ENV_PATH), "NEWS_TELEGRAM_PAIR_CODE", code)
        print(
            json.dumps(
                {
                    "start_link": f"https://t.me/{username}?start={code}",
                    "next": "Open link, press Start, then run --bind within 30 minutes.",
                }
            )
        )
    else:
        updates = api(
            config,
            "getUpdates",
            data={"timeout": "0", "limit": "100", "allowed_updates": '["message"]'},
        )
        config.chat_id = pairing_chat(
            updates, os.getenv("NEWS_TELEGRAM_PAIR_CODE", ""), time.time()
        )
        check(config)
        set_key(str(ENV_PATH), "NEWS_TELEGRAM_CHAT_ID", config.chat_id)
        set_key(str(ENV_PATH), "NEWS_DELIVERY", "telegram")
        set_key(str(ENV_PATH), "NEWS_TELEGRAM_PAIR_CODE", "")
        print(
            json.dumps(
                {"private_chat_paired": True, "delivery": "telegram", "sent_any_message": False}
            )
        )


if __name__ == "__main__":
    try:
        main()
    except BotError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from None
