# Tech Stack (Authoritative Pins and Rationale)

Status: v0.1 (aligns with docs/architecture.md §Tech Stack and docs/prd.md)

## Languages & Runtimes
- Python: 3.11.9 (pin)
- Node.js: 22.x (LTS, pin)

## Backend
- Framework: FastAPI 0.115.x — async‑first; Pydantic v2
- CLI/Jobs: Typer 0.12.x — ergonomic CLIs for ingest/derive/backtest
- Models: Pydantic v2 — validation and schemas
- Logging: structlog 24.1.x — JSON structured logs

## Data & Compute
- Dataframe: Polars 1.9.x (preferred) — fast, Arrow‑native
- Columnar IO: PyArrow 16.x + Parquet — efficient on‑disk storage
- Market Data: Databento SDK 0.38.x — DBN TRADES + TBBO
- Backtesting: Nautilus Trader 0.10.x — strategy execution via adapter

## Storage & Catalog
- Artifacts: Local filesystem (Parquet/JSON)
- Catalog: SQLite 3.x (plus JSON export) — simple local catalog; schema in scripts/catalog_init.sql

## Transport & Interfaces
- REST: FastAPI
- Playback: WebSocket (primary), SSE (fallback)

## Frontend
- Tooling: Vite 5.4.x, TypeScript 5.6.x
- Framework: React 18.3.x
- UI: Tailwind CSS 4.0.x
- Charts: TradingView Lightweight Charts 4.2.x
- Data: TanStack Query 5.51.x; Zod 3.23.x
- Tests: Vitest 1.6.x

## Quality & Tooling
- Python Lint/Format: Ruff 0.6.x; Black 24.8.x
- FE Lint/Format: ESLint 9.10.x; Prettier 3.3.x

## Versioning & Determinism Notes
- Pins recorded in env lockfiles (uv / npm lock). Manifests include code hash and env lock.
- NASDAQ market calendar version and TZ=America/New_York are recorded in manifests.
- SHA‑256 hashing for raw/derived artifacts; input_hash for idempotent POST /backtests.

## Platform Targets
- Dev: macOS (Apple Silicon). Linux optional for headless jobs.

## Rationale (selected)
- WS primary + SSE fallback: bidirectional control with a simple fallback path.
- SQLite catalog: minimal ops, adequate for single‑user MVP; indices defined for list/filter.
- Presentational UI: components do not fetch/mutate; data orchestration lives in containers/services.

## References
- PRD §2 (FR/NFR), §4 (Technical Assumptions)
- Architecture §Tech Stack, §API Contracts, §Source Tree
- scripts/catalog_init.sql
