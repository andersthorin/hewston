# Epic 6 — Frontend MVP: Acceptance Test Checklist
Epic ID: E6



Preconditions
- Backend Epics 4–5 complete; WS/SSE endpoints working
- Frontend app scaffolded with Vite + React + TS + Tailwind

Test Cases
1) Runs List view (AC)
   - Step: Open Runs List route
   - Verify: Fetches GET /backtests; displays rows (empty state on fresh DB)
   - Filters/pagination (if present) operate without errors

2) Run Detail playback (AC)
   - Step: Open a DONE run
   - Verify: Connects to WS /backtests/{id}/ws; plays frames; chart updates; equity and overlays render
   - Pause/Play/Speed/Seek controls invoke WS ctrl and reflect in UI
   - SSE fallback toggle (if implemented) switches to /stream and continues playback

3) Presentational components only (AC)
   - Verify: Components have no side-effects; data comes from containers/services (code review + lints)

4) Performance sanity
   - Verify: Smooth UI at ~30 FPS updates; no major jank on M2-class hardware

Pass/Fail Criteria
- Runs List and Run Detail function as described; UI adheres to presentational philosophy

Artifacts
- Screenshots or short recordings; component tree snapshot; lint output

