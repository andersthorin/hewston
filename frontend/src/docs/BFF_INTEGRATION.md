# BFF Integration Guide

This document explains the Frontend BFF (Backend for Frontend) integration implemented in Epic 9.

## Overview

The BFF integration provides a unified data layer that can route API calls to either BFF aggregated endpoints or direct backend endpoints based on feature flag configuration. This enables:

- **Gradual Migration**: Feature flags allow endpoint-by-endpoint migration with instant rollback
- **Performance Optimization**: BFF provides data aggregation and caching
- **Simplified Frontend**: Reduced complexity by moving data transformation to BFF layer
- **Backward Compatibility**: Existing components work unchanged

## Architecture

### Feature Flag System

The feature flag system (`frontend/src/services/featureFlags.ts`) controls BFF vs backend routing:

```typescript
// Environment variables control BFF usage
VITE_BFF_ENABLED=false              // Master toggle
VITE_BFF_CHART_DATA_ENABLED=false   // Chart data endpoints
VITE_BFF_RUN_DATA_ENABLED=false     // Run data endpoints  
VITE_BFF_WEBSOCKET_ENABLED=false    // WebSocket endpoints
```

### API Router

The API router (`frontend/src/utils/apiRouter.ts`) provides conditional endpoint selection:

```typescript
// Automatically routes based on feature flags
const response = await apiGetWithFlags('/chart-data', 'chartData')
```

### Service Layer

#### Chart Data Service (`frontend/src/services/chartData.ts`)

Unified interface for chart data that routes to BFF or backend:

```typescript
// Single service handles both BFF and backend
const data = await chartDataService.fetchDailyData('AAPL', '2023-01-01', '2023-12-31')
```

**BFF Benefits:**
- Single API call replaces multiple backend requests
- Data decimation handled server-side
- Caching and performance optimization

#### Run Data Service (`frontend/src/services/runData.ts`)

Unified interface for run data with aggregation support:

```typescript
// Gets complete run data in single request (BFF) vs multiple requests (backend)
const completeRun = await runDataService.getCompleteRunData('run-123')
```

**BFF Benefits:**
- Aggregated response combines run details, metrics, equity, and orders
- Single request replaces 3+ backend calls
- Simplified loading states

### React Hooks

#### Chart Data Hooks (`frontend/src/hooks/useChartData.ts`)

BFF-aware hooks with backward compatibility:

```typescript
// New BFF-aware hooks
const { data } = useDailyChartData('AAPL', from, to)
const { data } = useMinuteChartData('AAPL', from, to, target)
const { data } = useHourChartData('AAPL', from, to)

// Legacy compatibility hooks (same interface)
const { data } = useDailyData('AAPL', from, to)  // Still works!
```

#### Run Data Hooks (`frontend/src/hooks/useRunData.ts`)

BFF-aware hooks with aggregation support:

```typescript
// New BFF-aware hooks
const { data } = useRunList(query)
const { data } = useCompleteRunData(run_id)  // Aggregated data
const createRun = useCreateRun()

// Legacy compatibility hooks
const { data } = useBacktestList(query)      // Still works!
const { data } = useRunDetail(run_id)        // Still works!

// BFF-specific hooks for aggregated data
const { data: metrics } = useRunMetrics(run_id)
const { data: equity } = useRunEquity(run_id)
const { data: orders } = useRunOrders(run_id)
```

## Migration Guide

### 1. Enable Feature Flags

Update `.env.local` to enable BFF endpoints:

```bash
# Enable BFF master toggle
VITE_BFF_ENABLED=true

# Enable specific endpoint groups
VITE_BFF_CHART_DATA_ENABLED=true
VITE_BFF_RUN_DATA_ENABLED=true
```

### 2. Component Updates

Components automatically use BFF when feature flags are enabled. No code changes required for basic migration.

#### Before (Direct Backend)
```typescript
// Component automatically uses backend
const { data } = useQuery(['hour', symbol], () => fetchHour(symbol, from, to))
```

#### After (BFF-Aware)
```typescript
// Same component automatically uses BFF when flags enabled
const { data } = useHourChartData(symbol, from, to)
```

### 3. Gradual Migration

Enable endpoints one at a time:

```bash
# Week 1: Enable chart data only
VITE_BFF_CHART_DATA_ENABLED=true
VITE_BFF_RUN_DATA_ENABLED=false

# Week 2: Enable run data
VITE_BFF_RUN_DATA_ENABLED=true

# Week 3: Enable WebSocket
VITE_BFF_WEBSOCKET_ENABLED=true
```

### 4. Rollback

Instant rollback by disabling feature flags:

```bash
# Emergency rollback
VITE_BFF_ENABLED=false
```

## Development Tools

### Browser Console Commands

When `VITE_FEATURE_FLAG_DEBUG=true`:

```javascript
// Check feature flag status
__FF_STATUS__()

// View current endpoint mappings  
__FF_ENDPOINTS__()

// View feature flag state
__FEATURE_FLAGS__

// Help
__FF_HELP__()
```

### Performance Monitoring

```typescript
// Get performance metrics
const metrics = useChartDataMetrics()
console.log('BFF enabled:', metrics.bffEnabled)
console.log('Last load time:', metrics.lastLoadTime)

const runMetrics = useRunDataMetrics()
console.log('Using aggregation:', runMetrics.isUsingAggregation)
console.log('API call reduction:', runMetrics.aggregationBenefit)
```

## Testing

### Unit Tests

Tests validate both BFF and backend modes:

```typescript
// Test BFF mode
mockFeatureFlagService.isFeatureFlagEnabled.mockReturnValue(true)
const { result } = renderHook(() => useDailyChartData('AAPL'))

// Test backend mode  
mockFeatureFlagService.isFeatureFlagEnabled.mockReturnValue(false)
const { result } = renderHook(() => useDailyChartData('AAPL'))
```

### Integration Testing

```bash
# Test with BFF enabled
VITE_BFF_ENABLED=true npm test

# Test with BFF disabled  
VITE_BFF_ENABLED=false npm test
```

## Performance Benefits

### Chart Data
- **Backend**: 3+ API calls for different timeframes
- **BFF**: 1 API call with server-side aggregation
- **Improvement**: ~60% reduction in network requests

### Run Data
- **Backend**: 3+ API calls (run details + metrics + equity + orders)
- **BFF**: 1 API call with complete aggregated data
- **Improvement**: ~70% reduction in network requests

### Caching
- BFF provides server-side caching
- Reduced backend load
- Faster subsequent requests

## Error Handling

### Graceful Fallback

```typescript
// Automatic fallback to backend when BFF fails
const data = await apiRouter.routeAPICall('chartData', '/bars/daily', {
  allowFallback: true  // Default: true
})
```

### Error Types

1. **BFF Errors**: Wrapped with additional context
2. **Backend Errors**: Passed through unchanged  
3. **Network Errors**: Handled consistently

## Troubleshooting

### Common Issues

1. **Feature flags not working**
   - Check `.env.local` file exists
   - Verify environment variable names (must start with `VITE_`)
   - Restart development server after changes

2. **BFF endpoints not found**
   - Verify BFF service is running on port 8001
   - Check Vite proxy configuration
   - Confirm BFF endpoints are implemented

3. **Performance not improved**
   - Verify feature flags are enabled
   - Check browser network tab for request count
   - Monitor BFF cache hit rates

### Debug Commands

```javascript
// Check configuration
__FF_STATUS__()

// Validate endpoints
__FF_ENDPOINTS__()

// Monitor routing decisions
// (Check browser console for routing logs)
```

## WebSocket Integration (Story 9.3)

### Enhanced WebSocket Management

The BFF WebSocket integration provides enhanced connection management with automatic reconnection and health monitoring:

```typescript
// WebSocket connections automatically route based on feature flags
const { state, subscribe, onPlay, onPause, getConnectionHealth } = useRunPlayback(runId)

// Enhanced health monitoring
const { performanceMetrics, connectionStatus, reconnect, ping } = useWebSocketHealth(runId)

// Performance monitoring with alerts
const { alerts, hasAlerts } = useWebSocketPerformanceMonitor(runId, {
  fpsThreshold: 25,
  latencyThreshold: 50,
})
```

### WebSocket Endpoints

- **Backend**: `ws://127.0.0.1:8000/backtests/{id}/ws`
- **BFF**: `ws://127.0.0.1:8001/api/v1/runs/{id}/stream`

### Enhanced Features

1. **Auto-Reconnection**: Exponential backoff with configurable retry limits
2. **Health Monitoring**: Real-time connection status and performance metrics
3. **Message Queuing**: Buffer messages during temporary disconnections
4. **Performance Tracking**: FPS monitoring, latency measurement, dropped frame counting

### Performance Validation

```typescript
// Run performance tests
const testResult = await webSocketPerformanceTester.runPerformanceTest(runId, 30000, 'streaming')

// Compare BFF vs backend performance
const comparison = await webSocketPerformanceTester.comparePerformance(runId)
```

## Development Tools

### Performance Monitor Component

When `VITE_FEATURE_FLAG_DEBUG=true`, a performance monitor appears in development:

- Real-time WebSocket performance metrics
- Feature flag status display
- Performance alerts and warnings
- Quick actions (ping, reconnect, health logging)
- Performance testing controls

### Enhanced Console Commands

```javascript
// WebSocket-specific debugging
__FF_WEBSOCKET__()         // Show WebSocket configuration and routing

// Performance monitoring
__PERFORMANCE_TEST__()     // Run WebSocket performance test
__HEALTH_REPORT__()        // Get detailed connection health report
```

## Complete Epic 9 Implementation

### Stories Completed

✅ **Story 9.1**: API Client Configuration and Feature Flags
✅ **Story 9.2**: Frontend Component Migration
✅ **Story 9.3**: WebSocket Integration and Validation

### Performance Improvements Delivered

1. **API Calls**: 60-70% reduction through BFF aggregation
2. **WebSocket Reliability**: Enhanced connection management with auto-reconnection
3. **Loading States**: Simplified through aggregated data responses
4. **Error Handling**: Graceful fallback with automatic retry logic

### Migration Path

```bash
# Phase 1: Enable API endpoints
VITE_BFF_ENABLED=true
VITE_BFF_CHART_DATA_ENABLED=true
VITE_BFF_RUN_DATA_ENABLED=true

# Phase 2: Enable WebSocket proxy
VITE_BFF_WEBSOCKET_ENABLED=true

# Emergency rollback
VITE_BFF_ENABLED=false
```

## Future Enhancements

1. **Advanced Caching**: Client-side cache coordination with BFF
2. **Performance Metrics**: Detailed performance tracking and reporting
3. **A/B Testing**: Feature flag-based performance comparison
4. **Load Balancing**: Multiple BFF instance support
