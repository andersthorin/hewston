# Epic 17 Plan — Strategy Expansion and Registry

Objective
- Add Momentum, RSI Mean Reversion, and Breakout strategies with schemas/defaults and registry entries.

Phases and Tasks
1) Strategy scaffolds (owner: BE)
   - Create modules: momentum.py, rsi_mr.py, breakout.py
   - Implement as Nautilus `Strategy` subclasses (single-instrument)
2) Parameter schemas (owner: BE)
   - Define pydantic or JSON-schema for each strategy
   - Validate in StrategyFactory prior to instantiation
3) Registry integration (owner: BE)
   - Register `momentum`, `rsi_mr`, `breakout` ids
   - Expose defaults for Agentic Mode
4) Tests & fixtures (owner: QA/BE)
   - Smoke tests on small samples
   - Golden-metrics snapshots with tolerances
5) Docs (owner: Arch/BE)
   - Add strategy notes and examples in docs/architecture/strategy-notes.md

Dependencies
- Epic 19 sizing policy hooks

Acceptance Criteria
- Strategies build, run, and emit sensible trades with defaults
- Registered and selectable by orchestrator
- Tests pass with golden metrics

