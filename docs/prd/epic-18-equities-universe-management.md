# Epic 18 — Equities Universe Management (XNAS)

Goal
- Auto-select a viable equity symbol set for a given date range using warehouse availability and coverage guardrails.

Why (Value)
- Ensures backtests run on symbols with sufficient, reliable data; scales naturally as new symbols arrive.

Scope (In)
- Discovery: enumerate symbols from data/warehouse/quotes/venue=XNAS/symbol=*/date=*
- Coverage: compute % of days present within [from, to]; threshold (e.g., ≥ 90%)
- Liquidity proxies (optional, later): average quote frequency or spread proxy to filter illiquid symbols
- Universe Agent:
  - Returns included symbols and excluded symbols with reasons (insufficient coverage, no data, etc.)
- UI: display included/excluded lists with explanations

Scope (Out)
- Non-XNAS venues
- Fundamental or sector-based filters (future enhancement)

Design
- Start with your current 5 symbols; logic scales automatically as directories appear
- Acceptable dates derive from available partitions under symbol/.../date=YYYY-MM-DD
- Provide a cap on max symbols per run plan (configurable; default small for M1)

Acceptance Criteria
- Universe discovery produces a list of eligible symbols for the date range with coverage %
- Exclusions list contains reasons per symbol
- Exposed in Plan Preview and persisted in manifest

Milestones
1) Symbol discovery + coverage computation
2) Threshold filter + explanations
3) UI exposure + manifest integration

