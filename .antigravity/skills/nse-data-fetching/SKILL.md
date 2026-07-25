---
name: nse-data-fetching
description: Best practices, anti-bot header management, fallback logic, and lazy-fetch caching patterns for fetching NSE India equity data.
---

# NSE Data Fetching & Caching Strategy

## Overview
Fetching equity data from NSE (National Stock Exchange of India) requires careful session handling, cookie initialization, rate-limit defense, and caching contracts to prevent bot blocks.

## Core Rules

1. **Never call NSE/Yahoo Finance directly during a user request.**
   - All user GET requests read Redis-first with Postgres durable fallback (<100ms response).
   - Only background crons or lazy cache-miss handlers touch external data sources.

2. **Session & Anti-Bot Cookie Rules (NSE Direct):**
   - Must perform an initial GET request to `https://www.nseindia.com` to capture `nsit` and `nseappid` cookies before calling JSON API endpoints.
   - Use standard browser User-Agent headers:
     `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36`
   - Set `Accept-Language: en-US,en;q=0.9` and `Referer: https://www.nseindia.com/`.

3. **Ticker Formatting:**
   - Always append `.NS` for NSE stocks when querying Yahoo Finance / yfinance (e.g. `RELIANCE.NS`, `TCS.NS`).
   - Strip `.NS` when querying direct NSE endpoints (e.g., `RELIANCE`, `TCS`).

4. **Lazy Historical Fetching:**
   - EOD price data (OHLCV) is immutable.
   - On backtest range request, check `price_cache`. If missing, fetch the specific missing date range from NSE bhavcopy archive, persist to Postgres permanently (`TTL = infinite`).

5. **Supported Scenarios & Historical Boundary:**
   - NSE Equity market began on **3 November 1994**.
   - Per-stock backtesting is valid for scenarios from Nov 1994 to present (Ketan Parekh 2000, GFC 2008, Demonetization 2016, COVID 2020, Adani-Hindenburg 2023).
   - Pre-1994 (e.g. Harshad Mehta 1992 scam) is **Index-level SENSEX static table only**, never per-stock backtest.
