# Epic 6 — Frontend MVP

Goal
- Implement Runs List and Run Detail playback UI with presentational components and WS hook/Worker.

Why (Value)
- Provides the owner-operator dashboard to browse runs, replay results, and visualize equity/overlays.

Scope (In)
- Views: RunsList, RunDetail (compose containers + presentational components)
- Services: REST client (TanStack Query), WS hook (ws.ts), Worker to parse frames
- Components: charts (Lightweight Charts), metrics, overlays (orders/fills)
- No data creation/mutation in components; props-only rendering

Out of Scope
- Complex strategy controls; multi-symbol playback; auth

Deliverables
- Runs List shows rows from catalog
- Run Detail plays back a selected run at time-compressed speed with overlays

Acceptance Criteria
- WS hook connects to /backtests/{id}/ws and handles ctrl/events
- SSE fallback supported via Worker
- Presentational components have no side-effects; all data via containers/services

Dependencies
- Epic 5 (Playback Streaming)

Risks & Mitigations
- Performance with frequent updates → decimate at server; lightweight updates to chart
- UI logic creep → enforce presentational/container split; lint rules

Definition of Done
- Usable dashboard with list + playback; follows component philosophy and meets responsiveness expectations

References
- Architecture: Source Tree and Module Boundaries (frontend); Tech Stack; API Contracts

