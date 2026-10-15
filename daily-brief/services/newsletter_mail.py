"""Bounded Gmail IMAP intake. Read-only mailbox and PEEK; no mail mutations."""

import hashlib
import imaplib
import json
import os
import re
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path

from bs4 import BeautifulSoup

CATALOG = json.loads(
    (Path(__file__).resolve().parents[1] / "newsletter_sources.json").read_text(encoding="utf-8")
)
MAX_MESSAGE_BYTES = 262144
MAX_MESSAGES = 30


@dataclass(frozen=True)
class MailboxConfig:
    user: str = field(repr=False)
    password: str = field(repr=False)
    exact_senders: tuple = ()

    @classmethod
    def load(cls):
        user = os.getenv("NEWSLETTER_IMAP_USER", "").strip()
        password = os.getenv("NEWSLETTER_IMAP_PASSWORD", "").replace(" ", "")
        senders = tuple(
            value.strip().lower()
            for value in os.getenv("NEWSLETTER_ALLOWED_SENDERS", "").split(",")
            if value.strip()
        )
        if not re.fullmatch(r"[^\s@]+@gmail\.com", user, re.I) or not password:
            raise ValueError("Newsletter Gmail credentials are missing or invalid.")
        if any(not re.fullmatch(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", value) for value in senders):
            raise ValueError("Invalid newsletter sender configuration.")
        return cls(user, password, senders)


def approved_sender(message, config):
    addresses = getaddresses(message.get_all("From", []))
    if len(addresses) != 1:
        return None
    sender = addresses[0][1].lower()
    domain = sender.rpartition("@")[2]
    for provider in CATALOG["providers"]:
        if any(domain == root or domain.endswith("." + root) for root in provider["domains"]):
            return provider
    if sender in config.exact_senders:
        # Explicit approvals can support shared platforms; never approve their whole domain.
        return {
            "id": "approved",
            "name": "Approved AI newsletter",
            "subscribe": "https://mail.google.com/",
        }
    return None


def authenticated(message):
    # Reported Gmail authentication is a header check, not our own signature verification.
    headers = message.get_all("Authentication-Results", [])
    return bool(
        headers
        and re.match(r"\s*mx\.google\.com\s*;", str(headers[0]), re.I)
        and re.search(r"\bdmarc=pass\b", str(headers[0]), re.I)
    )


def clean_body(message):
    body = message.get_body(preferencelist=("plain", "html"))
    if body is None or body.get_content_disposition() == "attachment":
        return ""
    text = body.get_content()
    if not isinstance(text, str):
        return ""
    if body.get_content_type() == "text/html":
        soup = BeautifulSoup(text, "html.parser")
        for element in soup.select("script,style,form,img,svg,head,[hidden],[aria-hidden=true]"):
            element.decompose()
        text = soup.get_text("\n", strip=True)
    lines = []
    for line in text.splitlines():
        if re.search(
            r"unsubscribe|manage (?:your )?(?:preferences|subscription)|view (?:this )?(?:email|in browser)|sponsored|advertisement|paid partner",
            line,
            re.I,
        ):
            continue
        # No tracked links, recipient addresses or personalised URLs enter model context.
        line = re.sub(r"https?://\S+", "", line)
        line = re.sub(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", "[email removed]", line, flags=re.I)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)[:6000]


def issue(raw, config, now=None):
    now = now or datetime.now(timezone.utc)
    if len(raw) > MAX_MESSAGE_BYTES:
        return None
    message = BytesParser(policy=policy.default).parsebytes(raw)
    provider = approved_sender(message, config)
    if not provider or not authenticated(message):
        return None
    try:
        published = parsedate_to_datetime(message["Date"])
        if published.tzinfo is None or not timedelta(0) <= now - published <= timedelta(days=7):
            return None
    except (TypeError, ValueError, OverflowError):
        return None
    subject = re.sub(r"\s+", " ", str(message.get("Subject", "AI newsletter"))).strip()[:250]
    subject = re.sub(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", "[email removed]", subject, flags=re.I)
    text = clean_body(message)
    if len(text) < 100 or re.search(
        r"confirm your|verify your|welcome to|reset.*password|sign.in code", subject, re.I
    ):
        return None
    identifier = hashlib.sha256(
        (str(message.get("Message-ID", "")) + subject + published.isoformat()).encode()
    ).hexdigest()[:24]
    return {
        "id": "mail-" + identifier,
        "title": subject,
        "publisher": provider["name"],
        "url": provider["subscribe"],
        "published_at": published.astimezone(timezone.utc).isoformat(),
        "read_status": "approved_newsletter_excerpt",
        "evidence_text": text,
        "categories": ["policy"],
        "source_kind": "newsletter_commentary",
    }


def collect(now=None, factory=imaplib.IMAP4_SSL):
    if os.getenv("NEWSLETTER_IMAP_ENABLED", "false").lower() != "true":
        return {"status": "not_enabled", "items": [], "checked": 0}
    connection = None
    stage = "configuration"
    try:
        config = MailboxConfig.load()
        stage = "connection"
        connection = factory(
            "imap.gmail.com", 993, ssl_context=ssl.create_default_context(), timeout=20
        )
        stage = "authentication"
        connection.login(config.user, config.password)
        stage = "mailbox_selection"
        status, _ = connection.select("INBOX", readonly=True)
        if status != "OK":
            raise ValueError("Mailbox unavailable")
        now = now or datetime.now(timezone.utc)
        since = (now - timedelta(days=7)).strftime("%d-%b-%Y")
        domains = [domain for provider in CATALOG["providers"] for domain in provider["domains"]]
        uids = set()
        stage = "sender_search"
        for sender in [*domains, *config.exact_senders]:
            status, data = connection.uid(
                "search", None, "SINCE", since, "FROM", '"' + sender + '"'
            )
            if status != "OK":
                raise ValueError("Mailbox search unavailable")
            uids.update((data[0] or b"").split())
        selected = sorted(uids, key=int, reverse=True)[:MAX_MESSAGES]
        items, skipped = [], 0
        stage = "approved_message_read"
        for uid in selected:
            status, response = connection.uid("fetch", uid, "(RFC822.SIZE BODY.PEEK[HEADER])")
            if status != "OK":
                skipped += 1
                continue
            literals = [part for part in response if isinstance(part, tuple)]
            if not literals:
                skipped += 1
                continue
            descriptor, headers = literals[0]
            size = re.search(rb"RFC822.SIZE (\d+)", descriptor)
            header = BytesParser(policy=policy.default).parsebytes(headers)
            if (
                not size
                or int(size[1]) > MAX_MESSAGE_BYTES
                or not approved_sender(header, config)
                or not authenticated(header)
            ):
                skipped += 1
                continue
            status, response = connection.uid("fetch", uid, "(BODY.PEEK[])")
            raw = next((part[1] for part in response if isinstance(part, tuple)), b"")
            parsed = issue(raw, config, now) if status == "OK" else None
            if parsed:
                items.append(parsed)
            else:
                skipped += 1
        return {
            "status": "available" if items else "no_approved_issues",
            "items": items,
            "checked": len(selected),
            "skipped": skipped,
            "capped": len(uids) > MAX_MESSAGES,
        }
    except (imaplib.IMAP4.error, OSError, ValueError, TypeError, KeyError):
        # Provider replies can contain account details: never log exceptions or raw headers.
        return {"status": "unavailable", "items": [], "checked": 0, "failure_stage": stage}
    finally:
        if connection:
            try:
                connection.logout()
            except (imaplib.IMAP4.error, OSError):
                pass
