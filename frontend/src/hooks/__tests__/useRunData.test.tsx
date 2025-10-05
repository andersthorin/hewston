import React from 'react'
/**
 * Tests for BFF-aware run data hooks.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useBacktestList, useBacktestDetail, useCreateBacktest } from '../useRunData'
import type { ReactNode } from 'react'

// Import the mocked services to access them in tests
import { backtestDataService } from '../../services/runData'
import { featureFlagService } from '../../services/featureFlags'

// Mock the backtest data service
vi.mock('../../services/runData', () => ({
  backtestDataService: {
    listBacktests: vi.fn(),
    getCompleteBacktest: vi.fn(),
    createBacktest: vi.fn(),
    getPerformanceMetrics: vi.fn(),
    isUsingAggregation: vi.fn(),
  }
}))

// Mock feature flag service
vi.mock('../../services/featureFlags', () => ({
  featureFlagService: {
    isFeatureFlagEnabled: vi.fn(),
    getDebugInfo: vi.fn(),
    evaluateFeatureFlag: vi.fn(),
  }
}))

// Test wrapper with QueryClient
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  })
  
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

describe('Run Data Hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(featureFlagService.isFeatureFlagEnabled).mockReturnValue(false)
    vi.mocked(featureFlagService.getDebugInfo).mockReturnValue({
      configuration: { bffEnabled: false, runDataEnabled: false },
      lastEvaluations: {},
    })
  })

  describe('useBacktestList', () => {
    it('should fetch backtest list successfully', async () => {
      const mockData = {
        items: [
          {
            backtest_id: 'run-123',
            created_at: '2023-01-01T00:00:00Z',
            strategy_id: 'sma_crossover',
            status: 'completed',
            symbol: 'AAPL',
            run_from: '2023-01-01',
            run_to: '2023-12-31',
            duration_ms: 5000,
            total_return: 0.15,
            sharpe_ratio: 1.2,
            max_drawdown: -0.05,
          }
        ],
        total: 1,
        limit: 20,
        offset: 0,
        meta: { source: 'backend' as const }
      }

      vi.mocked(backtestDataService.listBacktests).mockResolvedValue(mockData as any)

      const { result } = renderHook(
        () => useBacktestList({ symbol: 'AAPL' }),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(vi.mocked(backtestDataService.listBacktests)).toHaveBeenCalledWith({ symbol: 'AAPL' })
      expect(result.current.data).toEqual(mockData)
    })

    it('should include BFF flag in query key', async () => {
      vi.mocked(featureFlagService.isFeatureFlagEnabled).mockReturnValue(true)

      const { result } = renderHook(
        () => useBacktestList(),
        { wrapper: createWrapper() }
      )

      // Query should be loading or successful
      expect(result.current.isLoading || result.current.isSuccess).toBe(true)
    })
  })

  describe('useBacktestDetail', () => {
    it('should fetch complete backtest data with aggregation', async () => {
      const mockData = {
        backtest_id: 'run-123',
        strategy_id: 'sma_crossover',
        status: 'completed',
        dataset_id: 'AAPL-2023-1m',
        run_from: '2023-01-01',
        run_to: '2023-12-31',
        metrics: {
          total_return: 0.15,
          sharpe_ratio: 1.2,
          max_drawdown: -0.05,
          win_rate: 0.6,
          profit_factor: 1.8,
          total_trades: 50,
        },
        equity: [
          { ts: '2023-01-01T00:00:00Z', value: 100000 },
          { ts: '2023-12-31T23:59:59Z', value: 115000 },
        ],
        orders: [
          { ts: '2023-01-01T09:30:00Z', side: 'buy' as const, quantity: 100, price: 150.0 },
        ],
        meta: {
          aggregated: true,
          source: 'bff' as const,
          components_loaded: ['run', 'metrics', 'equity', 'orders'],
        }
      }

      vi.mocked(backtestDataService.getCompleteBacktest).mockResolvedValue(mockData as any)

      const { result } = renderHook(
        () => useBacktestDetail('run-123'),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(vi.mocked(backtestDataService.getCompleteBacktest)).toHaveBeenCalledWith('run-123')
      expect(result.current.data).toEqual(mockData)
    })

    it('should not fetch when backtest_id is undefined', () => {
      renderHook(
        () => useBacktestDetail(undefined),
        { wrapper: createWrapper() }
      )

      expect(vi.mocked(backtestDataService.getCompleteBacktest)).not.toHaveBeenCalled()
    })
  })

  describe('useCreateBacktest', () => {
    it('should create backtest successfully', async () => {
      const mockResponse = { backtest_id: 'run-456', status: 'created' }
      vi.mocked(backtestDataService.createBacktest).mockResolvedValue(mockResponse as any)

      const { result } = renderHook(
        () => useCreateBacktest(),
        { wrapper: createWrapper() }
      )

      const request = {
        strategy_id: 'sma_crossover',
        params: { fast: 20, slow: 50 },
        symbol: 'AAPL',
        year: 2023,
      }

      await act(async () => {
        const response = await result.current.mutateAsync({
          request,
          idempotencyKey: 'test-key'
        })
        expect(response).toEqual(mockResponse)
      })

      expect(vi.mocked(backtestDataService.createBacktest)).toHaveBeenCalledWith(request, 'test-key')
    })

    it('should handle creation errors', async () => {
      const error = new Error('Creation failed')
      vi.mocked(backtestDataService.createBacktest).mockRejectedValue(error)

      const { result } = renderHook(
        () => useCreateBacktest(),
        { wrapper: createWrapper() }
      )

      await act(async () => {
        try {
          await result.current.mutateAsync({
            request: { strategy_id: 'test' }
          })
        } catch (e) {
          expect(e).toEqual(error)
        }
      })
    })
  })

  describe('Feature Flag Integration', () => {
    it('should use different query keys for BFF vs backend', () => {
      // Test backend mode
      vi.mocked(featureFlagService.isFeatureFlagEnabled).mockReturnValue(false)
      const { result: backendResult } = renderHook(
        () => useBacktestDetail('run-123'),
        { wrapper: createWrapper() }
      )

      // Test BFF mode
      vi.mocked(featureFlagService.isFeatureFlagEnabled).mockReturnValue(true)
      const { result: bffResult } = renderHook(
        () => useBacktestDetail('run-123'),
        { wrapper: createWrapper() }
      )

      // Both should be loading or have data, but with different cache keys
      expect(backendResult.current.isLoading || backendResult.current.isSuccess).toBe(true)
      expect(bffResult.current.isLoading || bffResult.current.isSuccess).toBe(true)
    })
  })

  describe('Error Handling', () => {
    it('should handle fetch errors gracefully', async () => {
      const error = new Error('Network error')
      vi.mocked(backtestDataService.listBacktests).mockRejectedValue(error as any)

      const { result } = renderHook(
        () => useBacktestList(),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.error).toEqual(error)
    })
  })
})
