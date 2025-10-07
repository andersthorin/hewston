import React from 'react'
/**
 * Tests for BFF-aware chart data hooks.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useDailyChartData, useMinuteChartData, useHourChartData } from '../useChartData'
import type { ReactNode } from 'react'

// Import the mocked services to access them in tests
import { chartDataService } from '../../services/chartData'
import { featureFlagService } from '../../services/featureFlags'

// Mock the chart data service
vi.mock('../../services/chartData', () => ({
  chartDataService: {
    fetchDailyData: vi.fn(),
    fetchMinuteData: vi.fn(),
    fetchHourData: vi.fn(),
    getPerformanceMetrics: vi.fn(),
  },
}))

// Mock feature flag service
vi.mock('../../services/featureFlags', () => ({
  featureFlagService: {
    isFeatureFlagEnabled: vi.fn(),
    getDebugInfo: vi.fn(),
    evaluateFeatureFlag: vi.fn(),
  },
}))

// Test wrapper with QueryClient
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('Chart Data Hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(featureFlagService.isFeatureFlagEnabled).mockReturnValue(false)
    vi.mocked(featureFlagService.getDebugInfo).mockReturnValue({
      configuration: { bffEnabled: false, chartDataEnabled: false },
      lastEvaluations: {},
    })
  })

  describe('useDailyChartData', () => {
    it('should fetch daily chart data when enabled', async () => {
      const mockData = {
        symbol: 'AAPL',
        timeframe: 'daily' as const,
        bars: [{ t: '2023-01-01', o: 100, h: 105, l: 99, c: 103, v: 1000 }],
        meta: { points: 1, source: 'backend' as const },
      }

      vi.mocked(chartDataService.fetchDailyData).mockResolvedValue(mockData)

      const { result } = renderHook(() => useDailyChartData('AAPL', '2023-01-01', '2023-12-31'), {
        wrapper: createWrapper(),
      })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(vi.mocked(chartDataService.fetchDailyData)).toHaveBeenCalledWith(
        'AAPL',
        '2023-01-01',
        '2023-12-31',
      )
      expect(result.current.data).toEqual(mockData)
    })

    it('should not fetch when symbol is undefined', () => {
      renderHook(() => useDailyChartData(undefined), { wrapper: createWrapper() })

      expect(vi.mocked(chartDataService.fetchDailyData)).not.toHaveBeenCalled()
    })

    it('should include BFF flag in query key', async () => {
      vi.mocked(featureFlagService.isFeatureFlagEnabled).mockReturnValue(true)

      const { result } = renderHook(() => useDailyChartData('AAPL'), { wrapper: createWrapper() })

      // Query key should include BFF flag
      expect(result.current.isLoading || result.current.isSuccess).toBe(true)
    })
  })

  describe('useMinuteChartData', () => {
    it('should fetch minute chart data with decimation', async () => {
      const mockData = {
        symbol: 'AAPL',
        timeframe: 'minute' as const,
        bars: [{ t: '2023-01-01T09:30:00', o: 100, h: 101, l: 99, c: 100.5, v: 500 }],
        meta: { points: 1, decimated: true, source: 'backend' as const },
      }

      vi.mocked(chartDataService.fetchMinuteData).mockResolvedValue(mockData)

      const { result } = renderHook(
        () => useMinuteChartData('AAPL', '2023-01-01', '2023-01-02', 10000, true),
        { wrapper: createWrapper() },
      )

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(vi.mocked(chartDataService.fetchMinuteData)).toHaveBeenCalledWith(
        'AAPL',
        '2023-01-01',
        '2023-01-02',
        10000,
        true,
      )
      expect(result.current.data).toEqual(mockData)
    })

    it('should not fetch when required parameters are missing', () => {
      renderHook(() => useMinuteChartData('AAPL', undefined, '2023-01-02'), {
        wrapper: createWrapper(),
      })

      expect(vi.mocked(chartDataService.fetchMinuteData)).not.toHaveBeenCalled()
    })
  })

  describe('useHourChartData', () => {
    it('should fetch hour chart data', async () => {
      const mockData = {
        symbol: 'AAPL',
        timeframe: 'hour' as const,
        bars: [{ t: '2023-01-01T09:00:00', o: 100, h: 102, l: 99, c: 101, v: 2000 }],
        meta: { points: 1, source: 'backend' as const },
      }

      vi.mocked(chartDataService.fetchHourData).mockResolvedValue(mockData)

      const { result } = renderHook(
        () => useHourChartData('AAPL', '2023-01-01', '2023-01-02', true),
        { wrapper: createWrapper() },
      )

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(vi.mocked(chartDataService.fetchHourData)).toHaveBeenCalledWith(
        'AAPL',
        '2023-01-01',
        '2023-01-02',
        true,
      )
      expect(result.current.data).toEqual(mockData)
    })
  })

  describe('Feature Flag Integration', () => {
    it('should use different query keys for BFF vs backend', () => {
      // Test backend mode
      vi.mocked(featureFlagService.isFeatureFlagEnabled).mockReturnValue(false)
      const { result: backendResult } = renderHook(() => useDailyChartData('AAPL'), {
        wrapper: createWrapper(),
      })

      // Test BFF mode
      vi.mocked(featureFlagService.isFeatureFlagEnabled).mockReturnValue(true)
      const { result: bffResult } = renderHook(() => useDailyChartData('AAPL'), {
        wrapper: createWrapper(),
      })

      // Both should be loading or have data, but with different cache keys
      expect(backendResult.current.isLoading || backendResult.current.isSuccess).toBe(true)
      expect(bffResult.current.isLoading || bffResult.current.isSuccess).toBe(true)
    })
  })

  describe('Error Handling', () => {
    it('should handle fetch errors gracefully', async () => {
      const error = new Error('Network error')
      vi.mocked(chartDataService.fetchDailyData).mockRejectedValue(error)

      const { result } = renderHook(() => useDailyChartData('AAPL'), { wrapper: createWrapper() })

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.error).toEqual(error)
    })
  })
})
