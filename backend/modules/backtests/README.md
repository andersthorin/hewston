# Backtests Module (Pilot Exemplar)

Purpose
- Demonstrate hexagonal boundaries via thin HTTP controllers delegating to application/services
- Preserve existing API contracts; no behavior change in pilot

Structure
- adapters/http/controllers.py — thin functions mapping HTTP to application services
- application, domain, infrastructure — to be populated during batch refactors

Notes
- Routes are wired in backend/api/routes/backtests.py to call these controllers
- Full migration will move services and ports into application/ports and adapters

