"""Hash the explicitly publishable Daily Brief project; private config stays local."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "config.py",
    "requirements.txt",
    "requirements-deploy.txt",
    "pyproject.toml",
    ".gitignore",
    ".env.example",
    "PROJECT_GUIDE.md",
    "README.md",
    "NEWSLETTER_SOURCES.md",
    "newsletter_sources.json",
    "services/__init__.py",
    "tests/__init__.py",
    "services/news_reader.py",
    "services/news_digest.py",
    "services/news_bot.py",
    "services/telegram_delivery.py",
    "services/finance_teacher.py",
    "services/finance_class.py",
    "services/finance_foundations.json",
    "services/finance_lesson_depth.json",
    "services/finance_textbook.py",
    "services/finance_textbook.json",
    "services/news_memory.py",
    "services/daily_newsletters.py",
    "services/finance_curriculum.json",
    "services/gemini_client.py",
    "services/cache_manager.py",
    "services/filing_sources.py",
    "services/local_store.py",
    "services/ai_newsletter.py",
    "services/story_research.py",
    "services/brief_format.py",
    "services/detailed_report.py",
    "services/delivery_time.py",
    "services/newsletter_mail.py",
    "scripts/standalone_news.py",
    "scripts/setup_telegram.py",
    "scripts/setup_newsletters.py",
    "scripts/setup_scheduler.py",
    "scripts/build_manifest.py",
    "scripts/deploy.py",
    "tests/test_news_bot.py",
    "tests/test_telegram_delivery.py",
    "tests/test_finance_teacher.py",
    "tests/test_daily_newsletters.py",
    "tests/test_finance_class.py",
    "tests/test_news_memory.py",
    "tests/test_ai_newsletter.py",
    "tests/test_story_research.py",
    "tests/test_brief_delivery.py",
    "tests/test_newsletter_mail.py",
)


def build():
    manifest = {
        name: {"sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest()} for name in FILES
    }
    (ROOT / "bundle_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"publishable_files": len(manifest), "private_config_excluded": True}))


if __name__ == "__main__":
    build()
