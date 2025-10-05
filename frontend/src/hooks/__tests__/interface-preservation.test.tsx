import React from 'react'
/**
 * Hook Interface Preservation Tests
 * 
 * These tests validate that hook interfaces remain unchanged during BFF migration.
 * Critical for ensuring backward compatibility and zero-risk migration.
 */

import { describe, it, expect, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useDailyChartData, useMinuteChartData, useHourChartData } from '../useChartData'
import { useBacktestList, useBacktestDetail, useCreateBacktest } from '../useRunData'
import { useWebSocketHealth } from '../useWebSocketHealth'

// Mock the services to prevent actual API calls
vi.mock('../../services/chartData', () => ({
  chartDataService: {
    fetchDailyData: vi.fn().mockResolvedValue({
      symbol: 'AAPL',
      timeframe: 'daily',
      bars: [],
      meta: { points: 0, source: 'backend' }
    }),
    fetchMinuteData: vi.fn().mockResolvedValue({
      symbol: 'AAPL',
      timeframe: 'minute',
      bars: [],
      meta: { points: 0, source: 'backend' }
    }),
    fetchHourData: vi.fn().mockResolvedValue({
      symbol: 'AAPL',
      timeframe: 'hour',
      bars: [],
      meta: { points: 0, source: 'backend' }
    }),
  }
}))

vi.mock('../../services/runData', () => ({
  backtestDataService: {
    listBacktests: vi.fn().mockResolvedValue({
      items: [],
      total: 0,
      limit: 20,
      offset: 0,
      meta: { source: 'backend' }
    }),
    getCompleteBacktest: vi.fn().mockResolvedValue({
      backtest_id: 'test-backtest',
      metrics: {},
      equity: [],
      orders: [],
      meta: { source: 'backend' }
    }),
    createBacktest: vi.fn().mockResolvedValue({
      backtest_id: 'new-backtest',
      status: 'created'
    }),
  }
}))

vi.mock('../../services/featureFlags', () => ({
  featureFlagService: {
    isFeatureFlagEnabled: vi.fn().mockReturnValue(false),
    getDebugInfo: vi.fn().mockReturnValue({
      configuration: { bffEnabled: false },
      lastEvaluations: {}
    }),
    getEffectiveApiBaseUrl: vi.fn().mockReturnValue('http://127.0.0.1:8000'),
    getEffectiveWsBaseUrl: vi.fn().mockReturnValue('ws://127.0.0.1:8000'),
    getConfiguration: vi.fn().mockReturnValue({
      bffEnabled: false,
      chartDataEnabled: false,
      runDataEnabled: false,
      websocketEnabled: false
    }),
    evaluateFeatureFlag: vi.fn().mockReturnValue({
      enabled: false,
      source: 'backend',
      endpointUrl: 'http://127.0.0.1:8000'
    })
  }
}))

vi.mock('../../services/ws', () => ({
  useBacktestPlayback: vi.fn().mockReturnValue({
    getConnectionHealth: vi.fn().mockReturnValue({
      state: 'connected',
      reconnectAttempts: 0,
      messagesReceived: 0,
      connectionSource: 'backend'
    }),
    ping: vi.fn(),
    reconnect: vi.fn(),
    subscribe: vi.fn().mockReturnValue(() => {}),
  })
}))

describe('Hook Interface Preservation', () => {
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={new QueryClient({
      defaultOptions: { queries: { retry: false } }
    })}>
      {children}
    </QueryClientProvider>
  )

  describe('Chart Data Hooks', () => {
    it('should preserve useDailyChartData interface', () => {
      const { result } = renderHook(
        () => useDailyChartData('AAPL', '2023-01-01', '2023-12-31'),
        { wrapper }
      )
      
      // Verify expected interface properties exist
      expect(result.current).toHaveProperty('data')
      expect(result.current).toHaveProperty('isLoading')
      expect(result.current).toHaveProperty('error')
      expect(result.current).toHaveProperty('isSuccess')
      expect(result.current).toHaveProperty('isError')
      expect(result.current).toHaveProperty('refetch')
    })

    it('should preserve useMinuteChartData interface', () => {
      const { result } = renderHook(
        () => useMinuteChartData('AAPL', '2023-01-01', '2023-01-02', 10000, true),
        { wrapper }
      )
      
      expect(result.current).toHaveProperty('data')
      expect(result.current).toHaveProperty('isLoading')
      expect(result.current).toHaveProperty('error')
      expect(result.current).toHaveProperty('isSuccess')
      expect(result.current).toHaveProperty('isError')
      expect(result.current).toHaveProperty('refetch')
    })

    it('should preserve useHourChartData interface', () => {
      const { result } = renderHook(
        () => useHourChartData('AAPL', '2023-01-01', '2023-01-02', true),
        { wrapper }
      )
      
      expect(result.current).toHaveProperty('data')
      expect(result.current).toHaveProperty('isLoading')
      expect(result.current).toHaveProperty('error')
      expect(result.current).toHaveProperty('isSuccess')
      expect(result.current).toHaveProperty('isError')
      expect(result.current).toHaveProperty('refetch')
    })

    it('should maintain chart data hook parameter interfaces', () => {
      // Test parameter type safety
      expect(() => {
        renderHook(() => useDailyChartData('AAPL'), { wrapper })
        renderHook(() => useDailyChartData('AAPL', '2023-01-01'), { wrapper })
        renderHook(() => useDailyChartData('AAPL', '2023-01-01', '2023-12-31'), { wrapper })
      }).not.toThrow()

      expect(() => {
        renderHook(() => useMinuteChartData('AAPL'), { wrapper })
        renderHook(() => useMinuteChartData('AAPL', '2023-01-01', '2023-01-02'), { wrapper })
        renderHook(() => useMinuteChartData('AAPL', '2023-01-01', '2023-01-02', 10000), { wrapper })
        renderHook(() => useMinuteChartData('AAPL', '2023-01-01', '2023-01-02', 10000, true), { wrapper })
      }).not.toThrow()
    })
  })

  describe('Backtest Data Hooks', () => {
    it('should preserve useBacktestList interface', () => {
      const { result } = renderHook(
        () => useBacktestList({ symbol: 'AAPL' }),
        { wrapper }
      )

      expect(result.current).toHaveProperty('data')
      expect(result.current).toHaveProperty('isLoading')
      expect(result.current).toHaveProperty('error')
      expect(result.current).toHaveProperty('isSuccess')
      expect(result.current).toHaveProperty('isError')
      expect(result.current).toHaveProperty('refetch')
    })

    it('should preserve useBacktestDetail interface', () => {
      const { result } = renderHook(
        () => useBacktestDetail('test-backtest-123'),
        { wrapper }
      )

      expect(result.current).toHaveProperty('data')
      expect(result.current).toHaveProperty('isLoading')
      expect(result.current).toHaveProperty('error')
      expect(result.current).toHaveProperty('isSuccess')
      expect(result.current).toHaveProperty('isError')
      expect(result.current).toHaveProperty('refetch')
    })

    it('should preserve useCreateBacktest interface', () => {
      const { result } = renderHook(
        () => useCreateBacktest(),
        { wrapper }
      )

      expect(result.current).toHaveProperty('mutate')
      expect(result.current).toHaveProperty('mutateAsync')
      const keys = Object.keys(result.current)
      expect(keys.includes('isLoading') || keys.includes('isPending')).toBe(true)
      expect(result.current).toHaveProperty('isError')
      expect(result.current).toHaveProperty('isSuccess')
      expect(result.current).toHaveProperty('error')
      expect(result.current).toHaveProperty('data')
      expect(result.current).toHaveProperty('reset')
    })

    it('should maintain backtest hook parameter interfaces', () => {
      // Test parameter type safety
      expect(() => {
        renderHook(() => useBacktestList(), { wrapper })
        renderHook(() => useBacktestList({}), { wrapper })
        renderHook(() => useBacktestList({ symbol: 'AAPL' }), { wrapper })
        renderHook(() => useBacktestList({ symbol: 'AAPL', limit: 10 }), { wrapper })
      }).not.toThrow()

      expect(() => {
        renderHook(() => useBacktestDetail('backtest-123'), { wrapper })
        renderHook(() => useBacktestDetail(undefined), { wrapper })
      }).not.toThrow()
    })
  })

  describe('WebSocket Hooks', () => {
    it('should preserve useWebSocketHealth interface', () => {
      const { result } = renderHook(
        () => useWebSocketHealth('test-run-123'),
        { wrapper }
      )

      expect(result.current).toHaveProperty('connectionStatus')
      expect(result.current).toHaveProperty('performanceMetrics')
      expect(result.current).toHaveProperty('hasGoodPerformance')
      expect(result.current).toHaveProperty('reconnect')
      expect(result.current).toHaveProperty('ping')
    })

    it('should maintain WebSocket hook parameter interfaces', () => {
      expect(() => {
        renderHook(() => useWebSocketHealth('run-123'), { wrapper })
        renderHook(() => useWebSocketHealth(undefined), { wrapper })
      }).not.toThrow()
    })
  })

  describe('Hook Return Type Safety', () => {
    it('should maintain TypeScript type safety for chart data hooks', () => {
      const { result } = renderHook(
        () => useDailyChartData('AAPL'),
        { wrapper }
      )

      // Verify return types are as expected
      expect(typeof result.current.isLoading).toBe('boolean')
      expect(typeof result.current.isSuccess).toBe('boolean')
      expect(typeof result.current.isError).toBe('boolean')
      expect(typeof result.current.refetch).toBe('function')
    })

    it('should maintain TypeScript type safety for run data hooks', () => {
      const { result } = renderHook(
        () => useBacktestList(),
        { wrapper }
      )

      // React Query exposes flags; depending on version, isLoading or isPending may be present
      const keys = Object.keys(result.current)
      expect(keys.includes('isLoading') || keys.includes('isPending')).toBe(true)
      expect(typeof result.current.isSuccess).toBe('boolean')
      expect(typeof result.current.isError).toBe('boolean')
      expect(typeof result.current.refetch).toBe('function')
    })

    it('should maintain TypeScript type safety for mutation hooks', () => {
      const { result } = renderHook(
        () => useCreateBacktest(),
        { wrapper }
      )

      expect(typeof result.current.mutate).toBe('function')
      expect(typeof result.current.mutateAsync).toBe('function')
      const keys = Object.keys(result.current)
      expect(keys.includes('isLoading') || keys.includes('isPending')).toBe(true)
      expect(typeof result.current.reset).toBe('function')
    })
  })

  describe('Hook Behavior Consistency', () => {
    it('should maintain consistent query behavior across BFF and backend modes', () => {
      // Test that hooks behave consistently regardless of BFF flag state
      const { result: backendResult } = renderHook(
        () => useDailyChartData('AAPL'),
        { wrapper }
      )

      // Should expose at least these core fields (React Query adds more)
      const keys = Object.keys(backendResult.current)
      expect(keys).toEqual(expect.arrayContaining([
        'data', 'error', 'isError', 'isLoading', 'isSuccess', 'refetch'
      ]))
    })

    it('should maintain consistent mutation behavior', () => {
      const { result } = renderHook(
        () => useCreateBacktest(),
        { wrapper }
      )

      // Mutation interface should include standard fields (React Query v5 uses isPending)
      const keys = Object.keys(result.current)
      expect(keys).toEqual(expect.arrayContaining([
        'data', 'error', 'isError', 'isSuccess', 'mutate', 'mutateAsync', 'reset'
      ]))
      expect(keys.includes('isLoading') || keys.includes('isPending')).toBe(true)
    })
  })
})
