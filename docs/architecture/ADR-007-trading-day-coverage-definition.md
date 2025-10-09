# ADR-007 — Trading‑Day Coverage Definition

Status
- Proposed

Context
- Universe selection relies on data coverage. Using calendar days overstates gaps and penalizes weekends/holidays. We must define coverage on trading days.

Decision
- Compute coverage% against US NYSE trading days in [from,to].
- Coverage% = observed_trading_days / expected_trading_days.

Details
- Trading calendar: use official NYSE calendar (or embed a minimal holiday list) to derive expected_trading_days.
- Observed days: count unique `date=YYYY-MM-DD` partitions under data/warehouse/quotes/venue=XNAS/symbol=SYMBOL.
- Partial-day handling: count as present if any quotes exist; later we may threshold by minimum records/day.

Thresholds
- Baseline threshold: ≥ 90% for inclusion (configurable per Epic 18).

Observability
- Persist per-symbol coverage diagnostics with expected vs observed and missing dates.

Consequences
- Fair coverage assessment and fewer false exclusions.

Links
- Epic 18 PRD/Plan
- ADR-005 Metrics and Guardrails Baseline

