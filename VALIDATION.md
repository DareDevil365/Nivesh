# Validation record

Validation performed locally on 13 October 2026. This record distinguishes deterministic correctness checks from changing provider data. Architecture, numerical contracts and remaining integrations are in [PROJECT_GUIDE.md](PROJECT_GUIDE.md).

## Automated checks

- `python backend/test_backend.py`: 138 offline regression tests. Tests use temporary SQLite databases and controlled data; they do not depend on market availability or AI credentials.
- `uvx ruff check backend`: passed using the repository's Ruff configuration.
- `uvx ruff format --check backend`: passed.
- `npm run typecheck --prefix frontend`: passed.
- `npm run build --prefix frontend`: production compilation, TypeScript checking and static route generation passed.
- `git diff --check`: no whitespace errors. Windows line-ending conversion notices are unrelated to test failures.

The suite checks known financial-model answers, unavailable inputs, fiscal date alignment, EPS/share units, real three-year CAGR, provider-only exchange resolution, indicator periods/defaults/warm-up, crossing events, next-open fills, cost and slippage effects, stop gaps/ambiguous bars, terminal liquidation, unaffordable positions, known demerger exclusions, CSV quoting/FIFO/partial fills/invalid rows, dated trade heuristics, signed-cookie isolation, private feedback, persistent watchlists and owner-protected condition deletion. This is not a numerical audit, complete code-coverage claim or certification of investment models.

## Live provider checks

- Company, chart, annual financials, quarterly results, ratios, forensic, valuation, technicals, business description, ownership, relationship and research-note endpoints returned valid responses for a covered company through the frontend proxy.
- Ownership returns an explained unavailable state. Supply-chain relationships now come from documents collected for the requested issuer; runtime code no longer loads the original company maps. The illustrative sector view remains separately labelled.
- An initial full snapshot covered 59 of 61 bundled symbols and exposed two failed fetches. Investigation found obsolete LTIM and TATAMOTORS symbols. Exchange-verified alias repairs restored the final snapshot to **61 of 61**, with zero failed fetches in that refresh. This is the bundled universe, not the entire NSE market.
- Old-symbol lookups resolved to LTM and TMPV and returned usable quotes. TMPV displays the demerger caveat, suppresses misleading cross-break growth comparisons, and rejects unsupported backtest ranges spanning the transition.
- A live TCS MACD backtest over 2023–2025 returned 31 closed trades and actual available dates. This checks execution/integration, not the attractiveness of the strategy.
- The default browser RSI backtest returned an equity curve, trade log, cost breakdown and execution assumptions.

Live prices, results and provider availability can change. HTTP 200 by itself is not treated as evidence of financial correctness.

## Browser workflows

Checked using the Playwright CLI skill against the local production build:

- Open company research; render the candlestick/volume chart and source timestamps.
- Open financial statements and verify EPS is shown in rupees per share.
- Open valuation scenarios with reported annual FCF per share and disclosed assumptions.
- Add a company to the watchlist; revisit the watchlist; retain it across server restarts.
- Save a price condition and display the observed value and condition-met status.
- Parse the explicitly labelled trade demo, review closed observations, and calculate descriptive statistics with supplied costs.
- Run a backtest through the visible builder and display dated results and trade logs.
- Apply a maximum-P/E screen, paginate covered results and download the CSV with units/source dates.
- Write research notes and download the Markdown export.
- Save feedback and read the current workspace's report history; dismiss the native dialog with Escape.
- Inspect a 390-pixel mobile screener viewport; document width remained within the viewport. Tables have their own horizontal scrolling containers.
- Inspect desktop research rendering. After the favicon fix, the checked production page reload reported zero console errors and warnings.

The feature-restoration follow-up also checked the dedicated Supply chain and AI deep dive tabs, TCS's sourced graph, selecting BSNL and inspecting its date/source/scope note, the original research-lead view, node filtering, and a real CSV download with evidence/source columns. RSI and Bollinger controls were enabled together without console errors. The supply-chain layout stayed within a 390-pixel mobile viewport. The AI tab rendered all twelve sections and explicit missing-key setup guidance; the live POST returned 503 without a key and rejected an excerpt without its source URL with 422. Provider-success, quote mismatch, unknown evidence IDs, incomplete output and excerpt-cache privacy paths were checked with mocked AI responses. Live Gemini generation was **not** verified because this server has no configured key.

Screenshots and snapshots are local ignored artifacts under `output/playwright/`; browser downloads and CLI session artifacts are ignored as well. The browser verification does not claim a complete accessibility audit or coverage of every viewport and provider failure.

## Operational limits

The GitHub check workflow is configured but has not been run on a hosted runner in this session. No deployment, commit, push, brokerage connection or order execution was performed. Local backend and frontend services were started for review.

Verified exchange ownership histories, comprehensive filing/transcript/news discovery, complete maintained supplier networks, comprehensive corporate actions, full historical NSE universes, account recovery/sync, background notifications and public publishing remain external integrations or future work. The graph uses partially extracted issuer reports. PIB/RBI feed leads and allowlisted official HTML context are implemented; broad global news search, OCR and arbitrary PDF table normalization are not. Hosted durability requires a persistent data directory and stable signing secret.

## Issuer-independent research workflow

The live collector was run for Rentomojo, which is outside the bundled screener universe, and TCS through the same symbol-driven NSE annual-report, IPO-document and announcement adapters. No issuer-specific source URLs or answers are embedded in the runtime collector.

- Rentomojo's 436-page prospectus was discovered inside NSE's ZIP archive; a 44-page investor presentation was also read. The original manufacturing/supply paragraph on physical PDF page 242 was rendered with Poppler and visually inspected. A separate results attachment failed the issuer-identity check and is exposed as a collection error.
- TCS's 361-page 2025–2026 annual report was discovered from the live annual-report feed. Explicit partner extraction was checked and refined after real-data inspection caught truncated names and a self-reference. A low-information meeting document produced an explicit extraction gap.
- The collector CLI exported source/evidence JSON packs, first using local services and then reusing the running backend. Persisted collections survive backend restarts. Automated tests cover PDF and ZIP extraction, archive-path safety, source identity, unrecognised documents, supplier/brand/customer/partner distinctions, source discovery for an unknown symbol, DNS/redirect/download bounds, persistence, interruptions and AI source/role checks.
- Browser checks verified the live graph, node quotes/pages, navigation into Research workflow, evidence categories and original source links, source coverage/errors, hypothesis input and JSON export. The export included scenario assumptions and hypothesis text.
- A browser scenario with explicitly entered test assumptions (revenue ₹100 Cr, net profit ₹10 Cr, 100 million shares and price ₹20) returned the expected ₹11.40/₹21/₹34.50 bear/base/bull scenario prices. These are QA inputs, not forecasts for Rentomojo. Missing baseline values remain visible and edits are marked as user assumptions.
- The Research workflow remained within a 390-pixel viewport and checked browser console output had zero errors/warnings. Source collection and scenario arithmetic work without an AI key. Live AI generation remains unverified because the server has no configured Gemini key; mocked responses verify that collected evidence and financial-source contracts are validated.
- The reusable `.agents/skills/equity-research` skill passed its creator's validation. Its CLI and analyst/source references are present and linked. The skill supports a Codex-assisted investigation; it does not turn the background collector into an autonomous general-web research agent.

The structured NSE annual-results endpoint was also investigated for financial fallback: it returned no annual rows for Rentomojo in that check, and a quote endpoint did not return usable JSON. Neither was used to invent a missing share count. The existing provider financial adapter remains the structured-number source, with explicit user overrides available in the learning scenario model.

## Adversarial audit and official-context follow-up

The latest checks supersede the earlier collection snapshots above. No Gemini key was configured. AI tests used controlled responses; they do not establish live model accuracy.

- Initially failing adversarial cases reproduced negative/proposed/terminated relationships, competitor or parent partnerships attached to the issuer, scattered-name-token identity matches, a ZIP whose largest PDF belonged to another issuer, unsupported AI factual prose despite a real quote, stale refresh documents, missed fallback candidates and leaked queue slots after submission failure. Fixes were checked with those cases, not only successful examples.
- Additional cases cover Unicode/prepositions/abbreviations in names, procurement headings before an issuer subject, community/CSR labels, reversed supplier direction, policy sources incorrectly used as issuer relationships, wrong exchange symbols, stale AI writes, parser/context version changes, invalid financial units, non-finite values, future/duplicate/misaligned periods, provider baseline changes, missing values, original-page quote mismatch, headline/body mismatch, XML entity rejection, HTML access challenges and ASP.NET article form wrappers.
- AI factual fields must equal their source quotations. Qualitative hypotheses remain separate and require evidence; numerical reinterpretations are rejected. Successful quoted-fact/qualitative-hypothesis output was tested as well as rejection paths. Interpretation itself remains unverified.
- Live collection used the same generic pipeline for Rentomojo, TCS and HDFC Bank. Latest retained issuer documents: 2, 3 and 3 respectively. Latest unique graph relationships: 11, 9 and 15. Rentomojo's general-industry consumer mention no longer becomes an issuer customer. Brands remain brands, and explicit community collaborations are labelled separately. A generic collaboration does not imply a commercial counterparty.
- Original PDFs were downloaded again: 35 relationship quotations matched their physical pages, and all 8 retained PDF hashes matched. Structured financial unit/period/citation audits returned zero failures. They returned review warnings for semantic judgment and Rentomojo's missing share count. Passing these checks does not establish commercial significance or complete coverage.
- Both official feeds were read live. PIB's first regional request redirected to an empty feed; an explicit English regional feed worked. Three RBI articles were collected per checked dossier. A separate current PIB article was read with its posted date. Retaining ASP.NET form content fixed an actual empty-article failure. Feed timestamps later than collection time are explicitly flagged for publisher/time-zone review.
- Legitimate source gaps remain visible: Rentomojo results attachments failed the first-three-page text identity check; some low-information documents had no relevant readable passages; a TCS annual report exceeded the 24 MB limit. No content was inferred from these failures.
- Live invalid official/context URLs and excessive source lists returned 422. The keyless AI POST returned 503 without a provider call. The collector, offline pack audit, live statement audit and original-PDF verification scripts were executed.
- Browser checks verified the working data-audit button, zero-failure result with missing-input warnings, readable policy articles, original-source links, future timestamp warnings, and coverage/error states. HDFC Bank correctly disables the generic revenue/margin valuation model. Completed documents, relationships and contextual sources survived a backend restart. The workflow remained within a 390px viewport with zero browser console messages. Production build, Ruff checks/formatting, skill validation and Git whitespace checks passed.

Ignored evidence packs, audit JSON, test logs and screenshots are under `output/research/` and `output/playwright/`. No live Gemini generation, OCR, universal-source coverage or semantic certification is claimed.


## Independent Gem Aromatics / Sambhv / Hy-Tech benchmark

The user requested these specific companies as a comparison with an independent research process. Legal identities were confirmed from primary filings. The baseline packs were retained before changes; their three-document collections each produced no graph relationships. The independent findings and source links are in [research/RESEARCH_COMPARISON.md](research/RESEARCH_COMPARISON.md).

| Selected benchmark checks | Before | After |
| --- | --- | --- |
| GEMAROMA | 4/12 | 12/12 |
| SAMBHV | 2/9 | 9/9 |
| HTEL | 2/12 | 12/12 |

These 33 checks cover selected disclosed counterparties, eight financial row/basis combinations, key retrieved operating evidence, transcript coverage and newspaper exclusion. They are not a general accuracy percentage or semantic certification. The fixture JSON is used only by the benchmark CLI and never seeds the runtime collector.

- All three final collections retained six sources. Current graphs contain 16/18/5 extracted relationship mentions respectively. These counts include unresolved naming variants/brands and historical disclosures; they are not counts of independently verified current legal counterparties.
- Re-downloaded all 18 retained originals, including company HTML pages. All 18 content hashes and 39 relationship quotations matched. No original-source checks failed or remained unavailable in this final run. Data audits returned zero failures and explicit warnings for accounting-basis/definition review and semantic judgment.
- Rendered and visually inspected Gem's consolidated annual income statement (physical page 138), Sambhv's consolidated statement (179), and HTEL's consolidated presentation table (22). Explicit crore/million conversion, fiscal periods, note numbers, losses, missing values, ambiguous bases/layouts and Cash-PAT exclusions were tested independently with synthetic tables.
- Live financial comparisons exposed Gem and HTEL revenue differences from provider values and the large Gem standalone/consolidated profit difference. Values remain separate. Browser selection of HTEL's FY26 consolidated table supplied revenue ₹189.4 Cr and profit ₹22.6 Cr. The downloaded evidence pack preserved those values, period, basis, source URL and page; assertions against the actual download passed.
- Discovered and fixed newspaper contamination, fragment-only navigation links displacing a real annual PDF, extensionless document links, missing current transcripts, split legal names containing “and”, foreign legal suffixes, prose mistaken for a customer name and multi-page customer tables. Anonymous counterparties remain anonymous. Company HTML enabled explicit NMDC/SECL mentions without guessing which entities anonymous PSU labels referred to.
- The app found a newer HTEL incorporation filing that corrected the independent research's initial reliance on September plans. The research note was revised to distinguish October 5 incorporation from October 7 certificate receipt and from unestablished commercial operations. Material-filing leads and a recency diligence check now expose this distinction; unread full filings remain marked as gaps.
- A cold first browser load exposed two proxy failures while the market endpoints later returned 200. The installed Next.js proxy used a 30-second default; its timeout is now bounded at 65 seconds, beyond the browser's existing 60-second timeout/error handling. This is a resilience adjustment, not a guarantee of provider response time. Fresh production-browser checks returned zero console errors/warnings.
- The cross-check table, same-table baseline selection, source links, material-filings panel and business-specific questions were exercised in the browser. A 390px viewport had document width 390px. Production build, 138 offline tests, Ruff checks/formatting and skill validation passed. Collection results survived service restart.

Live Gemini remained unconfigured, so this exercise compared deterministic collection/extraction and my primary-source research. AI generation and evidence contracts were tested with controlled responses only. Broad global-event discovery, OCR, arbitrary statement parsing, accounting judgment, canonical legal-entity resolution and full valuation remain incomplete.


## Live AI connection follow-up

Both configured credentials passed model metadata access. A small live generation succeeded. Full HTEL generation exposed a timeout and stricter validation failures; no rejected content was accepted as evidence. The resulting flow now distinguishes HTTP 504 timeouts, uses a simplified provider JSON schema and explicitly displays partial reports while retaining strict per-section quotation and relationship validation. The final live HTEL HTTP request returned 200 in 21.6 seconds with twelve sections, two accepted evidence sections, eleven validation warnings and twenty-two source entries. This verifies connection and partial report behavior; AI adherence and semantic accuracy remain unresolved limitations. Partial reports are not cached. No real quota was intentionally exhausted; project-scoped fallback remains tested with controlled HTTP responses. Backend regression suite: 151 passing tests.

Frontend production build (including TypeScript) passed; restarted frontend and backend health/page checks returned HTTP 200.


## Disclosure timeline and private projects

Added a bounded source-linked timeline and workspace-isolated project ledger, not broad scheduled monitoring. Offline suite: **166 passing tests**; Python lint and formatting passed. Production frontend build includes TypeScript validation. New tests cover unread headlines without inferred outcomes, retained source versions, negative statements, future/unsafe sources, potential follow-ups, issuer identity, four-attempt bounds, event fingerprint invalidation, lifecycle/date validation, owner isolation, append-only history, stale updates/deletes and review flags. Live classification bugs involving takeover-regulation references and financing monitoring agencies became regression tests.

Live checks used GEMAROMA, SAMBHV and HTEL. Sampled timelines exposed 28/50/8 items and 7/9/5 excerpt-backed items respectively; counts are coverage observations, not accuracy scores, and may change after refresh. GEMAROMA/SAMBHV yielded two/four additional short attachments; HTEL's relevant incorporation filing was already collected. All **six added attachment hashes and seventeen page quotations** matched re-downloaded originals. Duplicate content is labelled, not treated as independent confirmation. The complete HTEL background workflow also finished with six main documents.

Real-browser testing created an explicitly fictional project in an isolated browser workspace, recorded bid-submitted then preferred-bidder observations, verified preserved history and a passed-estimate review flag, exported JSON, and deleted the fixture. Export retained unverified-entry and date-basis labels. At 390px, document width was 390; screenshots were visually inspected and console reported zero errors/warnings. Ignored artifacts: `output/playwright/HTEL-developments-export.json`, `developments-pending-mobile.png`, `developments-timeline-mobile.png`; live packs are in `output/research/*-developments.json`. No AI calls were needed for this functionality. Automatic tender/outcome matching, broad news/rumour feeds, scheduled alerts and the planned AI-quality redesign remain unimplemented.

Final-build follow-up: possible-follow-up prefill retained the unknown project stage, HTTPS link and source text; explicit select/textarea accessible labels passed real-browser checks. No project was saved during this prefill check. The 390px layout and final production build passed. A concurrent database-update test confirms exactly one writer succeeds for a shared prior version and the other receives 409.


## Reading desk, community and learning release — 14 October 2026

Final offline backend suite: **192 tests passed**. Ruff check passed across the backend; new/changed learning and news Python files passed format checks. The production Next build passed including TypeScript and both `/news` and `/learn`. Git whitespace checks passed (Windows line-ending notices only).

New offline checks cover RSS/Atom parsing, date windows/timezones, unsafe links, duplicate headlines, company-name matching, XML entity and HTML challenge rejection, unavailable versus quiet feeds, cache/refresh/stale behavior, fixed provider queries, partial status, literal topic validation, stock-pick exclusion, publisher-domain spoofing and category-headline relevance. Live unrelated WSJ Navy and China-only economy stories motivated the category and US-region relevance guards. Headline filters remain heuristics, not full article classification. X is tested as search-link-only, with no request for posts.

The deterministic learning lab was independently checked for a known ₹165 example, 20% dilution with unchanged profit, a 12% price-scenario decline despite 10% earnings growth, non-positive earnings with no P/E price, bounds/missing/extra/nonfinite inputs and extreme valid finite outputs. It has no network/AI dependency. These checks establish arithmetic and input handling, not valuation accuracy for actual companies.

Live retrieval returned six available global categories with 40 retained headlines each and six reading suggestions. Company news returned GEMAROMA 3, SAMBHV 12 and HTEL 14 name-matching headlines. A custom cement-demand search returned nine. These counts are snapshots, not coverage targets or independent issuer verification. In the final community check Gem had no matches, while Sambhv and HTEL were unavailable; Reddit's upstream access can change. The unavailable state was shown explicitly. An earlier HTEL check returned a post; no claim of reliable complete Reddit coverage is made. X search URL and non-ingestion label were checked.

Browser checks exercised missing/wrong/correct quiz answers, completion persistence after reload, all nine correct-answer paths and repeat-check deduplication, search terms, all four history cards, all six strategy cards, pitch editing/persistence and actual JSON download contents. The exported learning record contained the synthetic QA note and completion; reading-list export preserved the saved/read flags. Valuation default/dilution/loss cases, clearing stale results on editing, server validation errors and error recovery passed. Simulated API outages verified saved-story access and calculator recovery; corrupted learning storage was left untouched while an in-memory draft remained usable.

Mobile width checks for learning, reading and company/community were 390px document / 390px viewport; the learning desktop check was 1440px / 1440px. A final normal-flow check reported zero uncaught browser page errors. A synthetic Reddit response separately verified successful community-card rendering and its unverified label despite live provider outages. Screenshots were retained under ignored `output/playwright/` and inspected. Expected console network errors occurred only while deliberately returning 422/503 failures; these were handled by the interface. Browser test scripts initially used incorrect button/link selectors; those harness errors were corrected and the actual interaction rerun. QA fixtures were confined to the isolated browser, not written into company evidence or project ledgers.

These features make no AI calls and require no extra API keys. This release does not retest or certify live Gemini interpretation quality, exhaustive source coverage, automatic project outcomes or trading returns. See the preparation plan and project guide for explicit limits.


## Daily news digest and Gmail delivery — 14 October 2026

- Offline suite: **200 passing tests**; Ruff and production Next/TypeScript build passed. New cases cover IST day boundaries, source/quote/numeric/category validation, all-input acknowledgements, HTML escaping, unsafe links, wrong article headings, restricted/challenge pages, 24-hour filtering, deduplication, private delivery metadata exclusion, atomic archive loading and exclusive delivery claims.
- Live source pack: 265 unique retained headlines; 12 bounded article excerpts, 27 publisher previews and 226 headline-only records. All six search feeds and both BBC feeds were available; Guardian was unavailable. These are a dated observation, not guaranteed coverage.
- Prepared six category sections and twelve cited bullets. The validator rejected a numeric publisher-name false positive; prose was corrected rather than weakening the unsupported-number guard. All supporting quotes matched retained evidence. Email HTML contained twelve HTTPS links and no scripts.
- Browser checks expanded all six sections and downloaded a JSON copy identical to the archive. Mobile document width equalled the 390px viewport; no uncaught page errors occurred. Screenshots/export were retained in ignored `output/playwright/`.
- A real initial digest was sent through the connected Gmail account to the user-authorised recipient; Gmail returned a SENT message ID and the narrow Sent search confirmed it. No recipient, mailbox identity, credentials or Gmail IDs are stored in documentation. Delivery metadata is private/ignored. Successful Gmail acceptance does not certify inbox placement or readership.
- Daily 06:00 IST Codex heartbeat created ACTIVE and verified. Its protocol performs dated Sent checks, exclusive claim, send and confirmed-ID recording; it avoids blind retries after ambiguous sends and stays quiet in the thread after success. Actual future scheduled execution remains dependent on an awake computer, running Codex, available sources and connected Gmail. No independent always-on deployment or exact arrival-time guarantee is claimed.


### Plain-text delivery follow-up

Recipient feedback supersedes any inference of inbox delivery from the original SENT record: both HTML attempts were not received; the plain-text control with explicit authenticated From was received. Plain-text rendering now preserves the summary, source URLs, dates, access labels and explanatory sections, with unsafe links rejected. Backend suite: **202 passing tests** and Ruff checks passed. CLI finalization generates both plain-text delivery and HTML preview artifacts. The existing active daily 06:00 IST heartbeat was updated, preserving its schedule and send guards. MIME and explicit From changed together, so causality is not isolated. No recipient address or mailbox identity is included here.


## Independent cloud migration — 14 October 2026

The standalone bot removes the Codex runtime dependency. **217 backend tests passed**, including fifteen standalone cases; those fifteen also passed in a clean environment containing only `requirements-news.txt` dependencies and in GitHub Actions. Ruff and production Next/TypeScript build passed. Tests cover schema/quote/number rejection, labelled fallback, empty-input failure, credential/header validation, plaintext TLS SMTP with exact envelope, narrow IMAP Sent checks, exclusive claims, no blind ambiguous resend, existing-Sent recovery and remote optimistic SHA updates.

Live model smoke tests used a retained 265-headline pack without mail authentication/sending. The refined structured-output constraints accepted four AI categories (US/India/policy/commodities) and explicitly fell back for world/events. A previous attempt exposed quotes longer than the validation limit; schema and prompt lengths were tightened without relaxing evidence validation. A model-access 404 was observed on an alternate call; no universal model access or generation success is claimed.

Only the allowlisted standalone folder and hosted workflow were published through PR #2, which passed hosted checks and was merged. Active private environments and unrelated local work were excluded; the publish scan checks actual secret/recipient values. Existing model credentials and mail account/destination configuration were encrypted into Actions secrets. The separate Gmail app password remained missing, so scheduled email activation and real independent SMTP delivery were pending. A hosted non-sending preview was dispatched. Earlier successful Codex Gmail tests do not establish standalone SMTP or hosted delivery.


The hosted manual preview subsequently passed both verification and collection/model jobs: run 38563467107 retained 260 headlines, 12 article excerpts and 25 feed excerpts; five AI categories passed and world news was explicitly a fallback. It performed no mail authentication or delivery. The old Codex heartbeat was paused as part of moving to an independent runtime. The hosted schedule is still gated off because the Gmail app password has not yet been supplied, so cloud email delivery is not claimed.

Replacement-sender check: private configuration presence and runtime/file consistency passed. Gmail IMAP returned an authentication failure; a separate no-send SMTP authentication attempt disconnected. No test email was sent, no invalid credential was published, and the hosted schedule remains disabled pending a valid app password and hosted send verification.

## Telegram migration (2026-10-15)

All 226 backend tests pass. The 24 standalone cases also pass in the isolated news-only environment. New checks cover token/destination validation, private identifiers, rotation-stable daily IDs, caption limits with Unicode, fallback labels, exact HTTPS upload/no parse mode, safe non-retried errors, wrong identity/chat rejection, claim-before-send, complete source attachment, duplicate prevention, ambiguous receipt handling and nonce-based recent private-human pairing. Ruff and whitespace checks pass. Live token identity and private pairing succeeded; pairing sends no message. Hosted delivery and activation must still be verified separately. No credentials, chat IDs or personal addresses are recorded here.

Live document-format follow-up: PR #3 passed GitHub verification and merged. Hosted run 38635795379 returned Telegram acceptance and persisted an accepted claim; the recipient confirmed receipt. Coverage: 258 headlines, eleven article excerpts, twenty-nine feed excerpts and 218 headline-only records. US/India used validated AI output; world/policy/commodities/events were explicit headline fallbacks.

At the user request, delivery was revised to direct numbered HTML messages with clickable source links. All 229 backend tests and 27 standalone tests pass, including escaped special characters, intact Unicode and links across chunks, rejecting unsafe/oversized citations before claiming, complete multipart acceptance and partial-progress/no-replay handling. The full report is no longer a text attachment. Hosted verification of the revised format and schedule activation are pending at this stage.

Teacher clarification: no image feature was implemented. All 237 backend tests and 35 isolated standalone tests pass. The 47-lesson course renders completely under Telegram limits with examples, research tasks, source links and self-check/spoiler answers. Tests cover source/answer fields, first/next day, leap dates, invalid/future starts, explicit review cycles, labelled optional news exercises, separate news/lesson claims, failure/no-replay and delivery-free dry runs. The messages-only hosted run 38636763098 completed successfully. Hosted teaching delivery and final schedule activation are still pending at this point; message acceptance is not assumed to prove readership.

Final universal-format checks: 246 backend tests and 44 isolated standalone tests pass. The bot-only general-news categories preserve the website finance desks. Separate edition headings/content, weekday/date routing, empty gaps, partial-failure isolation, closing-task gating, bounded/diverse story selection, prediction/nonobject rejection and headline-only empty feed descriptions are covered. The local live no-mail run retained 360 items across all eight topics: eleven article excerpts, 127 feed excerpts, 222 headline-only. FT and ET/Mint/Business Standard records were present. Nine direct feeds were available; Guardian Business was explicitly unavailable. This run sent nothing and made no AI calls. Final hosted bundle delivery/activation still requires verification.

Final hosted verification/activation: PR #5 passed on final head ca89212fd416042203008304dbd6fd2b5a8753cc and merged as 6371a3a4b185a9092dae6a16a93a3202c6c249cd. Run 38640499793 accepted all four newsletters, teacher and closing task, with sixteen of sixteen persisted parts confirmed. Coverage: 360 items, eleven article excerpts, 128 feed excerpts, 221 headline-only; one AI category and seven explicit headline fallbacks. Final-format readability/link receipt was requested separately and is not assumed from API acceptance.

Repeat hosted run 38641604732 returned already_accepted for every component, with no collection/model work or repeated messages. NEWS_BOT_ENABLED was enabled and read back as true, NEWS_DELIVERY as telegram, and the learning start setting was verified. Daily target is 06:00 IST; the next fresh bundle after the migration-day manual test targets 2026-10-16. This verifies configuration and real hosted delivery/deduplication, not future exact cron execution or user readership. The old Codex heartbeat remains paused.

The CI-only test failure was resolved by isolating the CLI test from GITHUB_ACTIONS; all 44 standalone tests then passed with the hosted flag explicitly present and on the final GitHub runner. Ruff and normal whitespace checks pass. All 246 backend tests had passed before that test-only isolation fix; runtime changes also passed final hosted verification.

Finance Class/memory revision: 264 backend tests and 62 isolated runtime tests pass, including the hosted environment flag. All 42 broad lessons render under Telegram limits with original notes/examples and primary further-reading links; Stock Daddy retains the separate 47-lesson research course. New tests reject unsupported model numbers, keep headline-only reports out of detailed case selection, label historical allegations and hypothetical cases, verify distinct delivery claims, enforce seven-day/24-hour exclusion boundaries, remember only acknowledged presented sources, recover history from receipts, prune active memory and exact local artifacts, prevent raw-footer spill, and repeat a complete bundle without additional sends.

Live no-mail collection worked for daily and weekly windows. The seven-day scan retained 113 records, all between 24 and 168 hours old, with four selected significant follow-up candidates. Provider availability remains labelled. No new credential/provider/dependency is required. Hosted deployment and actual revised-format receipt still require verification; the schedule is gated off briefly for this migration.

Hosted migration follow-up: PR #6 passed checks and merged. Run 38693686585 confirmed all revised news, weekly, Finance Class, Finance in context and Stock Daddy parts, but a history reconciliation error made the run partial and withheld the closing task. Receipt inspection confirmed acceptance; history was repaired without resending. Finance Class accepted a quote-checked AI elaboration; context and news used labelled authored/headline fallbacks when the provider quota was unavailable. Reconciliation now has one bounded state-only retry, tested both before a write and after a successful write whose acknowledgement is lost. All 267 backend tests pass; final hosted recovery verification/reactivation remain pending. No duplicate-send claim is cleared automatically.

Final recovery and activation: PR #7 passed hosted verification and merged as a2da83ff55321a23ca182e575cf6c911cb8ace46. Hosted completion run 38694723464 returned already_accepted for the four daily editions, seven-day follow-up, Finance Class, Finance in context and Stock Daddy; only the previously withheld closing task was newly sent. All eighteen parts across nine components were confirmed accepted. Active story memory held 38 hashes, with no raw titles, URLs, bodies or chat identifiers. No accepted message was replayed. User readability confirmation was requested separately.

All 267 backend tests and 65 small-runtime tests pass. Added recovery tests cover failure before a state write and a lost acknowledgement after a successful write, with no message API calls. Final hosted flags and direct readback verified the schedule active, Telegram selected and independent Finance Class/Stock Daddy start settings. Daily target remains 06:00 IST; the next fresh edition after the manual migration-day preview targets 2026-10-16. Exact future arrival, source completeness, semantic interpretation and physical Git-history erasure are not claimed.

## Deeper Finance Class, local validation (2026-10-15)

272 backend tests and 70 isolated standalone tests pass, including simulation with GITHUB_ACTIONS=true. All 42 lessons render as a separate heading plus two numbered content parts. Largest message is 3532 UTF-16 units, below Telegram's 4096 limit. Day 1 estimates six minutes reading plus three to five minutes practice. Checks cover complete authored depth, teaching-before-assessment, balanced permitted HTML, independent numerical exercise calculations, missing-depth rejection, one-day/seven-day recall and a class-only migration followed by a no-send repeat. Ruff and normal git diff --check pass. Hosted PR verification and revised lesson delivery remain pending at this point; the existing schedule has not been disabled.


## Deeper Finance Class deployed and verified (2026-10-15)

The reader confirmed the stream split and requested greater teaching depth. PR #8 passed hosted verification on head 1afd286e7be05915fb172bd16ee7b7d1a6ef039b and merged as d4b7ee390e64ee664fd3f4ccdff2b3587d71d27c. Hosted run [38709000442](https://github.com/DareDevil365/Nivesh/actions/runs/38709000442) succeeded: only the revised Finance Class was sent; all four daily news editions, seven-day follow-up, context, Stock Daddy and closing were already accepted and skipped. All three revised class parts have accepted receipts, and their body hash matches the locally tested full authored Day 1 preview. API acceptance does not establish reader comprehension or satisfaction with depth.

All 42 lessons have substantive original depth notes, three-step examples, misconceptions and explained application exercises. One-day/seven-day recall is calendar-based, not performance-based. Every no-AI lesson renders as a heading and two numbered content messages; the maximum is 3532 UTF-16 units. The introductory lesson estimates six minutes reading plus three to five minutes practice. Subsequent daily topics keep their existing calendar dates. Gemini is optional and bounded; the expanded core requires no additional API calls or keys.

Final validation is 272 backend tests, 70 isolated runtime tests, successful hosted checks, Ruff and whitespace checks. Tests include all-course HTML/length/order, 23 numerical exercises calculated independently, missing-depth rejection, recall/review boundaries and one-time class migration with no replay. The current active schedule and both course start settings were read back from the hosted repository; delivery remains Telegram at 00:30 UTC / 06:00 IST, subject to GitHub delays. No local computer or Codex runtime is required. The old Codex heartbeat remains paused. Lesson breadth is a foundation rather than a complete degree; mathematical checks and source/quote guards do not certify every interpretation or pedagogical outcome.


## Textbook-length Finance Class: local validation (2026-10-15)

The reader chose 15–20 minutes of reading, replacing the earlier compact preference. All 42 complete no-AI chapters contain 2577–2797 words including message labels and recall; the actual in-message reading estimates are 16–18 minutes at an explicit 160 words/minute. Each has a separate heading plus six numbered content parts, with maximum size 3533 UTF-16 units. Practice is additional. Shared module foundations, cases and supporting readings are deliberately reused and labelled rather than represented as entirely new daily essays.

275 backend tests and 73 isolated standalone tests pass. Validation covers the canonical 2400–3200-word budget, all reading estimates and HTML/ordering/transport limits, coverage and connection rejection, unsafe-link rejection, escaping, and refusal to produce a textbook claim when supplied content is insufficient. Existing arithmetic, independent delivery, calendar and no-repeat tests remain active. Ruff and normal git diff --check pass. Hosted deployment and one textbook-only preview remain pending at this stage; the 6 AM IST schedule remains active.


## Textbook edition live and verified (2026-10-15)

PR #9 passed hosted checks on ffc1de16c60301d3bf50508d0ab59ecc9ae59052 and merged as 39b77f827a0611c6da924f4952dd109cd35dfe99. Hosted run [38724492551](https://github.com/DareDevil365/Nivesh/actions/runs/38724492551) completed successfully. Only the revised Finance Class was sent; all four news editions, weekly follow-up, Finance in context, Stock Daddy and closing were already accepted and skipped. The class receipt confirms all seven parts (heading plus six content messages), and the saved body hash matches the complete locally tested authored Day 1 chapter. API acceptance is not a claim of learner comprehension or human approval of the chapter.

All 42 no-AI chapters contain 2577–2797 words including message labels and recall, with in-message estimates of 16–18 minutes at 160 words/minute. Practice is additional. The chapters deliberately reuse labelled module foundations and cases and include curated supporting concepts; they are not 42 wholly independent essays. Core content requires no additional model calls. Both course start settings and active Telegram scheduling were read back from the cloud repository. Delivery remains scheduled for 00:30 UTC / 06:00 IST without the user's computer, backend or Codex, subject to GitHub delays. No previous delivery claim was cleared.

Validation: 275 backend tests, 73 isolated runtime tests, successful hosted verification, Ruff and whitespace checks. The migration test now models an accepted compact v2 class followed by the v3 textbook class, with no news replay and no send on the next retry. Existing arithmetic and semantic-guard limits still apply. Length and transport tests establish that the requested reading material is present and deliverable; they do not certify a complete finance degree, every causal interpretation or teaching effectiveness.


## Daily Brief sibling project verified and active (2026-10-15)

PR #10 passed its final hosted 95-test verification (run 38733138172, head 2355be6f46c7cc5b3480b5eb0f3168f3984b0565) and merged as 261ff6001f8fd355c8199a01dacff0f53abf3a14. Hosted run [38733394925](https://github.com/DareDevil365/Nivesh/actions/runs/38733394925) succeeded. Only the new AI newsletter was sent: its heading and two content parts have accepted receipts. All existing world/India finance and general news, weekly follow-up, Finance Class, context, Stock Daddy and closing claims were already accepted and skipped. The prior Finance Class body hash still matches the authored chapter; no accepted claim was reset.

Read-only verification confirmed daily-brief/ is present on the hosting repository's main branch and news-bot/ is removed. Telegram's Daily Brief display name was verified. The schedule was re-enabled and read back as active at 00:30 UTC / 06:00 IST. AI delivery is enabled. The previous Codex heartbeat remains paused. No local computer, backend or Codex runtime is needed.

Mailbox authentication remains unresolved: the existing credential was rejected, and no real newsletter-email ingestion is claimed. The AI edition can use public sources while the reader's replacement app password and subscriptions are pending. This is distinct from the successfully tested mailbox parser/protocol fixtures and accepted public-source AI briefing. Hosted receipts do not certify whether Gemini interpretation was available or semantically correct; unavailable synthesis is explicitly labelled source-led. A private environment edit must be synced to hosted secrets before future runs use it.

Daily Brief now owns bot-specific private environment fields; those fields were removed from the Nivesh backend environment after preserving them in Daily Brief. Shared Gemini keys remain available to the research application. The updated local guide includes this live outcome; the deployed code is the reviewed PR head, while these final operational notes were recorded after that run. Final validation is 95 standalone tests plus Nivesh's 202 remaining application tests, with Ruff and migration hash checks. Source availability, same-story rewording, imperfect advertisement/personalisation filtering, account-wide app-password scope and GitHub schedule delays remain as described above.
