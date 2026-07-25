# Nivesh — Agent Context (always-loaded)

> This file is the single always-loaded source of truth for this project. Keep it under ~500 lines.
> The full spec lives at `docs/PROJECT_SPEC.md` — do NOT re-read it every session. See "How to use this file" at the bottom.

## 0. What this is
A ₹0-budget, NSE-focused web platform with four bundled features:
1. **Snowflake dashboard** — Simplywall.st-style 5-axis visual company analysis (Value/Future/Past/Health/Dividend)
2. **NL Strategy Backtester** — plain-English trading idea → deterministic `vectorbt` backtest (LLM only maps English to a fixed JSON schema, never executes anything itself)
3. **Behavior Analyzer** — upload trade CSV → diagnosed trading psychology (cuts winners early? revenge trades? erratic sizing?)
4. **Pseudo-Brain / AI Research Digest** — reads corporate announcements, insider filings, news, concalls → plain-English summaries, always linked to source

Reference sites: simplywall.st (visual clarity), Screener.in (data density, speed), Tijori Finance (sector framing).

## 1. The one rule that governs every decision
**AI is a garnish, never the dish.** Every AI-touched feature must work correctly with the LLM entirely absent — worse prose, never wrong/broken/blank. Concretely:
- Numbers (revenue, ratios, prices, stats) **NEVER** come from an LLM. Always from `pandas`/`pandas-ta`/`vectorbt` reading structured cached data.
- LLM calls only ever produce **structured JSON against a closed schema/vocabulary**, validated before use, never freeform text, never executed directly.
- Every LLM call: cached forever (by content hash), one retry on failure, then silent fallback to a rule-based/templated/empty path. Never blocks page render. Never shows a raw error.
- Where a non-AI path can do the job (templated "what we found" bullets, rule-based Pros/Cons, technical indicators), it does — zero LLM cost.

## 2. Tech stack (do not deviate without strong reason)
| Layer | Choice |
|---|---|
| Frontend | Next.js 14 App Router + TypeScript + Tailwind |
| Charts | `lightweight-charts` (candlesticks), Recharts (Snowflake/radar/bar/line) |
| Backend | Python 3.11 + FastAPI |
| Backtesting | `vectorbt` (free edition) for prototyping/vectorized math; **execution path built on plain pandas/numpy you own outright** — see caveat below |
| Indicators | `pandas-ta` |
| DB | Supabase Postgres (free, 500MB) |
| Cache | Upstash Redis (free, 10k cmd/day) |
| Cron | GitHub Actions (free, 2000 min/mo) |
| Backend host | Render.com or Fly.io free tier |
| LLM | Gemini 3.6 Flash (free tier, Google AI Studio), Gemini 3.5 Flash-Lite for cheap classification calls, **structured JSON-schema output mode only** |
| Auth | Supabase Auth (email + Google OAuth) |

## 3. Data layer — non-negotiable rules
- **No user request ever calls an external data source directly.** Only background jobs (GitHub Actions cron) touch `yfinance`/`nsepython`/`nsefin`/scrapers. User requests read Redis-first, Postgres-fallback, `<100ms`.
- Refresh cadence: EOD prices daily after close; intraday "live" price 60–90s poll (only for viewed/watchlisted tickers); fundamentals & shareholding weekly.
- Be upfront it's ~15min delayed, not true real-time — show a "Delayed ~15 min" badge.
- **Historical/backtest data: fetch-on-demand, cache forever** (EOD data is immutable — no bulk backfill). On cache miss, fetch just the missing date range from NSE bhavcopy archive, persist permanently.
- **Data honesty constraint:** NSE equity data only exists from Nov 1994 onward. Pre-1994 (e.g. Harshad Mehta 1992 scam) has **no free live-fetchable per-stock source** — that scenario is index-level-only (static seed table), never faked as a per-stock backtest.

## 3a. vectorbt license caveat (read before building the backtester)
The free `vectorbt` is Apache 2.0 **+ Commons Clause** — it bars selling a product that's *primarily* this software, and the free edition is frozen/unmaintained (active work moved to a paid `vectorbt.pro`). Since the backtester is the headline feature, use `vectorbt` for prototyping and vectorized-math patterns, but keep the actual shipped execution engine on plain `pandas`/`numpy`/`numba`. Don't make the core product depend on it directly.

## 4. Strategy Backtester — the headline feature
- **Two entry points, one engine.** (1) Guided Builder (dropdowns: indicator/condition/value/exit/stop-loss/date-range) — the primary, always-works, zero-AI path, shown first. (2) Free-text NL box — optional convenience layer that pre-fills the SAME Guided Builder via one Gemini structured-output call.
- **Critical reliability rule:** parsed LLM output always lands back in the visible, editable Guided Builder before anything executes — nothing auto-runs off raw LLM output. On parse failure/timeout: silently degrade to an empty Guided Builder, no error page.
- Closed indicator vocabulary: RSI, MACD, SMA/EMA crossover, Bollinger touch, ADX, volume spike, price % change over N days. Closed condition vocabulary: `crosses_above`, `crosses_below`, `greater_than`, `less_than`.
- Strategy JSON schema (shared contract between Guided Builder form state and LLM parser output — engine doesn't care which produced it):
```json
{
  "ticker": "TCS.NS",
  "entry_rule": {"indicator": "RSI", "params": {"period": 14}, "condition": "crosses_below", "value": 30},
  "exit_rule": {"indicator": "RSI", "params": {"period": 14}, "condition": "crosses_above", "value": 70},
  "position_sizing": {"type": "fixed_capital", "amount": 100000},
  "stop_loss_pct": 5, "take_profit_pct": null,
  "date_range": {"start": "2020-02-01", "end": "2020-08-31"},
  "scenario_label": "COVID-19 Crash & Recovery"
}
```
- Preset scenario library (all real, live-fetchable per-stock unless noted): Ketan Parekh/dot-com bust (Feb 2000–Sep 2001), Global Financial Crisis (Jan 2008–Mar 2009), 2016 Demonetization, COVID Crash & Recovery (Feb–Aug 2020), Adani-Hindenburg (Jan–Apr 2023). Harshad Mehta scam = index-level only, clearly labeled.

## 5. Behavior Analyzer
- CSV upload (generic template + Zerodha/Groww mappings) → all metrics computed as pure Python functions with unit tests (must be numerically correct, test against hand-calculated examples) → one cached LLM narration call layered on top of the always-correct metrics cards.

## 6. Pseudo-Brain / AI Research Digest (§3.8 in full spec)
- **The one rule that makes it trustworthy: numbers never come from the LLM.** LLM only ever summarizes/tags *qualitative* text (announcements, concalls, news) — never restates or computes a figure.
- Three streams, honest about automation level: (1) Corporate announcements via `nse` (bennythadikaran/NseIndiaApi — circulars method) + insider trading via `pnsea`, polled 15–30min — fully automatable, all NSE companies. (2) News via free RSS — fully automatable. (3) Concall transcripts — NOT centrally available free; scope to a curated list (start Nifty 50/200), grow manually. Everyone else shows "not yet available," never a fabricated summary.
- Pipeline: rule-based keyword triage first (no LLM, handles ~80% of filings) → only high-signal docs go to one batched Gemini call per document (structured output: 1-2 sentence summary, category tag from closed vocab, sentiment flag for concalls, red-flag pattern tags from closed vocab) → validated → cached forever by document hash.
- UI must visually distinguish rule-based flags (from numbers) vs AI-derived flags (from documents) — never blur the two. Every AI line carries an "AI-summarized from [source]" tag linking to the original.

## 7. Core API surface (FastAPI)
```
GET  /api/companies/{ticker}                  -> profile + snowflake scores
GET  /api/companies/{ticker}/chart?interval=  -> OHLCV + indicators
GET  /api/companies/{ticker}/peers            -> sector peer comparison
GET  /api/companies/{ticker}/pros-cons        -> rule-based flags
GET  /api/companies/{ticker}/insider-activity
GET  /api/companies/{ticker}/documents
GET  /api/companies/{ticker}/research-notes   -> AI digest or "not yet available"
GET  /api/screener?filters=...
POST /api/strategies/parse                    -> {text} -> Strategy JSON (the one Gemini call)
POST /api/backtest                            -> {strategy_json} -> results, cached by hash
POST /api/behavior/upload / analyze
GET/POST /api/watchlist
POST /api/alerts
```
Every GET: Redis-first, Postgres-fallback, stale-while-revalidate. Never blocks on an external call mid-request.

## 8. Security
- Supabase Auth (email + Google OAuth), JWT sessions.
- Row-Level Security on all user-owned tables (`watchlists`, `trades`, `strategies`) — enforced at DB level.
- Trade CSVs: file upload only, never store broker credentials, no broker API linking in v1.
- Rate-limit own public endpoints (Redis token bucket) to protect free-tier quota.

## 9. Design tokens (implement literally)
```
Background:        #0B1210   Surface/card:    #131B18
Primary accent:     #1E7A4C   Secondary accent: #C9A227
Positive:           #2ECC71   Negative:         #E74C3C
Text:               #E6EDEA   Muted text:       #8FA096
Border:             #223028
Font headings/numbers: 'Sora' 600/700   Font body/UI: 'Inter' 400/500
Cards: 12px radius, 1px border, no heavy shadow — flat, data-forward
Spacing scale: 4/8/12/16/24/32/48px
```
Dark-mode-first; light theme is v2.

## 10. Deployment survival notes
- Render/Fly free tier sleeps after ~15min idle (30-50s cold start) → GitHub Actions cron hits `/health` every 10min during usage hours; frontend shows a "waking up" state for cold hits.
- Supabase free tier pauses after 7 days inactivity → same keep-alive cron (`SELECT 1`).
- Secrets only in env vars / platform secret managers, never in repo.

## 11. Build order (do not skip ahead — each phase depends on the last)
0. Foundation (monorepo, Supabase, Redis, hello-world deploy pipeline)
1. Data pipeline + Company Dashboard MVP
2. Charts & Technical Analysis
3. Screener + Watchlist + Alerts
4. Strategy Backtester (Guided Builder fully working FIRST, NL layer second)
5. Behavior Analyzer
6. Pseudo-Brain / AI Research Digest
7. Polish (heatmap, DCF calculator, glossary, responsive, empty/error states)
8. Launch readiness (keep-alive crons, analytics, docs)

Full per-phase checkboxes and acceptance criteria: see `docs/PROJECT_SPEC.md` §10.

## 12. Where to find more detail (don't re-derive — read once, then use these Skills)
- `.antigravity/skills/nse-data-fetching/SKILL.md` — exact headers/session/cookie handling for `nsepython`, lazy-fetch-and-cache logic (spec §2.4)
- `.antigravity/skills/ai-research-digest/SKILL.md` — announcement category vocabulary, triage keyword rules, document chunking approach (spec §3.8)
- `docs/PROJECT_SPEC.md` — the full original spec (feature detail, DB schema §4, full scenario table §3.3, AI reliability doctrine §6, feature-parity audit §0.1). Treat this as reference material, not something to load every turn — see below.

## How to use this file (read once)
This file is intentionally the *condensed* version. The full spec is long — don't reload it every session. Instead:
- Keep this AGENTS.md as your always-on context (Antigravity loads it automatically at session start).
- Consult `docs/PROJECT_SPEC.md` only when a task needs a section this file doesn't cover in enough depth (e.g. the exact DB schema, the full competitor feature-parity tables).
- Once you've worked out something non-obvious (auth headers for NSE scraping, a chunking strategy, a scoring rubric), write it into the relevant `SKILL.md` under `.antigravity/skills/` — that's the persistence mechanism, not re-deriving it from the spec next time.
