# Nivesh — NSE Equity Research, NL Backtester & Trading Psychology Platform

[![Next.js 14](https://img.shields.io/badge/Frontend-Next.js%2014-000000?style=flat&logo=nextdotjs)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%200.109-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat&logo=python)](https://python.org)
[![Gemini 3.6 Flash](https://img.shields.io/badge/LLM-Gemini%203.6%20Flash-4285F4?style=flat&logo=google)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Nivesh** is a ₹0-budget, institutional-grade web platform for Indian (NSE) equity markets combining **Simplywall.st-style 5-axis visual company analysis**, **natural-language strategy backtesting**, **trading behavior/psychology diagnostics**, and an **AI-powered Research Digest ("pseudo-brain")**.

---

## Key Features & Benchmark Parity

### 1. SimplyWall.st Parity
- **5-Axis Snowflake Radar:** Visual radar evaluating company strength across **Value**, **Future**, **Past**, **Health**, and **Dividend** (0–6 score scale).
- **"Why Does This Matter" Hover Glossary:** Site-wide 1-sentence plain-English tooltips for financial metrics (P/E, P/B, ROE, ROCE, Debt/Equity, Dividend Yield, RSI, MACD, Snowflake, Promoter Holding).
- **Interactive DCF Narrative Model:** Interactive Discounted Cash Flow valuation calculator with growth and discount rate sliders estimating intrinsic fair value per share.
- **Shareable Report Card Export:** Client-side HTML5 canvas snapshot generator for social media sharing.

### 2. Screener.in Parity
- **Multi-Metric Dynamic Stock Screener & 8 Presets:** Multi-metric filter query engine with 8 pre-built screens (*Quality Compounders*, *Deep Value*, *High Dividend Yield*, *Low Debt + High Growth*, *Zero Promoter Pledge*, *Sector Leaders*, *GARP*, *Cash Flow Kings*).
- **Automated Rule-Based Pros & Cons Flags:** Derived strictly from numerical debt, ROE, ROCE, P/E, and promoter holding thresholds with zero LLM involvement.
- **Peer Benchmarking Matrix & CSV Export:** Sector peer comparison matrix and 1-click CSV download.

### 3. Tijori Finance Parity
- **NSE Sector Performance Heatmap:** Treemap/grid visualization displaying all NSE sectors sized by market cap and color-coded by daily percentage performance.

### 4. Natural-Language Strategy Backtester (Headline Feature)
- **Pure Vectorized Python Math Engine:** Deterministic backtest simulation engine computing equity curves, trade logs, and risk statistics (Total Return %, CAGR, Max Drawdown %, Sharpe Ratio, Win Rate %, Total Trades). Zero licensing risk.
- **Guided Builder UI + Gemini Flash NL Sandbox:** Natural language prompt parser pre-filling visible form state before deterministic execution.
- **Historical Crisis Scenario Library:** COVID-19 Crash (2020), Global Financial Crisis (2008-09), 2016 Demonetization, Ketan Parekh Bust (2000-01), Adani-Hindenburg Episode (2023), and Harshad Mehta Scam (1992) (*Index-Level SENSEX Approximation*).

### 5. Trading Behavior Analyzer (Differentiator Feature)
- **Pure Statistics Psychology Engine:** Computes Disposition Effect Score (PGR/PLR holding ratio), Loss Aversion Ratio (`avg_loss / avg_gain`), Revenge Trading Indicator, and Position Sizing CV across Zerodha, Groww, and Generic CSV formats.
- **Behavior Report Card UI:** Interactive report card with metric score gauges, automated behavioral diagnostic flags, and AI-narrated advice.

### 6. Pseudo-Brain: AI Research Digest (§3.8)
- **Filing Triage & Concall Synthesis:** Rule-based corporate filing triage, management tone flags, red flag badges, and direct source document links (`source_url`).
- **Strict Data Honesty Rule:** *Numbers NEVER come from an LLM* — numbers always come from code (`fundamentals_cache`).

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| **Frontend** | **Next.js 14 (App Router) + TypeScript + Tailwind CSS** | Server Components, fast hydration, dark-mode first |
| **Charting** | **TradingView Lightweight-Charts** & **Recharts** | Lightweight-charts for OHLCV; Recharts for Snowflake radar |
| **Backend / API** | **Python 3.11+ FastAPI** | High-performance async API server with pandas/numpy math |
| **Backtesting Engine** | **Pure pandas/numpy** | Vectorized math you own outright with 0 Commons Clause licensing risk |
| **Database** | **Supabase Postgres (Free Tier)** | Free Postgres with Row-Level Security |
| **Cache Shield** | **Upstash Redis (Free Tier)** | 60s intraday TTL & EOD price caching shield |
| **LLM** | **Gemini 3.6 Flash (Google AI Studio)** | JSON-schema structured output for strategy parsing & qualitative summaries |

---

## Architecture Diagram

```
                       [ User / Browser ]
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
[ Next.js 14 Frontend App Router ]      [ FastAPI Python Backend ]
  - Snowflake Radar                       - Vectorized Backtest Engine
  - Lightweight-Charts                    - Screener Query Engine
  - Screener & Heatmap                    - Behavior Psychology Engine
  - Behavior Report Card                  - Gemini 3.6 Flash Parser
            │                                     │
            └──────────────────┬──────────────────┘
                               ▼
                [ Redis Cache & Supabase Postgres ]
```

---

## Quickstart Local Setup

### Prerequisites
- Node.js 18+ & npm
- Python 3.10+ & pip

### 1. Clone Repository
```bash
git clone https://github.com/DareDevil365/Nivesh.git
cd Nivesh
```

### 2. Backend Setup (FastAPI)
```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
pip install -r requirements.txt

# Start FastAPI dev server on http://localhost:8000
python -m uvicorn main:app --reload --port 8000
```

### 3. Frontend Setup (Next.js 14)
```bash
cd ../frontend
npm install

# Start Next.js dev server on http://localhost:3000
npm run dev
```

Open **http://localhost:3000** to launch Nivesh!

---

## Core API Surface

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/companies/{ticker}` | `GET` | Full company profile + 5-axis Snowflake scores |
| `/api/companies/{ticker}/chart` | `GET` | OHLCV price bars + SMA/EMA/RSI/MACD indicators |
| `/api/companies/{ticker}/peers` | `GET` | Sector peer benchmark matrix |
| `/api/companies/{ticker}/pros-cons` | `GET` | Screener.in-style rule-based pros/cons flags |
| `/api/companies/{ticker}/insider-activity` | `GET` | Promoter & insider disclosures feed |
| `/api/companies/{ticker}/documents` | `GET` | Filings & announcements list |
| `/api/companies/{ticker}/research-notes` | `GET` | Pseudo-Brain AI Research Digest |
| `/api/screener` | `GET` | Multi-metric stock filter query engine |
| `/api/screener/presets` | `GET` | 8 pre-built screener presets |
| `/api/screener/sector-heatmap` | `GET` | Tijori-style sector market cap heatmap |
| `/api/strategies/parse` | `POST` | Plain-English prompt → Strategy JSON schema |
| `/api/backtest` | `POST` | Vectorized strategy backtest simulation |
| `/api/behavior/upload` | `POST` | Broker CSV trade log parser |
| `/api/behavior/analyze` | `POST` | Trading psychology metrics & narrated advice |
| `/api/watchlist` | `GET/POST` | User watchlists management |
| `/api/alerts` | `GET/POST` | Active indicator/price alert triggers |
| `/api/leaderboard` | `GET` | Community strategy leaderboard |
| `/api/keepalive` | `GET` | GitHub Actions keep-alive cron endpoint |

---

## Data Honesty & Disclosure
- **NSE Price Data:** Intraday quotes are polled with a 60s Redis TTL and marked with a `"Delayed ~15 min"` badge.
- **Historical Scenarios:** Stock-level backtesting is supported from Nov 1994 onward (NSE inception). Pre-1994 (Harshad Mehta 1992 scam) is rendered via an index-level SENSEX static approximation table.

---

## License
Distributed under the MIT License. See `LICENSE` for details.
