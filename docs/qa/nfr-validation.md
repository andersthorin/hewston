Non‑Functional Requirements (NFR) Validation — Initial Report

Environment
- API base: http://127.0.0.1:8000
- Node: v22+ (for WS bench script)
- Host: fill in your machine specs (CPU/RAM)

How to run
1) Start API (and ensure at least one completed run exists)
- make start-backend
- Optionally create a run via API or CLI if none exist

2) REST latency (p50/p95)
- ./scripts/bench_rest.sh http://127.0.0.1:8000 200
- Output example:
  - [bench_rest] GET /backtests x200 → p50=4.2 ms p95=12.8 ms
  - [bench_rest] GET /backtests/<id> x200 → p50=3.7 ms p95=9.9 ms

3) WS streaming jitter/FPS
- node scripts/bench_ws.js ws://127.0.0.1:8000/backtests/<run_id>/ws 10
- Output JSON example:
  - { "frames": 280, "fps": 28.0, "p50_ms": 33, "p95_ms": 51 }

4) Storage footprint
- ./scripts/measure_sizes.sh data
- Example output:
  - derived: 120 MiB
  - backtests: 340 MiB
  - raw: 1.8 GiB
  - per-run (top 10):
    - run_abc 12000 KiB
    - run_def 8000 KiB

Acceptance targets (MVP)
- REST p95 under 100 ms on developer laptop
- WS effective playback 25–30 FPS with p95 inter‑frame under 80 ms (local)
- Storage per derived symbol-year under 1 GiB; per run artifacts under 100 MiB

Notes
- These scripts provide consistent, comparable local measurements.
- For CI/regression gates, consider running REST bench with a small COUNT (e.g., 20) to keep CI time low and detect regressions qualitatively.

