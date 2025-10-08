# Hewston BFF Feature Flags

This document lists relevant environment variables for Epic 15 (Backtests List UX and Metrics).

- BFF_FEATURE_LIST_METRICS (default: true)
  - Controls whether the BFF enriches the `/api/v1/backtests` list with summary metrics for terminal runs (DONE/COMPLETED).
  - When enabled, the BFF performs a bounded fan-out to `/backtests/{id}/metrics` for runs on the current page and attaches these fields when present:
    - total_return (fraction, e.g., 0.1234 → 12.34%)
    - max_drawdown (fraction, negative values indicate drawdown)
    - sharpe_ratio (number)
    - win_rate (fraction, e.g., 0.55 → 55%)
  - Enrichment uses a small in-memory TTL (120s) cache to reduce repeated calls.

Other related flags (for context):
- BFF_FEATURE_RUN_AGGREGATION (default: true)
- BFF_FEATURE_CHART_AGGREGATION (default: true)
- BFF_FEATURE_WEBSOCKET_PROXY (default: true)

How to set (examples):
- Shell: `export BFF_FEATURE_LIST_METRICS=false`
- .env: `BFF_FEATURE_LIST_METRICS=false`

Operational notes:
- Meta.backend_calls in the list response reflects the additional fan-out.
- If the backend list already includes metrics fields, the BFF will pass them through and only fill missing ones from the per-run metrics endpoint.

