# Epic 18 Plan — Equities Universe Management (XNAS)

Objective
- Discover viable symbols for a date range, compute coverage, and select the universe with explanations.

Phases and Tasks
1) Discovery (owner: BE)
   - Enumerate symbols under data/warehouse/quotes/venue=XNAS/symbol=*
   - For each symbol: list date partitions and compute coverage % in [from,to]
2) Filters (owner: BE)
   - Threshold coverage (e.g., ≥ 90%)
   - Cap max symbols per plan (configurable)
   - Optional: simple liquidity proxy (avg quote count/day)
3) Explanations & API (owner: BE)
   - Return included & excluded with reason codes
   - Integrate into propose_plan output
4) UI (owner: FE)
   - Show included/excluded lists in Plan Preview

Dependencies
- None (reads file system)

Acceptance Criteria
- Universe list returned with per-symbol coverage and reasons
- Plan Preview shows final set and exclusions

