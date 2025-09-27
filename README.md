# Hewston

**Reproducible backtesting MVP with time-compressed playback**

Hewston is a comprehensive backtesting platform that enables traders and researchers to test trading strategies against historical market data with deterministic, reproducible results. The platform features real-time playback visualization, comprehensive performance metrics, and a modern web interface.

## 🚀 Key Features

- **Deterministic Backtesting**: Identical inputs produce identical results with seed-based randomization
- **Time-Compressed Playback**: Visualize entire trading years in minutes with WebSocket streaming
- **Real-Time Charts**: Interactive candlestick and equity curve charts with TradingView Lightweight Charts
- **Comprehensive Metrics**: Detailed performance analytics including Sharpe ratio, drawdown, and trade statistics
- **Modern Architecture**: FastAPI backend with React/TypeScript frontend, fully type-safe
- **Market Data Integration**: Databento integration for high-quality TRADES and TBBO data

## 🛠 Tech Stack

### Backend
- **Python 3.11** with FastAPI and Pydantic v2
- **Polars** for high-performance data processing
- **SQLite** for local catalog and metadata
- **Nautilus Trader** for backtesting execution
- **WebSocket/SSE** for real-time streaming

### Frontend
- **React 19** with TypeScript and Vite
- **TailwindCSS** for styling
- **TanStack Query** for data fetching and caching
- **Zod** for runtime type validation
- **TradingView Lightweight Charts** for visualization

### Data & Storage
- **Databento** for market data (TRADES + TBBO)
- **Parquet** files for efficient data storage
- **JSON** manifests for run metadata
- **Local filesystem** for artifacts and caching

## 📋 Prerequisites

- **macOS** (Apple Silicon) or **Linux**
- **Python 3.11** (uv recommended for package management)
- **Node.js 22.x** and npm
- **sqlite3** CLI tool
- **Databento API key** (export DATABENTO_API_KEY=...)

## 🚀 Quick Start

### 1. Setup Environment
```bash
make setup
```

### 2. Initialize Database
```bash
make db-apply
```

### 3. Build Baseline Dataset (AAPL 2023)
```bash
make data SYMBOL=AAPL YEAR=2023
```

### 4. Run Baseline Backtest
```bash
make backtest SYMBOL=AAPL FROM=2023-01-01 TO=2023-12-31 STRATEGY=sma_crossover FAST=20 SLOW=50 SPEED=60 SEED=42
```

### 5. Start Development Servers
```bash
make start
```
- **Backend**: http://127.0.0.1:8000 (see /healthz for status)
- **Frontend**: http://127.0.0.1:5173 (Vite dev server)

## 📁 Project Structure

```
hewston/
├── backend/                 # Python FastAPI backend
│   ├── app/                # FastAPI application factory
│   ├── api/routes/         # REST API endpoints
│   ├── domain/             # Pydantic models and types
│   ├── services/           # Business logic orchestration
│   ├── adapters/           # External integrations (Databento, Nautilus, SQLite)
│   ├── ports/              # Interface definitions (hexagonal architecture)
│   └── jobs/               # CLI commands for data processing
├── frontend/               # React TypeScript frontend
│   ├── src/components/     # Presentational UI components
│   ├── src/containers/     # Data-connected containers
│   ├── src/services/       # API clients and data services
│   ├── src/hooks/          # Custom React hooks
│   ├── src/types/          # TypeScript type definitions
│   └── src/workers/        # Web Workers for stream processing
├── docs/                   # Comprehensive documentation
│   ├── api/                # API specifications and schemas
│   ├── architecture/       # System design and standards
│   └── prd/                # Product requirements and features
├── scripts/                # Database schemas and utilities
└── data/                   # Local data storage
    ├── raw/databento/      # Cached market data
    ├── derived/bars/       # Processed OHLCV data
    └── backtests/          # Run artifacts and results
```

## 🔧 Development Workflow

### Available Make Targets
```bash
make help                   # Show all available commands
make setup                  # Setup Python venv and frontend dependencies
make start                  # Start both backend and frontend servers
make start-backend          # Start only FastAPI server
make start-frontend         # Start only Vite dev server
make lint                   # Run linters (ruff + eslint)
make format                 # Run formatters (black + prettier)
make test                   # Run test suites (pytest + vitest)
make clean                  # Remove caches and temp files
```

### Code Quality
- **Backend**: Ruff for linting, Black for formatting, pytest for testing
- **Frontend**: ESLint for linting, Prettier for formatting, Vitest for testing
- **Type Safety**: 100% TypeScript coverage with strict mode enabled
- **Validation**: Zod schemas at all API boundaries

## 📚 Documentation

### Core Documentation
- **[Architecture Overview](docs/architecture.md)** - System design and patterns
- **[API Specification](docs/api/openapi.yaml)** - REST API documentation
- **[Tech Stack Details](docs/architecture/tech-stack.md)** - Technology choices and versions
- **[Coding Standards](docs/architecture/coding-standards.md)** - Development guidelines

### API & Integration
- **[WebSocket Protocol](docs/api/ws-protocol.md)** - Real-time streaming specification
- **[Error Codes](docs/api/error-codes.md)** - API error reference
- **[Database Schema](docs/api/catalog.md)** - SQLite catalog structure

### Development
- **[Frontend Component Map](docs/frontend/component-map.md)** - UI architecture guide
- **[Source Tree](docs/architecture/source-tree.md)** - Codebase organization


## 🎯 Key Concepts

### Deterministic Backtesting
- **Reproducible Results**: Same inputs always produce identical outputs
- **Seed-Based Randomization**: Controlled randomness for order execution
- **Code Hashing**: Track strategy versions for result traceability
- **Manifest Files**: Complete audit trail of run parameters and environment

### Time-Compressed Playback
- **Real-Time Visualization**: Watch years of trading in minutes
- **WebSocket Streaming**: Low-latency frame delivery to frontend
- **Interactive Controls**: Play, pause, seek, and speed control
- **Synchronized Charts**: Candlestick and equity curves update together

### Data Pipeline
1. **Ingest**: Download TRADES/TBBO data from Databento
2. **Derive**: Process into 1-minute OHLCV bars with TBBO aggregates
3. **Backtest**: Execute strategy with Nautilus Trader
4. **Stream**: Real-time playback of results via WebSocket

## 🧪 Example Usage

### Create and View a Backtest Run

1. **Create a run via API**:
```bash
curl -X POST http://127.0.0.1:8000/backtests \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "from": "2023-01-01",
    "to": "2023-03-31",
    "strategy_id": "sma_crossover",
    "params": {"fast": 20, "slow": 50},
    "seed": 42,
    "slippage_fees": {"k_spread": 0.5, "fees_bps": 1}
  }'
```

2. **View results in browser**:
   - Navigate to http://127.0.0.1:5173/runs
   - Click on your run to see detailed playback
   - Use playback controls to visualize the strategy execution

### WebSocket Streaming Example
```javascript
const ws = new WebSocket('ws://127.0.0.1:8000/backtests/{run_id}/ws');
ws.onmessage = (event) => {
  const frame = JSON.parse(event.data);
  if (frame.t === 'frame') {
    // Update charts with OHLC data, orders, and equity
    updateCharts(frame.ohlc, frame.orders, frame.equity);
  }
};
// Send control commands
ws.send(JSON.stringify({t: 'ctrl', cmd: 'play', speed: 60}));
```

## 🔍 Monitoring & Debugging

### Health Checks
- **Backend Health**: http://127.0.0.1:8000/healthz
- **Database Status**: Check `data/catalog.sqlite` exists
- **Frontend Build**: `cd frontend && npm run build`

### Logging
- **Structured JSON logs** with request IDs and run IDs
- **Log levels**: INFO for normal operations, DEBUG for development
- **WebSocket events**: Connection, frame delivery, and error tracking

### Common Issues
- **Missing Databento key**: Ensure `DATABENTO_API_KEY` is exported
- **SQLite errors**: Run `make db-apply` to initialize schema
- **Port conflicts**: Backend uses 8000, frontend uses 5173
- **TypeScript errors**: Run `cd frontend && npx tsc --noEmit` to check

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Run `make setup` to install dependencies
3. Create a feature branch
4. Make changes following coding standards
5. Run `make lint && make test` to verify quality
6. Submit a pull request

### Code Quality Standards
- **TypeScript**: Strict mode enabled, no `any` types in production code
- **Testing**: Unit tests for business logic, integration tests for APIs
- **Documentation**: Update relevant docs with code changes
- **Performance**: Profile chart updates and streaming performance

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Databento** for high-quality market data APIs
- **Nautilus Trader** for robust backtesting infrastructure
- **TradingView** for excellent charting libraries
- **FastAPI** and **React** communities for outstanding frameworks
