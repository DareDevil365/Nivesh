"""Detailed HTML report with its own SMTP/Sent reconciliation and durable claim."""

import hashlib
import html
import os
import secrets
import smtplib
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import format_datetime

from services import news_bot


@dataclass(repr=False)
class ReportConfig(news_bot.MailConfig):
    @classmethod
    def load(cls):
        user = os.getenv("NEWS_REPORT_SMTP_USER") or os.getenv("NEWSLETTER_IMAP_USER", "")
        password = (
            os.getenv("NEWS_REPORT_SMTP_PASSWORD") or os.getenv("NEWSLETTER_IMAP_PASSWORD", "")
        ).replace(" ", "")
        recipient = os.getenv("NEWS_DETAIL_EMAIL_TO", "").strip()
        if (
            not news_bot.valid_address(user)
            or not user.lower().endswith("@gmail.com")
            or not news_bot.valid_address(recipient)
            or not password
        ):
            raise news_bot.BotError("Detailed report Gmail credentials or recipient are missing.")
        return cls(user.strip(), password, recipient)

    def message_id(self, day):
        identity = hashlib.sha256(
            (self.user.casefold() + "|" + self.recipient.casefold()).encode()
        ).hexdigest()[:20]
        return f"<daily-brief-report-v1-{day}-{identity}@gmail.com>"


def enabled():
    return os.getenv("NEWS_DETAIL_EMAIL_ENABLED", "false").lower() == "true"


def build(day, editions, weekly, ai=None):
    from services import ai_newsletter, daily_newsletters

    parts = []
    for _, title, categories in daily_newsletters.EDITIONS:
        parts.extend(daily_newsletters.edition_messages(editions, title, categories))
    parts.extend(daily_newsletters.weekly_messages(weekly, day))
    if ai:
        parts.extend(ai_newsletter.messages(ai))
    body = '<!doctype html><html><head><meta charset="utf-8"></head><body style="font-family:Arial,sans-serif;max-width:800px;margin:24px auto;line-height:1.6">'
    body += (
        "<h1>Daily Brief — "
        + html.escape(day)
        + "</h1><p>Detailed news and research. Finance Class stays separate on Telegram.</p>"
    )
    body += "".join(
        '<section style="margin:24px 0">' + part.replace("\n", "<br>") + "</section>"
        for part in parts
    )
    body += "</body></html>"
    # Text fallback includes the real URLs, rather than discarding links with markup.
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(body, "html.parser")
    for link in soup.find_all("a", href=True):
        link.replace_with(link.get_text() + " (" + link["href"] + ")")
    return {
        "subject": "Daily Brief — Detailed news — " + day,
        "html": body,
        "text": soup.get_text("\n", strip=True),
    }


def existing(day, ledger, config=None):
    return news_bot.existing_delivery(day, config or ReportConfig.load(), ledger)


def send(config, report, identifier):
    message = EmailMessage()
    message["From"] = config.user
    message["To"] = config.recipient
    message["Subject"] = report["subject"]
    message["Date"] = format_datetime(datetime.now(timezone.utc))
    message["Message-ID"] = identifier
    message.set_content(report["text"], charset="utf-8")
    message.add_alternative(report["html"], subtype="html", charset="utf-8")
    try:
        with smtplib.SMTP_SSL(
            "smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=25
        ) as client:
            client.login(config.user, config.password)
            if client.send_message(message, from_addr=config.user, to_addrs=[config.recipient]):
                raise news_bot.BotError("Detailed report recipient was refused.")
    except (OSError, smtplib.SMTPException) as error:
        raise news_bot.BotError(
            "Detailed report SMTP acceptance is uncertain; inspect Sent before retrying."
        ) from error


def deliver(day, report, ledger, config=None):
    config = config or ReportConfig.load()
    prior = existing(day, ledger, config)
    if prior:
        return prior
    identifier = config.message_id(day)
    key = hashlib.sha256(identifier.encode()).hexdigest()[:32]
    ledger.reserve(
        key,
        {
            "status": "pending",
            "message_id": identifier,
            "claimed_at": datetime.now(timezone.utc).isoformat(),
            "attempt": secrets.token_hex(8),
        },
    )
    send(config, report, identifier)
    ledger.accepted(
        key,
        {
            "status": "accepted",
            "message_id": identifier,
            "accepted_at": datetime.now(timezone.utc).isoformat(),
            "basis": "smtp_acceptance",
        },
    )
    return "smtp_accepted"
