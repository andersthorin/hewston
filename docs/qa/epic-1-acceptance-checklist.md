# Epic 1 — Backend Skeleton: Acceptance Test Checklist
Epic ID: E1



Preconditions
- Code scaffolded per docs/architecture.md Source Tree
- Makefile available; uv/uvicorn installed (dev box)

Test Cases
1) Health endpoint (AC1)
   - Step: `make start-backend`
   - Verify: GET http://127.0.0.1:8000/healthz → 200 and JSON {"status":"ok"}
   - Negative: Unknown route returns 404 with error shape

2) WebSocket echo endpoint (AC2)
   - Step: Connect WS ws://127.0.0.1:8000/backtests/test-run/ws
   - Verify: Server sends `{ "t":"hb" }` heartbeat roughly every 5s
   - Step: Send `{ "t":"ctrl", "cmd":"play" }`
   - Verify: Receives identical payload + `{ "echo": true }`
   - Negative: Send `{}` → receives `{ "t":"err", "code":"BAD_PAYLOAD" }`

3) Structure & non-blocking (AC3, AC4)
   - Verify: Files exist: backend/app/main.py; backend/api/routes/backtests.py; backend/api/routes/health.py
   - Run: `make lint` → no errors in backend/
   - Manual: WS echo does not peg CPU; closing socket cleans up without errors

Pass/Fail Criteria
- All above pass; no unhandled exceptions in server logs; code layout matches Architecture

Artifacts
- Optional: Save a short screencast/log transcript of WS session

