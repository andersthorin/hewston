# Epic 8 — Backend-for-Frontend (BFF) Implementation: Acceptance Test Checklist
Epic ID: E8

## Preconditions
- Core platform complete (Epics 1–7)
- BFF service deployed alongside existing backend/frontend
- Redis available for caching (optional but recommended)
- Feature flags configured for gradual migration

## Test Cases

### 1) BFF Service Infrastructure (Stories 8.1-8.2)

**1.1) BFF Service Health & Integration**
- Step: `make start-bff` (or equivalent Docker command)
- Verify: GET http://127.0.0.1:8001/health → 200 and JSON with service status, version, dependencies
- Verify: BFF service starts without affecting existing backend (port 8000) or frontend
- Verify: Docker compose includes BFF service with proper networking
- Negative: BFF service down → health endpoint returns 503

**1.2) Basic HTTP Proxy Functionality**
- Step: Configure frontend to use BFF endpoints (feature flag enabled)
- Verify: GET /api/v1/backtests → proxies to backend /backtests with identical response
- Verify: POST /api/v1/backtests → proxies to backend with request/response body preservation
- Verify: Authentication headers pass through correctly (test with valid/invalid tokens)
- Verify: Error responses maintain exact backend format and status codes
- Negative: Backend down → BFF returns appropriate error with correlation ID

**1.3) Request/Response Logging**
- Exercise: Make several API calls through BFF proxy
- Verify: Structured logs include correlation IDs, request/response times, status codes
- Verify: Log format matches existing backend patterns (structlog)
- Verify: Error scenarios logged with appropriate severity levels

### 2) Data Aggregation & Performance (Stories 8.3-8.4)

**2.1) Chart Data Aggregation**
- Step: GET /api/v1/chart-data?symbol=AAPL&timeframe=1D&from_date=2024-01-01&to_date=2024-12-31
- Verify: Single request returns aggregated chart data (replaces multiple /bars/* calls)
- Verify: Response includes metadata (total_bars, decimated, cache_hit, load_time_ms)
- Verify: Data decimation works with target_points parameter (default 10000)
- Verify: All timeframes supported: 1D, 1H, 1M, 1M_DECIMATED
- Performance: Chart data loads within 2 seconds for any symbol/timeframe
- Negative: Invalid symbol → appropriate error response

**2.2) Run Data Aggregation**
- Step: GET /api/v1/runs/{id}/complete
- Verify: Single request returns run details + metrics + equity + orders
- Verify: Optional parameters control data inclusion (include_orders, include_equity, include_metrics)
- Verify: Concurrent backend calls minimize total response time
- Verify: Partial responses when some data unavailable (graceful degradation)
- Performance: Complete run data loads within 1 second for cached runs
- Negative: Non-existent run ID → 404 with proper error format

**2.3) Caching Performance**
- Exercise: Request same chart/run data multiple times
- Verify: Cache hit/miss status in response metadata
- Verify: Cached responses significantly faster than initial requests
- Verify: Cache TTL working (data refreshes after expiration)
- Verify: Cache invalidation on data updates (if applicable)

### 3) WebSocket Proxy & Reliability (Story 8.5)

**3.1) WebSocket Proxy Functionality**
- Step: Connect WS ws://127.0.0.1:8001/api/v1/runs/{id}/stream
- Verify: Connection established and proxies to backend WebSocket
- Verify: All control commands forwarded correctly (play, pause, seek, speed)
- Verify: Frame streaming maintains existing protocol and message formats
- Verify: Multiple concurrent client connections supported (test 10+ clients)

**3.2) Connection Management & Reliability**
- Exercise: Simulate backend WebSocket disconnection
- Verify: Automatic reconnection with exponential backoff (1s, 2s, 4s, 8s, max 30s)
- Verify: Client connections maintained during backend reconnection
- Verify: Message queuing during temporary disconnections
- Verify: Connection health monitoring and status reporting
- Performance: WebSocket proxy latency <50ms for message forwarding

**3.3) Streaming Performance**
- Exercise: Run backtest playback through BFF WebSocket proxy
- Verify: Maintains ~30 FPS streaming performance (same as direct backend)
- Verify: Frame rate adaptation based on client connection quality
- Verify: Dropped frame counter and performance metadata available
- Load test: 50+ concurrent streaming connections without degradation

### 4) Frontend Integration & Migration (Story 8.6)

**4.1) Feature Flag Functionality**
- Step: Toggle BFF feature flags (chart data, run data, WebSocket)
- Verify: Frontend can switch between BFF and direct backend seamlessly
- Verify: Individual endpoint groups can be toggled independently
- Verify: Feature flag status visible in development tools
- Verify: Instant rollback capability without service restart

**4.2) API Client Migration**
- Exercise: Use frontend with BFF endpoints enabled
- Verify: All existing functionality works identically through BFF
- Verify: Chart components load faster with aggregated data
- Verify: Run detail views show improvement from single aggregated request
- Verify: WebSocket streaming maintains existing user experience
- Verify: Error handling preserves existing user-facing messages

**4.3) Component Simplification**
- Code review: Frontend components using BFF endpoints
- Verify: Complex data transformation logic removed from frontend
- Verify: Multiple loading states eliminated where BFF provides aggregation
- Verify: TypeScript types updated for new BFF response formats
- Verify: Existing component interfaces preserved during migration

### 5) Cross-cutting Quality Requirements

**5.1) Performance Targets**
- API Latency: BFF proxy adds <100ms to backend response times
- Chart Loading: All chart data loads within 2 seconds
- Run Analysis: Complete run data loads within 1 second (cached)
- WebSocket Streaming: Maintains ~30 FPS performance
- Concurrent Load: 100+ concurrent API requests without degradation

**5.2) Security & Authentication**
- Verify: Authentication tokens pass through transparently
- Verify: No authentication logic implemented in BFF (pass-through only)
- Verify: Backend authorization decisions preserved exactly
- Verify: No additional attack surface introduced by BFF layer
- Verify: Input validation at BFF layer using Pydantic models

**5.3) Monitoring & Observability**
- Verify: BFF metrics collection (response times, error rates, cache hit ratios)
- Verify: Correlation IDs link requests across BFF and backend
- Verify: Error tracking and reporting for BFF-specific issues
- Verify: Performance monitoring for all BFF endpoints
- Verify: Alerting thresholds configured for BFF performance

**5.4) Regression Prevention**
- Execute: Complete existing test suite with BFF enabled
- Verify: All existing functionality preserved without changes
- Verify: No performance regression in critical user flows
- Verify: Existing API contracts maintained exactly
- Verify: Database operations unchanged (BFF read-only)

## Pass/Fail Criteria
- All BFF endpoints functional with performance targets met
- Zero regression in existing functionality
- Feature flags enable safe rollback at any point
- Frontend complexity reduced by 50%+ for data-heavy components
- WebSocket streaming maintains existing performance characteristics
- Comprehensive monitoring and error handling operational

## Artifacts
- BFF performance benchmark report
- Feature flag testing documentation
- Frontend complexity reduction metrics
- WebSocket streaming performance validation
- Cache hit rate and performance analysis
- Regression testing results
- Security validation report

## Risk Mitigation Validation
- Feature flag rollback tested and functional
- Performance monitoring alerts configured
- Error correlation across services working
- Graceful degradation scenarios tested
- Backend failure handling validated
