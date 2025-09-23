# Playback Streaming Protocol (WebSocket primary, SSE fallback)

Status: v0.1 — Authoritative contract for playback channels. Aligns with PRD §2, §4 and Architecture §Playback Channel Protocol.

## Endpoints
- WebSocket (primary): GET /backtests/{id}/ws
- SSE fallback:        GET /backtests/{id}/stream?speed=60

## Goals and Constraints
- Target: ~1 year of data → ~60 seconds playback.
- Server decimates to ≈30 FPS target; client drops oldest on lag.
- Bidirectional control only over WebSocket; SSE is server→client only.

## Message Shapes

Client → Server (WS control)
- Envelope
```
{ "t": "ctrl", "cmd": "play|pause|seek|speed", "pos": "ISO-UTC|frameIndex?", "val": number? }
```
- Semantics
  - play: resume streaming
  - pause: pause streaming (server may continue preparing next frame)
  - speed: set target compression factor (e.g., 60 ⇒ ~1y→~60s)
  - seek: jump to timestamp or frame index; server snaps to nearest frame within range

Server → Client (WS/SSE)
- Frame
```
{ "t":"frame", "ts":"ISO-UTC", "ohlc": { ... }, "orders": [ ... ], "equity": number, "dropped": integer }
```
- Heartbeat
```
{ "t": "hb" }
```
- End of stream
```
{ "t": "end" }
```
- Error
```
{ "t": "err", "code": "RANGE|RUN_NOT_FOUND|...", "msg": "human-readable", "details": { ... } }
```

SSE framing
- Content-Type: text/event-stream
- Event name: frame
- Payload: StreamFrame JSON (one per event)

Example SSE event
```
event: frame

data: {"t":"frame","ts":"2023-03-01T14:30:00Z","ohlc":{...},"orders":[],"equity":123.4,"dropped":0}
```

## Heartbeats and Timeouts
- Server sends `{ "t":"hb" }` every 5s when idle or paused.
- Client may echo `{ "t":"hb" }` (optional). Server drops connections after idle timeout (e.g., 30s without any message).

## Backpressure and Jank Control
- Server decimates frames to ≈30 FPS. On server lag, coalesce/skips older frames.
- Client should drop oldest buffered frames if UI can’t keep up and surface the `dropped` counter from frames.

## Error Semantics
- Use canonical codes from docs/api/error-codes.md
  - RANGE — out-of-range seek or before run is ready
  - RUN_NOT_FOUND — unknown id
  - VALIDATION — bad control payload
- On fatal errors, server may send `{ "t":"err" }` then close.

## Connection Lifecycle
- Connect → (optional) pause → play → stream frames → seek/speed as needed → end → close
- Reconnect behavior: client may reconnect and resume; server should support resuming from last known position when feasible.

## Versioning
- This protocol is versioned implicitly with the API. Breaking changes must be documented and coordinated across BE/FE.

