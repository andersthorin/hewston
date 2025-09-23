# Epic 4 — Backtest Runner & Artifacts

Goal
- Execute a baseline backtest via Nautilus Trader against derived 1m bars and persist artifacts and a run manifest.

Why (Value)
- Validates end-to-end run pipeline and produces comparable, reproducible outputs for later playback and analysis.

Scope (In)
- adapters/nautilus.py implements BacktestRunnerPort
- jobs/run_backtest.py (Typer command) executes strategy and writes artifacts
- services/backtests.create orchestrates POST /backtests (enqueue + status)
- Artifacts: metrics.json, equity.parquet, orders.parquet, fills.parquet, run-manifest.json
- Idempotency: input_hash + optional Idempotency-Key — return prior run on match

Out of Scope
- Playback streaming; frontend UI

Deliverables
- POST /backtests functional (202 queued → DONE)
- Artifacts written under data/backtests/{run_id}/
- run_metrics row computed and inserted

Acceptance Criteria
- POST /backtests with dataset_id + strategy params produces a DONE run with artifacts
- Repeating the same request with Idempotency-Key returns status EXISTS and prior run_id

Dependencies
- Epic 3 (Data Ingest and Derive)

Risks & Mitigations
- Nautilus integration complexity → start with baseline SMA crossover, pin versions, wrap via adapter
- Artifact schema drift → keep minimal required fields; validate before insert

Definition of Done
- End-to-end baseline backtest completes on cached data ≤ 30s (M2-class)
- Catalog reflects run + metrics; artifacts present; idempotency verified

References
- Architecture: API Contracts; Data Models; Catalog Schema; Implementation Plan Milestone 5

