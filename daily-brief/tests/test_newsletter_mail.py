"""Mailbox intake privacy, sender/date validation and read-only protocol behavior."""

import imaplib
import json
import unittest
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import format_datetime
from unittest.mock import patch

from services import newsletter_mail as mail

NOW = datetime(2026, 10, 15, 9, tzinfo=timezone.utc)
CONFIG = mail.MailboxConfig("reader@gmail.com", "private-app-password")


def email(sender="news@therundown.ai", age=0, authenticated=True):
    message = EmailMessage()
    message["From"] = sender
    message["To"] = "private-reader@example.com"
    message["Subject"] = "AI models and research this week"
    message["Date"] = format_datetime(NOW - timedelta(days=age))
    message["Message-ID"] = "<private-issue-identifier@example.com>"
    if authenticated:
        message["Authentication-Results"] = "mx.google.com; dmarc=pass header.from=therundown.ai"
    message.set_content(
        "A company announced a new AI model and described its research approach. The report discusses its limitations and availability.\nContact private-reader@example.com\nhttps://tracking.example/click?secret=PRIVATE\nUnsubscribe here"
    )
    return message


class FakeMailbox:
    def __init__(self, message=None, size=None, fail=False):
        self.message = message or email()
        self.raw = self.message.as_bytes()
        self.size = size or len(self.raw)
        self.calls = []
        self.fail = fail

    def login(self, user, password):
        if self.fail:
            raise imaplib.IMAP4.error("private-account@example.com private provider error")

    def select(self, folder, readonly=False):
        self.calls.append(("select", folder, readonly))
        return "OK", []

    def uid(self, operation, *args):
        self.calls.append((operation, *args))
        if operation == "search":
            return "OK", [b"1"]
        if "HEADER" in args[-1]:
            headers = self.raw.split(b"\n\n", 1)[0] + b"\n\n"
            return "OK", [(f"1 (RFC822.SIZE {self.size} BODY[HEADER]".encode(), headers)]
        return "OK", [(b"1 (BODY[]", self.raw)]

    def logout(self):
        self.calls.append(("logout",))


class NewsletterMailTests(unittest.TestCase):
    def test_only_approved_authenticated_issue_reaches_model_shape(self):
        result = mail.issue(email().as_bytes(), CONFIG, NOW)
        self.assertEqual(result["publisher"], "The Rundown AI")
        text = json.dumps(result)
        for secret in (
            "private-reader",
            "PRIVATE",
            "tracking.example",
            "private-issue-identifier",
            "private-app-password",
        ):
            self.assertNotIn(secret, text)
        self.assertEqual(result["url"], "https://www.therundown.ai/subscribe")
        self.assertEqual(result["source_kind"], "newsletter_commentary")

    def test_display_names_and_domain_lookalikes_are_not_approval(self):
        for sender in (
            '"The Rundown AI" <attacker@example.com>',
            "news@therundown.ai.evil.example",
            "news@eviltherundown.ai",
        ):
            self.assertIsNone(mail.issue(email(sender).as_bytes(), CONFIG, NOW))
        self.assertIsNotNone(
            mail.issue(email("news@updates.therundown.ai").as_bytes(), CONFIG, NOW)
        )

    def test_missing_or_failed_reported_authentication_is_rejected(self):
        self.assertIsNone(mail.issue(email(authenticated=False).as_bytes(), CONFIG, NOW))
        message = email()
        message.replace_header("Authentication-Results", "mx.google.com; dmarc=fail")
        message["Authentication-Results"] = "mx.google.com; dmarc=pass"
        self.assertIsNone(mail.issue(message.as_bytes(), CONFIG, NOW))

    def test_date_window_welcome_and_size_checks(self):
        for age in (8, -1):
            self.assertIsNone(mail.issue(email(age=age).as_bytes(), CONFIG, NOW))
        message = email()
        message.replace_header("Subject", "Confirm your subscription")
        self.assertIsNone(mail.issue(message.as_bytes(), CONFIG, NOW))
        self.assertIsNone(mail.issue(b"x" * (mail.MAX_MESSAGE_BYTES + 1), CONFIG, NOW))

    def test_html_pixels_scripts_and_attachments_do_not_enter_text(self):
        message = email()
        message.set_content(
            "<h1>AI research</h1><p>Useful AI model analysis with documented limitations and deployment details.</p><script>PRIVATE_SCRIPT</script><img src='https://pixel.example/PRIVATE'><p hidden>PRIVATE_HIDDEN</p>",
            subtype="html",
        )
        message.add_attachment(
            b"PRIVATE_ATTACHMENT",
            maintype="application",
            subtype="octet-stream",
            filename="secret.bin",
        )
        result = mail.clean_body(message)
        self.assertIn("Useful AI model", result)
        self.assertNotIn("PRIVATE", result)

    def test_live_signup_shapes_do_not_become_news_evidence(self):
        for subject, intro in (
            ("\U0001f389 Welcome! 3 quick steps to get started", "Welcome to our AI newsletter."),
            ("We've got AI treats for you", "**Welcome humans. Thanks for joining our newsletter.**"),
            ("Confirm Signup", "Confirm your email to receive our newsletter."),
            ("Confirm your Publisher subscription", "Please confirm your subscription."),
            ("Your first message", "Thank you for subscribing to our newsletter."),
        ):
            with self.subTest(subject=subject):
                message = email()
                message.replace_header("Subject", subject)
                message.set_content(intro + "\n" + "A practical introduction to this subscription. " * 8)
                self.assertIsNone(mail.issue(message.as_bytes(), CONFIG, NOW))
        message = email()
        message.set_content("A company published research about welcome messages in AI products. " * 3)
        self.assertIsNotNone(mail.issue(message.as_bytes(), CONFIG, NOW))

    def test_invisible_preview_padding_does_not_hide_useful_evidence(self):
        message = email()
        message.set_content("\u034f\u00ad\u200b" * 3000 + "\n" + "Useful model research and limitations. " * 5)
        cleaned = mail.clean_body(message)
        self.assertTrue(cleaned.startswith("Useful model research"))
        self.assertNotIn("\u034f", cleaned)
        self.assertLess(len(cleaned), 300)

    def test_verified_publisher_senders_keep_identity_without_platform_wildcard(self):
        for sender, publisher in (
            ("dan@tldrnewsletter.com", "TLDR AI"),
            ("superhuman@mail.joinsuperhuman.ai", "Superhuman AI"),
            ("bensbites@substack.com", "Ben's Bites"),
        ):
            with self.subTest(sender=sender):
                result = mail.issue(email(sender).as_bytes(), CONFIG, NOW)
                self.assertEqual(result["publisher"], publisher)
                self.assertNotIn("mail.google.com", result["url"])
        self.assertIsNone(mail.issue(email("another@substack.com").as_bytes(), CONFIG, NOW))

    def test_sender_search_includes_verified_exact_catalog_addresses(self):
        fake = FakeMailbox()
        with (
            patch.dict("os.environ", {"NEWSLETTER_IMAP_ENABLED": "true"}),
            patch.object(mail.MailboxConfig, "load", return_value=CONFIG),
        ):
            mail.collect(NOW, factory=lambda *a, **kw: fake)
        searches = [call[-1] for call in fake.calls if call[0] == "search"]
        self.assertIn('"dan@tldrnewsletter.com"', searches)
        self.assertIn('"bensbites@substack.com"', searches)
        self.assertNotIn('"substack.com"', searches)

    def test_shared_platform_requires_exact_private_sender_approval(self):
        message = email("publisher@shared-platform.example")
        self.assertIsNone(mail.issue(message.as_bytes(), CONFIG, NOW))
        approved = mail.MailboxConfig(
            CONFIG.user, CONFIG.password, ("publisher@shared-platform.example",)
        )
        self.assertIsNotNone(mail.issue(message.as_bytes(), approved, NOW))
        self.assertNotIn(CONFIG.password, repr(CONFIG))
        self.assertNotIn(CONFIG.user, repr(CONFIG))

    def test_imap_uses_readonly_and_peek_and_only_sender_searches(self):
        fake = FakeMailbox()
        with (
            patch.dict("os.environ", {"NEWSLETTER_IMAP_ENABLED": "true"}),
            patch.object(mail.MailboxConfig, "load", return_value=CONFIG),
        ):
            result = mail.collect(NOW, factory=lambda *a, fake=fake, **kw: fake)
        self.assertEqual(result["status"], "available")
        self.assertEqual(fake.calls[0], ("select", "INBOX", True))
        for call in fake.calls:
            if call[0] == "search":
                self.assertIn("FROM", call)
                self.assertIn("SINCE", call)
            if call[0] == "fetch":
                self.assertIn("BODY.PEEK", call[-1])
        self.assertFalse(
            any(call[0] in {"store", "delete", "expunge", "append"} for call in fake.calls)
        )

    def test_unapproved_or_oversized_headers_stop_before_body_download(self):
        for fake in (
            FakeMailbox(email("attacker@example.com")),
            FakeMailbox(size=mail.MAX_MESSAGE_BYTES + 1),
        ):
            with (
                patch.dict("os.environ", {"NEWSLETTER_IMAP_ENABLED": "true"}),
                patch.object(mail.MailboxConfig, "load", return_value=CONFIG),
            ):
                result = mail.collect(NOW, factory=lambda *a, fake=fake, **kw: fake)
            self.assertEqual(result["status"], "no_approved_issues")
            self.assertFalse(
                any(call[0] == "fetch" and call[-1] == "(BODY.PEEK[])" for call in fake.calls)
            )

    def test_failure_is_sanitised_and_disabled_reader_does_not_connect(self):
        fake = FakeMailbox(fail=True)
        with (
            patch.dict("os.environ", {"NEWSLETTER_IMAP_ENABLED": "true"}),
            patch.object(mail.MailboxConfig, "load", return_value=CONFIG),
        ):
            result = mail.collect(NOW, factory=lambda *a, fake=fake, **kw: fake)
        self.assertEqual(result["failure_stage"], "authentication")
        self.assertNotIn("private-account", json.dumps(result))
        with patch.dict("os.environ", {"NEWSLETTER_IMAP_ENABLED": "false"}):
            result = mail.collect(NOW, factory=lambda *a, **kw: self.fail("Must not connect"))
        self.assertEqual(result["status"], "not_enabled")

    def test_mailbox_scan_caps_candidates_even_when_search_returns_many(self):
        class ManyMessages(FakeMailbox):
            def uid(self, operation, *args):
                if operation == "search":
                    return "OK", [b" ".join(str(i).encode() for i in range(1, 81))]
                return super().uid(operation, *args)

        fake = ManyMessages()
        with (
            patch.dict("os.environ", {"NEWSLETTER_IMAP_ENABLED": "true"}),
            patch.object(mail.MailboxConfig, "load", return_value=CONFIG),
        ):
            result = mail.collect(NOW, factory=lambda *a, **kw: fake)
        self.assertEqual(result["checked"], 30)
        self.assertTrue(result["capped"])
        self.assertEqual(
            sum(call[0] == "fetch" and call[-1] == "(BODY.PEEK[])" for call in fake.calls), 30
        )

    def test_elapsed_budget_stops_before_sender_or_body_queries(self):
        fake = FakeMailbox()
        with (
            patch.dict("os.environ", {"NEWSLETTER_IMAP_ENABLED": "true"}),
            patch.object(mail.MailboxConfig, "load", return_value=CONFIG),
            patch.object(mail.time, "monotonic", side_effect=[0, 46]),
        ):
            result = mail.collect(NOW, factory=lambda *a, **kw: fake)
        self.assertEqual(result["status"], "bounded_timeout")
        self.assertTrue(result["time_budget_reached"])
        self.assertFalse(any(call[0] in {"search", "fetch"} for call in fake.calls))
