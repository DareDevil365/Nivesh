# Independent Nivesh news bot

This deployable news-only project runs on GitHub-hosted runners with Gemini and personal Telegram delivery. Gmail remains an optional legacy adapter. Runtime requires no Codex, browser, Nivesh web server or powered-on laptop. Code/workflow creation alone does not activate hosting: merge deployment to the default branch, configure secrets and enable the schedule after a live delivery check. Hosting this bot is separate from hosting the full website.

## Architecture and flow

The collection/model pipeline below is shared. The Gmail-specific delivery steps describe the legacy adapter. The current Telegram transport, pairing and recovery behavior are documented under Telegram delivery below; Telegram does not require Gmail credentials.

1. GitHub Actions targets 00:30 UTC, equivalent to 06:00 IST. Manual runs default to a non-sending dry run. Pull requests run independent offline tests without secrets or mail.
2. Before collection, the CLI checks persistent delivery status and narrowly searches Gmail Sent for a deterministic per-date/per-recipient Message-ID. It never downloads unrelated mailbox bodies.
3. The shared collector gathers six finance searches plus two bot-only general-news searches, alongside ten publisher feeds: BBC Business/World, Guardian Business/World, FT International, Economic Times Markets/Economy/India, Mint Markets and Business Standard Markets. It filters the last 24 hours, merges exact headline duplicates, retains at most 360 records and attempts up to twelve accessible BBC/Guardian pages. The financial publishers are read through their public feeds; restricted articles are not represented as read. Unread articles, delays and source failures remain explicit. This is bounded discovery rather than exhaustive coverage.
4. Deterministic code filters stock tips and selects up to twelve candidates per topic using relevance, headline form, evidence access, publisher diversity and recency; article/feed evidence is capped at 1800 characters per candidate for Gemini. The model creates up to two bullets per category with structured output, exact quotations and existing source IDs. Two categories run concurrently. Each gets at most one repair, with bounded credential/quota fallback. Unsupported numbers, mismatched quotes, references outside the selected set, malformed output and obvious certainty/trading-direction patterns are rejected. These checks are not semantic certification. No delivery credential or private destination enters model input.
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

## Stock Daddy: company research course

`services/finance_teacher.py` provides the separate Stock Daddy research track: 47 lessons covering business research, accounting terms, valuation, strategies and stock pitches. It was originally labelled as the finance teacher; the user clarified that broad finance education should be separate. `finance_curriculum.json` is a reviewed snapshot of the existing Nivesh learning notes, independent of the frontend. Changes to web notes do not automatically update it. Examples are hypothetical, not company forecasts. Source links are further reading for original teaching prose.

Each research lesson has a separate `Stock Daddy · Day N` heading and content. It gives an example, research task, self-check and spoiler answer. A matching news link is a practice exercise, not evidence of company impact. This track uses no AI calls. It is separate from Finance Class below.

`NEWS_LEARNING_START_DATE` sets Day 1; the cloud variable defaults to the migration date. Topics advance by calendar day, even if a delivery is missed. After 47 days the course explicitly enters a review cycle; it does not claim endlessly new material. The bot does not grade replies, remember quiz performance or offer interactive personalised tutoring. Those are future features, not implemented behavior.

News and teaching use separate daily claims. If all four news editions are already accepted but the lesson/closing task is pending, the CLI sends only the remaining components without repeating source/model work or news. Failed/uncertain lessons keep their claim and do not replay accepted news. Dry runs authenticate/send neither. A single lesson body must fit the message limit; all 47 are covered by offline checks.

## Universal daily editions and message order

`daily_newsletters.py` sends four independently claimed editions in this order: World news & finance (world, US, policy, commodities and economically relevant world events), India news & finance, World general news, and India general news. Each starts with a separate heading message containing its name and the weekday/date. Complete content follows in numbered messages with clickable publisher citations. The separate learning heading/body follows, then one closing message suggests the reading order and a three-line evidence exercise. That closing task has its own claim and is withheld if any edition/lesson is incomplete.

The bot-only general-news categories do not change the website's six finance desks. Edition routing follows search/feed categories and is heuristic: country-specific feeds can include global context, and exact-title overlaps can appear in more than one edition. Counts are explicitly across all editions. Empty editions report a collection/summary gap rather than a quiet news day. There is no intraday breaking-news monitor or exhaustive forward-events calendar. The final message order now also includes the seven-day follow-up and three separate education/research messages described below.

Each edition includes its own heading within its durable multipart claim. Confirmed-part counts include headings; an uncertain heading/body keeps that edition pending. A failed send does not block attempts for other editions or the teacher, while retries skip accepted components. Rendering validates blocks/links before the first bundle send. If all news claims are accepted the CLI avoids recollection/model work entirely. The universal-v1 namespace permits one user-requested replacement of the earlier combined briefing on migration day.

## Finance Class: a broad beginner foundation

`finance_class.py` and `finance_foundations.json` define a separate 42-lesson foundation course in seven modules: money and everyday decisions; time, prices and risk; banking and payments; markets and institutions; accounting/reporting; financial instruments; and the economy, institutions and resilience. It starts with what finance is rather than how to choose a stock. Banking, budgets, interest/compounding, inflation, market infrastructure, listing, financial years/quarters, funds, bonds, derivatives, leverage, government finance and currency exposure are included. This is a beginner foundation, not a complete finance degree.

The author supplies the topic, learning notes, hypothetical example, question, answer, keywords and primary further-reading links. Gemini can elaborate in at most one bounded generation/repair task per lesson using only those notes. Its structured paragraphs must have real input IDs, matching quotations and supported numeric tokens. A complete authored lesson remains when AI is unavailable/rejected. Teaching preparation happens before news synthesis so educational elaboration is not dependent on spare quota after all news calls. No new API provider or runtime dependency is required.

A separate `Finance in context · News, history and what-if` message can use a current finance report with at least a substantive feed/article excerpt. Headlines alone never become detailed incident analyses. Gemini gets the selected report, the authored lesson and an explicitly labelled historical note where relevant, with a separate bounded generation/repair task. The supplied historical references distinguish the 2007–09 crisis from current news and the SEC's April 2022 account of alleged Archegos margin pressure in March 2021 from present incidents or a complete legal history. Similarity is not proof of the same cause. A missing/unavailable case falls back to a clearly hypothetical exercise; it does not invent a current crash or identify the user's anecdote.

Reported events, possible mechanisms, dated historical references and hypothetical counterfactuals have separate labels. Buy recommendations, call options and margin calls are explicitly distinguished. Quote/numeric checks cannot certify economic logic, causation or every factual interpretation; model passages still need critical reading. Definitions and notes cite primary further reading rather than claiming the authored prose is a verbatim publisher quotation.

Finance Class has its own `NEWS_FINANCE_START_DATE`, defaulting to the existing course start, and its own daily claim. Stock Daddy keeps `NEWS_LEARNING_START_DATE`. Both advance by calendar day and explicitly enter review cycles after their authored syllabus. Neither grades replies or offers interactive tutoring. Each has a separate heading and content; the context case has another claim. The technical limitations remain in saved data and this guide; Telegram now receives short formatted reading notes, not a long implementation paragraph.

## Seven-day follow-up, sent-story memory and retention

The normal editions scan the latest 24 hours. A second bounded collection queries seven-day search RSS and retains publication timestamps at least 24 and at most 168 hours old, with the same time/size/provider guards. Up to four unseen significant candidates are selected deterministically for a separate seven-day follow-up. It uses no extra AI call. Publication time is not necessarily event time, so source dates are preserved and the scan is not described as an exhaustive events calendar. The original source's current RSS depth can limit historical discovery.

`news_memory.py` stores hashes of normalised sent headlines and canonical public URLs plus dates. Only sources included in fully acknowledged news/follow-up messages are recorded, never every scraped or model-input story. Exact normalised syndicated headlines are suppressed across publishers; a changed headline at a previously linked URL can be an update and receives an update label. This is fingerprint deduplication, not semantic understanding of all multi-day events. Different wording can still repeat a story, and cross-edition overlap is possible.

Accepted delivery claims include non-sensitive story fingerprints so a failure to update history can be reconciled without replaying messages. Partial/ambiguous claims remain pending and are not blindly resent. History writes are skipped if reconciliation changes nothing. Active history keeps fourteen calendar days, pruning older entries on subsequent runs. Exact dated local input/digest/summary/email artifacts are also pruned after that period; company dossiers, unknown files, symlinks and delivery claims are untouched. Hosted report files are ephemeral. The state branch retains delivery audit claims and old Git revisions containing non-sensitive hashes; this is active-memory/report expiry, not a promise of physical Git-history erasure.

Final order: four daily news editions; seven-day follow-up; Finance Class; Finance in context; Stock Daddy; one closing learning/research task. Each component has its own persistent claim. The universal-v2 namespace permits one revised-format migration-day preview. The CLI's fast path requires all daily news and follow-up claims, then reconciles history and skips already accepted education/closing components without repeat source/model work. Future scheduled starts still depend on GitHub/provider availability and may be delayed.
