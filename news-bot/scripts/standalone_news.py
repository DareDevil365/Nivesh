"""Run the cloud-capable news bot without Codex or the Nivesh web servers."""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import news_bot, news_digest  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="Prepare files, never authenticate to mail or send"
    )
    parser.add_argument(
        "--input", type=Path, help="Use a retained source pack for an offline/smoke run"
    )
    parser.add_argument(
        "--no-ai", action="store_true", help="Explicitly labelled headline fallback only"
    )
    parser.add_argument(
        "--check-mail",
        action="store_true",
        help="Authenticate and inspect only the bot's dated Sent ID; never send",
    )
    args = parser.parse_args()
    try:
        config = None if args.dry_run else news_bot.MailConfig.load()
        if args.check_mail:
            if config is None:
                parser.error("--check-mail and --dry-run cannot be combined")
            exists = news_bot.sent_message_exists(
                config, config.message_id(news_digest.local_day())
            )
            print(json.dumps({"mail_authentication": "ok", "today_in_sent": exists}))
            return
        ledger = None
        if config:
            ledger = (
                news_bot.GitHubLedger(
                    os.getenv("GITHUB_REPOSITORY", ""), os.getenv("GITHUB_TOKEN", "")
                )
                if os.getenv("GITHUB_ACTIONS") == "true"
                else news_bot.LocalLedger()
            )
            prior = news_bot.existing_delivery(news_digest.local_day(), config, ledger)
            if prior:
                print(json.dumps({"status": prior, "date_ist": news_digest.local_day()}))
                return
        pack = (
            json.loads(args.input.read_text(encoding="utf-8"))
            if args.input
            else news_digest.collect()
        )
        if not args.dry_run and pack["date_ist"] != news_digest.local_day():
            raise news_bot.BotError("Refusing to email an old pack as today's brief.")
        digest = news_bot.summarise(pack, use_ai=not args.no_ai)
        folder = news_digest.DIGEST_DIR
        news_digest.atomic_json(folder / f"{pack['date_ist']}-input.json", pack)
        news_digest.atomic_json(folder / f"{pack['date_ist']}-digest.json", digest)
        (folder / f"{pack['date_ist']}-email.txt").write_text(
            news_digest.email_text(digest), encoding="utf-8"
        )
        if args.dry_run:
            status = "prepared_without_mail"
        else:
            status = news_bot.deliver(digest, config, ledger)
        print(
            json.dumps(
                {
                    "status": status,
                    "date_ist": digest["date_ist"],
                    "summary_status": digest["summary_status"],
                    "summary_modes": digest["summary_modes"],
                    "coverage": digest["coverage"],
                }
            )
        )
    except news_bot.BotError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
