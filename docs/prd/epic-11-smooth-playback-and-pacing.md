# Epic 11 — Smooth Playback and Pacing (WS primary, SSE fallback)

Goal
- Deliver visually smooth, clocked playback of historical runs at compressed time (e.g., ~1h per ~150ms), eliminating bursty rendering while keeping existing transports.

Why (Value)
- Users perceive quality via smoothness, not raw throughput. Even pacing improves comprehension of charts/metrics and reduces UI jank.

Decisions
- Keep raw WebSocket for frame data; keep SSE as fallback.
- Do not adopt socket.io for high‑rate frame transport; consider it only for control-plane if complexity grows.
- Smoothness is achieved at the edges: frontend render scheduler + optional BFF edge pacer.

Scope (In)
- Frontend ring buffer + requestAnimationFrame scheduler; drop-oldest policy; configurable cadence.
- Dev monitor: render jitter (p50/p95), buffer size, dropped.
- Optional BFF pacer (latest-frame scheduler @ fixed cadence).
- Backend: optional `seq` and cadence/fps params.

Out of Scope
- Changing charting library.
- True real-time streaming; live market ingestion.

Deliverables
- FE implementation in `frontend/src/services/ws.ts` with bounded buffer + rAF scheduler (done).
- Tests pass (type-check + vitest).
- Stories S11.1–S11.4 and QA gates added.

Acceptance Criteria
- Visual inter-frame p50 ≤ 25 ms and p95 ≤ 60 ms at target cadence (~6–8 FPS for 1h/150ms), measured in dev monitor.
- No sustained stutter under normal conditions; buffer remains within bounds; dropped policy is latest-wins.
- WS/SSE functionality unchanged; controls (play/pause/seek/speed) remain functional.

Risks & Mitigations
- Risk: double pacing (backend+BFF+FE). Mitigation: FE scheduler is tolerant; optional BFF pacer kept off by default.
- Risk: buffer growth → memory. Mitigation: strict cap and drop-oldest.

References
- Epic 5 (WS primary, SSE fallback) and existing QA performance plan.
- Implementation: `frontend/src/services/ws.ts`.

