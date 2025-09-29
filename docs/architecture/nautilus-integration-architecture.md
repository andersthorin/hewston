# Nautilus Trader Integration Architecture

**Document Version**: 1.0
**Epic**: E10 - Nautilus Trader Full Implementation
**Last Updated**: 2025-09-29

## Overview

This document describes the architecture for integrating Nautilus Trader as the core backtesting engine, replacing the current stub implementation while maintaining backward compatibility and system integrity.

## Current State vs Target State

### Current Architecture (Stub Implementation)
```
BacktestRunnerPort → NautilusBacktestRunner (stub) → Polars calculations → Basic metrics
                                                   ↓
                                            Simple SMA crossover logic
                                                   ↓
                                            Manual order/fill generation
```

### Target Architecture (Full Nautilus Integration)
```
BacktestRunnerPort → NautilusBacktestRunner (real) → Nautilus BacktestEngine → Strategy Framework
                                                                              ↓
                                                    Strategy Registry → Multiple Strategies
                                                                              ↓
                                                    Nautilus Performance Analytics → Enhanced Metrics
```

## Version and Dependency Targets

- Nautilus Trader: 0.10.x (aligns with project tech stack)
- Python: 3.11
- Apple Silicon (M1/M2) support: prefer prebuilt wheels; avoid compiling heavy deps on dev laptops
- Package manager: uv/pip with pinned lockfile; CI validates reproducible installs


## Integration Components

### 1. Data Feed Adapter

**Purpose**: Convert 1m Parquet bars to Nautilus-compatible data format

```python
class ParquetDataAdapter:
    """Converts Parquet bars to Nautilus data feed format."""

    def load_bars(self, dataset_id: str, from_date: str | None, to_date: str | None) -> pl.DataFrame:
        """Load 1m OHLCV bars (Polars) from catalog-resolved Parquet for the given dataset and window."""

    def convert_to_nautilus(self, bars_df: pl.DataFrame) -> list[Bar]:
        """Convert Polars DataFrame rows to Nautilus Bar objects with correct TZ and symbol."""
### Parquet Schema Mapping (MVP)

- Required columns: `ts|t` (timestamp, UTC or NY TZ), `o` (open), `h` (high), `l` (low), `c` (close), `v` (volume)
- Timestamp handling: accept `t` or `ts`; normalize to timezone-aware UTC; ensure strict sort by time
- Symbol: derive from dataset_id; attach to Nautilus Bar instrument
- Data validation: non-decreasing timestamps, no NaNs in OHLC; volume >= 0
- Windowing: apply `from_date`/`to_date` inclusive filtering before conversion



    def create_data_engine(self, bars: list[Bar]) -> DataEngine:
        """Create Nautilus DataEngine with historical bars."""
```

**Key Responsibilities**:
- Read 1m OHLCV bars from Parquet files
- Convert to Nautilus Bar objects with proper timestamps
- Handle timezone conversion (America/New_York)
- Validate data integrity and completeness

### Instrument Mapping (MVP)

- Derive instrument from dataset_id using MIC-based convention for US equities
- Mapping rule: `instrument_id = f"{dataset_id.upper()}.XNAS"` (NASDAQ default)
- Rationale: Simple, standard, and aligns with Nautilus examples (e.g., AAPL.XNAS)
- Future: Support venue-specific mapping per dataset when needed

### Timestamp Canonicalization (UTC)

- Canonical storage and processing timezone: UTC
- Input bars: expect `t|ts` as tz-aware UTC; if NY/local, normalize to UTC
- Strictly sort by timestamp and validate monotonic non-decreasing order
- Preserve UTC for all generated artifacts (orders/fills/equity)

### Slippage and Fees Model (MVP)

- No reliable spread in 1m bars; use simple configurable constants
- Parameters (defaults): `slippage_bps=1`, `fee_bps=1`
- Application:
  - Slippage adjusted fill price: `buy: px*(1+slip)` / `sell: px*(1-slip)` where `slip=slippage_bps/10_000`
  - Fees on notional: `fee = qty * fill_px * fee_bps/10_000`
- Future: Replace with spread-based model from TBBO when available

### Trade Pairing and Win Rate (MVP)

- Position model: long-only, no pyramiding (position in {0,1})
- Trade definition: entry at 0→1 transition; exit at 1→0; PnL = sum fills between entry/exit minus fees
- Win rate: `wins / total_trades`, where a win has positive PnL; 0 if no closed trades
- Future: Extend to shorts and multi-unit FIFO pairing

### 2. Strategy Framework

**Purpose**: Pluggable architecture for multiple trading strategies

```python
class StrategyRegistry:
    """Registry for mapping strategy_id to Nautilus strategy classes."""

    def register_strategy(self, strategy_id: str, strategy_class: Type[Strategy]):
        """Register a strategy class with an identifier."""

    def create_strategy(self, strategy_id: str, params: Dict[str, Any]) -> Strategy:
        """Create and configure strategy instance."""

class StrategyFactory:
    """Factory for creating configured strategy instances."""

    def __init__(self, registry: StrategyRegistry):
        self.registry = registry

    def build_strategy(self, strategy_id: str, params: Dict[str, Any]) -> Strategy:
        """Build strategy with parameter validation."""
```

**Supported Strategies (MVP and Future)**:
- MVP: **SMA Crossover** (converted from existing stub logic)
- Future: **Momentum** (price momentum with configurable lookback)
- Future: **Mean Reversion** (RSI-based mean reversion)

### 3. Nautilus Engine Integration

**Purpose**: Core backtesting execution using Nautilus Trader

```python
class NautilusBacktestRunner:
    """Real Nautilus Trader implementation of BacktestRunnerPort."""

    def __init__(self):
        self.data_adapter = ParquetDataAdapter()
        self.strategy_factory = StrategyFactory(StrategyRegistry())
        self.metrics_calculator = StandardMetricsCalculator()

    def run(self, *, dataset_id: str, strategy_id: str, params: Dict[str, Any],
            seed: int, from_date: str = None, to_date: str = None) -> Dict[str, Any]:
        """Execute backtest using Nautilus engine."""

        # 1. Load and convert data
        bars = self.data_adapter.convert_bars_to_nautilus(dataset_id, from_date, to_date)

        # 2. Create strategy
        strategy = self.strategy_factory.build_strategy(strategy_id, params)

        # 3. Configure and run backtest
        engine = self._create_backtest_engine(bars, strategy, seed)
        results = engine.run()

        # 4. Calculate metrics and format output
        return self._format_results(results)
```

### 4. Enhanced Metrics System

**Purpose**: Comprehensive trading analytics with extensible architecture

```python
class MetricsCalculator:
    """Interface for calculating trading metrics."""

    def calculate_metrics(self, backtest_result: BacktestResult) -> Dict[str, Any]:
        """Calculate metrics from Nautilus backtest results."""
        raise NotImplementedError

class StandardMetricsCalculator(MetricsCalculator):
    """Standard trading metrics implementation (MVP)."""

    def calculate_metrics(self, backtest_result: BacktestResult) -> Dict[str, Any]:
        # MVP metrics; extend with max_drawdown/sharpe later via pluggable calculators
        return {
            "total_return": self._calculate_total_return(backtest_result),
            "win_rate": self._calculate_win_rate(backtest_result),
        }
```

## Interface Compatibility

### BacktestRunnerPort Contract
The integration maintains exact compatibility with the existing interface:

```python
class BacktestRunnerPort(Protocol):
    def run(self, *, dataset_id: str, strategy_id: str, params: Dict[str, Any],
            seed: int) -> Dict[str, Any]:
        """Run a backtest and return structured result."""
```

**Input Compatibility**:
- `dataset_id`: Unchanged - references existing Parquet datasets
- `strategy_id`: Enhanced - supports multiple strategies via registry
- `params`: Unchanged - JSON dictionary with strategy parameters
- `seed`: Unchanged - for reproducible results

**Output Compatibility**:
## Artifact Mapping (MVP)

### Orders Parquet
- ts_utc: order timestamp in UTC
- order_id: unique ID
- side: BUY / SELL
- type: MKT (MVP)
- tif: IOC (MVP)
- qty: filled quantity (int/float)
- price: order limit/exec reference price if applicable

### Fills Parquet
- ts_utc: fill timestamp in UTC
- order_id: foreign key to orders.order_id
- fill_id: unique ID per fill
- side: BUY / SELL
- qty: filled quantity
- price: executed price after slippage adjustment
- fee: computed fee (bps of notional)

### Equity Parquet
- ts_utc: bar timestamp in UTC
- value: portfolio equity (mark-to-market on each bar)

### Metrics JSON (MVP)
- total_return: (final_equity - initial_equity) / initial_equity
- win_rate: wins / total_trades (per trade pairing above)

- `orders`: List of order dictionaries (enhanced with Nautilus data)
- `fills`: List of fill dictionaries (enhanced with Nautilus data)
- `equity`: List of equity curve points (enhanced precision)
- `metrics`: Dictionary of performance metrics (expanded set)

## Data Flow Architecture

### 1. Data Ingestion Flow
```
Parquet Files → ParquetDataAdapter → Nautilus Bar Objects → DataEngine
```
- `HEWSTON_USE_NAUTILUS_STUB`: When true, force stub runner; when false or unset, use real Nautilus. Useful for quick local smoke tests and CI.
- Single-symbol MVP: run one instrument per backtest; multi-asset support deferred.


### 2. Strategy Execution Flow
```
Strategy ID + Params → StrategyFactory → Configured Strategy → BacktestEngine
```

### 3. Results Processing Flow
```
Nautilus Results → MetricsCalculator → Enhanced Metrics → Artifact Persistence
```

### 4. Artifact Generation Flow
```
Backtest Results → Format Conversion → Parquet Files + JSON → File System
```

## Configuration Management

### Environment Variables
- `NAUTILUS_LOG_LEVEL`: Control Nautilus logging verbosity
- `NAUTILUS_CACHE_DIR`: Directory for Nautilus cache files
- `HEWSTON_USE_NAUTILUS_STUB`: Rollback flag to use stub implementation

### Strategy Configuration
```yaml
strategies:
  sma_crossover:
    class: "SMAStrategy"
    params:
      fast: {type: int, min: 1, max: 200, default: 20}
      slow: {type: int, min: 1, max: 200, default: 50}
  momentum:
    class: "MomentumStrategy"
    params:
      lookback: {type: int, min: 1, max: 100, default: 14}
      threshold: {type: float, min: 0.001, max: 1.0, default: 0.02}
```

## Performance Considerations

### Memory Management
- Nautilus objects lifecycle managed properly
- Large datasets processed in chunks if needed
- Memory profiling to prevent leaks

### Execution Performance
- Target: ≤30s for 1-year AAPL backtest
- Nautilus engine optimizations enabled
- Parallel processing where applicable

### Caching Strategy
- Nautilus internal caching leveraged
- Data conversion results cached when appropriate
- Strategy compilation cached

## Error Handling & Resilience

### Data Validation
- Parquet data integrity checks
- Missing data handling
- Timezone consistency validation

### Strategy Errors
- Parameter validation before execution
- Strategy runtime error handling
- Graceful degradation for invalid strategies

### Engine Failures
- Nautilus engine error capture
- Partial results recovery where possible
- Detailed error logging and reporting

## Migration Strategy

### Phase 1: Core Engine (Story 10.1)
- Replace stub with real Nautilus engine
- Maintain single SMA strategy
- Ensure artifact compatibility

### Phase 2: Strategy Framework (Story 10.2)
- Implement strategy registry/factory
- Add multiple baseline strategies
- Maintain parameter compatibility

### Phase 3: Enhanced Metrics (Story 10.3)
- Implement comprehensive metrics
- Create extensible metrics system
- Maintain backward compatibility

### Rollback Plan
- Environment variable to revert to stub
- Database compatibility maintained
- Artifact format unchanged

## Testing Strategy

### Unit Tests
- Data adapter conversion accuracy
- Strategy logic validation
- Metrics calculation correctness

### Integration Tests
- End-to-end backtest execution
- Artifact generation and format
- API compatibility verification

### Performance Tests
- Execution time benchmarks
- Memory usage profiling
- Concurrent execution testing

## Monitoring & Observability

### Logging
- Nautilus engine operations
- Strategy execution events
- Performance metrics

### Metrics Collection
- Execution time tracking
- Memory usage monitoring
- Error rate tracking

### Alerting
- Performance degradation alerts
- Error threshold monitoring
- System health checks

## References

- **Nautilus Trader Documentation**: https://docs.nautilustrader.io/
- **Current Implementation**: `backend/adapters/nautilus.py`
- **Interface Definition**: `backend/ports/backtest_runner.py`
- **Epic Documentation**: `docs/prd/epic-10-nautilus-trader-full-implementation.md`
