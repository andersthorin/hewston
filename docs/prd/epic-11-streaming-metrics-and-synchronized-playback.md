# Epic 11 — Streaming Metrics and Synchronized Playback (Brownfield Enhancement)

Status: Draft v0.1
Owner: PO
Related Epics: E5 (Playback Streaming), E6 (Frontend MVP), E8–E9 (BFF)

## Goal
Deliver a synchronized playback experience where charts, orders/events, and metrics update in lockstep during backtest playback (finished-run replay, v1). Establish a single Playback Clock as the source of truth and extend backend frames to include running metrics computed by the Nautilus engine (or compatible backend service), so the frontend does not implement its own financial metric computations.

## Why (Value)
- Users see the system “breathe” in real-time, improving insight and trust.
- Productizes streaming at portfolio scale while preserving consistency (Nautilus as metrics source of truth).
- Lays the foundation for multi-symbol playback by centralizing time and synchronization.

## Scope (In)
- Central Playback Clock in frontend (single source of truth: currentSimTime, playing, seek).
- Backend frame extension to include running metrics and aggregates (Nautilus-derived):
  - Portfolio-level: equity_so_far, total_return_so_far, max_drawdown_so_far, sharpe_so_far (as provided by backend).
  - Event markers (orders/fills) surfaced in-frame for timeline markers.
  - Symbol-focus data + portfolio aggregates in the same frame.
- Frontend UI updates in sync with the Playback Clock:
  - OHLC chart continues hour-tick updates (aggregating to daily bars as today).
  - Metrics panel updates per frame using backend-provided metrics.
  - Orders feed updates per frame; timeline renders event markers.
  - Controls: Play/Pause, Seek/Scrub. (No speed control in v1.)
- Works for finished runs only (full scrub range known).

## Out of Scope (v1)
- “Jump to next/prev event” control.
- Frontend computation of financial metrics (we rely on backend/Nautilus outputs).
- Complex multi-symbol visualizations beyond symbol focus + portfolio aggregates.
- Advanced rolling windows not provided by backend (unless included by Nautilus).
- In-progress live playback and "follow latest" behavior (deferred)


## Users
- Primary: Internal quants and devs (v1). External users later.

## UX Overview
- Playback area shows:
  1) OHLC chart (hourly ticks, daily aggregation as in current implementation)
  2) Metrics panel that updates per frame (total_return, max_drawdown, sharpe, etc., as provided)
  3) Orders/events feed
  4) Timeline with a minimal scrubber and event markers
  5) Symbol focus frame (select active symbol) + portfolio aggregate metrics

Minimal timeline scrubber = a simple time slider with:
- Start/end bound to run window (fixed for finished runs)
- A draggable handle that updates Playback Clock (seek)
- Ticks/markers for notable events (orders/fills) as dots/lines below the track

## Technical Approach
- Central Playback Clock
  - A shared store (Context or lightweight state library) that holds: currentSimTime (ISO), playing, status, and bounds (start/end).
  - Stream ingester (WS + Worker) updates the store per frame; consumers subscribe to the store, not the socket.
  - ChartOHLC, metrics panel, orders feed, and timeline subscribe to the same clock to avoid drift.

- Backend frames (single source for metrics)
  - Extend WS/SSE frame to include a metrics object and aggregates computed by Nautilus (or backend service):
    {
      t: 'frame',
      ts: ISO,
      ohlc?,
      orders: [...],
      equity: { ts, value },
      metrics: { total_return_so_far, max_drawdown_so_far, sharpe_so_far, ... },
      portfolio?: { exposure?, positions? },
      symbols?: { [symbol]: { position?, exposure? } },
      dropped: n
    }
  - For finished runs (v1): compute metrics per emitted timestamp from artifacts using Nautilus-compatible code paths.

- Event markers
  - Surface orders/fills in-frame; frontend maps them to timeline markers keyed by ts.

- Multi-symbol posture (v1)
  - Symbol focus pane (choose active symbol for the OHLC view) + portfolio aggregates in metrics panel.
  - Data model anticipates multiple symbols; UI shows focus + aggregates without complex per-symbol visualizations.

## Data Contracts (v1)
- Input (WS/SSE frame) additions (backend):
  - metrics: object of numeric fields (Nautilus-derived running metrics)
  - portfolio: optional object with aggregate exposures/positions (if cheaply available)
  - symbols: optional map for per-symbol lightweight stats (to support symbol focus)
- Frontend does not compute metrics; it renders values as provided.

## Performance Targets (v1)
- Target FPS: 30
- End-to-end latency budget: ≤ 100–150 ms under normal load
- Dropped frames tolerance: ≤ 1%
- Synchronization tolerance: all panels within one frame of the Playback Clock
- Deterministic replay (finished runs): identical sequences on repeat

## Success Criteria (Acceptance)
- All selected panels (chart, metrics, orders feed, timeline) update from a single Playback Clock.
- No per-component independent timekeeping; a single source of truth is enforced.
- Frames include backend-computed running metrics; frontend shows them without local recomputation.
- Event markers render on the timeline with correct timestamps; scrubber seeks accurately.
- Performance targets and sync tolerance are met.
- Symbol focus + portfolio aggregates visible and updated per frame.

## Risks & Mitigations
- Drift between components → Single store; time-indexed updates; strict reliance on the Playback Clock.
- Backend compute overhead for per-frame metrics → Keep metrics set minimal in v1; compute incrementally; leverage Nautilus runners where possible.
- Multi-symbol memory/CPU → Windowed buffers, cap visible data, minimal per-symbol stats in v1.

## Dependencies
- E5 (transport, WS/SSE already implemented)
- Backend changes to produce per-frame metrics (Nautilus-based); BFF passthrough if used

## Definition of Done
- Playback Clock integrated; chart, metrics, orders feed, and timeline subscribe to it
- WS/SSE frames include running metrics (backend/Nautilus)
- UI implements play/pause and seek/scrub; shows event markers
- Symbol focus + portfolio aggregates included
- Acceptance and performance criteria validated

