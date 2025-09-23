# Source Tree and Module Boundaries (Authoritative)

Status: v0.1 (aligns with docs/architecture.md §Source Tree and Module Boundaries)

## Monorepo Layout (proposed)
```
backend/
  app/main.py                # FastAPI app factory; mounts REST + WS/SSE
  api/routes/backtests.py    # POST/GET /backtests; SSE fallback; idempotency
  api/routes/health.py       # /healthz
  domain/models.py           # Pydantic models (Dataset, Run, Metrics, Manifests)
  domain/types.py            # Typed aliases, enums
  services/backtests.py      # Orchestration (create/list/get)
  services/streamer.py       # Frame producer/decimator; WS/SSE plumbing
  ports/market_data.py       # MarketDataPort (interface)
  ports/backtest_runner.py   # BacktestRunnerPort (interface)
  ports/catalog.py           # CatalogPort (interface)
  ports/streamer.py          # StreamerPort (interface)
  adapters/databento.py      # MarketDataPort impl (DBN ingest + derive bars)
  adapters/nautilus.py       # BacktestRunnerPort impl (Nautilus)
  adapters/sqlite_catalog.py # CatalogPort impl (SQLite)
  adapters/streams.py        # StreamerPort impl (emit frames → WS/SSE)
  jobs/cli.py                # Typer CLI: data, backtest
  jobs/ingest.py             # Ingest TRADES+TBBO → raw cache
  jobs/derive.py             # Derive 1m bars + TBBO aggregates (Parquet)
  jobs/run_backtest.py       # Execute backtest and write artifacts
frontend/
  src/components/            # Presentational only (no fetch/mutate)
  src/views/                 # RunsList, RunDetail (compose containers + components)
  src/containers/            # Data wiring (TanStack Query) and WS/SSE integration
  src/services/api.ts        # REST client; query keys
  src/services/ws.ts         # WebSocket hook/handler; SSE fallback
  src/workers/streamParser.ts# Decode/normalize frames off main thread
  src/features/backtests/    # Feature slice for backtests
  src/styles/                # Tailwind setup
  src/lib/                   # Utilities (formatting, schema helpers)
  index.html, main.tsx, ...  # App bootstrap
scripts/
  catalog_init.sql           # SQLite schema (see docs/architecture.md)
 data/
  raw/databento/...          # Cached DBN (TRADES/TBBO)
  derived/bars/...           # 1m OHLCV + TBBO aggregates (Parquet) + manifest
  backtests/{run_id}/...     # metrics.json, equity.parquet, orders.parquet, fills.parquet, run-manifest.json
```

## Boundaries & Contracts
- Ports/Adapters (hexagonal-lite):
  - MarketDataPort: ensure_dataset(symbol, from_date, to_date) -> dataset_id; derive_bars(dataset_id)
  - BacktestRunnerPort: run(dataset_id, strategy_id, params, seed, slippage_fees, run_id)
  - CatalogPort: upsert_dataset/get_dataset; create_run/get_run/list_runs; set_run_status
  - StreamerPort: async frames(run_id, speed); control(run_id, cmd, **kwargs)
- REST & Streaming:
  - OpenAPI: docs/api/openapi.yaml (POST/GET /backtests, SSE fallback)
  - WS protocol: GET /backtests/{id}/ws (ctrl/frame/hb/end/err)
- Catalog:
  - SQLite DDL: scripts/catalog_init.sql; indices for list/filter/search

## Rules of the Road (enforced boundaries)
- API handlers are non-blocking; CPU-bound work runs in Typer subprocesses.
- Presentational components never fetch or mutate; data/logic lives in containers/services.
- Determinism:
  - UTC timestamps in artifacts; UI renders America/New_York.
  - Manifests include calendar_version, tz, dataset IDs, code_hash, env_lock, params, seed.
  - Input hashing for idempotent POST /backtests.

## Makefile Targets (developer UX)
- setup: create Python venv (uv), prepare frontend (npm)
- start: run backend + frontend dev servers (if present)
- start-backend: uvicorn app
- start-frontend: vite dev
- data: ingest Databento DBN + derive bars (SYMBOL, YEAR)
- backtest: submit baseline run (FROM/TO/STRATEGY/FAST/SLOW/SPEED/SEED)
- db-apply: apply scripts/catalog_init.sql to data/catalog.sqlite

## Cross-References
- PRD §4.3 Architecture and Interfaces; §6 Next Steps
- Architecture §Source Tree and Module Boundaries; §Catalog Schema; §API Contracts
- docs/api/openapi.yaml; scripts/catalog_init.sql

