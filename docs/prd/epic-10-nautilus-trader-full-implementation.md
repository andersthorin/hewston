# Epic 10 — Nautilus Trader Backtest Engine - Full Implementation


## Documentation Package Overview
- Architecture: [docs/architecture/nautilus-integration-architecture.md](../architecture/nautilus-integration-architecture.md)
- User Stories: [docs/stories/10.1.story.md](../stories/10.1.story.md), [docs/stories/10.2.story.md](../stories/10.2.story.md), [docs/stories/10.3.story.md](../stories/10.3.story.md)
- QA Acceptance Checklist: [docs/qa/epic-10-acceptance-checklist.md](../qa/epic-10-acceptance-checklist.md)

## Goal
Replace the current stub Nautilus adapter with a full Nautilus Trader integration that provides realistic backtesting execution, supports multiple strategies, and delivers comprehensive trading metrics for AI-powered strategy development.

## Why (Value)
- **Professional-Grade Backtesting**: Real execution simulation with proper order handling, slippage, and fees
- **Multiple Strategy Support**: Pluggable architecture enabling AI-powered strategy development
- **Analytics (MVP)**: Core metrics PnL and win rate; modular design to add Sharpe and max drawdown later
- **Future-Ready Foundation**: Modular design supporting custom metrics and advanced strategies

## Scope (In)
- Replace `backend/adapters/nautilus.py` stub with real Nautilus Trader engine integration
- Implement pluggable strategy framework with SMA strategy; enable future additional strategies
- Enhance metrics calculation with comprehensive trading analytics
- Maintain backward compatibility with existing BacktestRunnerPort interface
- Preserve artifact format and streaming integration

## Out of Scope
- Frontend UI changes (existing streaming/charts continue working)
- New data ingestion methods (uses existing 1m bars)
- Multi-asset backtesting (single symbol focus for MVP)
- Advanced risk metrics (VaR, beta, correlation - future enhancement)

## Deliverables
- **Real Nautilus Engine**: Professional backtesting execution replacing stub calculations
- **Strategy Framework**: Registry/factory supporting multiple strategies with AI agent integration points
- **Enhanced Metrics**: Comprehensive analytics with modular calculation system
- **Backward Compatibility**: Existing API, streaming, and artifact formats preserved

## Stories

### Story 10.1: Core Nautilus Engine Integration
**Goal**: Replace stub adapter with real Nautilus Trader engine execution
- Replace `NautilusBacktestRunner` implementation with actual Nautilus engine
- Convert 1m Parquet bars to Nautilus-compatible data feed
- Maintain BacktestRunnerPort interface compatibility
- Ensure artifact output format consistency

### Story 10.2: Strategy Framework & Multiple Strategy Support
**Goal**: Create pluggable strategy architecture for multiple trading strategies
- Implement strategy registry/factory pattern
- Convert existing SMA crossover to proper Nautilus strategy
- Prepare examples/placeholders for future strategies (no additional strategies required this epic)
- Enable AI agent integration points for future strategies

### Story 10.3: Enhanced Metrics & Analytics Engine
**Goal**: Implement comprehensive trading metrics with modular calculation system
- Calculate PnL and win rate from Nautilus results (MVP); design for future metrics
- Create MetricsCalculator interface for extensibility
- Enhance artifact persistence with richer metrics data
- Maintain backward compatibility with existing metrics format

## Acceptance Criteria
- **Functional**: Real Nautilus Trader engine executing backtests with multiple strategies
- **Performance**: ≤30s for 1-year AAPL backtest (maintain current benchmark)
- **Compatibility**: Existing API endpoints, streaming, and frontend functionality unchanged
- **Metrics (MVP)**: PnL and win rate calculated and persisted; architecture allows adding Sharpe and max drawdown later
- **Extensibility**: Modular architecture supporting future AI-powered strategies

## Dependencies
- **Epic 4**: Existing backtest runner and artifacts (foundation)
- **Epic 5**: Streaming infrastructure (must remain compatible)
- **Epic 6**: Frontend integration (must continue working)

## Risks & Mitigations
- **Nautilus Integration Complexity**:
  - *Risk*: Complex library integration breaking existing functionality
  - *Mitigation*: Incremental implementation, extensive testing, feature flags for rollback
- **Performance Regression**:
  - *Risk*: Real engine slower than stub calculations
  - *Mitigation*: Performance benchmarking, optimization, maintain ≤30s target
- **Interface Compatibility**:
  - *Risk*: Breaking changes affecting downstream systems
  - *Mitigation*: Strict interface preservation, comprehensive integration tests

## Definition of Done
- **Engine Integration**: Real Nautilus Trader executing backtests with proper simulation
- **Strategy Support**: Multiple strategies working through pluggable architecture
- **Metrics Enhancement**: Comprehensive analytics calculated and persisted
- **System Integrity**: No regression in existing API, streaming, or frontend functionality
- **Performance**: Benchmark targets met (≤30s for baseline backtest)
- **Documentation**: Updated with new capabilities and integration patterns
- **Testing**: Full test coverage including integration and performance tests

## Technical Architecture

### Current State
```
BacktestRunnerPort → NautilusBacktestRunner (stub) → Polars calculations → Basic metrics
```

### Target State
```
BacktestRunnerPort → NautilusBacktestRunner (real) → Nautilus Engine → Strategy Framework → Enhanced metrics
```

### Integration Points
- **Data Feed**: 1m Parquet bars → Nautilus data format conversion
- **Strategy Registry**: strategy_id → Nautilus strategy class mapping
- **Metrics Pipeline**: Nautilus results → MetricsCalculator → artifact persistence
- **Artifact Format**: Maintain existing equity.parquet, orders.parquet, fills.parquet, metrics.json

## References
- **Architecture**: docs/architecture.md (BacktestRunnerPort interface)
- **Current Implementation**: backend/adapters/nautilus.py (stub to replace)
- **Data Models**: backend/domain/models.py (BacktestMetrics, artifacts)
- **Catalog Schema**: backend/adapters/sqlite_catalog.py (metrics persistence)
- **Tech Stack**: docs/architecture/tech-stack.md (Nautilus Trader integration)

## Success Metrics
- **Execution Quality**: Real backtesting with proper order simulation
- **Strategy Flexibility**: Pluggable architecture in place; SMA strategy implemented; future strategies can be added without core changes
- **Analytics Depth (MVP)**: 2 core metrics (PnL, win rate) calculated; extensible to add more later
- **System Stability**: Zero regression in existing functionality
- **Performance**: Maintain or improve current execution speed
- **Extensibility**: Clear path for AI agent strategy integration
