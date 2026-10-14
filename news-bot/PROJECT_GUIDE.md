# Independent Nivesh news bot

This deployable news-only project runs on GitHub-hosted runners with Gemini and personal Telegram delivery. Gmail remains an optional legacy adapter. Runtime requires no Codex, browser, Nivesh web server or powered-on laptop. Code/workflow creation alone does not activate hosting: merge deployment to the default branch, configure secrets and enable the schedule after a live delivery check. Hosting this bot is separate from hosting the full website.

## Architecture and flow

The collection/model pipeline below is shared. The Gmail-specific delivery steps describe the legacy adapter. The current Telegram transport, pairing and recovery behavior are documented under Telegram delivery below; Telegram does not require Gmail credentials.

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

The bundle includes `config.py`, `services/`, `scripts/standalone_news.py`, `scripts/setup_telegram.py`, `tests/`, `requirements.txt`, a blank environment example and this guide. Run `python -m unittest discover -s tests` from the bundle to test it without the web application. The root `.github/workflows/daily-news.yml` runs those tests on Linux/Python 3.12.

## Setup and commands

For legacy email delivery only, configure these GitHub Actions repository secrets. Telegram configuration is below:

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

The old Codex heartbeat is paused. Keep it paused to avoid duplicate schedulers. Disabling it alone is not cloud activation. Actual validation and deployment status are recorded in the parent project guide and validation log.

## Telegram delivery (current default)

`NEWS_DELIVERY=telegram` selects the Telegram adapter; `email` explicitly selects the legacy Gmail adapter. The standalone CLI checks the daily ledger before collecting/model work, then verifies the bot identity and exact paired private chat. A dry run does not contact either delivery service. No Telegram token, chat ID or other delivery credentials enter model input or reports. No always-running bot process, webhook server or Telegram SDK is needed: the existing small Python/httpx runtime uses verified HTTPS.

The complete report is sent directly as numbered `sendMessage` messages using Telegram HTML formatting. Source titles are explicit clickable links; category headings, full summaries/reasons, original source URLs, publication/access labels, all finance terms and coverage limitations remain in the messages. All content and URL attributes are HTML-escaped. Complete blocks are packed to a conservative 3500 raw UTF-16 units, leaving room for the numbered header below the 4096 message limit. Links/entities/Unicode are never cut; oversized individual blocks fail before sending rather than losing text. Link previews are disabled for reading comfort. The earlier text attachment was replaced at the user's request after a real cloud test. The bot does not currently answer chat questions or process research commands.

Before sending, the exclusive ledger stores an opaque per-day/per-bot/per-chat ID, report hash, total parts and pending status. Each positive message ID and exact private-chat receipt advances the confirmed-part count using optimistic state updates. Only the final part marks the briefing accepted. Messages are paced slightly over one second apart. Acceptance does not prove notifications, readership or semantic accuracy. The public ledger never stores raw chat IDs, bot tokens, message bodies or pairing codes. Tokens/chat IDs are excluded from logs, reports and model input. HTTP errors omit token-bearing URLs/provider bodies and are not automatically retried.

Telegram has no general bot Sent-history lookup or idempotency key. If any send times out after acceptance, or recording a part fails, the pending claim remains and subsequent runs stop for that day/destination. A partial briefing can therefore arrive; the header shows its expected total and the ledger records confirmed progress. Inspect the private chat and claim before a deliberate retry; claims are never automatically removed and accepted parts are never blindly replayed. New days have separate claims. This favours avoiding duplicates over automatic recovery and is not a distributed exactly-once guarantee. Token rotation preserves the destination ID. The messages-v2 delivery namespace deliberately permits a one-time replacement of the earlier document-format briefing on the migration day; subsequent runs skip it normally.

### Private setup

1. In the official [BotFather](https://t.me/BotFather), send `/newbot` and follow its name/username prompts.
2. Put its token in `NEWS_TELEGRAM_BOT_TOKEN` in private `backend/.env`; set `NEWS_DELIVERY=telegram`. Never paste tokens into chat or commit them.
3. Run `python backend/scripts/setup_telegram.py --link`. Open the generated private Start link and press Start.
4. Run `python backend/scripts/setup_telegram.py --bind` within thirty minutes of pressing Start. Only a recent private human message containing the random code can bind. The helper rejects ambiguous recipients, saves `NEWS_TELEGRAM_CHAT_ID` privately and clears the code. It does not send a message or print the chat ID. A new dedicated bot avoids conflicts with webhook/update consumers. A plain unrelated `/start` does not pair.
5. Set GitHub Actions secrets `GEMINI_API_KEYS`, optional `GEMINI_KEY_PROJECTS`, `NEWS_TELEGRAM_BOT_TOKEN` and `NEWS_TELEGRAM_CHAT_ID`; set repository variable `NEWS_DELIVERY=telegram`. Local environment changes do not automatically update cloud secrets. The deployment helper encrypts them with the repository public key and disables the schedule during configuration.
6. Run a manual hosted send, inspect its result and the private Telegram chat, then enable `NEWS_BOT_ENABLED=true`. The schedule remains 00:30 UTC / 06:00 IST, subject to GitHub delays and account/platform limits described above.

Pairing reads message updates needed to match the one-time code without printing update bodies or automatically choosing the first/recent person. It does not acknowledge unrelated updates. No background update consumer runs after pairing. Repeat the private-link/Start flow if pairing expires. [Telegram Bot API](https://core.telegram.org/bots/api), [BotFather setup](https://core.telegram.org/bots/features#botfather).

The root project guide and validation log record deployment and actual live-test status. Code presence alone is not schedule activation.
