# Epic 13 — Relevant Backtest Metrics with Playback (Brownfield Enhancement)

Status: Draft v0.1
Owner: PO
Related Epics: E5 (Playback Streaming), E6 (Frontend MVP), E11 (Streaming Metrics & Sync)

## Goal
Enable accurate, “current at any timestamp” portfolio metrics during playback, computed solely from Nautilus Trader outputs. Frontend shows a read‑only metrics panel; no sorting/filtering.

## Why (Value)
- Trust: Metrics match Nautilus and remain consistent over time.
- Insight: While scrubbing/playing back any run, users can see current drawdown, Sharpe, total return, realized PnL, etc.
- Performance: Precompute once post‑run → cheap lookups during playback.

## Scope (In)
- Source of truth: Nautilus outputs (returns series, equity, realized PnL; plus static analyzer stats).
- Post‑run precompute: build cumulative time‑series metrics from Nautilus series only; persist to metrics_path (JSON).
- Playback frames: attach latest cumulative values ≤ frame.ts (lookup only; no heavy math at stream time).
- Frontend: read‑only metrics panel; no sort/filter requirements.

## Constraints
- No metrics derived from anything other than Nautilus data.
- No guesswork from docs: verify bar interval (e.g., 1m) and available series in code/manifests.
- Keep DB schema out of the critical path (artifact is canonical); any DB metrics tables are legacy for this epic.

## Metrics (cumulative-to-date)
- equity (existing in frames)
- return (per bar) from Nautilus returns series
- realized_pnl (USD) cumulative
- total_return = equity_t / equity_0 − 1
- max_drawdown = (peak_equity_to_date − equity_t) / peak_equity_to_date
- sharpe_t = sqrt(P) × mean(r_1..t) / std(r_1..t) where P = periods/year derived from bar interval
- win_rate_t = wins_to_date / (wins_to_date + losses_to_date) based on realized trade outcomes

Notes:
- Use cumulative‑to‑date definitions (no look‑ahead).
- P (annualization): P = 252 × (minutes_per_session / bar_minutes). For 1‑minute bars and NASDAQ (390 mins/day): P ≈ 252 × 390 = 98,280.
- Edge cases: std=0 → null Sharpe; division by zero guarded.

## Data Flow & Artifacts
- Post‑run job writes metrics_path JSON with:
  - stats.raw: raw Nautilus analyzer outputs (pnls/returns/general) for static summary
  - series: array of [ts, { equity, return, realized_pnl, total_return, drawdown, sharpe, win_rate }]
- Streamer loads metrics_path once per run; per frame ts, picks latest series point ≤ ts and attaches values to frame.metrics.

## API & Contracts
- WS/SSE frame (additive):
  - metrics: {
    return, realized_pnl, total_return, drawdown, sharpe, win_rate
  }
- REST: keep existing metrics artifact endpoint (pass‑through JSON); no additional list/detail fields required in this epic.
- OpenAPI: document optional metrics object on StreamFrame.

## Frontend
- Playback metrics panel shows values from frame.metrics (no local recompute, no sort/filter).
- Keep presentational/containers boundaries: containers read from WS stream state.

## Acceptance Criteria
- A completed run produces metrics_path with non‑empty series and raw Nautilus stats.
- During playback, per‑frame metrics update deterministically and match recomputation on the same artifact.
- Latency budget met; frame payload remains backward compatible (metrics optional).
- FE renders equity, return, realized_pnl, total_return, drawdown, sharpe, win_rate.

## Out of Scope (for this epic)
- Rolling/windowed Sharpe/Sortino variants.
- Additional DB metrics columns or normalization.
- FE table sorting/filtering.

## Risks & Mitigations
- Nautilus version drift (keys/series): store raw stats under stats.raw; compute from series we extract; add unit tests.
- Bar interval ambiguity: record bar interval in manifest and compute P accordingly; test 1m/5m paths.
- Performance: precompute once; streaming does O(log N) or O(1) index lookup.

## Stories
1) Backend: Precompute cumulative metrics from Nautilus series
   - Extract series (returns, equity, realized PnL USD, closed trade PnLs) from Nautilus engine artifacts.
   - Compute cumulative total_return, drawdown, sharpe (with P), win_rate.
   - Persist JSON at metrics_path with stats.raw + series.
   - Unit tests on synthetic series (Sharpe/DD/WR edge cases).

2) Streamer: Attach metrics to frames
   - Load metrics_path on stream start; build an index by ts.
   - For each frame ts, attach latest ≤ ts values under frame.metrics.
   - Backwards compatible; nulls if no earlier point.

3) API/OpenAPI: Document frame.metrics
   - Extend StreamFrame schema to include optional metrics object and descriptions.
   - Keep metrics artifact endpoint as pass‑through.

4) Frontend: Read‑only metrics panel
   - Display equity, return, realized_pnl, total_return, drawdown, sharpe, win_rate.
   - No client computations beyond formatting.

## Validation
- Unit tests: math functions (Sharpe, DD, WR) with fixtures; annualization factor by interval.
- Integration: run job produces artifact; WS frames include metrics; FE renders live updates.
- Determinism: identical playback metrics on repeat from same artifact.

## Story Manager Handoff
- Tech stack: FastAPI + jobs; WS primary/SSE fallback; Vite/React/TS FE.
- Integration points: metrics_path artifact; WS frames with metrics.
- Conventions: cumulative metrics, USD realized PnL, P computed from bar interval.
- Acceptance: see criteria above.

