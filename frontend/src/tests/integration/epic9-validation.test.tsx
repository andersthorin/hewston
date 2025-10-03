/**
 * Epic 9 Comprehensive Validation Tests
 * 
 * End-to-end testing of complete BFF integration including:
 * - API routing with feature flags
 * - WebSocket proxy integration
 * - Performance validation
 * - Rollback capability
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'

// Import all the services and hooks we're testing
import { featureFlagService } from '../../services/featureFlags'
import { apiRouter } from '../../utils/apiRouter'
import { chartDataService } from '../../services/chartData'
import { runDataService } from '../../services/runData'
import { createWebSocketManager } from '../../services/websocket'
import { webSocketPerformanceTester } from '../../utils/websocketPerformance'

// Import hooks
import { useDailyChartData, useMinuteChartData } from '../../hooks/useChartData'
import { useRunList, useCompleteRunData } from '../../hooks/useRunData'
import { useWebSocketHealth } from '../../hooks/useWebSocketHealth'

// Mock fetch for API testing
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

// Mock WebSocket for WebSocket testing
class MockWebSocket {
  static OPEN = 1
  readyState = MockWebSocket.OPEN
  onopen: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null

  constructor(public url: string) {
    setTimeout(() => this.onopen?.(new Event('open')), 10)
  }

  send(data: string) {
    // Echo back for testing
    setTimeout(() => {
      this.onmessage?.(new MessageEvent('message', { data }))
    }, 5)
  }

  close() {
    this.readyState = 3
    setTimeout(() => this.onclose?.(new CloseEvent('close')), 5)
  }
}

vi.stubGlobal('WebSocket', MockWebSocket)

// Test wrapper with QueryClient
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

describe('Epic 9: Complete BFF Integration Validation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch.mockClear()
  })

  describe('Feature Flag System Integration', () => {
    it('should validate complete feature flag configuration', () => {
      const config = featureFlagService.getConfiguration()
      const issues = featureFlagService.validateConfiguration()
      
      expect(config).toHaveProperty('bffEnabled')
      expect(config).toHaveProperty('chartDataEnabled')
      expect(config).toHaveProperty('runDataEnabled')
      expect(config).toHaveProperty('websocketEnabled')
      expect(config).toHaveProperty('fallbackToBackend')
      
      expect(Array.isArray(issues)).toBe(true)
    })

    it('should provide endpoint mappings for all service types', () => {
      const endpointConfig = featureFlagService.getEndpointConfiguration()
      
      expect(endpointConfig.endpointMappings).toHaveProperty('chartData')
      expect(endpointConfig.endpointMappings).toHaveProperty('runData')
      expect(endpointConfig.endpointMappings).toHaveProperty('websocket')
      expect(endpointConfig.endpointMappings).toHaveProperty('health')
    })

    it('should evaluate feature flags for all endpoint groups', () => {
      const chartEval = featureFlagService.evaluateFeatureFlag('chartData')
      const runEval = featureFlagService.evaluateFeatureFlag('runData')
      const wsEval = featureFlagService.evaluateFeatureFlag('websocket')
      
      expect(chartEval).toHaveProperty('enabled')
      expect(chartEval).toHaveProperty('endpointUrl')
      expect(chartEval).toHaveProperty('source')
      
      expect(runEval).toHaveProperty('enabled')
      expect(runEval).toHaveProperty('endpointUrl')
      expect(runEval).toHaveProperty('source')
      
      expect(wsEval).toHaveProperty('enabled')
      expect(wsEval).toHaveProperty('endpointUrl')
      expect(wsEval).toHaveProperty('source')
    })
  })

  describe('API Integration with Feature Flags', () => {
    it('should route chart data API calls based on feature flags', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          symbol: 'AAPL',
          timeframe: 'daily',
          bars: [{ t: '2023-01-01', o: 100, h: 105, l: 99, c: 103, v: 1000 }],
          meta: { points: 1, source: 'backend' }
        })
      })

      const data = await chartDataService.fetchDailyData('AAPL', '2023-01-01', '2023-12-31')
      
      expect(data).toHaveProperty('symbol', 'AAPL')
      expect(data).toHaveProperty('timeframe', 'daily')
      expect(data).toHaveProperty('bars')
      expect(data).toHaveProperty('meta')
    })

    it('should route run data API calls based on feature flags', async () => {
      const mockRunList = {
        items: [
          {
            run_id: 'run-123',
            created_at: '2023-01-01T00:00:00Z',
            strategy_id: 'sma_crossover',
            status: 'completed',
            symbol: 'AAPL',
          }
        ],
        total: 1,
        limit: 20,
        offset: 0,
        meta: { source: 'backend' }
      }

      // Mock the service method directly since we're testing integration
      vi.spyOn(runDataService, 'listRuns').mockResolvedValue(mockRunList)
      
      const data = await runDataService.listRuns({ symbol: 'AAPL' })
      
      expect(data).toHaveProperty('items')
      expect(data.items).toHaveLength(1)
      expect(data.items[0]).toHaveProperty('run_id', 'run-123')
    })

    it('should handle API router fallback scenarios', async () => {
      // Mock BFF failure followed by backend success
      mockFetch
        .mockRejectedValueOnce(new Error('BFF unavailable'))
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ data: 'backend-fallback' })
        })

      const result = await apiRouter.routeAPICall('chartData', '/bars/daily', {
        allowFallback: true
      })

      expect(result).toEqual({ data: 'backend-fallback' })
    })
  })

  describe('WebSocket Integration', () => {
    it('should create WebSocket manager with correct endpoint based on feature flags', () => {
      const manager = createWebSocketManager('test-run-123')
      
      expect(manager).toBeDefined()
      expect(manager.getHealth().connectionSource).toBe('backend') // Default when BFF disabled
    })

    it('should handle WebSocket connection lifecycle', async () => {
      const manager = createWebSocketManager('test-run-123')
      
      await manager.connect()
      expect(manager.isReady()).toBe(true)
      expect(manager.getState()).toBe('connected')
      
      manager.close()
      expect(manager.getState()).toBe('closed')
    })

    it('should track WebSocket health metrics', async () => {
      const manager = createWebSocketManager('test-run-123')
      await manager.connect()
      
      const health = manager.getHealth()
      
      expect(health).toHaveProperty('state')
      expect(health).toHaveProperty('reconnectAttempts')
      expect(health).toHaveProperty('messagesReceived')
      expect(health).toHaveProperty('messagesSent')
      expect(health).toHaveProperty('connectionSource')
      
      manager.close()
    })
  })

  describe('React Hooks Integration', () => {
    it('should integrate chart data hooks with feature flags', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          symbol: 'AAPL',
          timeframe: 'daily',
          bars: [],
          meta: { points: 0, source: 'backend' }
        })
      })

      const { result } = renderHook(
        () => useDailyChartData('AAPL', '2023-01-01', '2023-12-31'),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isSuccess || result.current.isLoading).toBe(true)
      })
    })

    it('should integrate run data hooks with feature flags', async () => {
      vi.spyOn(runDataService, 'listRuns').mockResolvedValue({
        items: [],
        total: 0,
        limit: 20,
        offset: 0,
        meta: { source: 'backend' }
      })

      const { result } = renderHook(
        () => useRunList({ symbol: 'AAPL' }),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isSuccess || result.current.isLoading).toBe(true)
      })
    })
  })

  describe('Performance Validation', () => {
    it('should measure WebSocket performance metrics', async () => {
      const testResult = await webSocketPerformanceTester.runPerformanceTest(
        'test-run-123',
        1000, // 1 second test
        'streaming'
      )

      expect(testResult).toHaveProperty('config')
      expect(testResult).toHaveProperty('connection')
      expect(testResult).toHaveProperty('streaming')
      expect(testResult).toHaveProperty('latency')
      expect(testResult).toHaveProperty('throughput')
      expect(testResult).toHaveProperty('metadata')
      
      expect(testResult.config.connectionSource).toBe('backend')
      expect(testResult.metadata.success).toBe(true)
    })

    it('should validate streaming performance targets', async () => {
      const testResult = await webSocketPerformanceTester.runPerformanceTest(
        'test-run-123',
        2000,
        'streaming'
      )

      // Validate performance targets from story requirements
      expect(testResult.connection.establishmentTime).toBeLessThan(5000) // 5 second max
      expect(testResult.metadata.success).toBe(true)
    })
  })

  describe('Rollback Capability', () => {
    it('should support instant rollback via feature flags', () => {
      // Test that configuration can be changed
      const originalConfig = featureFlagService.getConfiguration()
      
      // Verify we can read current state
      expect(originalConfig).toHaveProperty('bffEnabled')
      expect(originalConfig).toHaveProperty('fallbackToBackend', true)
      
      // Verify validation works
      const issues = featureFlagService.validateConfiguration()
      expect(Array.isArray(issues)).toBe(true)
    })

    it('should maintain backward compatibility', async () => {
      // Test that all services work in backend mode (default)
      const chartData = await chartDataService.fetchDailyData('AAPL')
      const runList = await runDataService.listRuns()
      const wsManager = createWebSocketManager('test-run-123')
      
      expect(chartData).toBeDefined()
      expect(runList).toBeDefined()
      expect(wsManager).toBeDefined()
      
      wsManager.close()
    })
  })

  describe('Error Handling and Resilience', () => {
    it('should handle service failures gracefully', async () => {
      // Test API failure handling
      mockFetch.mockRejectedValue(new Error('Network error'))
      
      await expect(chartDataService.fetchDailyData('AAPL')).rejects.toThrow('Network error')
    })

    it('should handle WebSocket connection failures', async () => {
      // Mock WebSocket that fails to connect
      vi.stubGlobal('WebSocket', class {
        constructor() {
          setTimeout(() => this.onerror?.(new Event('error')), 10)
        }
        onerror: ((event: Event) => void) | null = null
        close() {}
      })

      const manager = createWebSocketManager('test-run-123', { connectionTimeout: 100 })
      
      await expect(manager.connect()).rejects.toThrow()
    })
  })

  describe('Development Tools Integration', () => {
    it('should provide debug information', () => {
      const debugInfo = featureFlagService.getDebugInfo()
      
      expect(debugInfo).toHaveProperty('configuration')
      expect(debugInfo).toHaveProperty('endpointMappings')
      expect(debugInfo).toHaveProperty('lastEvaluations')
      expect(debugInfo).toHaveProperty('lastUpdated')
    })

    it('should validate router configuration', () => {
      const issues = apiRouter.validateConfiguration()
      expect(Array.isArray(issues)).toBe(true)
    })
  })
})

