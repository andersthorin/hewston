# Epic 5 — Playback Streaming (WebSocket primary, SSE fallback)

Goal
- Stream time-compressed playback frames over WebSocket with in-band control, with SSE fallback for compatibility.

Why (Value)
- Delivers the “feels live” experience and validates transport, backpressure, and server-side decimation.

Scope (In)
- services/streamer.py: frame producer/decimator
- adapters/streams.py: WebSocket endpoint handler + SSE endpoint
- Control: play, pause, seek, speed
- Backpressure policy: target ≈30 FPS, drop-oldest on lag
- SSE fallback at /backtests/{id}/stream

Out of Scope
- Frontend UI; multi-stream playback

Deliverables
- GET /backtests/{id}/ws streams frames; ctrl works
- GET /backtests/{id}/stream streams frame events (fallback)

Acceptance Criteria
- A completed run can be played via WS at ≈30 FPS with stable jitter
- SSE fallback emits frames for the same run

Dependencies
- Epic 4 (Backtest Runner & Artifacts)

Risks & Mitigations
- WS jitter and client jank → decimation, drop-oldest, measure frames sent/dropped
- Memory pressure → stream small payloads and avoid buffering

Definition of Done
- WS protocol stable; ctrl semantics documented; SSE fallback functional

References
- Architecture: Playback Channel Protocol (WebSocket); API Contracts; NFRs (latency, FPS)

