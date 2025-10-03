# BFF Backtests Module (Pilot Exemplar)

Purpose
- Define outbound port to backend and provide HTTPX adapter
- Keep routing/controllers in BFF thin and delegate to application layer (future)

Structure
- application/ports/backend_gateway.py — outbound port definition
- adapters/http/backend_gateway_httpx.py — HTTPX-based implementation

Notes
- Not wired in pilot; exemplar only. Wiring and use-cases to be added during batch refactors.

