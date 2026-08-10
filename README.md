# Nivesh — NSE Equity Research, NL Backtester & Trading Psychology Platform

[![Next.js 14](https://img.shields.io/badge/Frontend-Next.js%2014-000000?style=flat&logo=nextdotjs)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%200.109-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat&logo=python)](https://python.org)
[![Gemini 3.6 Flash](https://img.shields.io/badge/LLM-Gemini%203.6%20Flash-4285F4?style=flat&logo=google)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Nivesh** is a ₹0-budget, institutional-grade equity research and algorithmic analytics web platform engineered for Indian (NSE/BSE) equity markets. It combines **SimplyWall.st-style 5-axis Snowflake company analysis**, **Tijori Finance-style supply chain graphs & forensic risk scoring**, **Screener.in multi-metric filtering**, **natural-language strategy backtesting**, **trading behavior/psychology diagnostics**, and an **AI-powered Research Digest ("pseudo-brain")**.

---

## 🌟 Key Features & Platform Modules

### 1. SimplyWall.st Parity & Visual Analysis
- **5-Axis Snowflake Radar Score:** Visual radar evaluating company fundamentals across **Value**, **Future Growth**, **Past Performance**, **Financial Health**, and **Dividend Yield** (0–30 score bounded scale, mapped to 0–6 per pillar).
- **Interactive Technical Stock Charting:** Powered by **TradingView Lightweight-Charts** with interactive candle toggles, Volume bars, SMA (20, 50, 200), EMA (20, 50, 200), RSI (14), and MACD (12, 26, 9) indicators.
- **"Why Does This Matter" Hover Glossary:** Site-wide plain-English metric tooltips (P/E, P/B, ROE, ROCE, Debt/Equity, Dividend Yield, RSI, MACD, Snowflake, Promoter Holding).
- **Interactive DCF & Reverse DCF Valuation Models:** 
  - **DCF Model:** Discounted Cash Flow calculator with growth rate, discount rate, and terminal growth sliders estimating intrinsic fair value per share.
  - **Reverse DCF Model:** Calculates the market-implied growth rate currently priced into the stock.
- **Historical Valuation Bands:** Multi-year historical P/E and P/B valuation band charts with mean, ±1σ, and ±2σ standard deviation channels.
- **Shareable Report Card Export:** Client-side HTML5 canvas snapshot generator for social media sharing.

### 2. Forensic Accounting & Supply Chain Intelligence (Tijori Parity)
- **Beneish M-Score Earnings Manipulation Detector:** Evaluates 8 financial ratios (DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI, TATA) to flag potential revenue/earnings manipulation risks.
- **Altman Z-Score Bankruptcy Model:** Calculates credit risk and distress likelihood customized for manufacturing and non-manufacturing companies.
- **Red Flag Breakdown Cards:** Automated qualitative risk badges highlighting governance, auditor qualification, debt strain, or revenue manipulation indicators.
- **Supply Chain & Segment Dependency Graph:** Interactive SVG node network showing key suppliers, enterprise customers, sector competitors, and business segment revenue breakdown.
- **NSE Sector Performance Heatmap:** Treemap/grid visualization displaying all NSE sectors sized by market cap and color-coded by real-time daily percentage change.

### 3. Screener.in Parity & Financial Intelligence
- **Multi-Metric Dynamic Stock Screener & 8 Presets:** Query engine filtering stocks by P/E, P/B, ROE, ROCE, Debt/Equity, Market Cap, Sales Growth, Profit Growth, and Dividend Yield across 8 built-in screens (*Quality Compounders*, *Deep Value*, *High Dividend Yield*, *Low Debt + High Growth*, *Zero Promoter Pledge*, *Sector Leaders*, *GARP*, *Cash Flow Kings*).
- **Automated Rule-Based Pros & Cons Flags:** Derived strictly from numerical fundamental thresholds with zero LLM involvement.
- **Complete Financial Statements:** Standalone and Consolidated Profit & Loss Statement, Balance Sheet, and Cash Flow Statement tables spanning multi-year historical periods.
- **Quarterly Results Engine:** YoY and QoQ sales, net profit, and operating profit margin (OPM) breakdown tables.
- **Financial Ratio Trends:** Multi-year ratio history and trend visualizer for profitability, liquidity, leverage, and efficiency metrics.
- **Shareholding Trend Analyzer:** Category breakdown over time (Promoter, FII, DII, Public) with automated promoter pledging alerts.
- **Sector Peer Benchmarking Matrix & CSV Export:** Sector peer comparison matrix with 1-click CSV download.

### 4. Natural-Language Strategy Backtester (Headline Feature)
- **Pure Vectorized Python Math Engine:** Deterministic backtest simulation engine (`pandas`/`numpy`) computing equity curves, trade logs, and risk statistics (Total Return %, CAGR, Max Drawdown %, Sharpe Ratio, Win Rate %, Total Trades). Zero licensing risk.
- **Guided Builder UI + Gemini 3.6 Flash NL Sandbox:** Natural language prompt parser parsing strategy rules into structured JSON schemas to pre-fill visible form parameters before deterministic execution.
- **Historical Crisis Scenario Library:**
  - 1992 Harshad Mehta Scam (*Index-Level SENSEX Approximation*)
  - 2000 Tech/Ketan Parekh Bust
  - 2008 Global Financial Crisis (GFC)
  - 2016 Demonetization Shock
  - 2020 COVID-19 Crash
  - 2023 Adani-Hindenburg Episode

### 5. Trading Behavior Analyzer (Differentiator Feature)
- **Pure Statistics Psychology Engine:** Computes Disposition Effect Score (PGR/PLR holding ratio), Loss Aversion Ratio (`avg_loss / avg_gain`), Revenge Trading Indicator, and Position Sizing Coefficient of Variation (CV).
- **Multi-Broker CSV Parser:** Seamlessly ingests trade logs from Zerodha, Groww, and Generic CSV formats.
- **Behavior Report Card UI:** Interactive report card with metric score gauges, automated behavioral diagnostic flags, and AI-narrated psychological advice.

### 6. Pseudo-Brain: AI Research Digest
- **Filing Triage & Concall Synthesis:** Rule-based corporate filing triage, management tone flags, red flag badges, and direct source document links (`source_url`).
- **Strict Data Honesty Rule:** *Numbers NEVER come from an LLM* — numbers always come strictly from code (`fundamentals_cache`).

---

## 🛠️ Architecture & Technology Stack

```
                        [ User / Browser ]
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
[ Next.js 14 Frontend App Router ]      [ FastAPI Python Backend ]
  - Tailwind CSS + Lucide Icons           - Vectorized Backtest Engine
  - TradingView Lightweight-Charts        - Screener & Peer Query Engine
  - Recharts (Snowflake & Ratios)         - Behavior Psychology Engine
  - Interactive Supply Chain & DCF        - Gemini 3.6 Flash Parser
  - Behavior & Research Digest            - Cache Shield & NSE Master
            │                                     │
            └──────────────────┬──────────────────┘
                               ▼
                [ Redis Cache & Supabase Postgres ]
```

| Layer | Choice | Purpose |
|---|---|---|
| **Frontend Framework** | **Next.js 14 (App Router) + TypeScript** | React Server Components, fast client hydration, dark-mode styling |
| **Styling & UI** | **Tailwind CSS + Lucide React Icons** | Sleek institutional dark-theme aesthetics & micro-animations |
| **Technical Charting** | **TradingView Lightweight-Charts** | Smooth canvas-rendered candlestick charts with SMA/EMA/RSI/MACD |
| **Data Visualization** | **Recharts & Custom SVG** | Recharts for Snowflake radar & ratio trends; Custom SVG for Supply Chain |
| **Backend API** | **Python 3.11+ FastAPI** | Asynchronous API server handling calculations, analytics & feeds |
| **Data Engine** | **yfinance + NSE Stock Master** | Real-time NSE/BSE symbol resolution, live quote polling & financial feeds |
| **Math Engine** | **Pure pandas & numpy** | Vectorized financial models, backtesting simulation, and forensic scoring |
| **Cache Shield** | **Upstash Redis (Free Tier)** | 60s intraday TTL & EOD price caching shield |
| **Database** | **Supabase Postgres (Free Tier)** | Free Postgres with Row-Level Security for watchlists & saved strategies |
| **AI Parsing** | **Gemini 3.6 Flash (Google AI Studio)** | JSON-schema structured output for strategy parsing & qualitative summaries |

---

## 📁 Repository Directory Structure

```
Nivesh/
├── backend/
│   ├── main.py                       # FastAPI application entrypoint & middleware
│   ├── config.py                     # Environment variables & application settings
│   ├── test_backend.py               # Comprehensive 100% core API surface automated test runner
│   ├── routers/
│   │   ├── backtest.py               # Strategy parsing & vectorized backtest endpoints
│   │   ├── behavior.py               # Trade log parser & psychological diagnostic endpoints
│   │   ├── companies.py              # Financials, charts, ratios, forensic & supply chain endpoints
│   │   ├── research.py               # Pseudo-Brain AI research notes & concall digests
│   │   ├── screener.py               # Multi-metric screener query & sector heatmap endpoints
│   │   └── watchlist.py              # User watchlist & alert management endpoints
│   └── services/
│       ├── backtest_engine.py        # Vectorized strategy simulation & crisis scenario math engine
│       ├── behavior_engine.py        # Trading psychology metrics (Disposition, Loss Aversion)
│       ├── cache_manager.py          # Redis & in-memory cache shield for intraday feeds
│       ├── data_fetcher.py           # yfinance market data fetcher & financial statement extractor
│       ├── db_client.py              # Supabase Postgres database client
│       ├── forensic_engine.py        # Beneish M-Score & Altman Z-Score forensic calculations
│       ├── gemini_client.py          # Gemini 3.6 Flash structured schema parser
│       ├── indicators.py             # SMA, EMA, RSI, MACD technical indicator math
│       ├── nse_stock_master.py       # Live symbol resolution & NSE ticker alias mapping
│       ├── pseudo_brain.py           # Regulatory filing triage & research digest synthesizer
│       ├── screener_engine.py        # Dynamic stock filter & pros/cons rule evaluator
│       ├── snowflake_calculator.py   # 5-pillar fundamental Snowflake score calculator
│       ├── supply_chain.py           # Supplier, customer & segment network graph builder
│       └── valuation_bands.py        # Historical PE/PB valuation bands & standard deviations
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx            # Global layout with header, footer & navigation
    │   │   ├── page.tsx              # Home dashboard with trending stocks & quick tools
    │   │   ├── backtester/           # Natural language & guided backtester UI
    │   │   ├── behavior/             # Broker CSV upload & trading psychology report card
    │   │   ├── leaderboard/          # Community backtest strategy leaderboard
    │   │   ├── screener/             # Multi-metric stock screener & sector heatmap
    │   │   ├── stock/[ticker]/       # Institutional stock research workspace
    │   │   └── watchlist/            # Saved stock watchlists & price alerts
    │   ├── components/
    │   │   ├── DCFCalculator.tsx     # Interactive DCF valuation sliders
    │   │   ├── EquityCurveChart.tsx  # Backtest equity curve & drawdown chart
    │   │   ├── FinancialStatements.tsx # P&L, Balance Sheet, Cash Flow tables
    │   │   ├── ForensicRiskCard.tsx  # Beneish M-Score & Altman Z-Score cards
    │   │   ├── GrowthForecastChart.tsx # Financial statement growth projection charts
    │   │   ├── PeerComparison.tsx    # Sector peer matrix & CSV export
    │   │   ├── QuarterlyResults.tsx  # YoY & QoQ sales/profit breakdown
    │   │   ├── RatioTrends.tsx       # Multi-year ratio trend charts
    │   │   ├── ResearchDigestCard.tsx# Pseudo-Brain AI research notes & filing triage
    │   │   ├── ReverseDCFCard.tsx    # Reverse DCF implied growth calculator
    │   │   ├── SectorHeatmap.tsx     # Sector performance treemap/grid
    │   │   ├── ShareholdingChart.tsx # Shareholding pattern & promoter pledge visualizer
    │   │   ├── SnowflakeChart.tsx    # 5-axis fundamental radar chart
    │   │   ├── StockChart.tsx        # TradingView Lightweight-Charts with technical indicators
    │   │   ├── SupplyChainGraph.tsx  # Interactive SVG supply chain & segment graph
    │   │   └── ValuationBandsChart.tsx # Historical PE/PB valuation bands chart
    │   └── lib/
    │       └── api.ts                # Frontend API client library
    └── vercel.json                   # Vercel deployment configuration
```

---

## ⚡ Quickstart Local Setup

### Prerequisites
- **Node.js**: v18.0.0 or higher & `npm`
- **Python**: v3.10 or higher & `pip`

### 1. Clone Repository
```bash
git clone https://github.com/DareDevil365/Nivesh.git
cd Nivesh
```

### 2. Environment Configuration
Create a `.env` file in `backend/`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_anon_key_here
UPSTASH_REDIS_REST_URL=your_upstash_redis_url_here
UPSTASH_REDIS_REST_TOKEN=your_upstash_redis_token_here
```

### 3. Backend Setup (FastAPI)
```bash
cd backend
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

# Launch FastAPI development server on http://localhost:8000
python -m uvicorn main:app --reload --port 8000
```

### 4. Frontend Setup (Next.js 14)
```bash
cd ../frontend
npm install

# Launch Next.js development server on http://localhost:3000
npm run dev
```

Open **http://localhost:3000** in your browser to launch Nivesh!

---

## 🌐 Core API Surface Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/companies/{ticker}` | `GET` | Full company profile, fundamental metrics & 5-axis Snowflake scores |
| `/api/companies/{ticker}/chart` | `GET` | OHLCV price bars + SMA, EMA, RSI, MACD technical indicators |
| `/api/companies/{ticker}/peers` | `GET` | Sector peer benchmarking matrix & comparison metrics |
| `/api/companies/{ticker}/pros-cons` | `GET` | Rule-based financial pros and cons flags |
| `/api/companies/{ticker}/financials` | `GET` | Complete Standalone/Consolidated P&L, Balance Sheet & Cash Flow |
| `/api/companies/{ticker}/quarterly-results` | `GET` | Quarterly sales, operating margin (OPM) & profit breakdown |
| `/api/companies/{ticker}/ratios` | `GET` | Financial ratio history & multi-year trend visualizer data |
| `/api/companies/{ticker}/shareholding` | `GET` | Shareholding category breakdown over time & promoter pledge status |
| `/api/companies/{ticker}/forensic` | `GET` | Beneish M-Score & Altman Z-Score risk scoring breakdown |
| `/api/companies/{ticker}/supply-chain` | `GET` | Supplier, customer, competitor & segment dependency network |
| `/api/companies/{ticker}/valuation-bands` | `GET` | Historical P/E and P/B valuation band channels & standard deviations |
| `/api/companies/{ticker}/insider-activity` | `GET` | Promoter & insider trading disclosures feed |
| `/api/companies/{ticker}/documents` | `GET` | Corporate filings, announcements & annual report links |
| `/api/companies/{ticker}/research-notes` | `GET` | Pseudo-Brain AI Research Digest & filing triage notes |
| `/api/screener` | `GET` | Multi-metric stock filter query engine |
| `/api/screener/presets` | `GET` | 8 pre-built stock screener preset strategies |
| `/api/screener/sector-heatmap` | `GET` | Sector performance treemap/grid by market capitalization |
| `/api/strategies/parse` | `POST` | Converts natural language backtest prompts into structured JSON rules |
| `/api/backtest` | `POST` | Vectorized strategy backtest simulation & equity curve calculation |
| `/api/behavior/upload` | `POST` | Ingests and parses Zerodha, Groww & generic broker trade log CSVs |
| `/api/behavior/analyze` | `POST` | Computes Disposition Effect, Loss Aversion, Revenge Trading & advice |
| `/api/watchlist` | `GET/POST` | Manages user watchlists |
| `/api/alerts` | `GET/POST` | Active technical indicator & price alert triggers |
| `/api/leaderboard` | `GET` | Community backtest strategy leaderboard |
| `/api/keepalive` | `GET` | Health check & cron keep-alive endpoint |

---

## 🧪 Testing & Quality Assurance

### Automated Backend Test Suite
Run the 100% core API surface verification test suite:
```bash
cd backend
python test_backend.py
```

### Production Build Validation
Verify Next.js frontend compilation:
```bash
cd frontend
npm run build
```

---

## 📜 Data Honesty & Compliance

- **NSE Price Data:** Intraday quotes are cached with a 60s Redis TTL and marked with a `"Delayed ~15 min"` badge.
- **Historical Scenarios:** Stock-level backtesting is supported from Nov 1994 onward (NSE inception). Pre-1994 (Harshad Mehta 1992 scam) is rendered via an index-level SENSEX static approximation table.
- **Strict Data Integrity:** All numerical values, fundamental ratios, and backtest results are computed deterministically in code (`pandas`/`numpy`). LLMs are strictly limited to parsing strategy rules and generating qualitative summaries.

---

## 📄 License
Distributed under the MIT License. See `LICENSE` for details.
