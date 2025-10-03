# Epic 11 — Streaming Metrics & Synchronized Playback: Acceptance Checklist
Epic ID: E11

Preconditions
- Backend WS `/backtests/{run_id}/ws` or BFF proxy available
- SSE fallback `/backtests/{run_id}/stream` available
- Frames include `metrics` object (backend/Nautilus-derived) per timestamp

Test Cases
1) Single source of truth (Playback Clock)
   - Instrument: log Playback Clock changes vs component updates
   - Verify: ChartOHLC, Metrics panel, Orders feed, Timeline all update within one frame of clock changes

2) Play/Pause
   - Action: Play → frames advance; Pause → frames stop
   - Verify: No desync; chart and metrics pause/resume together

3) Seek/Scrub
   - Action: Drag timeline handle to a past timestamp
   - Verify: Chart, metrics, and orders feed jump to that time; event markers align at target

4) Event Markers
   - Action: Observe timeline markers (orders/fills) while playing and when seeking
   - Verify: Marker timestamps match orders/fills; markers render consistently across seek/play/pause

5) Running Metrics (Backend-provided)
   - Observe: metrics.total_return_so_far, max_drawdown_so_far, sharpe_so_far (if provided)
   - Verify: Values are present, monotonic where expected (e.g., MDD non-decreasing), and consistent on replay

6) Symbol Focus + Portfolio Aggregates
   - Action: Switch active symbol; observe metrics and chart focus
   - Verify: Active symbol changes chart focus; portfolio aggregates continue updating; no UI stalls

7) Finished Run Determinism
   - Action: Replay the same run twice
   - Verify: Identical frame sequence and metrics values; same event marker layout



8) Performance & Health
   - Measure: FPS (avg >= 30), latency (<= 100–150ms), dropped frames (<= 1%) under normal load
   - Tools: `useWebSocketHealth`, `useWebSocketPerformanceMonitor`, BFFPerformanceMonitor

9) Error/End/Heartbeat Behavior
   - Verify: `{ t: 'hb' }` cadence ~5s; `{ t: 'end' }` at completion; `{ t: 'err' }` handled gracefully

Pass/Fail Criteria
- All functional cases pass; performance targets achieved; no component drifts from the Playback Clock beyond one frame

Artifacts
- Dev console logs or exported metrics from health hooks
- Screenshots of timeline markers and scrubber behavior

