"""Run the cloud-capable news bot without Codex or the Nivesh web servers."""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import (  # noqa: E402
    ai_newsletter,
    daily_newsletters,
    finance_class,
    news_bot,
    news_digest,
    news_memory,
    story_research,
    telegram_delivery,  # noqa: E402
)


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
        channel = os.getenv("NEWS_DELIVERY", "email").strip().lower()
        if channel not in ("email", "telegram"):
            raise news_bot.BotError("NEWS_DELIVERY must be email or telegram.")
        transport = daily_newsletters if channel == "telegram" else news_bot
        config = None
        if not args.dry_run:
            config = (
                telegram_delivery.TelegramConfig.load()
                if channel == "telegram"
                else news_bot.MailConfig.load()
            )
        if args.check_mail:
            if channel != "email":
                parser.error("--check-mail applies only to email delivery")
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
            prior = transport.existing_delivery(news_digest.local_day(), config, ledger)
            if prior:
                bundle = None
                if channel == "telegram":
                    telegram_delivery.check(config)
                    bundle = daily_newsletters.deliver(
                        None,
                        config,
                        ledger,
                        day=news_digest.local_day(),
                        include_ai=ai_newsletter.enabled(),
                        ai_use_ai=not args.no_ai,
                        ai_offline=bool(args.input),
                    )
                print(
                    json.dumps(
                        {
                            "status": prior,
                            "date_ist": news_digest.local_day(),
                            "bundle": bundle,
                        }
                    )
                )
                if bundle and bundle["status"] != "telegram_accepted":
                    raise news_bot.BotError(
                        "Some newsletter deliveries are incomplete; inspect their pending claims before retrying."
                    )
                return
            if channel == "telegram":
                telegram_delivery.check(config)
        pack = (
            json.loads(args.input.read_text(encoding="utf-8"))
            if args.input
            else news_digest.collect()
        )
        if not args.dry_run and pack["date_ist"] != news_digest.local_day():
            raise news_bot.BotError("Refusing to email an old pack as today's brief.")
        teaching, weekly_pack = None, None
        if channel == "telegram":
            teaching = finance_class.prepare(pack["date_ist"], pack, use_ai=not args.no_ai)
            history = (
                news_memory.load(ledger, news_memory.history_key(config), pack["date_ist"])
                if config
                else {"version": 1, "entries": {}}
            )
            pack = news_memory.filter_pack(pack, history)
            if not args.input and story_research.enabled():
                pack = story_research.enrich_pack(pack)
            # --input smoke runs are offline: weekly retrieval is explicit only for live collection.
            if not args.input:
                weekly_pack = news_digest.collect(
                    window_hours=168, older_than_hours=24, read_articles=False
                )
        digest = (
            news_bot.summarise(pack, use_ai=not args.no_ai)
            if pack["items"]
            else news_memory.empty_digest(pack)
        )
        if teaching:
            digest["finance_teaching"] = teaching
        folder = news_digest.DIGEST_DIR
        news_memory.cleanup_local(folder, pack["date_ist"])
        news_digest.atomic_json(folder / f"{pack['date_ist']}-input.json", pack)
        if weekly_pack:
            news_digest.atomic_json(folder / f"{pack['date_ist']}-weekly-input.json", weekly_pack)
        news_digest.atomic_json(folder / f"{pack['date_ist']}-digest.json", digest)
        (folder / f"{pack['date_ist']}-email.txt").write_text(
            news_digest.email_text(digest), encoding="utf-8"
        )
        if args.dry_run:
            status = "prepared_without_mail"
        else:
            result = (
                daily_newsletters.deliver(
                    digest,
                    config,
                    ledger,
                    weekly_pack=weekly_pack,
                    include_ai=ai_newsletter.enabled(),
                    ai_use_ai=not args.no_ai,
                    ai_offline=bool(args.input),
                )
                if channel == "telegram"
                else transport.deliver(digest, config, ledger)
            )
            status = result["status"] if channel == "telegram" else result
        print(
            json.dumps(
                {
                    "status": status,
                    "delivery": channel,
                    "editions": result["editions"]
                    if channel == "telegram" and not args.dry_run
                    else None,
                    "date_ist": digest["date_ist"],
                    "summary_status": digest["summary_status"],
                    "summary_modes": digest["summary_modes"],
                    "coverage": digest["coverage"],
                    "weekly_coverage": weekly_pack["coverage"] if weekly_pack else None,
                    "teaching_modes": {
                        "finance_class": "quote_checked_ai"
                        if teaching["explanation"]
                        else "curated_lesson",
                        "context": "quote_checked_ai" if teaching["case"] else "curated_exercise",
                    }
                    if teaching
                    else None,
                }
            )
        )
        if status == "partial_delivery":
            raise news_bot.BotError(
                "Some newsletter deliveries are incomplete; inspect their pending claims before retrying."
            )
    except news_bot.BotError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
