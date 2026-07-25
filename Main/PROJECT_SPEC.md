# PROJECT SPEC — "Nivesh" (working name)
### An AI-assisted equity research, backtesting & trading-psychology platform for the Indian (NSE) market
**Prepared as an execution brief for Google Antigravity (Gemini 3.6 Flash agent)**
**Author role:** Principal Software Architect & Lead Quant Engineer
**Budget:** ₹0 — every service below is on a free tier. No paid data vendor, no paid LLM credits beyond Gemini's free quota.

> **Verification note (this revision):** three factual issues from the earlier draft are corrected here after checking current sources: (1) the model reference is standardized to Gemini 3.6 Flash — Google's current Flash-tier model as of this writing, free-tier accessible but rate-limited, with Pro-series models no longer free; (2) the `nsefin`/`pnsea` package claims in §2.1 and §3.8 are corrected — `nsefin` covers OHLCV/candlestick data only, not filings or insider trading, and the package mix is adjusted accordingly; (3) a licensing caveat is added to §1 for `vectorbt`, whose free edition carries a Commons Clause restriction relevant to a product whose headline feature is the backtester.

> **How to use this document (for the Antigravity agent):** This spec is organized as a phased build plan. Each phase has a goal, exact deliverables, and acceptance criteria written as checkboxes. Work top-to-bottom. Do not skip ahead to Phase 4 (Backtester) before Phase 1's data layer is solid — everything downstream depends on it. Where a "Skill" is suggested, create it under `.antigravity/skills/<name>/SKILL.md` so the knowledge persists across sessions instead of being re-derived every run.

---

## 0. Product Vision

A retail-investor-facing web app for NSE-listed stocks that combines four things nobody currently bundles for free in India:

1. **Simplywall.st-style visual company analysis** (the "Snowflake") — instead of a spreadsheet, a glance-able picture of whether a company is cheap, healthy, growing, and paying dividends.
2. **A natural-language backtesting sandbox** — a user types a trading idea in plain English, optionally anchored to a real historical crisis (e.g. *"Buy Reliance whenever RSI drops below 30, sell at RSI 70, run this during the Harshad Mehta scam period"*), and gets a real, chart-backed simulation — not an LLM hallucinating an answer, but a deterministic backtest engine that an LLM only helped configure.
3. **A trading behavior/psychology analyzer** — upload your trade history, get a data-driven diagnosis of your habits (do you cut winners early and hold losers? do you revenge-trade after a loss? is your position sizing erratic?) — the kind of self-awareness tool no free Indian platform currently offers.
4. **An AI Research Digest ("pseudo-brain")** — the product actually reads corporate announcements, insider disclosures, news, and (for a growing set of covered companies) concall transcripts, and surfaces plain-English conclusions with sources — not by hallucinating from a model's memory, but by summarizing real documents fetched close to the moment they're filed. See §3.8.

**Design north star references:** simplywall.st (visual clarity, the Snowflake, "why does this matter" tooltips), Screener.in (data density, query-based screener, speed), Tijori Finance (sector/theme framing, clean typography).

**Non-negotiable engineering constraint:** this runs on free infrastructure. Every architectural decision below is filtered through "does this survive a free-tier rate limit / cold start / quota cap?"

### 0.1 Feature Parity Audit — what's taken from where, and what was missing until this revision

Direct answer to "did you get everything good from these sites": mostly, in the first draft — the gaps below are now closed in §3.1 and the new §3.8.

**From simplywall.st:**

| Feature | Status |
|---|---|
| Snowflake (5-pillar radar) | ✅ in v1 (§3.1) |
| "Why does this matter" hover explanations | ✅ in v1 (§3.7 glossary) |
| Analyst/community fair value estimates | ✅ partial — analyst estimates where available; **added:** interactive Narrative/DCF calculator (§3.1) as the free-tier substitute for community estimates |
| Insider transactions feed | ⚠️ was missing — **added** in this revision (§3.1, §3.8) |
| Portfolio tracker with returns/dividends | Not in v1 — v2 candidate; v1's Behavior Analyzer covers the closely related "diagnose your trades" need |
| Shareable report card | ✅ in v1 (§3.7) |

**From Screener.in:**

| Feature | Status |
|---|---|
| Query-based screener | ✅ in v1 (§3.5) |
| Peer comparison | ✅ in v1 (§3.1) |
| **Auto-generated Pros/Cons flags** | ⚠️ was missing — **added** in this revision (§3.1) |
| Concall transcript & annual report links | ⚠️ was missing — **added** in this revision (§3.1 Documents tab, feeds §3.8) |
| Custom formula/ratio builder | Not in v1 — v2 candidate (needs a small formula DSL, doable free but non-trivial scope) |
| Export to Excel | Partial — CSV export ships in v1, full XLSX formatting is a v2 nice-to-have |

**From Tijori Finance:**

| Feature | Status |
|---|---|
| Sector/theme framing | ✅ in v1 (§3.7 heatmap) |
| **Business segment revenue breakdown** | ⚠️ was missing — **added** in this revision (§3.1) |
| Corporate structure / subsidiaries map | Not in v1 — genuinely hard to source for free at scale (needs structured group-holding data no free API provides); stretch goal if a source is found later |

**This conversation's ask — reading concalls/filings/news/announcements and drawing conclusions:** ⚠️ **wasn't in the spec at all until now — this is the biggest addition, see the new §3.8 "Pseudo-Brain."** None of the three reference sites do this with LLM synthesis today, so done well, this is your actual differentiator, not just parity.

---

## 1. Tech Stack (final — do not deviate without a strong reason)

| Layer | Choice | Why |
|---|---|---|
| Frontend | **Next.js 14 (App Router) + TypeScript + Tailwind CSS** | Free hosting on Vercel, server components reduce client JS, great DX |
| Charting | **lightweight-charts (TradingView's open-source lib)** for candlesticks; **Recharts** for the Snowflake/radar, bar, and line charts | lightweight-charts is purpose-built for OHLC and free/MIT licensed; Recharts is simplest for composable dashboard charts |
| Backend / API | **Python 3.11 + FastAPI** | Non-negotiable — the quant stack (`pandas`, `numpy`, `vectorbt`) is Python-only and far more capable than any JS equivalent for this |
| Backtest engine | **vectorbt (free/open-source edition)** + custom event-loop fallback for strategies too complex for vectorized ops | Vectorized backtesting is orders of magnitude faster than a naive for-loop — matters a lot on free-tier CPU. **License caveat:** the free `vectorbt` (polakowo/vectorbt) is Apache 2.0 **with a Commons Clause** — it prohibits selling a product or service that is *primarily* this software, and the free edition is also no longer actively maintained (frozen around v0.28.x, with active development moved to a paid `vectorbt.pro`). Since the backtester is Nivesh's headline feature, use `vectorbt` for prototyping and the vectorized-math approach, but keep the actual execution path built on plain `pandas`/`numpy`/`numba` that you own outright — this avoids both the license ambiguity if you ever monetize and the risk of building your core feature on an unmaintained dependency. |
| Technical indicators | **pandas-ta** | Pure Python/pandas, no external calls, computes RSI/MACD/Bollinger/ADX/etc. instantly and for free |
| Database | **Supabase (Postgres, free tier: 500MB)** | Free Postgres + built-in Auth + row-level security + realtime subscriptions, all in one free product |
| Cache / rate-limit shield | **Upstash Redis (free tier: 10k commands/day)** | Every scraped/free-API call gets cached here first; this is what keeps you under rate limits |
| Scheduled jobs | **GitHub Actions (free, 2000 min/month on public repos)** | Nightly/hourly cron jobs to pre-fetch fundamentals, run screener rankings, refresh caches — free compute you'd otherwise need a paid worker for |
| Backend hosting | **Render.com free web service** (or Fly.io free allowance) | FastAPI app; note free tier sleeps after inactivity — see §9 for the workaround |
| LLM | **Gemini 3.6 Flash (free tier via Google AI Studio API key)**, with Gemini 3.5 Flash-Lite as a cheaper fallback for simple classification/tagging calls (§3.8 triage) | Used sparingly, as an optional layer on top of fully-working non-AI paths — see §6, "AI Reliability & Budget Doctrine". Free tier is rate-limited (RPM/TPM/RPD caps), not unlimited — the caching-forever discipline in §6 is what keeps this workable, not the raw quota size. |
| Auth | **Supabase Auth** (email + Google OAuth) | Free, integrated with the DB |

---

## 2. Data Layer — Free NSE Data Sourcing

This is the riskiest part of the whole project (NSE actively rate-limits/blocks scrapers), so treat it with real engineering discipline, not "just call the API and hope."

### 2.1 Sources (use all three, layered)

| Source | What it gives you | Notes |
|---|---|---|
| `yfinance` (ticker format `RELIANCE.NS`, `TCS.NS`) | OHLCV (15–20 min delayed), basic company info, some financials | Most reliable uptime, no key needed, but hits Yahoo's own rate limits if hammered |
| `jugaad-data` / `nsepython` | Official NSE bhavcopy (EOD full-market data), index data, corporate actions, delivery %, F&O data | Direct from NSE — richer but NSE actively anti-bot-protects the site; must set proper headers/session cookies and back off aggressively |
| Screener.in-style fundamentals (scraped, with respect) | P/E, P/B, ROE, ROCE, debt/equity, historical financials, shareholding pattern | Check `robots.txt` before scraping any specific page; scrape **once a week** into your own DB, never live-per-request |
| `pnsea` (insider trading, options, mutual fund data) + `nse` (bennythadikaran/NseIndiaApi — has a dedicated circulars method) | **Insider trading disclosures** (SEBI PIT/SAST — promoter/director buys & sells) via `pnsea`; **corporate announcements/circulars** via the `nse` package's circulars endpoint | This is the free, genuinely-automatable feed that powers the "announcements" half of the pseudo-brain in §3.8. Poll every 15–30 min during market hours, cache and diff against what you've already stored so you only process *new* filings. **Correction from an earlier draft:** `nsefin` was previously listed here too, but it only covers OHLCV/candlestick data, not filings or insider disclosures — dropped from this row accordingly, kept below for price data instead. |

### 2.2 The caching contract (this is what makes the product "fast")

**Rule: no user-facing request ever calls an external data source directly.** Every request is served from Postgres/Redis. External sources are only ever touched by background jobs.

```
[GitHub Actions cron] → [fetch from yfinance/nsepython] → [normalize] → [write to Postgres + Redis]
                                                                              ↓
[User loads company page] → [FastAPI reads Redis, falls back to Postgres] → [<100ms response]
```

Refresh cadence:
- **EOD price/OHLCV data:** once daily, after market close (3:45 PM IST), via GitHub Actions
- **Intraday quote (for the "live-ish" price ticker):** every 60–90 seconds, but only for tickers currently being viewed or on a watchlist — poll-on-demand with a 60s Redis TTL, not a blanket scrape of all ~2000 NSE stocks
- **Fundamentals/ratios:** weekly (they don't change daily anyway)
- **Corporate actions/shareholding:** weekly

### 2.3 "Real-time" — be honest about what this means
None of the free sources give true tick-by-tick real-time data (that requires a paid NSE feed or a broker API like Zerodha Kite Connect, which needs a funded trading account). Ship a **60-second polling "live" indicator** with a small "Delayed ~15 min" disclosure badge next to the price — this is exactly what free fintech tools do, and being upfront about it is a trust signal, not a weakness.

### 2.4 Historical (backtest) data — fetch-on-demand, cache forever

Good correction from you on the earlier draft, and it simplifies the architecture: there's no need for a big one-time bulk backfill job. **EOD historical data is immutable** — Reliance's closing price on 14 March 2008 will never change — so instead of pre-loading everything, fetch it lazily, the first time it's ever asked for, and cache it permanently (`TTL = infinite`, unlike the 60s/daily TTLs used for live data):

```
User requests backtest for TICKER, 2008-01-01 → 2009-03-31
        ↓
[Backend checks Postgres price_cache for that ticker+range]
        ↓
   Gap found? → [fetch missing dates from NSE bhavcopy archive, live, right now]
        ↓
[Write fetched rows to price_cache permanently] → [run backtest]
        ↓
Next user requesting an overlapping range → served entirely from cache, no external call at all
```

Frontend shows a one-time "Fetching historical data for this period — first request only, a few seconds…" loading state; every subsequent backtest against that range (by anyone) is instant. This is strictly better than a pre-emptive bulk backfill: you never fetch data nobody asked for, and it works for *any* date range without needing to know in advance which stocks/periods will be popular.

**The important caveat — what's actually fetchable, and what isn't:**

| Period | Available via free NSE/BSE data? |
|---|---|
| **Nov 1994 → today** | Yes. NSE's equity (Capital Market) segment only began trading on **3 November 1994** — before that date, NSE simply has no stock-level data because it didn't exist as an equity exchange yet. Free bhavcopy tooling (e.g. community NSE/BSE downloaders) generally treats NSE's archive as usable from ~Jan 1994 onward, so scenarios from late 1994 forward are genuinely live-fetchable per-stock. |
| **Pre-Nov 1994 (incl. the Harshad Mehta scam, Mar–Jun 1992)** | **Not reliably.** The Harshad Mehta scam predates NSE's existence entirely — it played out on the BSE, which is 150 years old but whose free, structured, per-stock EOD archives are commonly only available in an easily-scrapable form from roughly **2007 onward**. There is no free, live-fetchable, per-stock BSE data source for 1992 that this architecture can lean on. |

**What this means for the product (be upfront, not sloppy):**
- Ship the scenario library (§3.3) with periods from late-1994 onward as fully live, real, per-stock backtestable — this covers the Ketan Parekh crash, the GFC, demonetization, COVID, and Adani-Hindenburg, all of which *are* genuinely fetchable this way.
- For the Harshad Mehta scenario specifically, don't silently fake it. Either (a) omit it from the live per-stock backtester and clearly label it as "index-level only" using a small, manually-verified static seed table of historical SENSEX values (these specific index numbers are well-documented public historical facts, not something you scrape), or (b) leave it out of v1 entirely and revisit if you later find a genuine free source for 1992-era BSE per-stock data. Promising a stock-level Harshad Mehta backtest and quietly substituting fabricated numbers would be exactly the "sloppy result" you said you want to avoid — so the honest move is to gate the feature on real data, not paper over the gap.

📁 **Suggested Skill:** `.antigravity/skills/nse-data-fetching/SKILL.md` — document the exact headers/session/cookie handling needed for `nsepython`/direct NSE scraping once you've got it working, plus the lazy-fetch-and-cache logic above, so future agent runs don't have to rediscover it.

---

## 3. Feature Specs

### 3.1 Company Analysis Dashboard (the core page — `/stock/[ticker]`)

**Layout (top to bottom):**

1. **Header bar:** ticker, company name, sector/industry tag, current price with delayed-price badge, day change %, a "Add to Watchlist" star icon
2. **The Snowflake (hero element, top-left, ~400×400px):** a 5-axis radar chart, one axis each for:
   - **Value** — is it cheap relative to fair value/peers/history? (based on P/E vs sector median, P/B, DCF-estimated fair value vs current price)
   - **Future** — projected growth (revenue/earnings growth trend, analyst estimates if available, else trailing 3–5yr CAGR extrapolation)
   - **Past** — historical earnings track record (consistency of EPS growth, ROE trend)
   - **Health** — balance sheet strength (debt/equity, current ratio, interest coverage)
   - **Dividend** — yield and payout sustainability (yield vs sector, payout ratio, dividend growth streak)

   Each axis scored 0–6 (matching the reference site's convention), colored segments (green = strong, yellow = neutral, red = weak), and the *whole shape* is filled with a translucent color so the user reads it as one gestalt shape, not five separate numbers. Every axis label is clickable and expands an inline "why this score" explanation panel with the underlying 3–4 metrics.

3. **Price chart** (see §3.2) sits top-right, next to the Snowflake.
4. **Key stats strip:** a horizontal row of ~8 cards (Market Cap, P/E, P/B, Div Yield, 52W High/Low, ROE, Debt/Equity, Volume) — Screener.in-style density, but with tooltips on hover explaining each in plain English (simplywall.st's signature move — never assume the user knows what ROCE means).
5. **"What we found" narrative panel:** 4–6 auto-generated bullet points in plain English, e.g. *"Reliance is trading below its 5-year average P/E, suggesting relative value"* or *"Debt has increased 12% over the past year, which is worth watching."* — this is templated from computed thresholds (see §6.1), **not** an LLM call per page view.
6. **Peer comparison table:** same company vs 4–5 sector peers, sortable columns.
7. **Financial statements tab section:** Income Statement / Balance Sheet / Cash Flow, last 5 years, with YoY sparkline mini-charts inline in each row.
8. **Shareholding pattern:** stacked bar over time (Promoter/FII/DII/Public %) — a classic thing Indian retail investors specifically watch for (promoter pledge %, FII entry/exit).
9. **Pros & Cons (Screener.in-style, rule-based, zero LLM):** a two-column list — green checkmarks and red flags — auto-generated from the same threshold rules that drive the "What we found" panel above, e.g. *Pros: "Zero debt," "Consistent dividend payer for 10+ years"* / *Cons: "Promoter pledge increased in the last quarter," "Interest coverage below 2x."* This is one of Screener's most-loved features and costs nothing beyond the rule engine you're already building for item 5.
10. **Business segment breakdown (Tijori-style):** a donut or stacked bar of revenue by business segment, sourced from the segment-reporting note in the annual report where structured data is available; falls back to "not disclosed at segment level" rather than guessing.
11. **Insider & Bulk/Block Deal activity feed:** a simple table of recent promoter/director buys-sells (from the free SEBI PIT/SAST disclosures — see §2.1) and NSE bulk/block deals — retail investors specifically watch "is the promoter buying or selling," and this is public free data nobody in the free-tier Indian fintech space surfaces cleanly.
12. **Documents & Filings tab:** links to the company's annual reports, investor presentations, concall transcripts (where sourced — see §3.8), and recent exchange announcements, newest first. This tab doubles as the ingestion source list for the AI Research Digest in §3.8.

**Interactive Fair Value Calculator ("Narrative," simplywall.st-inspired):** a lightweight DCF tool where the user drags sliders for revenue growth rate, margin assumption, and discount rate, and sees a fair-value-per-share number update live — entirely client-side arithmetic (no backend or LLM call needed), pre-seeded with sensible defaults derived from the company's own historical growth/margins. This is simplywall.st's "Narratives" feature reimagined as a free, computed-not-crowdsourced tool, and it's a nice, cheap way to make the Value axis of the Snowflake feel interactive rather than a black box.

**Visual language:** dark theme by default (fintech convention, easier on the eyes for long research sessions), deep forest-green as the primary brand/accent color (used for the "positive/strong" states, nav highlights, and primary CTA buttons), amber/gold for neutral/caution states, and the conventional green-up/red-down for price moves. Typography: **Inter** for UI/body text, a slightly heavier weight (Inter Semibold or **Sora**) for headings and big numbers to give it a "serious financial tool" feel rather than a generic SaaS look. Generous whitespace, card-based layout with soft borders (not heavy drop shadows) — cf. §8 for full design tokens.

### 3.2 Real-Time-ish Charts & Technical Analysis

- Candlestick chart via `lightweight-charts`, intervals: 1D/1W/1M/3M/1Y/5Y/MAX (daily candles for anything beyond 3M to keep payload small; intraday 5-min candles only for 1D/1W views, sourced from the cached 60s poll)
- Overlay toggles: SMA(20/50/200), EMA(9/21), Bollinger Bands
- Sub-chart panel toggles: RSI(14), MACD(12,26,9), Volume histogram
- All of this computed server-side in one `pandas-ta` pass when the OHLCV data is cached, stored alongside the price data — **zero client-side computation, zero LLM involvement.** This is pure, fast, free-of-charge math.
- Drawing tools (trendline, horizontal ray) — client-side only, saved to `localStorage`-equivalent... **wait, no** — per the artifact/browser-storage rule for the eventual React build, use actual backend persistence (a small `chart_annotations` table) if you want drawings to survive a refresh; otherwise keep them in React state for the session only.

### 3.3 The Strategy Backtester — the headline feature

This is where most products would naively pipe everything through an LLM and burn through free credits in a day, and where a flaky free-tier model would make the *whole product* feel unreliable. **Neither happens here.** The design principle: **the LLM is an optional convenience layer bolted onto a system that works perfectly with zero AI involvement.** Given you've said AI should never become the reason something breaks, this is built so the core feature literally cannot fail because of an LLM having a bad day.

**Two entry points into the same deterministic engine:**

1. **Guided Builder (the default, always-works path):** a dropdown-based form — pick an indicator, a condition, a value, an exit rule, a stop-loss, a date range or scenario preset. No AI involved at all. This is what's shown first, and it's not a "fallback" — it's the primary UI. It's also just good UX: precise, no ambiguity, instant.
2. **"Describe it in your own words" (optional, LLM-assisted):** a free-text box that pre-fills the Guided Builder above by parsing the sentence. This is the convenience feature, not a separate system.

**Flow for the free-text path:**

```
User types free text
        ↓
[Gemini Flash — ONE call, JSON/structured-output mode enforced, not freeform text]
        ↓
[Validation layer] → checks the result against the strict schema (types, allowed indicator
                      vocabulary, sane value ranges)
        ↓
    Valid?  ──No──→ [Pre-fill the Guided Builder with whatever DID parse, highlight the
    │                 rest for the user to fill in manually — never guess, never silently
    │                 drop a condition]
    Yes
        ↓
[Pre-fill the Guided Builder fields, user reviews/confirms — nothing runs automatically
 off raw LLM output]
        ↓
[vectorbt engine — pure Python, no LLM, identical code path as the manual builder] → runs
 the actual backtest
        ↓
[Results renderer] → equity curve, trade log, stats table, annotated chart
```

The critical reliability rule: **the parsed output always lands back in the visible, editable Guided Builder before anything executes.** The user sees exactly what the AI understood and can correct it in two clicks — this single design choice is what turns "LLM might misparse something" from a product-breaking risk into a non-issue. If the Gemini call errors out or times out entirely (free-tier quota, network blip, whatever), the UI just quietly drops back to an empty Guided Builder with a small "Couldn't auto-fill that — build it manually below" note. The feature never shows an error page or a broken state; it degrades to "you fill in five dropdowns yourself," which was always a fully capable path anyway.

**Strategy JSON schema** (this is the shared contract — the Guided Builder writes it directly via form state, the LLM parser produces the exact same shape, and the engine doesn't know or care which one produced it):

```json
{
  "ticker": "TCS.NS",
  "entry_rule": {
    "indicator": "RSI",
    "params": {"period": 14},
    "condition": "crosses_below",
    "value": 30
  },
  "exit_rule": {
    "indicator": "RSI",
    "params": {"period": 14},
    "condition": "crosses_above",
    "value": 70
  },
  "position_sizing": {"type": "fixed_capital", "amount": 100000},
  "stop_loss_pct": 5,
  "take_profit_pct": null,
  "date_range": {"start": "2020-02-01", "end": "2020-08-31"},
  "scenario_label": "COVID-19 Crash & Recovery"
}
```

The engine supports a fixed, closed vocabulary of indicators (RSI, MACD, SMA/EMA crossover, Bollinger Band touch, ADX, volume spike, price % change over N days) and conditions (`crosses_above`, `crosses_below`, `greater_than`, `less_than`). **The LLM's entire job is mapping loose English onto this closed vocabulary via structured output** (use Gemini's native JSON-schema/function-calling mode, not "please respond in JSON" prompted freeform text — the enforced-schema mode is both more reliable and cheaper to validate). Never execute LLM-generated code directly — only ever LLM-generated *parameters* against a vocabulary and a validator you fully control. This is a security requirement as much as a reliability one, and it's also exactly what keeps this feature from ever producing a "sloppy" or nonsensical result: the worst a bad parse can do is fail validation and hand back an empty form.

**Preset Historical Scenario Library** — one-click date range presets so users don't need to know exact dates:

| Scenario | Approx. Date Range | Context shown to user | Per-stock backtest via live-fetch? |
|---|---|---|---|
| Ketan Parekh / dot-com bust | Feb 2000 – Sep 2001 | Tech-stock-led rally and subsequent crash | ✅ Yes — NSE was live and its bhavcopy archive covers this period |
| Global Financial Crisis | Jan 2008 – Mar 2009 | Global credit crisis, Sensex fell roughly 50%+ from its peak | ✅ Yes |
| 2016 Demonetization | Nov 2016 – Jan 2017 | Sudden currency policy shock, short sharp volatility | ✅ Yes |
| COVID-19 Crash & Recovery | Feb 2020 – Aug 2020 | Fastest bear market in Indian market history, followed by a sharp V-shaped recovery | ✅ Yes |
| Adani-Hindenburg Episode | Jan 2023 – Apr 2023 | Single-group-concentrated shock and its market-wide ripple | ✅ Yes |
| Harshad Mehta Scam crash | Mar 1992 – Jun 1992 | Market euphoria followed by a sharp correction after the securities scam broke | ⚠️ **Index-level only** — see §2.4. NSE didn't exist as an equity exchange yet (it launched Nov 1994), so there is no free, live-fetchable per-stock data for this period. Show this scenario with a clear "SENSEX index approximation, not live per-stock data" label, or omit it from v1. |

> ⚠️ Engineering note: verify exact index/price-level figures against your own ingested bhavcopy data before displaying any specific numbers in the UI — the date ranges above are directionally correct but should be confirmed against real ingested data, not hardcoded from memory.

**Results page:** equity curve overlaid on a "buy & hold" benchmark line, a trade log table (entry/exit date, price, P&L, holding days), and a stats card row: Total Return %, CAGR, Max Drawdown, Sharpe Ratio, Win Rate, Total Trades. All computed by `vectorbt`/`quantstats` — again, pure math, no LLM.

**One more Gemini touch (optional, cheap):** after the backtest runs, one short LLM call to turn the stats table into 2–3 plain-English sentences ("This strategy would have returned 34% over the period, but with a maximum drawdown of 22% — meaning you'd have needed to stomach a significant paper loss before it recovered.") Cache this per unique strategy+date-range combination so repeat views cost zero additional calls.

📁 **Suggested Skill:** `.antigravity/skills/backtest-engine/SKILL.md` — the vectorbt patterns, the strategy JSON schema, and the indicator vocabulary, so the agent doesn't reinvent this each session.

### 3.4 Trading Behavior Analyzer — the differentiator feature

**Input:** user uploads a CSV of their trade history (support common broker export formats — Zerodha Console, Groww, Upstox — plus a generic template) or enters trades manually. Minimum required columns: ticker, buy date, buy price, sell date, sell price, quantity.

**Computed metrics (all pure statistics — this entire feature needs zero LLM calls to compute, only to narrate):**

| Metric | What it measures | How it's computed |
|---|---|---|
| **Disposition Effect Score** | Do you sell winners too early and hold losers too long? | Compare average holding period of winning trades vs. losing trades (classic Odean-style PGR/PLR: proportion of gains realized vs. proportion of losses realized). A score skewed toward "holds losers 2-3x longer than winners" is flagged. |
| **Loss Aversion Ratio** | Average loss size vs. average gain size | `avg_loss_pct / avg_gain_pct` — a ratio > 1 means your losses are bigger than your wins on average, which forces you to win more often than 50% just to break even |
| **Revenge Trading Indicator** | Do you trade more/bigger right after a loss? | Flags trades opened within 24–48h of a losing exit, compares position size and frequency to your baseline |
| **Overtrading Score** | Trading frequency vs. a reasonable benchmark for your capital/strategy style | Trade count per week vs. portfolio turnover; flags abnormal spikes |
| **Position Sizing Consistency** | Are your bet sizes erratic or disciplined? | Coefficient of variation (std dev / mean) of position sizes across trades |
| **Win Rate vs. Expectancy** | Are you winning often but losing big, or losing often but winning big? | `(win_rate × avg_win) − (loss_rate × avg_loss)` — the real number that matters more than win rate alone |
| **Time-of-Day / Day-of-Week Pattern** | Do you make worse decisions at certain times? | Group P&L by hour/weekday, surface statistically significant patterns |
| **Sector/Stock Concentration** | Are you diversified or overexposed to one theme? | Herfindahl-Hirschman Index on position values by sector |

**Output UI:** a "Behavior Report Card" — a set of cards each showing one metric as a simple gauge/score, plus (this is the one place a short LLM call earns its keep) a narrated summary paragraph turning the raw numbers into advice a human would actually say to you: *"You tend to hold losing positions 2.4x longer than winning ones — a classic disposition effect pattern. Consider setting a hard stop-loss rule before entering a trade, rather than deciding in the moment."* One call per analysis run, cached against that user's trade-set hash so re-visiting the page doesn't re-spend quota.

📁 **Suggested Skill:** `.antigravity/skills/behavior-analytics/SKILL.md` — the exact formulas above, broker CSV format mappings, and the narration prompt template.

### 3.5 Screener

Screener.in-style query builder: users chain filter conditions (`P/E < 20 AND ROE > 15 AND Debt/Equity < 0.5 AND Market Cap > 5000cr`) with a simple visual AND/OR builder (dropdowns, not raw text — reduces error and doesn't need an LLM at all). Results in a sortable, exportable table. Save custom screens to your account. Ship 8–10 pre-built screens on launch: "Quality Compounders," "Deep Value," "High Dividend Yield," "Low Debt + High Growth," etc.

### 3.6 Watchlist & Alerts

Multiple named watchlists, drag-to-reorder, inline sparkline + day-change per row. Alerts: price crosses X, RSI crosses X, volume spike > Nx average — checked by a GitHub Actions cron every 15 min against cached data, delivered via email (free via Resend/Supabase's built-in email, 100/day free tier — plenty for a personal-scale alert system) since push notifications need a paid service at scale.

### 3.7 Extra Features (my additions — creative liberty, all free to build)

- **Sector Heatmap:** treemap of all NSE sectors sized by market cap, colored by day performance — a satisfying, glanceable homepage element (Recharts treemap or a custom SVG grid)
- **"Investor Score" gamification:** a light, optional score based on portfolio diversification, use of stop-losses (from behavior analyzer), and screener/watchlist engagement — turns research into a habit loop without being gimmicky
- **Shareable PDF/image company report card:** one-click export of the Snowflake + key stats as a shareable image (client-side canvas render, zero backend cost) — great for organic social sharing/growth
- **Strategy Leaderboard:** users can opt to publish a backtested strategy's results (not their live trades — no funds/personal data exposure) to a public leaderboard, ranked by risk-adjusted return — a low-cost viral/community loop
- **"Explain this term" hover-glossary:** every financial term site-wide is a dotted-underline hover trigger with a 1-sentence plain-English definition — pure content, zero API cost, but a huge trust/accessibility signal (this is one of simplywall.st's best UX ideas and costs nothing to replicate)

### 3.8 The "Pseudo-Brain" — AI Research Digest (reads filings, concalls, announcements & news, draws conclusions)

This is the feature none of the three reference sites do well today, and the one place in the whole product where an LLM's actual *reasoning* — not just formatting/translation — earns its keep. It has to be built with the same discipline as everything in §6, or it becomes exactly the "sloppy answers" risk you flagged: an LLM confidently misreading a balance sheet is worse than not having the feature at all.

**The one rule that makes this trustworthy: numbers never come from the LLM.** Every hard figure shown anywhere in the product (revenue, margins, debt, ratios) comes from the structured `fundamentals_cache`/`price_cache` you already built in §2, scraped and parsed by code. The LLM is only ever pointed at the *qualitative* material — text that has no structured alternative — and only ever asked to summarize/tag it, never to compute or restate a number from a document. This single boundary is what separates "AI research assistant" from "AI hallucination machine."

**Three data streams, three different levels of automation (be honest about which is which):**

| Stream | Source | Automation feasibility on a free tier |
|---|---|---|
| **Corporate announcements & insider trading** | NSE's public corporate-filings pages via `nse` (circulars) and `pnsea` (insider trading) (§2.1) | ✅ **Fully automatable.** Structured, free, official, poll-able every 15–30 min. |
| **News** | Free RSS feeds (Moneycontrol, ET Markets, Business Standard) | ✅ **Fully automatable.** Standard RSS parsing, no scraping fragility. |
| **Concall transcripts & annual report commentary (MD&A, notes)** | Company investor-relations pages (format varies wildly: PDF, HTML, sometimes not published at all) | ⚠️ **Not centrally/freely available in bulk.** There is no single free API that hands you every NSE company's concall transcript. Be upfront about this rather than promising blanket coverage. |

**Scoping decision (the honest one):** ship automated announcement + news coverage for the *entire* NSE universe from day one — that part is genuinely free and scalable. Scope concall/annual-report ingestion to a curated list you actively maintain (start with Nifty 50 or Nifty 200 — companies whose IR pages are more consistently formatted and where transcripts are more reliably published), and grow that list manually/semi-manually over time. A company outside that list simply shows "Concall digest not yet available for this company" instead of a broken or fabricated summary — same graceful-degradation principle as §6.3.

**Pipeline:**

```
[Trigger: new filing detected via 15-30min announcement poll, OR quarterly — new concall
 transcript manually/semi-automatically added for a covered company]
        ↓
[Rule-based triage — no LLM yet]: classify the announcement by keyword against a fixed
 category list (results, board meeting, credit rating change, auditor resignation,
 related-party transaction, litigation, pledge change, key personnel change, ...).
 Low-signal categories (routine board meeting notices, etc.) stop here — logged but not
 summarized. This alone answers "what changed" for ~80% of filings with zero AI cost.
        ↓
[High-signal announcements + concall transcripts] → chunked if long → ONE batched Gemini
 Flash call per document, structured-output mode, extracting:
   - a 1-2 sentence plain-English summary
   - category tag (from the same fixed list used in triage, so the LLM is tagging within
     a closed vocabulary, not inventing categories)
   - a sentiment/tone flag for concalls specifically (confident / cautious / mixed) —
     framed as "how management sounded," never as investment advice
   - any of a fixed list of red-flag patterns it noticed (e.g. "guidance walked back
     from last quarter," "auditor change mentioned," "litigation disclosed") — again,
     tags from a closed vocabulary, not freeform claims
        ↓
[Validation layer] → tag must be in the allowed set, summary length-capped; reject and
 fall back to "see original filing" (a plain link) if it fails
        ↓
[Stored permanently against (company, document) — never re-processed]
```

**Output UI — "AI Research Notes" card on the company page:**
- **Recent Announcements** (chronological, plain-English one-liners, color-coded by category, each linking to the original filing — nothing here is ever shown without a link back to the source document)
- **Concall Digest** (covered companies only): last quarter's management tone read, 3–5 key points raised, guidance given, notable Q&A themes
- **Quality/Red Flags panel:** a merged view combining (a) the purely rule-based structured-data checks you already have in item 9 of §3.1 (debt, pledge, interest coverage — no LLM needed) with (b) any document-derived flags from the pipeline above, clearly visually distinguished so the user always knows which flags are "computed from numbers" vs. "an AI noticed this phrase in a filing" — never blur the two together, since they carry very different confidence levels
- Every AI-derived line carries a small "AI-summarized from [source] — read original" tag. Never present a synthesized conclusion as if it were a verified fact with no lineage.

**Cost control:** identical discipline to §6 — one call per document, cached forever by document hash, batch-processed off a queue (not per page-view), with the same one-retry-then-link-to-source fallback. A quiet week of filings costs you a handful of Flash calls; a earnings-season week costs more but is still bounded by "number of new documents," never by "number of page views," which is what actually protects your quota.

📁 **Suggested Skill:** `.antigravity/skills/ai-research-digest/SKILL.md` — the announcement category vocabulary, the triage keyword rules, the document-chunking approach for long transcripts, and the exact separation-of-concerns rule (numbers from code, narrative from documents) so it's never accidentally violated in a later session.

---

## 4. Database Schema (Postgres via Supabase)

```
users                  (id, email, created_at, ...)  -- via Supabase Auth
watchlists              (id, user_id, name, created_at)
watchlist_items         (id, watchlist_id, ticker, added_at)
companies                (ticker PK, name, sector, industry, isin)
price_cache              (ticker, date, open, high, low, close, volume)  -- daily bars
intraday_cache           (ticker, timestamp, price)  -- 60s TTL, Redis primarily, Postgres as durable fallback
fundamentals_cache       (ticker, as_of_date, pe, pb, roe, roce, debt_equity, div_yield, ...)
snowflake_scores         (ticker, as_of_date, value_score, future_score, past_score, health_score, dividend_score)
pros_cons_flags          (ticker, as_of_date, flag_type ['pro'|'con'], text, rule_id)  -- rule-based, no LLM
saved_screens            (id, user_id, name, filter_json)
strategies               (id, user_id, name, strategy_json, created_at)
backtest_results         (id, strategy_id, date_range, stats_json, equity_curve_json, is_public)
trade_uploads            (id, user_id, uploaded_at, source_broker)
trades                   (id, upload_id, ticker, buy_date, buy_price, sell_date, sell_price, qty)
behavior_reports         (id, upload_id, metrics_json, narrative_text, generated_at)
alerts                   (id, user_id, ticker, condition_type, threshold, active, last_triggered_at)
insider_transactions     (ticker, disclosure_date, person_name, role, transaction_type, quantity, value, source_url)
documents                (id, ticker, doc_type ['announcement'|'concall'|'annual_report'], title, source_url, published_at, raw_text_hash)
ai_research_notes        (id, document_id, ticker, summary_text, category_tag, sentiment_tag, red_flag_tags[], generated_at)
```

## 5. Core API Endpoints (FastAPI)

```
GET  /api/companies/{ticker}                 → full company profile + snowflake scores
GET  /api/companies/{ticker}/chart?interval=  → OHLCV + computed indicators
GET  /api/companies/{ticker}/peers            → sector peer comparison
GET  /api/companies/{ticker}/pros-cons        → rule-based pros/cons flags
GET  /api/companies/{ticker}/insider-activity → insider & bulk/block deal feed
GET  /api/companies/{ticker}/documents        → filings/concalls/announcements list
GET  /api/companies/{ticker}/research-notes   → AI Research Digest (§3.8), or "not yet available"
GET  /api/screener?filters=...                → filtered company list
POST /api/strategies/parse                    → { text } → Strategy JSON (the one Gemini call)
POST /api/backtest                            → { strategy_json } → results (deterministic, cached by hash)
POST /api/behavior/upload                     → CSV → parsed trades
POST /api/behavior/analyze                    → { upload_id } → metrics + narrative
GET  /api/watchlist / POST /api/watchlist/item
POST /api/alerts
```

Every `GET` on company/chart/screener data reads Redis-first with a Postgres fallback and a `stale-while-revalidate` pattern — never blocks on an external API call during a user request.

---

## 6. AI Reliability & Budget Doctrine

This is the single most important non-obvious engineering decision in this whole spec. The governing rule, stated plainly: **AI is a garnish on a dish that's already complete without it.** Nothing in this product should require a successful LLM call to produce a correct result — at worst, a failed/flaky call should make something slightly less eloquently worded, never wrong, broken, or blank.

### 6.1 Where an LLM call is allowed
1. **Strategy NL → JSON parsing** (§3.3) — one call per new strategy text, cached forever by exact-text hash, output always routed back through the Guided Builder + validator before anything executes (never auto-runs)
2. **Backtest result narration** (§3.3) — one call per unique strategy+date-range, cached forever, sits *alongside* the already-complete numeric stats table (never replaces it)
3. **Behavior report narration** (§3.4) — one call per unique trade-upload hash, cached forever, sits alongside the already-complete metrics cards
4. **AI Research Digest document synthesis** (§3.8) — one call per new high-signal announcement/concall document, cached forever by document hash, triggered off a filing/document queue rather than a page view, and strictly limited to summarizing/tagging text — never restating or computing a financial figure (those always come from structured data)
5. *(Optional, batch-only)* weekly company "what we found" blurb regeneration — run as a single batched GitHub Actions job across all cached companies overnight, never per page-load

### 6.2 Where an LLM call is banned
- Anything computable with `pandas`/`pandas-ta`/`vectorbt` (indicators, backtests, stats) — **always code, never LLM**
- The "What we found" narrative bullets on the company page (§3.1) — templated from threshold rules (`if pe < sector_median_pe * 0.8: "trading below its sector average valuation"`), not generated live
- Any per-page-load, per-user-session repeated content
- Executing anything the LLM outputs directly — it only ever produces *parameters* into a schema you validate, never code, never a final answer shown unverified
- **Extracting or restating any financial figure from a document (§3.8).** If a number is needed, it comes from `fundamentals_cache`/`price_cache`, full stop — the LLM only ever summarizes/tags qualitative text, never reads a number off a PDF and reports it as fact

### 6.3 The reliability rules for every LLM call in the product
1. **Structured output, not freeform text.** Use Gemini's native JSON-schema/function-calling response mode for every call in this product. This alone eliminates the most common source of "sloppy" LLM output — a model going conversational when you needed a clean object back.
2. **Validate before use, every time.** Every LLM response is checked against a strict schema (types, enums, ranges) before touching anything downstream. A response that fails validation is treated exactly like a failed API call — see the fallback below — never partially trusted.
3. **One retry, then fall back — never hang, never loop.** If a call errors, times out, or fails validation: retry once with a slightly stricter prompt; if that also fails, fall back immediately (rule-based parser, template narration, or an empty editable form, per feature). The user should never wait more than ~3–4 seconds wondering if something's happening.
4. **The fallback path is a first-class feature, not an afterthought.** The rule-based keyword parser for strategies and the templated narration for behavior reports need to be built and tested as carefully as the LLM path, because on a free quota they *will* get exercised regularly — not just in theory.
5. **Never let a stuck/slow Gemini call block a page render.** All narration calls are async, fire-and-forget-with-a-loading-skeleton — the numeric results (which are the actually important, always-correct part) render immediately regardless of whether the narration has arrived yet.

Net effect: on a good day, the product feels a bit smarter and more conversational. On a bad day (quota exhausted, model having an off moment), it's still 100% functionally correct — same numbers, same working backtester, same working behavior analysis — just slightly plainer prose. That's the ceiling of "headache" this architecture allows an LLM to cause you.

---

## 7. Security & Auth

- Supabase Auth (email/password + Google OAuth), JWT-based sessions
- Row-Level Security policies on all user-owned tables (`watchlists`, `trades`, `strategies`) — a user can only ever read/write their own rows, enforced at the DB level, not just in application code
- Trade upload CSVs: never store raw broker credentials — file upload only, no broker API linking in v1 (that's a bigger, riskier scope for a later version)
- Rate-limit your own public endpoints (simple in-memory or Redis token bucket) to protect against someone hammering your free-tier backend and burning your Render/Supabase quota

---

## 8. Design System (for the frontend agent to implement literally)

```
Primary background:    #0B1210  (near-black, warm dark green undertone)
Surface/card:           #131B18
Primary accent:         #1E7A4C  (deep forest green — brand color, primary CTAs, positive states)
Secondary accent:       #C9A227  (muted gold — used sparingly for "featured"/premium-feeling elements)
Positive (price up):    #2ECC71
Negative (price down):  #E74C3C
Neutral text:           #E6EDEA
Muted text:             #8FA096
Border:                 #223028

Font — headings/numbers: 'Sora', sans-serif (600/700 weight)
Font — body/UI:          'Inter', sans-serif (400/500 weight)

Card style: 12px radius, 1px solid border (#223028), no heavy drop shadow — flat, confident, data-forward
Spacing scale: 4/8/12/16/24/32/48px
```

Keep the whole product dark-mode-first (a light theme is a nice-to-have for v2, not v1) — it reads as "serious analysis tool" rather than "consumer app," matching the simplywall.st/Tijori aesthetic register.

---

## 9. Deployment Notes (free-tier survival guide)

- **Render/Fly.io free web services sleep after ~15 min of inactivity** and take 30–50s to cold-start. Mitigate with: (a) a GitHub Actions cron hitting a `/health` endpoint every 10 min to keep it warm during expected usage hours, and (b) a "waking up the engine..." loading state on the frontend for the rare cold hit.
- **Supabase free tier pauses a project after 7 days of no activity.** The same keep-alive cron above (a trivial `SELECT 1`) prevents this.
- **Vercel free tier** is generous for a Next.js frontend and needs no special handling.
- Keep all secrets (Gemini API key, Supabase service key) in environment variables / Vercel & Render's secret managers — never in the repo.

---

## 10. Phased Build Plan (execute in order)

### Phase 0 — Foundation
- [ ] Initialize monorepo: `/frontend` (Next.js), `/backend` (FastAPI), `/scripts` (GitHub Actions data jobs)
- [ ] Set up Supabase project, run initial schema migration (§4)
- [ ] Set up Upstash Redis, wire a basic cache-read/write utility in the backend
- [ ] Deploy a "hello world" of each service (Vercel + Render) to confirm the full pipeline works end to end
- [ ] **Acceptance:** a deployed frontend can call a deployed backend endpoint that reads/writes both Postgres and Redis

### Phase 1 — Data Pipeline + Company Dashboard (MVP)
- [ ] Build the `nsepython`/`yfinance` ingestion script, write to `price_cache`/`fundamentals_cache`
- [ ] Set up the GitHub Actions nightly cron for EOD refresh
- [ ] Build `/api/companies/{ticker}` endpoint
- [ ] Compute and store Snowflake scores (§3.1) — start with a simple, documented scoring rubric per axis; refine later
- [ ] Build the `/stock/[ticker]` frontend page per the layout in §3.1
- [ ] **Acceptance:** searching any NSE-listed large-cap ticker returns a fully populated, fast-loading company page with a working Snowflake

### Phase 2 — Charts & Technical Analysis
- [ ] `pandas-ta` indicator computation pipeline, stored alongside cached OHLCV
- [ ] `lightweight-charts` integration with interval switching and overlay/sub-panel toggles
- [ ] **Acceptance:** chart renders in under 1s for cached tickers, toggling indicators is instant (no re-fetch)

### Phase 3 — Screener + Watchlist + Alerts
- [ ] Build filter query engine against `fundamentals_cache`
- [ ] Screener UI (visual filter builder) + 8–10 preset screens
- [ ] Watchlist CRUD + UI
- [ ] Alerts cron job + email delivery
- [ ] **Acceptance:** a saved screen returns results in under 500ms; a triggered alert emails the user within 15 min

### Phase 4 — Strategy Backtester (Guided Builder first, NL layer second)
- [ ] Define and lock the Strategy JSON schema (§3.3)
- [ ] Build the `vectorbt` backtest engine for the supported indicator vocabulary
- [ ] Build the lazy-fetch-and-cache-forever historical data path (§2.4) — on a cache miss for a requested ticker+range, fetch just that gap from the NSE bhavcopy archive and persist it
- [ ] Build the Guided Builder UI (dropdowns for indicator/condition/value/exit/stop-loss/date-range) — ship and test this as a fully working, zero-AI feature first
- [ ] Build the scenario preset picker using the corrected table in §3.3 (only offer per-stock backtests for scenarios that are actually live-fetchable; gate or clearly label the Harshad Mehta preset as index-level only)
- [ ] **Acceptance (v1, no AI required):** a user can build a strategy entirely via dropdowns and get a real, correct backtest result on any live-fetchable historical range
- [ ] Add the Gemini Flash NL-parsing layer on top (structured output + validation + one retry + fallback to an empty editable Guided Builder, per §6.3)
- [ ] **Acceptance (v1.1, AI layer):** a user can type "buy when RSI below 30, sell above 70, test on TCS during the COVID crash," see it correctly pre-fill the Guided Builder, and run the same engine from there

### Phase 5 — Behavior Analyzer
- [ ] CSV upload + broker-format parsers (start with a generic template, add Zerodha/Groww mappings)
- [ ] Implement all metrics in §3.4 as pure Python functions with unit tests (these formulas must be correct — test against hand-calculated examples)
- [ ] Narration LLM call + caching
- [ ] Behavior Report Card UI
- [ ] **Acceptance:** uploading a sample trade CSV produces correct, sensible metrics and a coherent narrative

### Phase 6 — The Pseudo-Brain: AI Research Digest
- [ ] Wire up `nse` (circulars) + `pnsea` (insider trading) for corporate announcements + insider trading, polling every 15–30 min, diffed against what's already stored
- [ ] Build the rule-based triage classifier (keyword → category vocabulary) — this alone should ship and be useful before any LLM call is added
- [ ] Build the Pros/Cons flag engine and business segment breakdown (§3.1, items 9–10) — pure structured-data, no LLM
- [ ] Add the Gemini Flash document-synthesis call (structured output, validated, cached by document hash) for high-signal announcements
- [ ] **Acceptance (v1, no concalls yet):** every NSE company shows real, live announcement and insider-activity feeds, with rule-based Pros/Cons and AI-summarized high-signal filings
- [ ] Manually/semi-manually source concall transcripts for a starting cohort (Nifty 50) and run the same synthesis pipeline against them
- [ ] Build the "AI Research Notes" card UI, clearly distinguishing rule-based flags from AI-derived ones, every AI line linking back to its source document
- [ ] **Acceptance (v1.1, concalls):** covered companies show a concall digest with tone/key-points/guidance, and the "not yet available" state is graceful for everyone else

### Phase 7 — Extra Features & Polish
- [ ] Sector heatmap, Investor Score, shareable report card export, strategy leaderboard, hover-glossary, interactive DCF/Narrative calculator (§3.1)
- [ ] Full responsive/mobile pass
- [ ] Loading skeletons, error states, empty states everywhere (nothing should ever show a raw error or blank white screen)
- [ ] **Acceptance:** product feels finished, not just functional — this phase is where "attractive" actually happens

### Phase 8 — Launch Readiness
- [ ] Keep-alive cron jobs live (§9)
- [ ] Basic analytics (privacy-respecting, e.g. Plausible free tier or self-hosted)
- [ ] README + this spec committed to the repo for future reference

---

## 11. Free Resource Reference List

- Data: `yfinance` (pypi), `nsepython`/`jugaad-data` (pypi, OHLCV/bhavcopy), NSE bhavcopy archives, `nse` (bennythadikaran/NseIndiaApi — circulars/announcements, IPOs, bhavcopy), `pnsea` (pypi — insider trading/SAST disclosures, options chain)
- Backend: FastAPI, `pandas-ta`, `vectorbt`, `quantstats`
- Infra: Supabase (DB+Auth), Upstash (Redis), Vercel (frontend hosting), Render/Fly.io (backend hosting), GitHub Actions (cron/compute)
- LLM: Google AI Studio free-tier API key (Gemini Flash family)
- Charts: TradingView `lightweight-charts`, Recharts
- Email: Resend or Supabase's built-in email (free tier, alert delivery)
