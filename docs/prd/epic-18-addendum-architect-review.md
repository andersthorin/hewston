# Epic 18 Addendum — Architect Review

Key Additions
- Trading-day coverage: compute coverage% against NYSE trading days (not calendar days); see ADR-007.
- Persist per-symbol coverage diagnostics: expected vs observed days, missing dates.
- Instrument ID normalization: use canonical format SYMBOL.XNAS and validate presence in warehouse before inclusion.

New Stories
- 18.4 — Trading calendar coverage computation
- 18.5 — Instrument ID normalization and validation

References
- ADR-007 Trading-Day Coverage Definition
- ADR-008 Plan Schema and Manifest Versioning

