# Nivesh â€” Indian equity research

A personal research workspace for company analysis, financial comparisons, transparent strategy backtesting and trade-journal statistics.

- Search NSE/BSE companies and inspect dated quotes, annual/quarterly statements, ratios and industry peers.
- Use a disclosed fundamental checklist, cash flow scenarios and input-backed financial screens.
- Save browser-owned watchlists and price/RSI/volume conditions in SQLite.
- Keep research notes and export tables, research snapshots and strategies.
- Backtest RSI, SMA/EMA crossover, MACD and Bollinger rules with next-open execution, costs and explicit assumptions.
- Import closed trades or match execution exports using validated FIFO; inspect excluded rows before analysis.

**Data availability is explicit.** Unknown promoter/pledge histories, filing feeds and supplier relationships are not fabricated. The screener covers a bundled universe, not every NSE listing. Yahoo Finance data may be delayed or incomplete. Public accounts, cross-device sync, background notifications and community publishing are not enabled.

The **Research workflow** tab discovers issuer documents from live NSE feeds and public company investor pages, reads bounded PDF/ZIP reports, and exposes page-linked business, supply-chain, competition, demand, accounting and risk evidence. **Supply chain** is generated from those documents, without a predefined company map. Collection works for resolved issuers outside the bundled screener; completeness depends on public source availability. The workspace adds editable operating scenarios, a hypothesis notebook and evidence-pack export.

**AI deep dive** interprets collected filings, structured provider financials and optional pasted evidence in twelve research sections, with source quotation checks and open questions. Generation requires a server-side `GEMINI_API_KEY` (or `GEMINI_API_KEYS`) in `backend/.env`; restart after setting it. `GEMINI_MODEL` defaults to `gemini-2.5-flash`. For multiple keys use `GEMINI_API_KEYS=key_one,key_two`; optionally set `GEMINI_KEY_PROJECTS=project_a,project_b` in matching order. Keys from the same actual project must share a label and share quota cooldowns. Without labels all keys share one cooldown group. Requests try at most three keys, with fallback for credential rejection or an available different project after quota exhaustion; network/server/request errors are not automatically replayed. Collection, deterministic extraction and calculations work without a key. AI interpretations require review. Price charts include moving averages, Bollinger bands and synchronized RSI.

The reusable analyst skill is [.agents/skills/equity-research/SKILL.md](.agents/skills/equity-research/SKILL.md). Its collector script uses the same services as the app:

```powershell
python .agents/skills/equity-research/scripts/research_company.py RENTOMOJO.NS --output output/research/RENTOMOJO.json
```

This example is not a company-specific adapter; pass another resolved symbol or an official report with `--source-url`. See [PROJECT_GUIDE.md](PROJECT_GUIDE.md) for collection limits, architecture, source handling and implemented versus proposed analysis.

Collection also gathers official PIB/RBI policy and macro leads. Add an official HTML source with `--context-url`; government/industry context remains separate from company disclosures and its impact requires review. The workflow shows missing evidence, failed sources and a **Run data & evidence checks** button. AI factual text must match its cited quotes; qualitative hypotheses are displayed separately and remain unverified.

Run a repeatable data audit, including re-downloaded original PDF quotations:

```powershell
python .agents/skills/equity-research/scripts/audit_research.py RENTOMOJO.NS --verify-originals --output output/research/RENTOMOJO-audit.json
```

Use `--pack output/research/RENTOMOJO.json` for an offline pack audit. Audits check units, periods and citations; they do not certify an investment thesis. The collector exits unsuccessfully when it collects no readable issuer documents, and supports `--timeout` for bounded waiting.

See [PROJECT_GUIDE.md](PROJECT_GUIDE.md) for the architecture, choices, request/data flows, calculation contracts, source references and deployment tradeoffs. See [VALIDATION.md](VALIDATION.md) for checks performed.

## Run locally

The independent [three-company comparison](research/RESEARCH_COMPARISON.md) documents the Gem Aromatics, Sambhv and Hy-Tech findings. The workflow now cross-checks explicit issuer income tables against provider inputs, preserves standalone/consolidated bases and original units, and offers a same-table annual baseline selector. Named counterparty lists/tables, company business HTML, transcripts and industry-specific diligence questions are supported. Ambiguous data remains a review gap.

Requires Python 3.11+ and Node.js 20.9+; CI uses Node 22. No cloud account or AI key is required.

From the repository root in PowerShell:

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -r backend/requirements.txt
    npm ci --prefix frontend

Start the API in the first terminal with the virtual environment active:

    cd backend
    python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

Start the interface from the root in another terminal:

    npm run dev:frontend

Open [Nivesh locally](http://localhost:3000). API documentation is at [FastAPI docs](http://127.0.0.1:8000/docs).

The interface proxies /api to the backend by default. Leave NEXT_PUBLIC_API_URL unset for same-origin workspace cookies. Optional settings are documented in [backend/.env.example](backend/.env.example), [frontend/.env.example](frontend/.env.example) and the project guide.

SQLite and the generated signing secret are created automatically in ignored backend/data/. Keep that directory on durable storage to preserve watchlists across restarts. Notes and saved strategy parameters remain in the browser. Clearing cookies loses workspace access; there is no account recovery.

## Checks

    python backend/test_backend.py
    npm run typecheck --prefix frontend
    npm run build --prefix frontend

Optional Python tooling:

    python -m pip install -r backend/requirements-dev.txt
    ruff check backend
    ruff format --check backend

The regression suite uses controlled data and temporary storage. Live coverage is checked separately. A successful HTTP response alone does not certify financial correctness.

For a production build, use npm run build --prefix frontend followed by npm run start --prefix frontend, and run the API without --reload. Hosted use needs durable storage, HTTPS, a stable signing secret and appropriate access controls. This is a personal browser workspace, not a hosted account service.


**Developments & pending projects:** open a company's Research workflow tab to browse supported disclosures, distinguish unread headlines from collected excerpts and review potential future milestones. Track a sourced bid, approval or expansion in a private browser-workspace ledger; add observations without replacing history and export your research. Expected dates have explicit source/estimate labels. Entries remain researcher-supplied and unverified. Broad news/rumour feeds, automatic tender-outcome matching and scheduled alerts are not connected. No additional API key is required. See [the monitoring specification](research/COMPANY_MONITORING_PLAN.md).


### Read and learn

Open `/news` for a free public-RSS reading desk (world/US/India, policy, commodities and world events), topic search and a saved reading list. Company pages include news and separate community discussion; X is search-link-only. Open `/learn` for the beginner stock-research path, terms, historical cases, strategy comparisons, deterministic practice lab and an exportable pitch worksheet. No additional API keys are required. See [PROJECT_GUIDE.md](PROJECT_GUIDE.md) and [the preparation plan](research/FINANCE_LEARNING_IMPLEMENTATION_PLAN.md) for architecture, sources and limits.


The personal daily news bot prepares a source-linked morning summary using the independent hosted runtime below. The earlier Codex/Gmail heartbeat is paused; its historical [bot protocol](research/DAILY_NEWS_BOT.md) is retained for reference. Local generated copies can appear in the news page; cloud reports do not automatically synchronise to that installation.


The independent hosted runtime is documented in [Daily Brief project guide](../daily-brief/PROJECT_GUIDE.md). GitHub Actions sends four daily Telegram news editions, plus a seven-day follow-up using fourteen-day sent-story memory. Separate headings/content teach a broad 42-lesson **Finance Class**, a source-grounded **Finance in context** case, and the 47-lesson **Stock Daddy** company-research track. A closing message suggests a learning task. Source links are clickable and technical notes stay out of the newsletter body. Code owns the curriculum, evidence limits, validation and delivery; Gemini can elaborate within supplied teaching notes and news evidence. Complete authored lessons work without AI. No Codex, local backend or awake laptop is required. Gmail remains an optional legacy adapter.

Finance Class now includes authored mechanism walkthroughs, three-step examples, misconceptions, application exercises with explained solutions, and one-day/seven-day recall across all 42 lessons. Gemini is optional; the full teaching remains available without it. See [the project guide](PROJECT_GUIDE.md) for architecture and validation.

Finance Class now uses textbook-length authored chapters targeting 15–20 minutes of reading, with separate practice. Chapters combine the main lesson, extended hypothetical cases and labelled reusable supporting readings; no extra Gemini calls are required.
