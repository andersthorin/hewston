-- Hewston Catalog Schema (SQLite)
-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Datasets: cached raw + derived slice per symbol/range
CREATE TABLE IF NOT EXISTS datasets (
  dataset_id            TEXT PRIMARY KEY,
  symbol                TEXT NOT NULL,
  from_date             TEXT NOT NULL, -- ISO date
  to_date               TEXT NOT NULL, -- ISO date
  products_json         TEXT NOT NULL, -- JSON array e.g. ["TRADES","TBBO"]
  calendar_version      TEXT NOT NULL,
  tz                    TEXT NOT NULL DEFAULT 'America/New_York',
  raw_dbn_json          TEXT NOT NULL, -- JSON array of file paths
  bars_parquet_json     TEXT NOT NULL, -- JSON array of file paths
  bars_manifest_path    TEXT NOT NULL,
  generated_at          TEXT NOT NULL, -- ISO datetime UTC
  size_bytes            INTEGER NOT NULL,
  status                TEXT NOT NULL CHECK (status IN ('READY','BUILDING','ERROR'))
);

CREATE INDEX IF NOT EXISTS idx_datasets_symbol_dates
  ON datasets(symbol, from_date, to_date);
CREATE INDEX IF NOT EXISTS idx_datasets_generated_at
  ON datasets(generated_at);

-- Runs: backtest executions referencing a dataset
CREATE TABLE IF NOT EXISTS runs (
  run_id                TEXT PRIMARY KEY,
  dataset_id            TEXT NOT NULL REFERENCES datasets(dataset_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  strategy_id           TEXT NOT NULL,
  params_json           TEXT NOT NULL, -- JSON object
  seed                  INTEGER NOT NULL,
  slippage_fees_json    TEXT NOT NULL, -- JSON object
  speed                 INTEGER NOT NULL DEFAULT 60,
  code_hash             TEXT NOT NULL,
  created_at            TEXT NOT NULL, -- ISO datetime UTC
  status                TEXT NOT NULL CHECK (status IN ('QUEUED','RUNNING','DONE','ERROR','CANCELLED')),
  duration_ms           INTEGER,
  metrics_path          TEXT,
  equity_path           TEXT,
  orders_path           TEXT,
  fills_path            TEXT,
  run_manifest_path     TEXT NOT NULL,
  input_hash            TEXT UNIQUE,   -- deterministic hash of inputs for idempotency
  idempotency_key       TEXT UNIQUE    -- optional client-provided key
);

CREATE INDEX IF NOT EXISTS idx_runs_dataset ON runs(dataset_id);
CREATE INDEX IF NOT EXISTS idx_runs_strategy_created ON runs(strategy_id, created_at);
CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at);

-- Run metrics: denormalized comparables for list/filter
CREATE TABLE IF NOT EXISTS run_metrics (
  run_id         TEXT PRIMARY KEY REFERENCES runs(run_id) ON UPDATE CASCADE ON DELETE CASCADE,
  total_return   REAL,
  cagr           REAL,
  max_drawdown   REAL,
  sharpe         REAL,
  sortino        REAL,
  hit_rate       REAL,
  avg_win        REAL,
  avg_loss       REAL,
  turnover       REAL,
  slippage_share REAL,
  fees_paid      REAL,
  computed_at    TEXT NOT NULL -- ISO datetime UTC
);

CREATE INDEX IF NOT EXISTS idx_metrics_sharpe ON run_metrics(sharpe);
CREATE INDEX IF NOT EXISTS idx_metrics_drawdown ON run_metrics(max_drawdown);

-- Convenience view for listing runs with symbol and date range
CREATE VIEW IF NOT EXISTS runs_list AS
SELECT r.run_id, r.created_at, r.strategy_id, r.status,
       d.symbol, d.from_date, d.to_date,
       r.duration_ms
FROM runs r
JOIN datasets d ON d.dataset_id = r.dataset_id;

