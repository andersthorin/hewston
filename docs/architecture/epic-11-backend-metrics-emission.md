# Epic 11 — Backend Metrics Emission Plan (Finished‑Run Replay)

Status: Draft v0.1
Owner: Architect
Related: docs/prd/epic-11-streaming-metrics-and-synchronized-playback.md, docs/api-reference.md (E11 delta), backend/services/streamer.py, backend/api/routes/backtests.py, bff/services/websocket_manager.py

## 1) Scope & Assumptions
- v1 covers finished‑run replay only.
- Per‑frame metrics are computed on the backend (Nautilus/compatible), not in the frontend.
- Frames are emitted via WS/SSE with an added `metrics` object and equity normalized to an object `{ ts, value }`.
- BFF proxy must pass fields through unchanged.

## 2) Metrics (v1 set)
Key names (freeze):
- `total_return_so_far` — run‑to‑date: equity_t / equity_0 − 1
- `max_drawdown_so_far` — non‑decreasing: max over τ≤t of (peak_to_date − equity_τ)/peak_to_date
- `sharpe_so_far` — run‑to‑date using per‑period returns r_τ at minute resolution where available; risk‑free r_f = 0 per metrics definitions

Consistency:
- Match docs/metrics/run-metrics-definitions.md formulas. Prefer Nautilus calculators when available; otherwise compute from artifacts using the same definitions.

## 3) Data Sources
- Equity parquet: columns [`ts_utc`, `value`] (optionally `drawdown`)
- Orders parquet: normalized for event markers (ts, side, qty, price, order_id, symbol?)
- (Optional later) Fills parquet for richer stats; not required in v1

## 4) Implementation Design
Target modules:
- `backend/services/streamer.py::produce_frames`
- `backend/api/routes/backtests.py` WS and SSE emitters

Approach (finished runs):
1. Load equity series once (vectorized via Polars/Pandas).
2. Precompute arrays for each metric across all timestamps (O(N)):
   - total_return_so_far[i]
   - max_drawdown_so_far[i] (track running peak; update MDD)
   - sharpe_so_far[i] (compute cumulative mean/std of r_t up to i; r_f=0)
   - Optional: precompute drawdown if not in artifacts
3. During `produce_frames`, select stride (currently 1 for non‑realtime) and for index `i`:
   - Build `frame.metrics = { total_return_so_far[i], max_drawdown_so_far[i], sharpe_so_far[i] }`
   - Keep existing fields: `ohlc`, `orders` (normalized), `equity = { ts, value }`, `dropped`
4. Serialize via WS/SSE handlers (no shape changes beyond `metrics` and `equity` object form).

Notes:
- Performance: Precompute metrics arrays before streaming to keep frame loop lightweight.
- Numerical stability: Use float64; round only at presentation (frontend). Store raw numbers in stream.
- Compatibility: Maintain `ohlc` and `orders` as today. Add `symbol` field to orders if available.

## 5) API Shape (E11 Delta)
- Equity field becomes an object `{ ts, value }` (instead of a bare number).
- Add `metrics` object as above.
- Optional aggregates when cheap: `portfolio` (e.g., exposure), `symbols` map with lightweight stats `{ position?, exposure? }`.
- See docs/api-reference.md for JSON example.

## 6) BFF Pass‑through
- bff/services/websocket_manager.py: no transformations; forward backend frames as‑is.
- Health/connection metadata unaffected.

## 7) Error Handling & Fallbacks
- If metrics precompute fails: log and omit `metrics` field (frontend shows placeholders).
- If equity series empty or malformed: emit `{ t: "err", code: "ARTIFACT_NOT_FOUND" }` and terminate stream.
- Validate metric array lengths match equity indices; assert and log if mismatch.

## 8) Testing Plan
Unit
- Deterministic synthetic equity series → verify total_return_so_far, MDD monotonic, Sharpe consistent with formulas.
- Precompute helpers return arrays of correct length and values (edge cases: constant equity, zero variance).

Integration (Backend)
- WS and SSE: frames include `metrics` fields; equity object form; orders preserved.
- Determinism: two complete replays produce identical metric sequences.

Integration (End‑to‑End with FE mocks)
- Frontend schema accepts metrics block; renders values; no errors when metrics absent.

Performance
- Measure precompute time and per‑frame overhead; log summary (frames_total, compute_ms, frames_produced).

## 9) Rollout & Compatibility
- Feature flag (optional): server side `E11_STREAMING_METRICS` to toggle metrics emission during early rollout.
- Frontend tolerant parsing: if `metrics` missing, UI shows placeholders; equity accepts both legacy (number) and new object for a transition window if needed.

## 10) Implementation Steps
1. Implement metric precompute helpers in `backend/services/streamer.py`:
   - `_precompute_metrics(equity_df) -> dict[str, list[float|None]]`
2. Integrate into `produce_frames`: attach `metrics[i]` to each yielded frame.
3. Update WS (`/backtests/{id}/ws`) and SSE (`/backtests/{id}/stream`) serializers to include `metrics` and equity object.
4. Add unit tests (pytest) for helpers and path through `produce_frames` (small synthetic artifacts).
5. Add integration test to open WS and validate frames contain metrics and are deterministic across runs.
6. Update API docs (done), ensure BFF pass‑through (no changes needed).

## 11) Open Decisions
- Sharpe flavor for run‑to‑date: confirm period base (minute) and risk‑free r_f=0 (per metrics doc). If only hourly/daily is available, define fallback conversion or compute from available frequency.
- Whether to include `portfolio.exposure` and `symbols.*` in v1 or defer to v1.1; if included, define their exact source and cost.

## 12) Acceptance (Backend portion)
- Frames include `metrics` with correct keys/values for all emitted timestamps (finished runs).
- Deterministic across replays (within float tolerance).
- Performance acceptable: precompute O(N), frame loop ~O(1), no significant added jitter.
- BFF proxy forwards fields unchanged.

