# Hewston Product Requirements Document (PRD)
> Mode: Interactive PRD Generation
> Source: Project Brief (Draft 1 complete)

## 1. Goals and Background Context

### 1.1 Goals
- Deliver a reproducible backtesting MVP with ~1 year → ~60s time‑compressed playback and persisted artifacts (manifest + metrics + series)
- Provide deterministic DBN → 1m bars pipeline (NASDAQ calendar, America/New_York) with local caching and manifests
- Enable end‑to‑end baseline backtest (AAPL, 2023, sma_crossover fast=20, slow=50) in ≤ 30s (cached data) on Apple M2‑class laptop
- Expose a minimal API to create/list/view/stream backtests and a catalog to filter/search runs
- Ship a Vite + React + TypeScript + Tailwind UI that plays back runs, shows equity/metrics, and overlays orders/fills (presentational components only)
- Provide Makefile developer workflow: `make setup`, `make start`, `make data`, `make backtest`

### 1.2 Background Context
Hewston is a single‑user, equities‑first agentic day‑trading application. The MVP focuses exclusively on fast, reproducible backtesting using Nautilus Trader on Databento data (TRADES + TBBO), with 1‑minute bars and time‑compressed playback that feels like a live dashboard. The system persists complete run artifacts and manifests to support re‑runs and apples‑to‑apples comparison.

The accompanying Project Brief defines scope, constraints, performance targets, and a forward path to paper/live trading and multi‑symbol runs. This PRD captures the functional and non‑functional requirements to deliver the MVP.

### 1.3 Change Log
| Date       | Version | Description                              | Author        |
|------------|---------|------------------------------------------|---------------|
| 2025-09-22 | 0.1     | Initial PRD draft from Project Brief     | Mary (BA)     |


## 2. Requirements
### 2.1 Functional (FR)
- FR1: The system shall ingest Databento TRADES+TBBO (DBN) and derive deterministic 1m OHLCV plus minute TBBO aggregates (bid_mean, ask_mean, spread_mean) with NASDAQ calendar and America/New_York timezone, writing Parquet files and a dataset manifest.
- FR2: The system shall expose Makefile targets `make setup`, `make start`, `make data`, and `make backtest`.
- FR3: The API shall allow creating a backtest run: POST /backtests {symbol, from, to, interval='1m', strategy_id='sma_crossover', params, speed, seed}.
- FR4: The API shall list runs and filter by symbol/date/strategy: GET /backtests.
- FR5: The API shall retrieve run metadata and artifacts: GET /backtests/{id}.
- FR6: The API shall stream time-compressed playback via WebSocket (primary): GET /backtests/{id}/ws with in-band control (play/pause/seek/speed); SSE fallback available: GET /backtests/{id}/stream?speed=60.
- FR7: The system shall persist run artifacts under data/backtests/{run_id}/ including run-manifest.json, metrics.json, equity.parquet, orders.parquet, fills.parquet.
- FR8: The UI shall provide a Runs List view to browse and filter runs and a Run Detail view to play back a run with chart, equity, and orders/fills overlays.
- FR9: The UI shall provide playback controls: play/pause, seek, speed control; and a rerun action using the run manifest.
- FR10: The backtest runner shall execute a baseline `sma_crossover` strategy with configurable fast/slow parameters and seed.

### 2.2 Non-Functional (NFR)
- NFR1: Reproducibility — Identical run manifests produce identical artifact hashes (SHA‑256); aggregate metrics drift tolerated only up to 0.05% if unavoidable.
- NFR2: Performance — Baseline E2E (AAPL 2023, sma fast=20/slow=50) completes ≤ 30s (cached data); playback avg ≈ 30 FPS; p95 dropped‑frame ≤ 5%; p99 frame latency ≤ 200 ms.
- NFR3: Storage — Derived 1m bars + aggregates per symbol‑year ≤ 250 MB; per‑run artifacts ≤ 50 MB.
- NFR4: Determinism — Bars generated with pinned NASDAQ calendar version and explicit DST handling; manifests capture calendar_version, tz, data snapshot IDs, code hash, env lock.
- NFR5: UI architecture — Presentational components contain no data fetching or mutation; all data comes from backend or a middle layer; WebSocket handled via hook/worker; SSE fallback parsing supported.
- NFR6: Security/ops — Secrets via env; no secrets in repo; ingestion success ≥ 99%; retryable error rate ≤ 1%.


## 3. User Interface Design Goals
### 3.1 Overall UX Vision
A responsive web dashboard optimized for desktop that presents ready‑to‑render data from the backend. The UI is intentionally “dumb”: presentational components render charts, metrics, and feeds without computing or mutating data. Playback feels “live” while running at time‑compressed speed.

Assumptions: single‑user desktop focus; minimal navigation; no auth; dark theme optional; Tailwind 4 utility classes.

### 3.2 Key Interaction Paradigms
- Runs List: filter/search; open a run
- Run Detail: live‑like playback with chart + equity + orders/fills overlays; controls (play/pause/seek/speed)
- Deterministic re‑run: button pre‑fills from manifest

### 3.3 Core Screens and Views
- Runs List
- Run Detail
- (Optional) Data Status/Settings (read‑only status; out of scope to edit)

### 3.4 Accessibility
Choice: None (single‑user) — aim for keyboard navigation and sufficient contrast.

### 3.5 Branding
None defined; use sensible defaults (Tailwind) with light/dark toggle optional post‑MVP.

### 3.6 Target Device and Platforms
Web Responsive (desktop‑first).


## 4. Technical Assumptions
Authoritative source for architecture choices is docs/brief.md (Technical Considerations). This section summarizes assumptions relevant to the PRD.

### 4.1 Repository and Runtime
- Monorepo; local-first development
- Python 3.11+, Node 22+, macOS (Apple Silicon) dev; Linux optional for headless jobs

### 4.2 Stack and Libraries
- Backend: FastAPI + Uvicorn; Pydantic v2; Typer for jobs
- Data: Polars or Pandas; PyArrow/Parquet; deterministic rebar
- Market Data: Databento SDK (DBN TRADES+TBBO)
- Backtesting: Nautilus Trader with 1m bar adapter + slippage hooks
- Storage: Local FS; Parquet/JSON artifacts; JSON/SQLite catalog
- Frontend: Vite + React + TypeScript + Tailwind 4; TradingView Lightweight Charts; TanStack Query; Zod; WebSocket handled in hook/worker; SSE fallback parsing

### 4.3 Architecture and Interfaces
- WebSocket for playback streaming (primary) with SSE fallback; server decimation; client backpressure
- Manifest schema includes: run_id, created_at, symbol(s), from, to, interval, calendar_version, tz, strategy_id, params, seed, slippage/fees, code_hash, env_lock, dataset_ids
- Single-symbol runs in MVP; multi-symbol future-ready

### 4.4 Testing and Tooling
- Makefile targets: setup/start/data/backtest
- Lint/format: Ruff/Black; pre-commit; Vitest/ESLint/Prettier
- Testing approach: fixtures for DBN→1m bars; adapter conformance; deterministic seeds; E2E smoke baseline

## 5. Epic List
- Epic 1: Foundation & Core Infrastructure — Establish project setup and deliver a minimal end-to-end vertical slice (health, Makefile targets, PRD-visible API stub).
- Epic 2: Data Ingestion & Bar Derivation — Fetch Databento DBN, derive deterministic 1m bars + TBBO aggregates with manifests.
- Epic 3: Backtest Runner & Artifacts — Execute baseline sma_crossover on 1m bars; persist run artifacts and manifest.
- Epic 4: API & Catalog — Expose POST/GET /backtests and catalog list/filter/search; run_id scheme and idempotency.
- Epic 5: Playback UI — Vite+React+TS+Tailwind UI; Runs List and Run Detail with time-compressed playback over WebSocket (SSE fallback); rerun from manifest.
- Epic 6: Reproducibility & Performance Hardening — Hash checks, determinism validation, performance budgets and logging.

Note: Stories live under docs/stories/, and epic documents live under docs/prd/ (files epic-1-*.md through epic-7-*.md).

## 6. Next Steps
### Immediate Actions
1. Lock baseline symbols/years (e.g., AAPL, 2023)
2. Finalize bar schema columns and manifest JSON schema
3. Define slippage/fees defaults (k, bps) and baseline strategy params (fast/slow)
4. Draft API contracts (POST/GET /backtests), WebSocket protocol (ctrl/frame/heartbeat) and SSE fallback payload, and run_id scheme
5. Choose catalog format (JSON vs SQLite) and indexing strategy
6. Document Makefile target specs and README quickstart outline

### Handoff
Use this PRD and the Epics folder with docs/brief.md to generate stories and acceptance criteria per epic.
