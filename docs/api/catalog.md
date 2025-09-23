# Runs Catalog Overview (SQLite)

Status: v0.1 — Companion to scripts/catalog_init.sql. Explains tables, indices, and common queries.

## Purpose
Lightweight local catalog to index datasets and runs for listing, filtering, and retrieving artifacts. SQLite chosen for simplicity and determinism.

## Tables
- datasets
  - dataset_id (PK), symbol, from_date, to_date
  - products_json ["TRADES","TBBO"], calendar_version, tz
  - raw_dbn_json (paths), bars_parquet_json (paths), bars_manifest_path
  - generated_at (UTC), size_bytes, status (READY|BUILDING|ERROR)
  - Indices: (symbol, from_date, to_date), (generated_at)

- runs
  - run_id (PK), dataset_id (FK → datasets)
  - strategy_id, params_json, seed, slippage_fees_json, speed
  - code_hash, created_at (UTC), status, duration_ms
  - metrics_path, equity_path, orders_path, fills_path, run_manifest_path
  - input_hash (deterministic hash of inputs), idempotency_key
  - Indices: (dataset_id), (strategy_id, created_at), (created_at)

- run_metrics
  - run_id (PK, FK → runs), total_return, cagr, max_drawdown, sharpe, sortino
  - hit_rate, avg_win, avg_loss, turnover, slippage_share, fees_paid, computed_at
  - Indices: (sharpe), (max_drawdown)

- View: runs_list
  - Joins runs with datasets for convenient listing (symbol, from_date, to_date)

See authoritative DDL in scripts/catalog_init.sql.

## Common queries

Count runs by symbol
```
SELECT d.symbol, COUNT(*) AS n
FROM runs r
JOIN datasets d ON d.dataset_id = r.dataset_id
GROUP BY d.symbol
ORDER BY n DESC;
```

List last N runs
```
SELECT * FROM runs_list
ORDER BY created_at DESC
LIMIT 20;
```

Filter runs (symbol + date overlap)
```
SELECT *
FROM runs_list
WHERE symbol = 'AAPL'
  AND from_date >= '2023-01-01'
  AND to_date   <= '2023-12-31'
ORDER BY created_at DESC;
```

Get run detail with artifact paths
```
SELECT r.*, d.symbol, d.from_date, d.to_date
FROM runs r
JOIN datasets d ON d.dataset_id = r.dataset_id
WHERE r.run_id = ?;
```

Insert or update metrics for a run
```
INSERT INTO run_metrics (run_id, total_return, cagr, max_drawdown, sharpe, sortino,
                         hit_rate, avg_win, avg_loss, turnover, slippage_share, fees_paid, computed_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
ON CONFLICT(run_id) DO UPDATE SET
  total_return=excluded.total_return,
  cagr=excluded.cagr,
  max_drawdown=excluded.max_drawdown,
  sharpe=excluded.sharpe,
  sortino=excluded.sortino,
  hit_rate=excluded.hit_rate,
  avg_win=excluded.avg_win,
  avg_loss=excluded.avg_loss,
  turnover=excluded.turnover,
  slippage_share=excluded.slippage_share,
  fees_paid=excluded.fees_paid,
  computed_at=datetime('now');
```

## Operational notes
- PRAGMA foreign_keys = ON; (enabled in schema script)
- Keep JSON fields stable (sorted keys) if used in input_hash calculations
- Run VACUUM/ANALYZE periodically for health if catalog grows

## Cross-references
- scripts/catalog_init.sql (authoritative DDL)
- docs/metrics/run-metrics-definitions.md
- docs/prd/features/00-baselines.md
- docs/api/openapi.yaml

