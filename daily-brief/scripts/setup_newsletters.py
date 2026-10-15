"""Check approved newsletter intake or explicitly add one shared-platform sender."""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import dotenv_values, set_key  # noqa: E402

import config  # noqa: E402,F401
from services import newsletter_mail  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument(
        "--approve-sender", help="An exact publisher From address; never a whole shared domain"
    )
    args = parser.parse_args()
    if args.approve_sender:
        address = args.approve_sender.lower().strip()
        if not re.fullmatch(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", address):
            parser.error("Use one exact sender email address")
        path = Path(__file__).resolve().parents[1] / ".env"
        current = dotenv_values(path).get("NEWSLETTER_ALLOWED_SENDERS", "") or ""
        senders = set(filter(None, current.split(","))) | {address}
        set_key(str(path), "NEWSLETTER_ALLOWED_SENDERS", ",".join(sorted(senders)))
        print(
            json.dumps(
                {
                    "sender_added": True,
                    "next_step": "Update hosted secrets using scripts/deploy.py configure",
                }
            )
        )
    else:
        result = newsletter_mail.collect()
        print(
            json.dumps(
                {
                    **{key: value for key, value in result.items() if key != "items"},
                    "approved_issues": len(result["items"]),
                }
            )
        )


if __name__ == "__main__":
    main()
