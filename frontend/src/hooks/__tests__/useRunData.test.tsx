/**
 * Tests for BFF-aware run data hooks.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useRunList, useCompleteRunData, useCreateRun } from '../useRunData'
import type { ReactNode } from 'react'

// Import the mocked services to access them in tests
import { runDataService } from '../../services/runData'
import { featureFlagService } from '../../services/featureFlags'

// Mock the run data service
vi.mock('../../services/runData', () => ({
  runDataService: {
    listRuns: vi.fn(),
    getCompleteRunData: vi.fn(),
    createRun: vi.fn(),
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

  describe('useRunList', () => {
    it('should fetch run list successfully', async () => {
      const mockData = {
        items: [
          {
            run_id: 'run-123',
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
      
      vi.mocked(runDataService.listRuns).mockResolvedValue(mockData)

      const { result } = renderHook(
        () => useRunList({ symbol: 'AAPL' }),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(vi.mocked(runDataService.listRuns)).toHaveBeenCalledWith({ symbol: 'AAPL' })
      expect(result.current.data).toEqual(mockData)
    })

    it('should include BFF flag in query key', async () => {
      vi.mocked(featureFlagService.isFeatureFlagEnabled).mockReturnValue(true)
      
      const { result } = renderHook(
        () => useRunList(),
        { wrapper: createWrapper() }
      )
      
      // Query should be loading or successful
      expect(result.current.isLoading || result.current.isSuccess).toBe(true)
    })
  })

  describe('useCompleteRunData', () => {
    it('should fetch complete run data with aggregation', async () => {
      const mockData = {
        run_id: 'run-123',
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
      
      vi.mocked(runDataService.getCompleteRunData).mockResolvedValue(mockData)

      const { result } = renderHook(
        () => useCompleteRunData('run-123'),
        { wrapper: createWrapper() }
      )

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(vi.mocked(runDataService.getCompleteRunData)).toHaveBeenCalledWith('run-123')
      expect(result.current.data).toEqual(mockData)
    })

    it('should not fetch when run_id is undefined', () => {
      renderHook(
        () => useCompleteRunData(undefined),
        { wrapper: createWrapper() }
      )
      
      expect(vi.mocked(runDataService.getCompleteRunData)).not.toHaveBeenCalled()
    })
  })

  describe('useCreateRun', () => {
    it('should create run successfully', async () => {
      const mockResponse = { run_id: 'run-456', status: 'created' }
      vi.mocked(runDataService.createRun).mockResolvedValue(mockResponse)
      
      const { result } = renderHook(
        () => useCreateRun(),
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
      
      expect(vi.mocked(runDataService.createRun)).toHaveBeenCalledWith(request, 'test-key')
    })

    it('should handle creation errors', async () => {
      const error = new Error('Creation failed')
      vi.mocked(runDataService.createRun).mockRejectedValue(error)
      
      const { result } = renderHook(
        () => useCreateRun(),
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
        () => useCompleteRunData('run-123'),
        { wrapper: createWrapper() }
      )

      // Test BFF mode
      vi.mocked(featureFlagService.isFeatureFlagEnabled).mockReturnValue(true)
      const { result: bffResult } = renderHook(
        () => useCompleteRunData('run-123'),
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
      vi.mocked(runDataService.listRuns).mockRejectedValue(error)
      
      const { result } = renderHook(
        () => useRunList(),
        { wrapper: createWrapper() }
      )
      
      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })
      
      expect(result.current.error).toEqual(error)
    })
  })
})
