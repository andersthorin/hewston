/**
 * Chart data hooks with BFF integration and feature flag support.
 * 
 * These hooks provide a unified interface for fetching chart data that
 * automatically routes to BFF or backend based on feature flag configuration.
 */

import { useQuery, type UseQueryResult } from '@tanstack/react-query'
import { chartDataService, type BFFChartDataResponse } from '../services/chartData'
import { featureFlagService } from '../services/featureFlags'

/**
 * Hook for fetching daily chart data with BFF integration.
 */
export function useDailyChartData(
  symbol: string | undefined,
  from?: string,
  to?: string,
  enabled: boolean = true
): UseQueryResult<BFFChartDataResponse, Error> {
  const useBFF = featureFlagService.isFeatureFlagEnabled('chartData')
  
  return useQuery({
    queryKey: ['chart-data', 'daily', symbol, from, to, useBFF ? 'bff' : 'backend'],
    queryFn: () => chartDataService.fetchDailyData(symbol!, from, to),
    enabled: enabled && !!symbol,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000,   // 10 minutes (was cacheTime)
  })
}

/**
 * Hook for fetching minute chart data with BFF integration and decimation support.
 */
export function useMinuteChartData(
  symbol: string | undefined,
  from: string | undefined,
  to: string | undefined,
  target?: number,
  rth_only: boolean = true,
  enabled: boolean = true
): UseQueryResult<BFFChartDataResponse, Error> {
  const useBFF = featureFlagService.isFeatureFlagEnabled('chartData')
  
  return useQuery({
    queryKey: [
      'chart-data', 
      'minute', 
      symbol, 
      from, 
      to, 
      target, 
      rth_only, 
      useBFF ? 'bff' : 'backend'
    ],
    queryFn: () => chartDataService.fetchMinuteData(symbol!, from!, to!, target, rth_only),
    enabled: enabled && !!symbol && !!from && !!to,
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 5 * 60 * 1000,    // 5 minutes
  })
}

/**
 * Hook for fetching hour chart data with BFF integration.
 */
export function useHourChartData(
  symbol: string | undefined,
  from: string | undefined,
  to: string | undefined,
  rth_only: boolean = true,
  enabled: boolean = true
): UseQueryResult<BFFChartDataResponse, Error> {
  const useBFF = featureFlagService.isFeatureFlagEnabled('chartData')
  
  return useQuery({
    queryKey: [
      'chart-data', 
      'hour', 
      symbol, 
      from, 
      to, 
      rth_only, 
      useBFF ? 'bff' : 'backend'
    ],
    queryFn: () => chartDataService.fetchHourData(symbol!, from!, to!, rth_only),
    enabled: enabled && !!symbol && !!from && !!to,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000,   // 10 minutes
  })
}

/**
 * Hook for fetching chart data with automatic timeframe selection.
 */
export function useAdaptiveChartData(
  symbol: string | undefined,
  from: string | undefined,
  to: string | undefined,
  preferredTimeframe: 'daily' | 'minute' | 'hour' = 'hour',
  enabled: boolean = true
): UseQueryResult<BFFChartDataResponse, Error> {
  const useBFF = featureFlagService.isFeatureFlagEnabled('chartData')
  
  // Calculate optimal target for decimation based on date range
  const calculateTarget = (from?: string, to?: string): number | undefined => {
    if (!from || !to) return undefined
    
    const fromDate = new Date(from)
    const toDate = new Date(to)
    const daysDiff = Math.ceil((toDate.getTime() - fromDate.getTime()) / (1000 * 60 * 60 * 24))
    
    // For minute data, target ~10k points for good performance
    if (preferredTimeframe === 'minute' && daysDiff > 30) {
      return 10000
    }
    
    return undefined
  }
  
  const target = calculateTarget(from, to)
  
  return useQuery({
    queryKey: [
      'chart-data', 
      'adaptive',
      preferredTimeframe,
      symbol, 
      from, 
      to, 
      target,
      useBFF ? 'bff' : 'backend'
    ],
    queryFn: () => {
      switch (preferredTimeframe) {
        case 'daily':
          return chartDataService.fetchDailyData(symbol!, from, to)
        case 'minute':
          return chartDataService.fetchMinuteData(symbol!, from!, to!, target, true)
        case 'hour':
          return chartDataService.fetchHourData(symbol!, from!, to!, true)
        default:
          throw new Error(`Unsupported timeframe: ${preferredTimeframe}`)
      }
    },
    enabled: enabled && !!symbol && !!from && !!to,
    staleTime: 3 * 60 * 1000, // 3 minutes
    gcTime: 8 * 60 * 1000,    // 8 minutes
  })
}

/**
 * Hook for getting chart data performance metrics.
 */
export function useChartDataMetrics() {
  const metrics = chartDataService.getPerformanceMetrics()
  const debugInfo = featureFlagService.getDebugInfo()
  
  return {
    ...metrics,
    featureFlags: {
      bffEnabled: debugInfo.configuration.bffEnabled,
      chartDataEnabled: debugInfo.configuration.chartDataEnabled,
    },
    lastEvaluations: debugInfo.lastEvaluations.chartData,
  }
}

/**
 * Hook for checking if chart data is using BFF.
 */
export function useIsChartDataBFF(): boolean {
  return featureFlagService.isFeatureFlagEnabled('chartData')
}

/**
 * Legacy compatibility hooks - these maintain the same interface as the original hooks
 * but internally use the new BFF-aware services.
 */

/**
 * Legacy hook for daily data - maintains backward compatibility.
 */
export function useDailyData(
  symbol: string | undefined,
  from?: string,
  to?: string,
  enabled: boolean = true
) {
  const result = useDailyChartData(symbol, from, to, enabled)
  
  // Transform BFF response to legacy format for backward compatibility
  return {
    ...result,
    data: result.data ? {
      symbol: result.data.symbol,
      bars: result.data.bars,
    } : undefined,
  }
}

/**
 * Legacy hook for minute data - maintains backward compatibility.
 */
export function useMinuteData(
  symbol: string | undefined,
  from: string | undefined,
  to: string | undefined,
  target?: number,
  rth_only: boolean = true,
  enabled: boolean = true
) {
  const result = useMinuteChartData(symbol, from, to, target, rth_only, enabled)
  
  // Transform BFF response to legacy format for backward compatibility
  return {
    ...result,
    data: result.data ? {
      symbol: result.data.symbol,
      bars: result.data.bars,
      meta: result.data.meta ? {
        stride_minutes: result.data.meta.stride_minutes,
        points: result.data.meta.points,
      } : undefined,
    } : undefined,
  }
}

/**
 * Legacy hook for hour data - maintains backward compatibility.
 */
export function useHourData(
  symbol: string | undefined,
  from: string | undefined,
  to: string | undefined,
  rth_only: boolean = true,
  enabled: boolean = true
) {
  const result = useHourChartData(symbol, from, to, rth_only, enabled)
  
  // Transform BFF response to legacy format for backward compatibility
  return {
    ...result,
    data: result.data ? {
      symbol: result.data.symbol,
      bars: result.data.bars,
    } : undefined,
  }
}
