# Independent Nivesh news bot

This deployable news-only project runs on GitHub-hosted runners with Gemini and Gmail SMTP/IMAP. Runtime requires no Codex, browser, Nivesh web server or powered-on laptop. Code/workflow creation alone does not activate hosting: merge deployment to the default branch, configure secrets and enable the schedule after a live delivery check.

## Architecture and flow

1. GitHub Actions targets 00:30 UTC, equivalent to 06:00 IST. Manual runs default to a non-sending dry run. Pull requests run independent offline tests without secrets or mail.
2. Before collection, the CLI checks persistent delivery status and narrowly searches Gmail Sent for a deterministic per-date/per-recipient Message-ID. It never downloads unrelated mailbox bodies.
3. The shared collector gathers the six reading-desk searches plus BBC/Guardian publisher feeds. It filters the last 24 hours, merges exact headline duplicates and attempts up to twelve readable publisher pages. All retained headlines and bounded article/feed excerpts are supplied by category. Unread articles, delays and source failures remain explicit. This is not exhaustive coverage or a full-article archive.
4. Gemini creates up to two bullets per category using structured output, short exact quotations and existing source IDs. Two categories run concurrently. Each category gets at most one repair; the existing rotator bounds credential/quota fallback. One model-access 404 may trigger an alternate call. Unsupported numbers, mismatched quotes and wrong references fail validation. No mail password, destination, GitHub token or private portfolio enters model input.
5. Failed/unavailable AI sections become explicitly labelled reported-headline fallbacks. Empty packs fail instead of inventing a quiet-market summary. Conditional explanations, sources, dates, access labels, coverage, terms and limitations remain in the email. Quote/number checks do not certify semantic support or financial interpretation; this path has no live human review.
6. Immediately before SMTP, an exclusive claim is committed on the dedicated `news-bot-state` branch using the repository-scoped workflow token. Only hashed destination keys, deterministic IDs and status timestamps are stored, never addresses, passwords, keys or message bodies. Existing claims cannot be silently overwritten; updates use the previous blob SHA.
7. Gmail mail is UTF-8 plain text, with explicit authenticated From and one configured recipient, over verified TLS. SMTP acceptance is recorded separately from inbox receipt. A later run checks Sent before handling an ambiguous attempt; pending records without confirmed acceptance require deliberate review rather than blind retries.

Python/httpx/BeautifulSoup/Pydantic and existing source/rotation helpers were retained. SMTP, IMAP, MIME and hashing use the standard library. The small requirements file avoids pandas, yfinance and frontend installation. Gemini uses existing credentials, while deterministic code performs collection, provenance checks and delivery control. Provider quotas/pricing and GitHub account limits still apply. No Codex runtime is used.

## Source of truth and bundle

Canonical implementation lives in the parent project's backend. Run `python backend/scripts/export_news_bot.py` to regenerate this self-contained `news-bot/` distribution and hash manifest. Do not hand-edit generated implementation copies. An explicit export allowlist excludes `.env`, private data, other project changes and unrelated features. Publishing this folder does not publish all local Nivesh work.

The bundle includes `config.py`, `services/`, `scripts/standalone_news.py`, `tests/`, `requirements.txt`, a blank environment example and this guide. Run `python -m unittest discover -s tests` from the bundle to test it without the web application. The root `.github/workflows/daily-news.yml` runs those tests on Linux/Python 3.12.

## Setup and commands

Configure these GitHub Actions repository secrets:

- `GEMINI_API_KEYS`: existing comma-separated credentials.
- `GEMINI_KEY_PROJECTS`: matching project labels, or blank for a conservative shared quota group.
- `NEWS_SMTP_USER`: sending Gmail account.
- `NEWS_SMTP_PASSWORD`: a Gmail app password, never the normal Google password.
- `NEWS_EMAIL_TO`: one receiving address.

Set repository variable `NEWS_BOT_ENABLED=true` after a successful hosted send and recipient check. `GEMINI_MODEL` is optional, defaulting to `gemini-2.5-flash`. Local `.env` values are independent of encrypted cloud secrets and are never committed. A Codex Gmail connection does not provide standalone SMTP credentials.

App passwords require an eligible Google account with two-step verification; some managed/protected accounts do not offer them. Create one at <https://myaccount.google.com/apppasswords> and keep it privately in the local environment or repository secret, never chat. [Google guidance](https://support.google.com/mail/answer/185833).

Local commands from the parent project, without a browser/server:

```powershell
python backend/scripts/standalone_news.py --dry-run
python backend/scripts/standalone_news.py --dry-run --no-ai
python backend/scripts/standalone_news.py --check-mail
python backend/scripts/standalone_news.py
```

The last command sends only after configuration, Sent verification and a new claim. `--input` supports a retained pack for a smoke run; actual sends reject old pack dates. `--dry-run` never authenticates to mail or sends. Hosted report files are ephemeral; the email and state persist. Cloud briefs do not automatically synchronise to a local installation's news page.

## Availability, recovery and tradeoffs

GitHub schedules can be delayed/dropped during load and must exist on the default branch. Public-repository schedules can be disabled after sixty days without activity. State commits record real delivery activity, but platform status/notifications still need checking when mail stops. Runner/provider/account limits remain external. This is a personal best-effort morning schedule, not guaranteed exact arrival. [GitHub schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

Workflow concurrency and optimistic persistent claims reduce duplicates. If SMTP accepts but status recording fails, a later run checks the stable Message-ID in Gmail Sent. If acceptance versus failure cannot be established, the job retains its pending record and fails clearly. Investigate Sent/bounces and state before a deliberate retry; never delete claims automatically. State records are public metadata when the repository is public; they intentionally omit plain addresses, credentials and content. No external mail action occurs in tests.

Keep the old Codex heartbeat only during migration. Disable it once independent delivery is verified to avoid duplicate schedulers. Disabling it alone is not cloud activation. Actual validation and deployment status are recorded in the parent project guide and validation log.
