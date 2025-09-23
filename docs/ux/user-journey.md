# User Journey (MVP)

Status: v0.1 — End-to-end flow aligning FE/BE with contracts.

## Primary flow: Create → List → Detail → Playback → Rerun
1) Create run (Backend/API)
   - POST /backtests { dataset_id OR (symbol, from, to), strategy_id, params, seed, slippage_fees, speed }
   - Response: 202 { run_id, status: "QUEUED" } | 200 { run_id, status: "EXISTS" }
   - Error codes: VALIDATION, CONFLICT, IDP_CONFLICT
   - Artifacts path reserved: data/backtests/{run_id}/

2) List runs (UI: Runs List)
   - GET /backtests?symbol=&from=&to=&strategy_id=&limit=&offset=
   - Display: table with symbol, date range, strategy, status, created_at, duration
   - Empty state: guidance to create a run; Error state: render error code/message

3) View run (UI: Run Detail)
   - GET /backtests/{id} → metadata and artifact refs
   - Show: equity chart, overlays for orders/fills (when available)
   - Actions: Connect to playback; rerun from manifest

4) Playback (WS primary; SSE fallback)
   - WS: GET /backtests/{id}/ws → ctrl (play/pause/seek/speed), frames (ohlc, orders, equity, dropped), hb, end, err
   - SSE: GET /backtests/{id}/stream?speed=60 → event: frame with StreamFrame payload
   - Targets: avg ≈30 FPS; p95 dropped ≤5%; p99 latency ≤200 ms

5) Rerun from manifest (UI action)
   - Read run_manifest.json; prefill POST /backtests body; submit to create a new run

## UI states to design (wireframes)
- Runs List: normal, empty, loading, error
- Run Detail: loading metadata, error (RUN_NOT_FOUND), waiting for playback, playing, paused, end
- Controls: play/pause, seek, speed; show error toast on {t:"err"}

## Links
- Baselines: ../prd/features/00-baselines.md
- API: ../api/openapi.yaml; Errors: ../api/error-codes.md; Protocol: ../api/ws-protocol.md
- Architecture: ../architecture.md; FE boundaries: ../architecture/source-tree.md

