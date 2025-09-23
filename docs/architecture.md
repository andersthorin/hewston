# Hewston Architecture Document

## Introduction
This document outlines the overall project architecture for Hewston, including backend systems, shared services, and non-UI specific concerns. Its primary goal is to serve as the guiding architectural blueprint for AI-driven development, ensuring consistency and adherence to chosen patterns and technologies.

Relationship to Frontend Architecture:
If the project includes a significant user interface, a separate Frontend Architecture Document will detail the frontend-specific design and MUST be used in conjunction with this document. Core technology stack choices documented herein (see "Tech Stack") are definitive for the entire project, including any frontend components.

### Starter Template or Existing Project
Decision: TBD (pending elicitation)

### Change Log
| Date       | Version | Description                 | Author    |
|------------|---------|-----------------------------|-----------|
| 2025-09-22 | 0.1     | Initialized architecture doc | Architect |



## High Level Architecture

### Technical Summary
- Single-service backend (FastAPI) with background CLI jobs; local-first storage (Parquet/JSON + SQLite catalog).
- Communication: REST for CRUD and control, WebSocket as primary playback channel (bidirectional control + frames), SSE fallback stream.
- Frontend: Vite + React + TS + Tailwind, presentational components only; data/logic in containers/hooks/services; WS handled in a hook/worker.
- Core patterns: Hexagonal-lite ports/adapters (MarketData, BacktestRunner, Catalog, Streamer), manifest-driven runs, idempotent create, deterministic bar pipeline.
- Heavy compute (ingest/derive/backtest) runs in Typer subprocesses; API never blocks the event loop.

### High Level Overview
- Style: Monolith backend with background CLI jobs; monorepo (backend/, frontend/, data/, scripts/, Makefile).
- Service architecture:
  - FastAPI app exposes REST endpoints: create/list/get runs; WS endpoint for playback; SSE fallback endpoint.
  - Typer CLI jobs: `make data` (ingest+derive), `make backtest` (submit runs).
  - Nautilus adapter consumes 1m bars; outputs artifacts per run.
- Primary data flow:
  1) Ingest TRADES+TBBO DBN → cache raw
  2) Derive deterministic 1m bars + TBBO aggregates (Parquet) under pinned calendar/TZ
  3) Backtest runs against derived bars via Nautilus adapter
  4) Persist artifacts (metrics/equity/orders/fills + run manifest)
  5) API lists/gets runs; WS streams time-compressed playback frames to frontend (SSE available as fallback)
- Decisions & rationale:
  - WebSocket (primary) enables in-band control (play/pause/seek/speed), lower overhead at higher frame rates; SSE retained as simple fallback.
  - Monolith + local FS for MVP simplicity/determinism; easy to evolve later.
  - Presentational UI enforces “dumb” components; containers/services own data orchestration.

### High Level Project Diagram
```mermaid
graph TD
  U[User (Owner-Operator)] --> FE[Frontend (Vite/React/TS/Tailwind)]
  FE -- REST --> API[FastAPI Backend]
  FE -- WS --> API
  API -- WS --> FE
  subgraph Backend
    API --> CAT[Runs Catalog (SQLite/JSON)]
    API --> ART[Artifacts (Parquet/JSON on FS)]
    JOB1[Typer: make data] --> RAW[Raw DBN Cache]
    JOB1 --> DER[Derived 1m Bars + TBBO (Parquet)]
    JOB2[Typer: make backtest] --> NT[Nautilus Runner (Adapter)]
    NT --> ART
    API --> NT
    CAT --> API
    ART --> API
  end
  subgraph Data Sources
    DBN[Databento TRADES+TBBO]
  end
  DBN --> JOB1
```

### Playback Channel Protocol (WebSocket)
- Endpoint: `GET /backtests/{id}/ws`
- Heartbeat: server sends `{ "t": "hb" }` at interval; client replies or auto-reconnects
- Backpressure: server decimation to target ~30 FPS; drop-oldest on client lag
- Message schema examples:
```json
{ "t": "ctrl", "cmd": "play|pause|seek|speed", "val": 60, "pos": "2023-03-01T14:30:00Z" }
{ "t": "frame", "ts": "2023-03-01T14:30:00Z", "ohlc": [...], "orders": [...], "equity": 123.4, "dropped": 2 }
{ "t": "end" }
{ "t": "err", "code": "RANGE", "msg": "out of range" }
{ "t": "hb" }
```
- Fallback SSE endpoint: `GET /backtests/{id}/stream` (server→client only)

### Architectural and Design Patterns (selected)
- Communication: REST + WebSocket (primary) with SSE fallback — WS supports bidirectional control and future multi-stream needs; SSE retained for simplicity/compat.
- Backend code organization: Hexagonal-lite ports/adapters (MarketData, BacktestRunner, Catalog, Streamer) — clear boundaries, testability, future swaps.
- Determinism & reproducibility: Manifest-driven + hashing (calendar/TZ pinned, seed, code hash, dataset ids) — strong guarantees without heavy infra.
- Idempotent create: `POST /backtests` with idempotency key or deterministic input hash — safe retries, no duplicate runs.
- Operability: Health endpoint; structured logs with run_id correlation; minimal metrics (timings, dropped frames).


## Tech Stack

### Cloud Infrastructure
- Provider: None (local‑first, single‑user MVP)
- Key Services: N/A (future: object storage, CI/CD)
- Deployment Regions: N/A

### Technology Stack Table (choices confirmed; versions to pin)
| Category | Technology | Version | Purpose | Rationale |
|---|---|---|---|---|
| Language | Python | 3.11.x (pin) | Backend jobs/API | Async support; mature ecosystem |
| Runtime | Node.js | 20.x (pin) | Frontend tooling | LTS; stable dev experience |
| Backend Framework | FastAPI | 0.115.x | REST/WS API | Async‑first; Pydantic v2 |
| CLI/Jobs | Typer | 0.12.x | Ingest/derive/backtest | Ergonomic CLIs; pairs with FastAPI |
| Dataframe | Polars | 1.9.x | Bar derivation/aggregations | Fast; Arrow‑native |
| Columnar IO | PyArrow + Parquet | PyArrow 16.x | On‑disk columnar storage | Efficient, interoperable |
| Market Data | Databento SDK (DBN TRADES+TBBO) | 0.38.x | Raw data ingest | Matches data source plan |
| Backtesting | Nautilus Trader | 0.10.x | Strategy execution | Performance; adapter model |
| Catalog | SQLite (+ JSON export) | 3.x (pin) | Runs/datasets index | Simple, fast, local |
| Transport | WebSocket primary + SSE fallback | N/A | Playback/control channel | Bidirectional control; fallback stream |
| Frontend | Vite + React + TypeScript + Tailwind 4 | Vite 5.4.x / React 18.3.x / TS 5.6.x / Tailwind 4.0.x | Playback UI | Your preference; fast DX |
| Charting | TradingView Lightweight Charts | 4.2.x | OHLC/equity rendering | Performance for time‑series |
| FE Data | TanStack Query + Zod | TQ 5.51.x / Zod 3.23.x | Fetch/cache + validation | Presentational components |
| Lint/Format | Ruff, Black; ESLint, Prettier | Ruff 0.6.x / Black 24.8.x / ESLint 9.10.x / Prettier 3.3.x | Code quality | Lightweight, standard |
| FE Tests | Vitest | 1.6.x | Unit tests | Fast; TS‑friendly |
| Logging | stdlib logging + structlog (JSON) | structlog 24.1.x | Structured logs | Simple; parsable |
| Env/Packaging | uv (preferred) | 0.4.x | Python env mgmt | Fast solver; lockfile |

Version pins:
- Python 3.11.9; Node 20.11.1 (LTS)
- FastAPI 0.115.x; Typer 0.12.x; Polars 1.9.x; PyArrow 16.x; Databento SDK 0.38.x; Nautilus Trader 0.10.x
- React 18.3.x; TypeScript 5.6.x; Vite 5.4.x; Tailwind CSS 4.0.x; TanStack Query 5.51.x; Zod 3.23.x; Vitest 1.6.x
- Ruff 0.6.x; Black 24.8.x; ESLint 9.10.x; Prettier 3.3.x; structlog 24.1.x

Notes:
- Exact patch versions will be locked in uv and package manager lockfiles and recorded in manifests.


## Data Models

### Dataset
Purpose: Cached slice of raw TRADES/TBBO and derived bars for one symbol+range.
Key Attributes:
- dataset_id (string), symbol (string), from_date/to_date (date)
- products: ["TRADES","TBBO"], calendar_version (string), tz ("America/New_York")
- paths: raw_dbn[] (list of file paths), bars_parquet[] (list), bars_manifest_path (string)
- generated_at (datetime), size_bytes (int), status (enum: READY|BUILDING|ERROR)
Relationships: 1..* Runs reference Dataset by dataset_id

### DatasetManifest (Derivation Manifest)
Purpose: Deterministic provenance for bars; used for hashing/verification.
Key Attributes:
- dataset_id, symbol, interval: "1m", from_date, to_date
- rebar_params: { clock:"NASDAQ", session_handling:"explicit-DST", aggregation:"TRADES→OHLCV", tbbo_agg:["bid_mean","ask_mean","spread_mean"] }
- input_hashes: { trades_dbn_sha256, tbbo_dbn_sha256 }
- output_hashes: { bars_parquet_sha256 }
- calendar_version, tz, corp_actions_source_version?, created_at
Relationships: 1:1 with Dataset (via bars_manifest_path)

### Run
Purpose: A single backtest execution with reproducible context.
Key Attributes:
- run_id (string), dataset_id (string)
- strategy_id ("sma_crossover"), params {fast:int, slow:int}, seed (int)
- slippage_fees { k_spread:float, fees_bps:float }, speed (int)
- code_hash (git), created_at (datetime), status (enum), duration_ms (int)
- artifacts { metrics_path, equity_path, orders_path, fills_path, run_manifest_path }
Relationships: Run → Dataset (many:1); Run has 1:1 RunMetrics

### RunManifest (Snapshot of Inputs)
Purpose: Immutable snapshot of inputs/settings at run time.
Key Attributes:
- dataset_id, strategy_id, params, seed, slippage_fees, speed
- data snapshot refs: bars_manifest_hashes
- calendar_version, tz, env_lock (python/node/pkg hashes), code_hash
- created_at
Relationships: 1:1 with Run (persisted as run-manifest.json)

### RunMetrics
Purpose: Normalized metrics for list/filter/search and comparisons.
Key Attributes:
- run_id, total_return, cagr, max_drawdown, sharpe, sortino
- hit_rate, avg_win, avg_loss, turnover, slippage_share, fees_paid
- computed_at
Relationships: 1:1 with Run

### Orders and Fills (artifacts)
Purpose: Parquet schemas for overlays and PnL (not in catalog tables).
Key Columns (suggested):
- orders: ts_utc, side, qty, price, order_id, type, time_in_force
- fills: ts_utc, order_id, qty, price, fill_id, slippage, fee

### StreamFrame (transient)
Purpose: Wire payload for WS/SSE playback; not persisted.
Key Fields:
- ts_utc, ohlc (current bar snapshot), overlays (orders at ts), equity (point), dropped_frames (int)

Assumptions
- Time base: Persist timestamps in UTC; UI renders in America/New_York.
- Catalog: SQLite tables (datasets, runs, metrics) with indices on (symbol, from_date, to_date, strategy_id).
- Hashing: SHA‑256 for raw/derived artifacts; code_hash from git; env_lock recorded in manifests.
- Idempotency: Server computes deterministic input-hash for POST /backtests; X‑Idempotency‑Key supported.


## API Contracts (REST + WebSocket)

### Conventions
- Base URL: http://localhost:8000
- Content types: application/json (REST), text/event-stream (SSE), WebSocket (WS)
- Timestamps: ISO‑8601 UTC strings
- Errors: uniform shape `{ error: { code, message, details? } }`
- Idempotency: Accept `Idempotency-Key` (alias: `X-Idempotency-Key`) on POST /backtests

### REST Endpoints
1) POST /backtests — create a run (async)
- Headers: Idempotency-Key? (string)
- Body (required fields shown):
  - dataset_id (string) OR { symbol, from, to } to resolve dataset
  - strategy_id (string), params (object), seed (int), slippage_fees { k_spread, fees_bps }
  - speed (int, default 60)
- Responses:
  - 202 Accepted { run_id, status: "QUEUED" }
  - 200 OK    { run_id, status: "EXISTS" } when idempotent key matches prior
  - 400/409/422 on validation/conflict

2) GET /backtests — list/filter runs
- Query: symbol?, from?, to?, strategy_id?, limit=50, offset=0, order="-created_at"
- 200 OK: `{ items: Run[], total: int, limit, offset }`

3) GET /backtests/{id} — get run metadata and artifact refs
- 200 OK: Run (includes artifact paths/urls, manifest ref)
- 404 if not found

4) GET /backtests/{id}/stream?speed=60 — SSE fallback stream
- Content-Type: text/event-stream; event: "frame"
- 200 stream of frames until end/cancel; 404 if run not found

5) GET /healthz — liveness
- 200 OK `{ status: "ok" }`

Example: POST /backtests body
```json
{ "dataset_id": "AAPL-2023-1m", "strategy_id": "sma_crossover", "params": {"fast":20,"slow":50}, "seed": 42, "slippage_fees": {"k_spread":0.5, "fees_bps":1}, "speed": 60 }
```

Example: Error shape
```json
{ "error": { "code": "RUN_NOT_FOUND", "message": "Run abc123 not found" } }
```

### WebSocket Playback
- URL: ws://localhost:8000/backtests/{id}/ws
- Subprotocol: none
- Heartbeat: server → `{ "t":"hb" }` every 5s; client may echo `{ "t":"hb" }`
- Backpressure: server decimation to ~30 FPS; drop‑oldest when client lags

Client → Server (control)
```json
{ "t":"ctrl", "cmd":"play|pause|seek|speed", "pos":"2023-03-01T14:30:00Z", "val":60 }
```

Server → Client (messages)
```json
{ "t":"frame", "ts":"2023-03-01T14:30:00Z", "ohlc":{...}, "orders":[...], "equity":123.4, "dropped":2 }
```
```json
{ "t":"end" } | { "t":"err", "code":"RANGE", "msg":"out of range" } | { "t":"hb" }
```

Notes
- API handlers never run CPU‑bound work; creation enqueues/executes via Typer subprocesses
- Seek semantics: `pos` may be ISO timestamp or frame index; server snaps to nearest frame
- Authorization: none (bind to localhost); LAN exposure requires explicit opt‑in


## Catalog Schema (SQLite DDL)

Conventions
- Dates/times are ISO-8601 UTC strings (TEXT)
- Arrays and maps stored as JSON (TEXT)
- Enums enforced via CHECK constraints
- Foreign keys enabled with `PRAGMA foreign_keys = ON;`

```sql
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
```

Notes
- For JSON fields, ensure serialization is stable (sorted keys) when included in input_hash computation.
- Artifact paths are file system locations; ensure they are relative to repository root or absolute with care.
- Consider VACUUM/ANALYZE periodically for catalog health.


## Source Tree and Module Boundaries

Repository layout (monorepo)
```
backend/
  app/main.py                # FastAPI app factory, WS/SSE endpoints wiring
  api/routes/backtests.py    # REST routes (POST/GET /backtests)
  api/routes/health.py       # /healthz
  domain/models.py           # Pydantic models (Dataset, Run, Metrics, Manifests)
  domain/types.py            # Typed aliases, enums
  services/backtests.py      # Orchestration logic (create, list, get)
  services/streamer.py       # Frame producer/decimator, WS/SSE plumbing
  ports/market_data.py       # MarketDataPort (interface)
  ports/backtest_runner.py   # BacktestRunnerPort (interface)
  ports/catalog.py           # CatalogPort (interface)
  ports/streamer.py          # StreamerPort (interface)
  adapters/databento.py      # MarketDataPort impl (DBN ingest + derive bars)
  adapters/nautilus.py       # BacktestRunnerPort impl (Nautilus Trader)
  adapters/sqlite_catalog.py # CatalogPort impl (SQLite)
  adapters/streams.py        # StreamerPort impl (frames → WS/SSE)
  jobs/cli.py                # Typer app with commands: data, backtest
  jobs/ingest.py             # Ingest TRADES+TBBO (DBN) to cache
  jobs/derive.py             # Derive 1m bars + TBBO aggregates
  jobs/run_backtest.py       # Execute backtest and write artifacts
frontend/
  src/components/            # Presentational only (charts, tables, UI widgets)
  src/views/                 # RunsList, RunDetail (compose containers + components)
  src/containers/            # Data wiring; map services → component props
  src/services/api.ts        # REST client (TanStack Query)
  src/services/ws.ts         # WebSocket hook/handler; SSE fallback
  src/workers/streamParser.ts# Decoding/normalizing frames off main thread
  src/features/backtests/    # Feature slices for backtests
  src/styles/                # Tailwind setup
  src/lib/                   # Utilities (formatting, schema helpers)
```

Backend ports (interfaces)
```python
class MarketDataPort:
    def ensure_dataset(self, symbol: str, from_date: str, to_date: str) -> str: ...  # returns dataset_id
    def derive_bars(self, dataset_id: str) -> None: ...

class BacktestRunnerPort:
    def run(self, *, dataset_id: str, strategy_id: str, params: dict, seed: int,
            slippage_fees: dict, run_id: str) -> None: ...  # writes artifacts

class CatalogPort:
    def upsert_dataset(self, dataset: dict) -> None: ...
    def get_dataset(self, dataset_id: str) -> dict | None: ...
    def create_run(self, run: dict) -> None: ...
    def get_run(self, run_id: str) -> dict | None: ...
    def list_runs(self, filters: dict, limit: int, offset: int) -> dict: ...
    def set_run_status(self, run_id: str, status: str, duration_ms: int | None = None) -> None: ...

class StreamerPort:
    async def frames(self, run_id: str, speed: int): ...  # async iterator of frames
    async def control(self, run_id: str, cmd: str, **kwargs): ...
```

Adapters
- adapters/databento.py implements MarketDataPort (uses Databento SDK; Polars/PyArrow for bars)
- adapters/nautilus.py implements BacktestRunnerPort (invokes Nautilus; writes artifacts)
- adapters/sqlite_catalog.py implements CatalogPort (tables from Catalog Schema)
- adapters/streams.py implements StreamerPort (server-side decimation; WS/SSE emitters)

Service layer
- services/backtests.py orchestrates create/list/get using CatalogPort + MarketDataPort + BacktestRunnerPort
- services/streamer.py composes StreamerPort with catalog/artifacts to serve frames (no CPU-heavy work)

API layer
- api/routes/backtests.py maps REST to services; computes input_hash; handles Idempotency-Key
- app/main.py wires DI: choose concrete adapters for ports and mounts WS/SSE endpoints

Jobs (Typer)
- jobs/cli.py exposes `data` (ingest, derive) and `backtest` commands
- Each job uses the same ports/adapters as services for consistency and testability

Frontend boundaries
- components/ are purely presentational (receive props; no fetching/mutation)
- containers/ handle TanStack Query calls (api.ts) and WS hookup (ws.ts)
- workers/streamParser.ts normalizes WS/SSE frames and handles backpressure signals
- views/ orchestrate containers + components per route (RunsList, RunDetail)

Notes
- Dependency Injection (simple module-level provider or lightweight container) enables swapping adapters in tests
- Keep ports small and stable; adapters can evolve independently (e.g., future live/broker adapters)
- All long-running/backtest work executes outside FastAPI request handlers (jobs or background tasks)


## Non-Functional Requirements and Performance Budgets

### Playback
- Target: ~1 year → ~60s
- Server decimation to ≈30 FPS; client drop-oldest on lag
- WebSocket latency: median inter-frame jitter ≤ 30 ms; P95 ≤ 80 ms

### REST API
- Median latency ≤ 50 ms; P95 ≤ 200 ms (local dev)
- Idempotent POST /backtests; safe retries

### Backtest Runtime (M2-class, cached data)
- End-to-end ≤ 30 s; cold path observed and logged but not SLO-bound

### Storage Budgets (MVP)
- Derived 1m bars + TBBO per symbol-year ≤ 250 MB
- Per-run artifacts ≤ 50 MB
- Retention: configurable; default keep latest N=100 runs (soft policy)

### Resource Targets (Apple Silicon M2 16 GB)
- Peak RSS during derive/backtest ≤ 6 GB
- API idle ≤ 300 MB
- Max concurrent WS sessions: 3 (MVP local)

### Concurrency & Isolation
- CPU-bound work in subprocesses (Typer); API handlers are non-blocking

## Determinism & Reproducibility Details

### Time & Calendar
- Bars indexed by UTC; UI renders in America/New_York
- Pinned NASDAQ calendar version; explicit DST handling policy

### Hashing & Manifests
- SHA-256 for raw/derived artifacts; code_hash from git
- env_lock recorded (Python/Node/package sets)

### Seeds & Sorting
- Seeded randomness where applicable
- Stable, explicit sort keys for all processing stages

### Idempotency
- Accept Idempotency-Key header
- Compute deterministic input_hash on server; POST returns existing run on match

## Operability & Observability

### Health & Readiness
- /healthz liveness (always on); optional /readyz if/when background queues exist

### Logging
- JSON logs with request_id, run_id, idempotency_key
- INFO for control flow; WARN/ERROR include error codes and key fields

### Metrics (minimal)
- ingest/derive/backtest durations; frames/sec produced/sent/dropped
- WS disconnect count; SSE fallback usage count

### Failure Handling
- Job-level retries with backoff
- Partial artifacts marked and surfaced; catalog status transitions visible

### Security
- Bind 127.0.0.1 by default; permissive CORS for local frontend
- No auth in MVP; LAN exposure requires explicit opt-in

## Key Risks & Mitigations
- WS throughput/jank at high compression → server decimation, frame coalescing, SSE fallback
- Local storage growth → retention policy, manual prune command, size telemetry in logs
- Nautilus integration drift → adapter boundary; pin versions; add smoke backtest job in CI later
- Data integrity (DBN parity, gaps) → manifest input hashes, validation of gaps, explicit reporting


## Implementation Plan & Roadmap (MVP)

Milestone 1 — Contracts and Catalog (docs-first)
- Output: docs/api/openapi.yaml; scripts/catalog_init.sql applied; Makefile targets ready
- Acceptance:
  - openapi.yaml passes a basic lint (structure valid)
  - `make db-apply` creates data/catalog.sqlite with tables/views

Milestone 2 — Backend skeleton
- Output: backend/app/main.py (/healthz), api/routes/backtests.py (stubs), WS echo endpoint, DI wiring
- Acceptance:
  - `make start-backend` serves /healthz 200 ok
  - WS endpoint accepts connection and echoes ctrl messages

Milestone 3 — Catalog adapter and models
- Output: Pydantic models; adapters/sqlite_catalog.py; services/backtests.py (list/get wired)
- Acceptance:
  - `GET /backtests` returns empty list on fresh DB
  - `GET /backtests/{id}` returns 404 when unknown

Milestone 4 — Jobs pipeline (ingest → derive)
- Output: jobs/cli.py with `data` command; adapters/databento.py; bars derivation (Polars/Parquet)
- Acceptance:
  - `make data SYMBOL=AAPL YEAR=2023` writes raw/derived files and upserts dataset row
  - Dataset manifest hashes recorded; sizes logged

Milestone 5 — Backtest runner + artifacts
- Output: adapters/nautilus.py; jobs/run_backtest.py; services/backtests.create
- Acceptance:
  - `POST /backtests` enqueues and completes a simple sma_crossover run on cached data
  - Artifacts written; run row updated; run_metrics row inserted
  - Idempotent POST returns prior run_id on repeat

Milestone 6 — Playback channel (WS primary, SSE fallback)
- Output: services/streamer.py; adapters/streams.py; FE WS hook/worker
- Acceptance:
  - `GET /backtests/{id}/ws` streams frames at decimated ≈30 FPS; ctrl play/pause/seek work
  - SSE fallback streams frames for the same run

Milestone 7 — Frontend MVP
- Output: Runs List, Run Detail; presentational components; charts (Lightweight Charts)
- Acceptance:
  - Runs List shows rows from catalog; Run Detail plays back with overlays and equity

Milestone 8 — Hardening & NFRs
- Output: Logging fields; basic metrics; retention controls; error handling
- Acceptance:
  - Meets latency and storage budgets in local tests; logs include run_id and counters

Notes
- All CPU-bound work runs outside request handlers (jobs or background tasks)
- Keep ports/adapters interfaces stable; prefer small increments and end-to-end vertical slices per milestone
