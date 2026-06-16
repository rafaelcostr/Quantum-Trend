-- ATLAS QUANT — initial schema (auto-applied on first docker-compose up)

CREATE TABLE IF NOT EXISTS candles (
    id BIGSERIAL PRIMARY KEY,
    exchange VARCHAR(32) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    timeframe VARCHAR(8) NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION NOT NULL,
    UNIQUE (exchange, symbol, timeframe, ts)
);

CREATE INDEX IF NOT EXISTS idx_candles_lookup
    ON candles (exchange, symbol, timeframe, ts DESC);

CREATE TABLE IF NOT EXISTS journal (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    mode VARCHAR(16) NOT NULL,
    event VARCHAR(64) NOT NULL,
    symbol VARCHAR(32),
    payload JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_journal_ts ON journal (ts DESC);
CREATE INDEX IF NOT EXISTS idx_journal_mode ON journal (mode);

CREATE TABLE IF NOT EXISTS trades (
    id BIGSERIAL PRIMARY KEY,
    mode VARCHAR(16) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    side VARCHAR(8) NOT NULL,
    entry_ts TIMESTAMPTZ NOT NULL,
    entry_price DOUBLE PRECISION NOT NULL,
    exit_ts TIMESTAMPTZ,
    exit_price DOUBLE PRECISION,
    quantity DOUBLE PRECISION NOT NULL,
    stop_price DOUBLE PRECISION,
    target_price DOUBLE PRECISION,
    pnl DOUBLE PRECISION,
    pnl_pct DOUBLE PRECISION,
    fees DOUBLE PRECISION DEFAULT 0,
    strategy VARCHAR(64) NOT NULL,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_trades_mode_ts ON trades (mode, entry_ts DESC);
