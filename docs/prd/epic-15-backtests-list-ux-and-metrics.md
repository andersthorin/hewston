# Epic 15 — Backtests List UX: Background Execution and Inline Metrics (Brownfield)

Status: Draft v0.1
Owner: Product (PO)
Theme: Improve /backtests usability while runs execute asynchronously

## Epic Goal
Enable users to start a backtest from the /backtests page without being forced into the detail view, and make the list powerful enough to be the default destination by surfacing run status and key performance metrics in-line.

## Existing System Context
- Frontend (Vite/React/TS + Tailwind):
  - /backtests lists runs and currently always renders a "View" button.
  - On create, the UI navigates immediately to /backtests/{id} and waits for completion before replay controls (“play”) become useful.
  - React Query polls lists/details while non‑terminal.
- BFF (FastAPI):
  - GET /api/v1/backtests proxies backend list (adds light normalization and metadata).
  - GET /api/v1/backtests/{id}/complete aggregates details + metrics + equity + orders via multiple backend calls.
- Backend (FastAPI):
  - POST /backtests enqueues a run and returns { run_id, status } with 202.
  - GET /backtests lists summaries (run_id, status, symbol, created_at, run_from/to, duration_ms).
  - GET /backtests/{id}/metrics returns the metrics.json artifact with keys like total_return, max_drawdown, win_rate, sharpe_ratio, etc.
- Data/Artifacts: metrics.json is written at run completion by the Nautilus backtest job.

## Enhancement Details
What’s being changed
- Creation UX: Do not auto‑navigate to detail on successful create. Instead, add the new run to the list and show a "Queued/Running" badge while it executes. 
- Action gating: Suppress the “View” button until the run reaches a terminal status (DONE/COMPLETED or ERROR/FAILED). 
- Inline metrics: For completed runs, display key summary metrics (total_return, max_drawdown, sharpe_ratio, win_rate) directly in the table so detail view is optional.

Integration approach
- Frontend: Remove navigate() after create; rely on existing invalidate + polling to reflect the new row and its evolving status. Update BacktestsTable to render badges and gate the View action. Add metrics columns with sensible formatting and placeholders while unavailable.
- BFF: Enhance GET /api/v1/backtests to optionally enrich summaries with metrics for terminal runs by calling backend GET /backtests/{id}/metrics for items in the current page (bounded fan‑out, small N). Protect with a feature flag and cache briefly.
- Backend: No schema changes required; reuse existing /backtests/{id}/metrics endpoint and metrics.json fields.

Success criteria
- From /backtests, users can start runs and continue working without context loss.
- New runs appear promptly with "Queued" then "Running" badges; polling stops when terminal.
- The list shows total_return, max_drawdown, win_rate, and sharpe_ratio for completed runs; detail view becomes optional for quick triage.
- No noticeable regressions in performance or reliability for the list endpoint (target p50 < 250 ms for first page under typical data volumes).

Best‑practice notes (informed by Nautilus Trader docs and common UX patterns)
- Metrics mapping: Use Nautilus portfolio analyzer outputs — returns/general stats typically expose Sharpe Ratio (252 days), Profit Factor, Win Rate; backend already promotes total_return/max_drawdown/win_rate and sharpe_ratio.
- Background jobs UX: Avoid forced navigation; add optimistic row then poll; use status badges and enable heavy actions only after terminal completion; provide optional toast with a “View” link when a run finishes.
- Accessibility: Announce status changes politely (ARIA live region) and ensure badges have discernible text/contrast.

## Stories
1. Story 15.1 — Frontend: Non‑navigating create + status badges + gated View
2. Story 15.2 — BFF: List enrichment with summary metrics for terminal runs
3. Story 15.3 — Frontend: Render inline metrics on /backtests with formatting

## Compatibility Requirements
- Existing APIs remain unchanged (no breaking changes).
- DB schema remains backward compatible; no migration required.
- UI follows existing component patterns and styling.
- Performance impact minimal; enrichment bounded to visible page only and cached.

## Risk Mitigation
- Primary risk: Increased latency on list when enriching metrics.
  - Mitigation: Enrich only terminal items on the current page; add short‑TTL cache; wrap under feature flag; degrade gracefully on per‑item fetch errors (show placeholders).
- Rollback plan: Disable the enrichment feature flag to revert to baseline list; FE can re‑enable navigate() post‑create behind a FE flag if needed.

## Definition of Done
- All three stories merged behind appropriate flags.
- UX validated: no auto‑navigation; badges and gated view behave as intended.
- Metrics visible and correct for completed runs; placeholders render for active runs.
- Tests: unit + integration for BFF enrichment; FE component tests for table rendering/gating; E2E smoke for create→list→complete.
- Docs updated: PRD epic and stories, and UI spec screenshots if available.

