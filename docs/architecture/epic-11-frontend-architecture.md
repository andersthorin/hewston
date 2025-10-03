# Epic 11 — Frontend Architecture: Playback Clock & Streaming Metrics (Finished‑Run Replay)

Status: Draft v0.1
Owner: Architect
Related: docs/prd/epic-11-streaming-metrics-and-synchronized-playback.md, docs/api-reference.md (E11 delta)

## 1) Scope
- Finished‑run replay only (fixed time window)
- Central Playback Clock is the single source of truth for time and frame
- Backend/Nautilus computes running metrics; frontend renders (no FE financial math)
- Symbol focus + portfolio aggregates (lightweight)
- Timeline scrubber with event markers; controls = Play/Pause + Seek/Scrub

## 2) High‑level Flow
WS → Worker(streamParser) → FrameNormalizer → PlaybackClock Store → Consumers
- Worker decodes/decimates; forwards frames
- FrameNormalizer ensures E11 frame shape (equity object; metrics block)
- Store updates per frame; consumers subscribe per-slice

## 3) PlaybackClock Store Contract (Context + useSyncExternalStore)
State
- currentSimTime: ISO string (current frame time)
- range: { start: ISO, end: ISO } (fixed for finished runs)
- playing: boolean
- frame?: {
  - ts, equity { ts, value }, ohlc?, orders[], metrics?, portfolio?, symbols?
}
- focusedSymbol?: string | null

Methods
- play(): void; pause(): void; seek(ts: string): void; setFocus(sym?: string): void
- getState(): State; subscribe(cb): () => void

Patterns
- Provide Store via React Context; expose hooks:
  - usePlaybackStore(): Store (rarely needed)
  - usePlaybackSelector<T>(sel: (s: State) => T): T (preferred)
- Worker → onFrame: store.setFrame(frame); avoid React setState per tick

## 4) Component Integration Contracts
ChartOHLC (imperative)
- Subscribe to selector(s => s.frame?.ohlc) and call chartApi.update(dp) imperatively
- On seek: setVisibleRange if necessary; avoid re‑seeding unless range change

MetricsPanel
- Subscribe to selector(s => s.frame?.metrics)
- Display with formatting only; if absent → show em‑dash placeholders

Orders/Events Feed
- Subscribe to selector(s => s.frame?.orders)
- When focusedSymbol set, filter to that symbol if present in payload

TimelineScrubber (finished‑run)
- Props: { range, currentTs, markers, onSeek(ts) }
- Markers: map from orders (and fills in future); render compact dots/lines
- Keyboard/ARIA: left/right (small step), page up/down (larger), home/end; aria-labels for handle

Symbol Focus + Aggregates
- SymbolSelector changes focusedSymbol → affects chart/markers; aggregates remain visible

## 5) Streaming Schema (E11 delta)
- Accept and prefer equity as object: { ts, value }
- Accept metrics object with numeric fields: total_return_so_far, max_drawdown_so_far, sharpe_so_far
- Optional: portfolio { exposure? } and symbols { [sym]: { position?, exposure? } }
- Tolerant parsing: if metrics missing, UI degrades gracefully

## 6) Performance Guide
- Use Context + useSyncExternalStore; subscribe via selectors to minimize re‑renders
- Perform chart updates imperatively inside subscription callback
- Avoid expensive derivations in render; pre‑compute lightweight projections if needed
- Consider micro‑throttle for low‑value consumers (e.g., 15–30 Hz) if jank observed

## 7) Error Handling & Resilience
- If WS frame lacks metrics: show placeholders; log once
- On parse error: surface non‑blocking toast/dev log; continue playback if possible
- Keep dropped counter visible in dev (BFFPerformanceMonitor)

## 8) Testing Strategy (FE)
Unit
- Store: subscribe/unsubscribe behavior; seek/play/pause transitions; selector stability
- TimelineScrubber: seeking calls with correct ISO; markers align with orders

Integration
- End‑to‑end (mock WS): ensure chart/metrics/orders stay within one frame of store time
- Determinism (finished run): two replays produce identical props sent to consumers
- Performance: ensure component render counts bounded at ~30 FPS

## 9) Minimal Sequence (ASCII)
1. WS frame → Worker → FrameNormalizer
2. store.setFrame(frame) updates currentSimTime and frame
3. Subscribers notified
4. Chart updates imperatively; panels re‑render on slice change
5. User scrubs → seek(ts) → backend snaps to nearest frame

## 10) File Layout (proposal)
- src/
  - store/playbackClock.ts (store impl, Context, hooks)
  - components/TimelineScrubber.tsx (finished‑run)
  - containers/RunPlayerContainer.tsx (wires WS + store)
  - services/ws.ts (unchanged API; ensure metrics forwarded)
  - workers/streamParser.ts (forward metrics)
  - types/streaming.ts, schemas/stream.ts (metrics fields)

## 11) Open Decisions (v1)
- Freeze metric semantics: run‑to‑date Sharpe (r_f = 0), MDD non‑decreasing
- Confirm orders carry symbol; optional symbols{} and portfolio{} available when cheap
- Range mapping: snap seek to nearest known frame on server

## 12) Acceptance (FE portion)
- Store contracts implemented; subscribers use selectors
- Chart/metrics/orders/timeline synced within one frame under normal load
- Scrubber seeks accurately; markers align; symbol focus behaves
- Graceful UI without metrics; dev tools show health

