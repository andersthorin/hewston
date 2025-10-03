/**
 * Epic 9: Complete BFF Integration Tests
 *
 * These tests validate the complete integration of all BFF features:
 * - Story 9.1: Chart data through BFF
 * - Story 9.2: Run data aggregation through BFF
 * - Story 9.3: WebSocket integration through BFF
 * - End-to-end BFF coordination and performance
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useDailyChartData } from '../../hooks/useChartData'
import { useBacktestList, useBacktestDetail } from '../../hooks/useRunData'
import { useWebSocketHealth } from '../../hooks/useWebSocketHealth'
import { WebSocketTestHarness } from '../utils/websocket-test-harness'
import type { ReactNode } from 'react'


// Mock fetch to track API calls
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

// Mock all services with comprehensive BFF support
vi.mock('../../services/featureFlags', () => ({
  featureFlagService: {
    isFeatureFlagEnabled: vi.fn(),
    getConfiguration: vi.fn(),
    getEffectiveApiBaseUrl: vi.fn(),
    getEffectiveWsBaseUrl: vi.fn(),
    evaluateFeatureFlag: vi.fn(),
    getDebugInfo: vi.fn(),
  }
}))

vi.mock('../../services/ws', () => ({
  useBacktestPlayback: vi.fn().mockReturnValue({
    getConnectionHealth: vi.fn().mockReturnValue({
      state: 'connected',
      reconnectAttempts: 0,
      messagesReceived: 0,
      connectionSource: 'bff'
    }),
    ping: vi.fn(),
    reconnect: vi.fn(),
    subscribe: vi.fn().mockReturnValue(() => {})
  })
}))

describe('Epic 9: Complete BFF Integration', () => {
  let queryClient: QueryClient
  let testHarness: WebSocketTestHarness

  beforeEach(async () => {
    vi.clearAllMocks()
    vi.resetModules()
    vi.unstubAllEnvs()
    mockFetch.mockClear()

    testHarness = new WebSocketTestHarness()
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } }
    })

    // Setup comprehensive feature flag mocks
    const { featureFlagService } = await import('../../services/featureFlags')
    vi.mocked(featureFlagService.isFeatureFlagEnabled).mockReturnValue(true)
    vi.mocked(featureFlagService.getConfiguration).mockReturnValue({
      bffEnabled: true,
      chartDataEnabled: true,
      runDataEnabled: true,
      websocketEnabled: true,
      fallbackToBackend: true
    })
    vi.mocked(featureFlagService.getEffectiveApiBaseUrl).mockReturnValue('http://127.0.0.1:8001')
    vi.mocked(featureFlagService.getEffectiveWsBaseUrl).mockReturnValue('ws://127.0.0.1:8001')
    vi.mocked(featureFlagService.evaluateFeatureFlag).mockReturnValue({
      enabled: true,
      source: 'bff',
      endpointUrl: 'http://127.0.0.1:8001'
    })
    vi.mocked(featureFlagService.getDebugInfo).mockReturnValue({
      configuration: {
        bffEnabled: true,
        chartDataEnabled: true,
        runDataEnabled: true,
        websocketEnabled: true,
        fallbackToBackend: true
      },
      endpointMappings: {
        chartData: 'http://127.0.0.1:8001/api/v1/chart-data',
        runData: 'http://127.0.0.1:8001/api/v1/backtests',
        websocket: 'ws://127.0.0.1:8001/ws',
        health: 'http://127.0.0.1:8001/health'
      },
      lastEvaluations: {
        chartData: { enabled: true, endpointUrl: 'http://127.0.0.1:8001/api/v1/chart-data', source: 'bff' },
        runData: { enabled: true, endpointUrl: 'http://127.0.0.1:8001/api/v1/backtests', source: 'bff' },
        websocket: { enabled: true, endpointUrl: 'ws://127.0.0.1:8001/api/v1/backtests/{id}/stream', source: 'bff' }
      },
      lastUpdated: Date.now()
    })
  })

  afterEach(() => {
    testHarness.cleanup()
    vi.unstubAllEnvs()
  })

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )

  describe('Complete BFF Mode Integration', () => {
    beforeEach(() => {
      // Enable all BFF features
      vi.stubEnv('VITE_BFF_ENABLED', 'true')
      vi.stubEnv('VITE_BFF_CHART_DATA_ENABLED', 'true')
      vi.stubEnv('VITE_BFF_RUN_DATA_ENABLED', 'true')
      vi.stubEnv('VITE_BFF_WEBSOCKET_ENABLED', 'true')
      vi.stubEnv('VITE_BFF_BASE_URL', 'http://127.0.0.1:8001')
    })

    it('should coordinate API and WebSocket through BFF', async () => {
      // Mock API responses for chart data
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          symbol: 'AAPL',
          timeframe: 'daily',
          bars: [{ t: '2023-01-01', o: 100, h: 105, l: 99, c: 103, v: 1000 }],
          meta: { source: 'bff', points: 1 }
        })
      } as Response)

      // Mock API responses for run data
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          backtest_id: 'test-run-123',
          strategy_id: 'test-strategy',
          status: 'completed',
          metrics: { totalReturn: 0.15 },
          equity: [{ ts: '2023-01-01', value: 10000 }],
          orders: [],
          meta: { source: 'bff', aggregated: true }
        })
      } as Response)

      // Test chart data hook
      const { result: chartResult } = renderHook(
        () => useDailyChartData('AAPL', '2023-01-01', '2023-12-31'),
        { wrapper }
      )

      // Test run data hook
      const { result: runResult } = renderHook(
        () => useBacktestDetail('test-run-123'),
        { wrapper }
      )

      // Test WebSocket health
      const { result: wsResult } = renderHook(
        () => useWebSocketHealth('test-run-123'),
        { wrapper }
      )

      // Wait for API calls to complete
      await waitFor(() => {
        expect(chartResult.current.isSuccess).toBe(true)
      })

      await waitFor(() => {
        expect(runResult.current.isSuccess).toBe(true)
      })

      // Validate all services are using BFF
      expect(mockFetch).toHaveBeenCalledTimes(2)
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('127.0.0.1:8001'),
        expect.any(Object)
      )

      // Validate data sources
      expect(chartResult.current.data?.meta.source).toBe('bff')
      expect(runResult.current.data?.meta.source).toBe('bff')
      expect(wsResult.current.performanceMetrics.connectionSource).toBe('bff')
    })

    it('should demonstrate API call reduction across all services', async () => {
      // Mock responses for all BFF endpoints (chart, list, detail) based on URL
      mockFetch.mockImplementation((url: string) => {
        if (url.includes('/api/v1/chart-data')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              symbol: 'AAPL', timeframe: 'daily', bars: [], meta: { source: 'bff' }
            })
          } as Response)
        }
        if (url.includes('/api/v1/backtests/') && url.includes('/complete')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              backtest_id: 'test-run-123', strategy_id: 's1', status: 'completed', metrics: {}, equity: [], orders: [], meta: { source: 'bff' }
            })
          } as Response)
        }
        if (url.includes('/api/v1/backtests')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ items: [], total: 0, limit: 20, offset: 0, meta: { source: 'bff' } })
          } as Response)
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response)
      })

      // Test multiple hooks simultaneously
      const { result: chartResult } = renderHook(
        () => useDailyChartData('AAPL'),
        { wrapper }
      )

      const { result: runListResult } = renderHook(
        () => useBacktestList({ symbol: 'AAPL' }),
        { wrapper }
      )

      const { result: runDetailResult } = renderHook(
        () => useBacktestDetail('test-run-123'),
        { wrapper }
      )

      // Wait for all to complete
      await waitFor(() => {
        expect(chartResult.current.data?.meta?.source).toBeDefined()
      })

      await waitFor(() => {
        expect(runListResult.current.data?.meta?.source).toBeDefined()
      })

      await waitFor(() => {
        expect(runDetailResult.current.data?.backtest_id).toBe('test-run-123')
      })

      // Should make only 3 API calls (one per service) instead of multiple calls per service
      expect(mockFetch).toHaveBeenCalledTimes(3)

      // All calls should go to BFF
      mockFetch.mock.calls.forEach(call => {
        expect(call[0]).toContain('127.0.0.1:8001')
      })
    })

    it('should maintain performance across all BFF services', async () => {
      // Mock fast BFF responses
      mockFetch.mockImplementation(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            meta: { source: 'bff', responseTime: 25 }
          })
        } as Response)
      )

      const startTime = Date.now()

      // Test multiple services concurrently
      const [chartResult, runListResult, runDetailResult] = await Promise.all([
        new Promise(resolve => {
          const { result } = renderHook(() => useDailyChartData('AAPL'), { wrapper })
          waitFor(() => result.current.isSuccess).then(() => resolve(result.current))
        }),
        new Promise(resolve => {
          const { result } = renderHook(() => useBacktestList(), { wrapper })
          waitFor(() => result.current.isSuccess).then(() => resolve(result.current))
        }),
        new Promise(resolve => {
          const { result } = renderHook(() => useBacktestDetail('test-run'), { wrapper })
          waitFor(() => result.current.isSuccess).then(() => resolve(result.current))
        })
      ])

      const totalTime = Date.now() - startTime

      // All services should complete quickly when using BFF
      expect(totalTime).toBeLessThan(2000) // < 2 seconds for all services
      expect(mockFetch).toHaveBeenCalledTimes(3)
    })
  })

  describe('Fallback and Error Handling', () => {
    it('should error when BFF fails (no fallback policy)', async () => {
      // Mock BFF failure
      mockFetch.mockRejectedValueOnce(new Error('BFF unavailable'))

      const { result } = renderHook(
        () => useDailyChartData('AAPL'),
        { wrapper }
      )

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      // No fallback: only one call attempted
      expect(mockFetch).toHaveBeenCalledTimes(1)
    })

    it('should handle mixed BFF/backend mode gracefully', async () => {
      // Enable only some BFF features
      vi.stubEnv('VITE_BFF_CHART_DATA_ENABLED', 'true')
      vi.stubEnv('VITE_BFF_RUN_DATA_ENABLED', 'false')

      const { featureFlagService } = await import('../../services/featureFlags')
      vi.mocked(featureFlagService.isFeatureFlagEnabled)
        .mockImplementation((flag: string) => flag === 'chartData')
      // Ensure evaluateFeatureFlag reflects mixed mode (chartData via BFF, runData via backend)
      vi.mocked(featureFlagService.evaluateFeatureFlag).mockImplementation((flag: any) => {
        if (flag === 'chartData') return { enabled: true, endpointUrl: 'http://127.0.0.1:8001/api/v1/chart-data', source: 'bff' }
        if (flag === 'runData')   return { enabled: false, endpointUrl: 'http://127.0.0.1:8000/backtests', source: 'backend' }
        if (flag === 'websocket') return { enabled: true, endpointUrl: 'ws://127.0.0.1:8001/api/v1/backtests/{id}/stream', source: 'bff' }
        return { enabled: false, endpointUrl: 'http://127.0.0.1:8000', source: 'backend' }
      })

      // Mock URL-routed responses for both BFF and backend
      mockFetch.mockImplementation((url: string) => {
        const isBFF = url.includes('127.0.0.1:8001')
        if (url.includes('/api/v1/chart-data')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              symbol: 'AAPL', timeframe: 'daily', bars: [], meta: { source: isBFF ? 'bff' : 'backend' }
            })
          } as Response)
        }
        if (url.includes('/api/v1/backtests')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ items: [], total: 0, limit: 20, offset: 0, meta: { source: isBFF ? 'bff' : 'backend' } })
          } as Response)
        }
        if (url.includes('/backtests')) {
          // Backend (non-BFF) list/detail endpoints - may not include meta
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ items: [], total: 0, limit: 20, offset: 0 })
          } as Response)
        }

        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response)
      })

      // Test both services
      const { result: chartResult } = renderHook(
        () => useDailyChartData('AAPL'),
        { wrapper }
      )

      const { result: runResult } = renderHook(
        () => useBacktestList(),
        { wrapper }
      )

      await waitFor(() => {
        expect(chartResult.current.data?.meta?.source).toBe('bff')
      })

      // For backend runData, the list response may not include meta; verify routing by URL instead
      await waitFor(() => {
        const calledWithBackend = mockFetch.mock.calls.some((c) => String(c[0]).includes('127.0.0.1:8000/backtests'))
        expect(calledWithBackend).toBe(true)
      })
      // Ensure the list hook has resolved at least once
      await waitFor(() => {
        expect(runResult.current.data).toBeDefined()
      })

      // Chart data should use BFF, run data should use backend
      expect(mockFetch).toHaveBeenCalledTimes(2)
      expect(chartResult.current.data?.meta.source).toBe('bff')
      // backend list may omit meta; ensure list structure is present
      expect(Array.isArray(runResult.current.data?.items)).toBe(true)
    })
  })

  describe('Epic 9 Performance Validation', () => {
    it('should achieve overall performance improvements with BFF', async () => {
      // Mock optimized BFF responses with valid shapes per endpoint
      mockFetch.mockImplementation((url: string) => {
        if (url.includes('/api/v1/chart-data')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              symbol: 'AAPL', timeframe: 'daily', bars: [], meta: { source: 'bff', optimized: true, responseTime: 15 }
            })
          } as Response)
        }
        if (url.includes('/api/v1/backtests/') && url.includes('/complete')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              backtest_id: 'test-run', strategy_id: 's1', status: 'completed', metrics: {}, equity: [], orders: [], meta: { source: 'bff', optimized: true, responseTime: 15 }
            })
          } as Response)
        }
        if (url.includes('/api/v1/backtests')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ items: [], total: 0, limit: 20, offset: 0, meta: { source: 'bff', optimized: true, responseTime: 15 } })
          } as Response)
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ meta: { source: 'bff', optimized: true, responseTime: 15 } }) } as Response)
      })

      const performanceStartTime = Date.now()

      // Test comprehensive Epic 9 functionality
      const { result: chartResult } = renderHook(
        () => useDailyChartData('AAPL'),
        { wrapper }
      )

      const { result: runListResult } = renderHook(
        () => useBacktestList({ symbol: 'AAPL' }),
        { wrapper }
      )

      const { result: runDetailResult } = renderHook(
        () => useBacktestDetail('test-run'),
        { wrapper }
      )

      const { result: wsHealthResult } = renderHook(
        () => useWebSocketHealth('test-run'),
        { wrapper }
      )

      // Wait for all Epic 9 features to be ready
      await waitFor(() => {
        expect(chartResult.current.data?.meta?.source).toBeDefined()
        expect(runListResult.current.data?.meta?.source).toBeDefined()
        expect(runDetailResult.current.data?.meta?.source).toBeDefined()
      })

      const totalEpicTime = Date.now() - performanceStartTime

      // Epic 9 should demonstrate significant performance improvements
      expect(totalEpicTime).toBeLessThan(3000) // < 3 seconds for complete Epic 9
      expect(mockFetch).toHaveBeenCalledTimes(3) // Reduced API calls

      // All services should be using optimized BFF
      expect(chartResult.current.data?.meta.source).toBe('bff')
      expect(runListResult.current.data?.meta.source).toBe('bff')
      expect(runDetailResult.current.data?.meta.source).toBe('bff')
      expect(wsHealthResult.current.performanceMetrics.connectionSource).toBe('bff')
    })
  })
})
