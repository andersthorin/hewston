# Hewston

Reproducible backtesting MVP with time-compressed playback. This README is a Quickstart aligned with the PRD and Architecture docs.

## Docs Map
- PRD: docs/prd.md
- Architecture overview: docs/architecture.md
- Tech stack / Source tree / Coding standards: docs/architecture/tech-stack.md, docs/architecture/source-tree.md, docs/architecture/coding-standards.md
- Baselines: docs/prd/features/00-baselines.md
- API: docs/api/openapi.yaml; Errors: docs/api/error-codes.md
- Streaming protocol: docs/api/ws-protocol.md
- Schemas: docs/api/schemas/dataset-manifest.schema.json, docs/api/schemas/run-manifest.schema.json
- Catalog: scripts/catalog_init.sql and docs/api/catalog.md
- Metrics: docs/metrics/run-metrics-definitions.md
- Performance plan: docs/qa/performance-test-plan.md
- Secrets/env: .env.example and docs/security/secrets-and-env.md
- Stories: docs/stories/; QA mapping: docs/qa/story-to-qa-mapping.md


## Prerequisites
- macOS (Apple Silicon) or Linux
- Python 3.11 (uv recommended), Node.js 20.x, npm
- sqlite3 CLI
- Databento API key in env (export DATABENTO_API_KEY=...)

## Setup
```
make setup
```

## Initialize catalog schema
```
make db-apply
```

## Build baseline dataset (AAPL 2023)
```
make data SYMBOL=AAPL YEAR=2023
```

## Run baseline backtest (SMA 20/50, seed=42, speed=60)
```
make backtest SYMBOL=AAPL FROM=2023-01-01 TO=2023-12-31 STRATEGY=sma_crossover FAST=20 SLOW=50 SPEED=60 SEED=42
```
Artifacts will be written under `data/backtests/{run_id}/` (metrics.json, equity.parquet, orders.parquet, fills.parquet, run-manifest.json).

## Start servers (when backend/frontend are scaffolded)
```
make start
```
- Backend: FastAPI on http://127.0.0.1:8000 (see /healthz)
- Frontend: Vite dev server (if present)

## API and Streaming
- OpenAPI: docs/api/openapi.yaml
- Playback protocol: docs/api/ws-protocol.md
- Error codes: docs/api/error-codes.md

## Technical baselines
See docs/prd/features/00-baselines.md for authoritative defaults (symbol/year, bars schema, slippage/fees, strategy params, manifests, FS layout).

## Architecture and standards
- Architecture overview: docs/architecture.md
- Tech stack: docs/architecture/tech-stack.md
- Source tree: docs/architecture/source-tree.md
- Coding standards: docs/architecture/coding-standards.md

## Make targets
```
make help
```

## Troubleshooting
- Missing backend/ or frontend/ folders: skeletons are introduced in Milestones 2 and 7 (see docs/architecture.md Implementation Plan).
- sqlite3 not found: install via your OS package manager.
- Databento issues: verify DATABENTO_API_KEY is exported and network access is permitted.
