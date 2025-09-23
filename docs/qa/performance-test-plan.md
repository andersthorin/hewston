# Performance Test Plan (Playback, API, Storage)

Status: v0.1 — Validates NFRs from PRD §2.2 and Architecture §Non‑Functional.

## Environment
- Hardware: Apple Silicon M2 (16 GB), macOS
- Dataset: AAPL 2023 derived per baselines (1m bars + TBBO aggregates)
- Build: local dev; backend in debug acceptable for MVP measurements

## Metrics and Targets
- Playback (WS primary)
  - Avg FPS ≈ 30; p95 dropped‑frame ≤ 5%; p99 frame latency ≤ 200 ms
- REST API
  - /backtests list p95 latency ≤ 150 ms (100 runs); get ≤ 100 ms
- Backtest runtime (cached data)
  - Baseline run ≤ 30 s E2E
- Storage budgets
  - 1m bars + TBBO per symbol‑year ≤ 250 MB; per‑run artifacts ≤ 50 MB

## Instrumentation
- Server
  - Structured logs: timestamps, run_id, frame counters (produced/sent/dropped), per‑frame latency
  - Metrics counters (minimal): frames_produced, frames_sent, frames_dropped
- Client
  - Worker measures inter‑frame arrival jitter and render latency; logs periodic summaries

## Test Procedures
1) Dataset ready
  - Build AAPL 2023: `make data SYMBOL=AAPL YEAR=2023`
  - Verify bars manifest includes calendar_version and hashes
2) Backtest baseline
  - `make backtest SYMBOL=AAPL FROM=2023-01-01 TO=2023-12-31 FAST=20 SLOW=50 SPEED=60 SEED=42`
  - Verify artifacts exist and manifest recorded
3) Playback WS
  - Connect to ws://localhost:8000/backtests/{run_id}/ws
  - Run sequence: pause → play → speed=60 → seek mid‑range → play to end
  - Record: avg FPS, p95 dropped‑frame ratio, p99 frame latency from logs/counters
4) SSE fallback
  - GET /backtests/{id}/stream?speed=60
  - Verify frames stream; check fallback stability (no control)
5) REST latencies
  - Seed catalog with N ~ 100 runs (synthetic acceptable for timing)
  - Measure p95 for list/get via repeated calls (exclude warm‑up)
6) Storage footprint
  - Measure sizes of derived bars and per‑run artifacts; compare to budgets

## Reporting
- Produce a short run report per test with:
  - Environment details (machine, versions)
  - Metrics table (targets vs observed)
  - Notable logs (anomalies, error codes)

## Acceptance
- All targets within specified thresholds; deviations documented with rationale and mitigation plan

