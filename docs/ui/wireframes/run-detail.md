# Wireframe — Run Detail (Playback)

Status: v0.1 (UX)

## Layout (Playing)
- Header
  - Left: run_id, status pill (QUEUED/RUNNING/DONE/ERROR)
  - Right: Rerun from manifest (button)
- Meta panel
  - symbol, date range, strategy_id/params, seed, created_at
- Controls bar
  - Play/Pause, Seek (slider + datetime input), Speed (30/60/120)
  - Indicators: WS connected | SSE fallback; Dropped: N
- Charts
  - OHLC main chart with overlays toggles (orders, fills)
  - Equity mini-chart below

## States
- Loading metadata: skeletons for header/meta; disabled controls
- Error (RUN_NOT_FOUND): banner + back link to Runs List
- Waiting for playback: metadata visible; controls enabled; chart placeholder
- Playing: live frames; dropped counter visible
- Paused: controls show paused; charts static
- End: toast End of stream; controls allow seek/replay

## Error events during playback
- Toast: code + short message on `{t:"err"}`; non-blocking unless fatal

## Interaction notes
- Keyboard shortcuts: Space (play/pause), 19/1A seek, +/- speed
- Focus ring visible; live region announces connection changes
- Responsive: Controls wrap; charts stack on small screens

