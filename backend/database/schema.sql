-- Nivesh Database Schema for Supabase Postgres

CREATE TABLE IF NOT EXISTS companies (
    ticker VARCHAR(20) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    sector VARCHAR(100),
    industry VARCHAR(100),
    isin VARCHAR(20),
    market_cap NUMERIC,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS price_cache (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(20) REFERENCES companies(ticker) ON DELETE CASCADE,
    date DATE NOT NULL,
    open NUMERIC NOT NULL,
    high NUMERIC NOT NULL,
    low NUMERIC NOT NULL,
    close NUMERIC NOT NULL,
    volume BIGINT NOT NULL,
    UNIQUE(ticker, date)
);

CREATE TABLE IF NOT EXISTS intraday_cache (
    ticker VARCHAR(20) PRIMARY KEY REFERENCES companies(ticker) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    price NUMERIC NOT NULL,
    day_change NUMERIC,
    day_change_pct NUMERIC
);

CREATE TABLE IF NOT EXISTS fundamentals_cache (
    ticker VARCHAR(20) PRIMARY KEY REFERENCES companies(ticker) ON DELETE CASCADE,
    as_of_date DATE NOT NULL,
    pe NUMERIC,
    pb NUMERIC,
    roe NUMERIC,
    roce NUMERIC,
    debt_equity NUMERIC,
    div_yield NUMERIC,
    revenue_growth_3yr NUMERIC,
    eps_growth_3yr NUMERIC,
    free_cash_flow NUMERIC,
    promoter_holding NUMERIC,
    pledged_shares_pct NUMERIC,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS snowflake_scores (
    ticker VARCHAR(20) PRIMARY KEY REFERENCES companies(ticker) ON DELETE CASCADE,
    as_of_date DATE NOT NULL,
    value_score INTEGER CHECK (value_score BETWEEN 0 AND 6),
    future_score INTEGER CHECK (future_score BETWEEN 0 AND 6),
    past_score INTEGER CHECK (past_score BETWEEN 0 AND 6),
    health_score INTEGER CHECK (health_score BETWEEN 0 AND 6),
    dividend_score INTEGER CHECK (dividend_score BETWEEN 0 AND 6),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pros_cons_flags (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(20) REFERENCES companies(ticker) ON DELETE CASCADE,
    as_of_date DATE NOT NULL,
    flag_type VARCHAR(10) CHECK (flag_type IN ('pro', 'con')),
    text TEXT NOT NULL,
    rule_id VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS watchlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS watchlist_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    watchlist_id UUID REFERENCES watchlists(id) ON DELETE CASCADE,
    ticker VARCHAR(20) REFERENCES companies(ticker) ON DELETE CASCADE,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(watchlist_id, ticker)
);

CREATE TABLE IF NOT EXISTS saved_screens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    filter_json JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    strategy_json JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS backtest_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID REFERENCES strategies(id) ON DELETE CASCADE,
    date_range JSONB NOT NULL,
    stats_json JSONB NOT NULL,
    equity_curve_json JSONB NOT NULL,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trade_uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source_broker VARCHAR(50) DEFAULT 'generic'
);

CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    upload_id UUID REFERENCES trade_uploads(id) ON DELETE CASCADE,
    ticker VARCHAR(20) NOT NULL,
    buy_date DATE NOT NULL,
    buy_price NUMERIC NOT NULL,
    sell_date DATE NOT NULL,
    sell_price NUMERIC NOT NULL,
    qty INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS behavior_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    upload_id UUID REFERENCES trade_uploads(id) ON DELETE CASCADE,
    metrics_json JSONB NOT NULL,
    narrative_text TEXT,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    ticker VARCHAR(20) REFERENCES companies(ticker) ON DELETE CASCADE,
    condition_type VARCHAR(50) NOT NULL,
    threshold NUMERIC NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    last_triggered_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS insider_transactions (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(20) REFERENCES companies(ticker) ON DELETE CASCADE,
    disclosure_date DATE NOT NULL,
    person_name VARCHAR(255) NOT NULL,
    role VARCHAR(100),
    transaction_type VARCHAR(50),
    quantity BIGINT,
    value NUMERIC,
    source_url TEXT
);

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(20) REFERENCES companies(ticker) ON DELETE CASCADE,
    doc_type VARCHAR(50) CHECK (doc_type IN ('announcement', 'concall', 'annual_report')),
    title TEXT NOT NULL,
    source_url TEXT,
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    raw_text_hash VARCHAR(64) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_research_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    ticker VARCHAR(20) REFERENCES companies(ticker) ON DELETE CASCADE,
    summary_text TEXT NOT NULL,
    category_tag VARCHAR(100) NOT NULL,
    sentiment_tag VARCHAR(20),
    red_flag_tags TEXT[],
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
