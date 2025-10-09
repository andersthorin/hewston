# Epic 16 Addendum — Architect Review

Key Additions
- Plan JSON schema (v1) with plan_hash for idempotency; see ADR-008.
- Rate limiting/backpressure: cap concurrent jobs per user; return 429 with retry-after.
- Plan caching/TTL: verify freshness or expire plans (e.g., 24h) before start.
- Standard reason codes: COVERAGE_LOW, MIN_TRADES, TURNOVER_HIGH, INVALID_METRICS, MAX_DRAWDOWN, etc.

Plan Schema (excerpt)
```json
{
  "version": "1",
  "from": "YYYY-MM-DD", "to": "YYYY-MM-DD",
  "universe": {"included": ["AAPL"], "excluded": [{"symbol": "TSLA", "reason": "COVERAGE_LOW"}]},
  "strategies": [{"id": "sma_crossover", "params": {"fast": 10, "slow": 20}}],
  "guardrails": {"checks": [{"name": "coverage", "ok": true, "details": {}}]},
  "plan_hash": "sha256:..."
}
```

New Stories
- 16.7 — Idempotency via plan_hash and duplicate detection
- 16.8 — Rate limiting/backpressure for concurrent job submissions

References
- ADR-008 Plan Schema and Manifest Versioning
- ADR-005 Metrics & Guardrails Baseline

