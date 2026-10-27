"""CLI for the scheduled assistant. Email is sent through its Gmail connector."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import news_digest  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("collect", "finalize", "claim", "mark-sent", "status"))
    parser.add_argument("--date", default=news_digest.local_day())
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--message-id")
    parser.add_argument("--no-articles", action="store_true")
    args = parser.parse_args()
    from datetime import date

    date.fromisoformat(args.date)
    folder = news_digest.DIGEST_DIR
    pack_path = folder / f"{args.date}-input.json"
    digest_path = folder / f"{args.date}-digest.json"
    sent_path = folder / f"{args.date}-sent.json"
    if args.action == "status":
        print(
            json.dumps(
                {
                    "date_ist": args.date,
                    "sent": sent_path.exists(),
                    "sending": (folder / f"{args.date}-sending.json").exists(),
                    "prepared": digest_path.exists(),
                    "pack": str(pack_path),
                }
            )
        )
    elif args.action == "collect":
        if args.date != news_digest.local_day():
            parser.error("Collection is only supported for today's actual news window.")
        pack = news_digest.collect(read_articles=not args.no_articles)
        news_digest.atomic_json(pack_path, pack)
        print(json.dumps({"pack": str(pack_path), "coverage": pack["coverage"]}))
    elif args.action == "finalize":
        if not args.summary:
            parser.error("--summary is required")
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        digest = news_digest.validate_summary(
            pack, json.loads(args.summary.read_text(encoding="utf-8"))
        )
        rendered = news_digest.email_html(digest)
        plain_text = news_digest.email_text(digest)
        news_digest.atomic_json(digest_path, digest)
        html_path = folder / f"{args.date}-email.html"
        html_path.write_text(rendered, encoding="utf-8")
        text_path = folder / f"{args.date}-email.txt"
        text_path.write_text(plain_text, encoding="utf-8")
        print(
            json.dumps(
                {
                    "digest": str(digest_path),
                    "email_html": str(html_path),
                    "email_text": str(text_path),
                    "delivery_mime_type": "text/plain",
                    "subject": digest["subject"],
                }
            )
        )
    elif args.action == "claim":
        if sent_path.exists() or not digest_path.exists():
            parser.error("Already sent, or no prepared digest exists.")
        news_digest.claim_delivery(args.date)
        print(json.dumps({"delivery_claimed": True}))
    else:
        if not args.message_id or len(args.message_id) > 150 or not digest_path.exists():
            parser.error("A prepared digest and confirmed Gmail --message-id are required.")
        if sent_path.exists():
            parser.error("Delivery is already recorded; do not send again.")
        news_digest.atomic_json(sent_path, {"message_id": args.message_id, "date_ist": args.date})
        print(json.dumps({"delivery_recorded": True}))


if __name__ == "__main__":
    main()
