# Epic 1: Foundation & Core Infrastructure

## Goal
Establish the project foundation and deliver a minimal end-to-end vertical slice to validate toolchain and workflow.

## Stories (Draft)
1. Project bootstrap and Makefile targets (setup/start/data/backtest) available
2. Backend skeleton with health route (`GET /health`) returns 200
3. PRD-visible API stub: `POST /backtests` accepts payload and returns stub run_id
4. Docs updates: README pointers to Brief and PRD shards

## Acceptance Criteria (Draft)
- AC1: `make start` runs backend placeholder and serves health
- AC2: `make data` is a no-op with clear help output (until Epic 2)
- AC3: `POST /backtests` responds with 202 + run_id placeholder
- AC4: Documentation updated with instructions to run the vertical slice

