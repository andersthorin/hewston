# Hewston BFF (Backend-for-Frontend) Service

The BFF service provides aggregated APIs and enhanced functionality for the Hewston trading platform frontend, reducing complexity and improving performance.

## Overview

The BFF service sits between the existing React frontend and FastAPI backend, providing:

- **API Aggregation**: Combines multiple backend calls into single requests
- **Data Transformation**: Optimizes data formats for frontend consumption
- **Caching**: Intelligent caching with Redis for improved performance
- **WebSocket Proxy**: Enhanced WebSocket management with automatic reconnection
- **Feature Flags**: Safe gradual migration with rollback capabilities

## Architecture

```
Frontend (React) → BFF Service (FastAPI) → Backend (FastAPI)
                        ↓
                   Redis (Optional)
```

## Quick Start

### Prerequisites

- Python 3.11+
- uv (recommended) or pip
- Redis (optional, for caching)
- Existing Hewston backend service running on port 8000

### Installation

1. **Install dependencies:**
   ```bash
   cd bff
   uv pip install -r requirements.txt
   ```

2. **Start the BFF service:**
   ```bash
   # Using uvicorn directly
   uvicorn bff.app.main:app --reload --host 127.0.0.1 --port 8001
   
   # Or using the Makefile (from project root)
   make start-bff
   ```

3. **Verify service is running:**
   ```bash
   curl http://127.0.0.1:8001/api/v1/health
   ```

4. **Test proxy functionality:**
   ```bash
   # Test backtests proxy (requires backend running)
   curl http://127.0.0.1:8001/api/v1/backtests

   # Test bars proxy (requires backend running)
   curl "http://127.0.0.1:8001/api/v1/bars/daily?symbol=AAPL"
   ```

5. **Test chart data aggregation:**
   ```bash
   # Test unified chart data endpoint
   curl "http://127.0.0.1:8001/api/v1/chart-data?symbol=AAPL&timeframe=1D&from=2024-01-01&to=2024-01-31"

   # Test with decimation
   curl "http://127.0.0.1:8001/api/v1/chart-data?symbol=AAPL&timeframe=1M&from=2024-01-01&to=2024-01-01&target_points=1000"
   ```

6. **Test run data aggregation:**
   ```bash
   # Test complete run data (requires backend with run data)
   curl "http://127.0.0.1:8001/api/v1/runs/test-run-123/complete"

   # Test selective data inclusion
   curl "http://127.0.0.1:8001/api/v1/runs/test-run-123/complete?include_orders=false&include_equity=true"

   # Test lightweight status endpoint
   curl "http://127.0.0.1:8001/api/v1/runs/test-run-123/status"
   ```

7. **Test WebSocket streaming:**
   ```bash
   # Test WebSocket service health
   curl "http://127.0.0.1:8001/api/v1/websocket/health"

   # Test WebSocket connection statistics
   curl "http://127.0.0.1:8001/api/v1/websocket/stats"

   # Connect to run-specific WebSocket (requires WebSocket client)
   # ws://127.0.0.1:8001/api/v1/runs/test-run-123/stream

   # Connect to general WebSocket for multi-run streaming
   # ws://127.0.0.1:8001/api/v1/stream
   ```

### Docker Development

```bash
# Build development image
docker build -f bff/Dockerfile --target development -t hewston-bff:dev .

# Run with Docker
docker run -p 8001:8001 --env HEWSTON_BACKEND_URL=http://host.docker.internal:8000 hewston-bff:dev
```

## Configuration

The BFF service is configured through environment variables:

### Core Configuration

- `HEWSTON_BACKEND_URL`: Backend API URL (default: `http://127.0.0.1:8000`)
- `BFF_BACKEND_TIMEOUT`: Backend request timeout in seconds (default: `30`)
- `BFF_LOG_LEVEL`: Logging level (default: `INFO`)
- `BFF_ENVIRONMENT`: Environment name (default: `development`)

### Redis Configuration (Optional)

- `REDIS_URL`: Redis connection URL (default: `redis://localhost:6379`)
- `BFF_REDIS_ENABLED`: Enable Redis caching (default: `false`)
- `BFF_REDIS_TTL_CHART`: Chart data cache TTL in seconds (default: `300`)
- `BFF_REDIS_TTL_RUN`: Run data cache TTL in seconds (default: `60`)

### Feature Flags

- `BFF_FEATURE_CHART_AGGREGATION`: Enable chart data aggregation (default: `true`)
- `BFF_FEATURE_RUN_AGGREGATION`: Enable run data aggregation (default: `true`)
- `BFF_FEATURE_WEBSOCKET_PROXY`: Enable WebSocket proxy (default: `true`)

## API Endpoints

### Health Checks

- `GET /api/v1/health` - Comprehensive health check with dependency status
- `GET /api/v1/health/ready` - Kubernetes readiness probe
- `GET /api/v1/health/live` - Kubernetes liveness probe

### Proxy Endpoints (Story 8.2)

**Backtests API:**
- `POST /api/v1/backtests` - Create new backtest (proxy to backend)
- `GET /api/v1/backtests` - List backtests with filtering (proxy to backend)
- `GET /api/v1/backtests/{id}` - Get backtest details (proxy to backend)

**Bars API:**
- `GET /api/v1/bars/daily` - Daily OHLCV bars (proxy to backend)
- `GET /api/v1/bars/minute` - Minute OHLCV bars (proxy to backend)
- `GET /api/v1/bars/minute_decimated` - Decimated minute bars (proxy to backend)
- `GET /api/v1/bars/hour` - Hourly OHLCV bars (proxy to backend)

### Chart Data Aggregation (Story 8.3)

**Unified Chart Data:**
- `GET /api/v1/chart-data` - Aggregated chart data with caching and decimation

**Features:**
- Single endpoint replaces multiple `/bars/*` calls
- Intelligent data decimation for performance
- Redis caching with TTL based on data recency
- Support for timeframes: 1D, 1H, 1M, 1M_DECIMATED
- Response metadata with performance metrics

### Run Data Aggregation (Story 8.4)

**Unified Run Data:**
- `GET /api/v1/runs/{id}/complete` - Complete aggregated run data
- `GET /api/v1/runs/{id}/status` - Lightweight run status

**Features:**
- Single endpoint replaces multiple `/backtests/{id}/*` calls
- Concurrent backend requests for optimal performance
- Selective data inclusion (orders, equity, metrics)
- Intelligent caching based on run status
- Graceful degradation for partial data failures

### WebSocket Streaming (Story 8.5)

**Real-time Communication:**
- `WS /api/v1/runs/{id}/stream` - Run-specific WebSocket streaming
- `WS /api/v1/stream` - General multi-run WebSocket streaming
- `GET /api/v1/websocket/stats` - WebSocket connection statistics
- `GET /api/v1/websocket/health` - WebSocket service health

**Features:**
- Bidirectional message forwarding between frontend and backend
- Automatic subscription management for run updates
- Connection lifecycle management with graceful error handling
- Ping/pong heartbeat for connection health monitoring
- Multi-client support with intelligent backend connection pooling

### Future Endpoints (Stories 8.6)

- Additional BFF enhancements and optimizations

## Development

### Running Tests

```bash
# Run all tests
pytest bff/tests/

# Run with coverage
pytest bff/tests/ --cov=bff --cov-report=html

# Run specific test file
pytest bff/tests/test_health.py -v
```

### Code Quality

```bash
# Linting
ruff check bff/

# Formatting
black bff/

# Type checking (if mypy is installed)
mypy bff/
```

### Development Workflow

1. **Start backend service** (required dependency):
   ```bash
   make start-backend
   ```

2. **Start BFF service** in development mode:
   ```bash
   make start-bff
   ```

3. **Run tests** to verify functionality:
   ```bash
   pytest bff/tests/
   ```

## Monitoring and Observability

### Logging

The BFF service uses structured logging with JSON output, following the same patterns as the backend service:

```json
{
  "timestamp": "2025-01-27T10:30:00.123Z",
  "level": "info",
  "event": "http.access",
  "request_id": "abc123...",
  "method": "GET",
  "path": "/api/v1/health",
  "status": 200,
  "latency_ms": 45,
  "service": "bff"
}
```

### Health Monitoring

- **Health endpoint**: `/api/v1/health` provides detailed service status
- **Correlation IDs**: All requests include `X-Correlation-ID` header
- **Dependency checks**: Validates backend API and Redis connectivity
- **Performance metrics**: Request timing and status tracking

### Metrics (Future)

Planned metrics collection includes:
- Request/response times
- Cache hit/miss ratios
- Backend communication health
- Error rates and types

## Troubleshooting

### Common Issues

1. **BFF service won't start**
   - Check if port 8001 is available
   - Verify backend service is running on port 8000
   - Check logs for dependency issues

2. **Health check fails**
   - Verify backend API is accessible at configured URL
   - Check network connectivity between services
   - Review Redis configuration if caching is enabled

3. **Performance issues**
   - Enable Redis caching for better performance
   - Check backend service response times
   - Review log output for slow requests

### Debug Mode

Enable debug logging:
```bash
export BFF_LOG_LEVEL=DEBUG
uvicorn bff.app.main:app --reload --host 127.0.0.1 --port 8001
```

## Contributing

1. Follow existing code patterns from the backend service
2. Add tests for new functionality
3. Update documentation for API changes
4. Ensure health checks validate new dependencies

## Architecture Decisions

- **Port 8001**: Chosen to avoid conflicts with backend (8000) and frontend (5173)
- **FastAPI**: Consistent with existing backend technology stack
- **Structured Logging**: Maintains compatibility with existing logging infrastructure
- **Optional Redis**: Graceful degradation when caching is unavailable
- **Feature Flags**: Enables safe gradual migration and rollback capabilities
