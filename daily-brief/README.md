# Daily Brief

A standalone personal Telegram briefing: world/Indian finance and general news, a seven-day follow-up, textbook Finance Class, Finance in context, Stock Daddy, and a separate **AI newsletter**. Hosted scheduling runs at 06:00 IST without a local computer or Codex.

Start with [the project guide](PROJECT_GUIDE.md) and [the free AI newsletter subscription list](NEWSLETTER_SOURCES.md).

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests
python scripts/setup_newsletters.py --check
python scripts/standalone_news.py --dry-run --no-ai
```

Private configuration lives in this folder's `.env`. For Gmail newsletter intake, use `NEWSLETTER_IMAP_USER` and `NEWSLETTER_IMAP_PASSWORD` (a Gmail app password). `NEWSLETTER_IMAP_ENABLED=true` enables the reader. Never put credentials in chat or version control. `NEWSLETTER_ALLOWED_SENDERS` optionally lists exact sender addresses for approved newsletters using shared sending platforms.

The AI edition also researches public OpenAI, Google, Hugging Face, Microsoft and arXiv sources. It keeps dates, evidence-access labels and clickable citations; company announcements, newsletter commentary and preprints are distinct. Mail or Gemini failures leave a labelled public/source-led edition.

After local setup changes, cloud secrets need updating separately:

```powershell
python -m pip install -r requirements-deploy.txt
python scripts/build_manifest.py
python scripts/deploy.py configure
```

Configuration deliberately gates scheduled sending until verification. See the guide for the full publish/check/merge/send/enable procedure. This project is locally separate from Nivesh; its reviewed runtime is published under `daily-brief/` in the existing hosting repository, retaining the previous state branch and duplicate protection.

Targeted follow-up now selects up to one story per world/India finance/general-news edition and up to two in the AI edition. It looks for relevant official pages, labels access/date gaps, and adds open questions and next evidence to watch. Existing Gemini summary calls receive the added excerpts; no separate research-model call is added. NEWS_RESEARCH_ENABLED=false disables the extra network research.

Telegram can use NEWS_BRIEF_MODE=short for roughly five minutes of news while retaining full Finance Class chapters. NEWS_DETAIL_EMAIL_ENABLED=true sends the detailed HTML news/research report to NEWS_DETAIL_EMAIL_TO with its own no-repeat claim. Report SMTP defaults to the newsletter Gmail account; optional report-specific overrides are supported.

For an external morning trigger, add private cron-job.org and repository-limited Actions keys, then run python scripts/setup_scheduler.py plan and python scripts/setup_scheduler.py configure. The prepared jobs collect from 05:40 IST, hold delivery until 06:00, and check again at 06:05. Until configured, GitHub cron remains the active scheduler and may be delayed. See the guide for timing evidence, setup and reliability limits.
