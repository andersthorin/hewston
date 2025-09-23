# Epic 5 — Playback Streaming: Acceptance Test Checklist
Epic ID: E5



Preconditions
- Completed run (DONE) exists with artifacts
- WS endpoint and SSE fallback implemented

Test Cases
1) WebSocket playback at ≈30 FPS (AC)
   - Step: Connect ws://127.0.0.1:8000/backtests/{run_id}/ws
   - Verify: Frames received at ~30 FPS average (sample over 10s)
   - Record: timestamped count to estimate FPS and jitter

2) Control: play/pause/seek/speed (AC)
   - Send `{ "t":"ctrl", "cmd":"pause" }` → stream stops (no frames) until play
   - Send `{ "t":"ctrl", "cmd":"play" }` → stream resumes
   - Send `{ "t":"ctrl", "cmd":"speed", "val": 120 }` → frame cadence accelerates
   - Send `{ "t":"ctrl", "cmd":"seek", "pos":"<ISO-UTC>" }` → stream jumps near target timestamp

3) Backpressure & dropped counter (AC)
   - Induce client lag (slow consumer) → verify `{ "dropped": N }` increments over interval

4) SSE fallback
   - Step: GET /backtests/{run_id}/stream?speed=60
   - Verify: text/event-stream emits `event: frame` with StreamFrame payloads

5) Error/end/heartbeat
   - Verify: `{ "t":"hb" }` period ~5s; `{ "t":"end" }` at completion; `{ "t":"err" }` on bad control

Non-Functional Validations
- WS jitter median ≤ 30 ms; P95 ≤ 80 ms (sample)
- CPU remains reasonable; no unbounded memory growth

Pass/Fail Criteria
- Controls work; FPS near target; SSE fallback functional; stability under lag

Artifacts
- Client logs (timestamps, counts); sample SSE transcript

