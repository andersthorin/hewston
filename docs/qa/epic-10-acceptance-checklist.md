# Epic 10 — Nautilus Trader Full Implementation - Acceptance Checklist

**Epic ID**: E10
**Epic Title**: Nautilus Trader Backtest Engine - Full Implementation
**Status**: Ready for Development

## Epic Overview
Replace the current stub Nautilus adapter with a full Nautilus Trader integration that provides realistic backtesting execution, supports multiple strategies, and delivers comprehensive trading metrics for AI-powered strategy development.

## Stories Acceptance Criteria

### Story 10.1: Core Nautilus Engine Integration
**Status**: ⏳ Pending

#### Functional Acceptance
- [ ] **F10.1.1**: Real Nautilus Trader engine executes backtests (not stub calculations)
- [ ] **F10.1.2**: BacktestRunnerPort interface remains unchanged
- [ ] **F10.1.3**: 1m Parquet bars converted to Nautilus data feed format
- [ ] **F10.1.4**: Artifact output format matches existing structure

#### Integration Acceptance
- [ ] **I10.1.1**: `make backtest` command works unchanged
- [ ] **I10.1.2**: Artifact files (equity.parquet, orders.parquet, fills.parquet, metrics.json) generated correctly
- [ ] **I10.1.3**: Services layer integration maintains same interface

#### Quality Acceptance
- [ ] **Q10.1.1**: Integration tests verify real Nautilus engine execution
- [ ] **Q10.1.2**: Performance benchmark ≤30s for 1-year AAPL backtest maintained
- [ ] **Q10.1.3**: No regression in API endpoints or streaming functionality

### Story 10.2: Strategy Framework & Multiple Strategy Support
**Status**: ⏳ Pending (Depends on S10.1)

#### Functional Acceptance
- [ ] **F10.2.1**: Strategy registry/factory maps strategy_id to Nautilus strategy classes
- [ ] **F10.2.2**: SMA crossover converted to proper Nautilus strategy (results equivalent)
- [ ] **F10.2.3**: Framework production-ready with SMA; future strategies deferred

#### Integration Acceptance
- [ ] **I10.2.1**: Existing strategy_id parameter handling unchanged
- [ ] **I10.2.2**: Parameters dictionary pattern preserved
- [ ] **I10.2.3**: BacktestRunnerPort method signature maintained

#### Quality Acceptance
- [ ] **Q10.2.1**: Unit tests for each strategy with known expected outcomes
- [ ] **Q10.2.2**: Strategy registration documented with parameter specifications
- [ ] **Q10.2.3**: No regression in existing SMA crossover results

### Story 10.3: Enhanced Metrics & Analytics Engine
**Status**: ⏳ Pending (Depends on S10.1)

#### Functional Acceptance
- [ ] **F10.3.1**: MVP metrics calculated: PnL and win rate
- [ ] **F10.3.2**: MetricsCalculator interface implemented for extensibility
- [ ] **F10.3.3**: Metrics extracted from Nautilus performance analytics

#### Integration Acceptance
- [ ] **I10.3.1**: Existing metrics.json format preserved (backward compatible)
- [ ] **I10.3.2**: Database unchanged for MVP; existing upsert pattern continues (no new columns)
- [ ] **I10.3.3**: BFF metrics API responses include new metrics without breaking changes

#### Quality Acceptance
- [ ] **Q10.3.1**: Unit tests for PnL and win rate calculations with known expected values
- [ ] **Q10.3.2**: MetricsCalculator interface documented for custom metrics
- [ ] **Q10.3.3**: No regression in frontend metrics display

## Epic-Level Integration Tests

### End-to-End Workflow Validation
- [ ] **E2E10.1**: Complete backtest workflow (data → Nautilus → artifacts → streaming) works
- [ ] **E2E10.2**: SMA strategy executes via registry/factory using strategy_id selection
- [ ] **E2E10.3**: Enhanced metrics appear correctly in frontend after backtest completion

### Backward Compatibility Validation

### E2E Procedure (MVP)

Preconditions:
- 1-year, 1-minute OHLCV bars exist for the chosen dataset (e.g., AAPL) in the catalog
- Environment: Apple Silicon dev box (M1/M2), Python 3.11
- Feature flag: `HEWSTON_USE_NAUTILUS_STUB=false` to use real Nautilus engine

Steps:
1. Prepare data (ensure bars are present for the symbol and date window)
2. Execute backtest using the existing CLI/Make target (example):
   - Dataset: `AAPL`
   - Strategy: `sma_crossover`
   - Params: `{ "fast": 20, "slow": 50 }`
3. Verify artifacts generated under the run directory:
   - equity.parquet, orders.parquet, fills.parquet, metrics.json
4. Validate metrics.json contains:
   - `total_return` (float), `win_rate` (float)
5. Validate equity.parquet schema: `ts_utc`, `value`
6. Validate orders/fills parquet fields (per Architecture: Artifact Mapping)
7. Check streaming playback still functions for the run
8. Measure execution time ≤ 30s (1-year, AAPL) with minimal logging


- [ ] **BC10.1**: Existing backtests in database continue to display correctly
- [ ] **BC10.2**: API responses maintain same structure with additional fields
- [ ] **BC10.3**: Frontend components work with both old and new metrics format

### Performance Validation
- [ ] **P10.1**: Nautilus engine performance meets or exceeds stub performance (≤30s baseline)
- [ ] **P10.2**: Memory usage remains within acceptable bounds for 1-year datasets
- [ ] **P10.3**: Multiple concurrent backtests don't degrade performance significantly

## Risk Mitigation Verification

### Integration Risk Controls
- [ ] **R10.1**: Feature flag or environment variable allows rollback to stub implementation
- [ ] **R10.2**: Comprehensive integration tests prevent breaking existing functionality
- [ ] **R10.3**: No DB migration required for MVP; future migrations must be backward compatible

### Performance Risk Controls
- [ ] **R10.4**: Performance benchmarks automated and monitored
- [ ] **R10.5**: Memory profiling confirms no significant leaks or bloat
- [ ] **R10.6**: Timeout mechanisms prevent runaway backtests

## Documentation Requirements

### Technical Documentation
- [ ] **D10.1**: Nautilus integration architecture documented
- [ ] **D10.2**: Strategy framework usage guide created
- [ ] **D10.3**: MetricsCalculator interface and custom metrics guide
- [ ] **D10.4**: Migration guide from stub to real Nautilus implementation

### API Documentation
- [ ] **D10.5**: Enhanced metrics schema documented in API reference
- [ ] **D10.6**: Strategy parameter specifications documented
- [ ] **D10.7**: Error handling and troubleshooting guide updated

## Deployment Readiness

### Configuration Management
- [ ] **C10.1**: Nautilus Trader library properly pinned in requirements
- [ ] **C10.2**: Environment variables documented for configuration
- [ ] **C10.3**: No DB migration required for MVP

### Monitoring & Observability
- [ ] **M10.1**: Logging enhanced for Nautilus engine operations
- [ ] **M10.2**: Metrics collection for strategy execution performance
- [ ] **M10.3**: Error tracking for Nautilus integration issues

## Epic Definition of Done

### Functional Completeness
- [ ] All story acceptance criteria met
- [ ] Real Nautilus Trader engine executing backtests
- [ ] Strategy framework in place with SMA strategy supported
- [ ] MVP metrics (PnL and win rate) calculated and persisted

### System Integrity
- [ ] No regression in existing functionality (API, streaming, frontend)
- [ ] Backward compatibility maintained for existing data
- [ ] Performance benchmarks met or exceeded

### Quality Assurance
- [ ] Full test coverage including unit, integration, and end-to-end tests
- [ ] Documentation complete and accurate
- [ ] Code review completed and approved

### Operational Readiness
- [ ] Deployment scripts and migrations ready
- [ ] Monitoring and logging configured
- [ ] Rollback procedures documented and tested

## Sign-off Requirements

### Technical Sign-off
- [ ] **Development Team**: All acceptance criteria verified
- [ ] **QA Team**: Test suite passes, no critical issues
- [ ] **Architecture Review**: Integration patterns approved

### Business Sign-off
- [ ] **Product Owner**: Epic goals achieved, value delivered
- [ ] **Stakeholders**: Enhanced metrics meet requirements for strategy evaluation

---

**Epic Completion Date**: _____________
**Final Status**: ⏳ In Progress | ✅ Complete | ❌ Failed
**Notes**: _________________________________
