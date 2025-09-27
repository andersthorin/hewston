/**
 * BFF Chart Data Service - Unified chart data fetching with feature flag support.
 * 
 * This service provides a unified interface for fetching chart data that can
 * route to either BFF aggregated endpoints or direct backend endpoints based
 * on feature flag configuration.
 */

import { z } from 'zod'
import { apiGetWithFlags } from '../utils/api'
import { featureFlagService } from './featureFlags'
import { 
  fetchDaily, 
  fetchMinute, 
  fetchMinuteDecimated, 
  fetchHour,
  type DailyResponse,
  type MinuteResponse,
  type HourResponse 
} from './bars'

/**
 * BFF Chart Data Response Schema - Unified response format from BFF.
 */
export const BFFChartDataResponseSchema = z.object({
  symbol: z.string(),
  timeframe: z.enum(['daily', 'minute', 'hour']),
  bars: z.array(z.object({
    t: z.string(),
    o: z.number(),
    h: z.number(),
    l: z.number(),
    c: z.number(),
    v: z.number().optional().default(0),
    n: z.number().optional().default(0),
  })),
  meta: z.object({
    from: z.string().optional(),
    to: z.string().optional(),
    stride_minutes: z.number().optional(),
    points: z.number(),
    decimated: z.boolean().optional().default(false),
    cache_hit: z.boolean().optional().default(false),
    load_time_ms: z.number().optional(),
    source: z.enum(['bff', 'backend']).optional().default('bff'),
  }).optional(),
})

export type BFFChartDataResponse = z.infer<typeof BFFChartDataResponseSchema>

/**
 * Chart data request parameters.
 */
export interface ChartDataRequest {
  symbol: string
  timeframe: 'daily' | 'minute' | 'hour'
  from?: string
  to?: string
  target?: number  // For decimation
  rth_only?: boolean
}

/**
 * Unified chart data service with BFF integration.
 */
export class ChartDataService {
  /**
   * Fetch chart data with automatic BFF/backend routing based on feature flags.
   */
  public async fetchChartData(request: ChartDataRequest): Promise<BFFChartDataResponse> {
    const useBFF = featureFlagService.isFeatureFlagEnabled('chartData')
    
    if (useBFF) {
      return await this.fetchFromBFF(request)
    } else {
      return await this.fetchFromBackend(request)
    }
  }

  /**
   * Fetch chart data from BFF aggregated endpoint.
   */
  private async fetchFromBFF(request: ChartDataRequest): Promise<BFFChartDataResponse> {
    const params = new URLSearchParams({
      symbol: request.symbol,
      timeframe: request.timeframe,
    })
    
    if (request.from) params.set('from', request.from)
    if (request.to) params.set('to', request.to)
    if (request.target) params.set('target', String(request.target))
    if (request.rth_only !== undefined) params.set('rth_only', String(request.rth_only))

    const response = await apiGetWithFlags(
      `/chart-data?${params.toString()}`,
      'chartData'
    )

    return BFFChartDataResponseSchema.parse(response)
  }

  /**
   * Fetch chart data from direct backend endpoints (fallback).
   */
  private async fetchFromBackend(request: ChartDataRequest): Promise<BFFChartDataResponse> {
    const { symbol, timeframe, from, to, target, rth_only = true } = request

    let backendResponse: DailyResponse | MinuteResponse | HourResponse
    let bars: any[]

    switch (timeframe) {
      case 'daily':
        backendResponse = await fetchDaily(symbol, from, to)
        bars = backendResponse.bars
        break
      
      case 'minute':
        if (target && target < 50000) {
          // Use decimated endpoint for large datasets
          backendResponse = await fetchMinuteDecimated(symbol, from!, to!, target, rth_only)
        } else {
          backendResponse = await fetchMinute(symbol, from!, to!, rth_only)
        }
        bars = backendResponse.bars
        break
      
      case 'hour':
        backendResponse = await fetchHour(symbol, from!, to!, rth_only)
        bars = backendResponse.bars
        break
      
      default:
        throw new Error(`Unsupported timeframe: ${timeframe}`)
    }

    // Transform backend response to BFF format
    return {
      symbol: backendResponse.symbol,
      timeframe,
      bars: bars.map(bar => ({
        t: bar.t,
        o: bar.o,
        h: bar.h,
        l: bar.l,
        c: bar.c,
        v: bar.v || 0,
        n: (bar as any).n || 0,
      })),
      meta: {
        from,
        to,
        stride_minutes: (backendResponse as any).meta?.stride_minutes,
        points: bars.length,
        decimated: target !== undefined && target < 50000,
        cache_hit: false,
        source: 'backend',
      },
    }
  }

  /**
   * Fetch daily chart data.
   */
  public async fetchDailyData(
    symbol: string, 
    from?: string, 
    to?: string
  ): Promise<BFFChartDataResponse> {
    return this.fetchChartData({
      symbol,
      timeframe: 'daily',
      from,
      to,
    })
  }

  /**
   * Fetch minute chart data with optional decimation.
   */
  public async fetchMinuteData(
    symbol: string,
    from: string,
    to: string,
    target?: number,
    rth_only: boolean = true
  ): Promise<BFFChartDataResponse> {
    return this.fetchChartData({
      symbol,
      timeframe: 'minute',
      from,
      to,
      target,
      rth_only,
    })
  }

  /**
   * Fetch hour chart data.
   */
  public async fetchHourData(
    symbol: string,
    from: string,
    to: string,
    rth_only: boolean = true
  ): Promise<BFFChartDataResponse> {
    return this.fetchChartData({
      symbol,
      timeframe: 'hour',
      from,
      to,
      rth_only,
    })
  }

  /**
   * Get chart data loading performance metrics.
   */
  public getPerformanceMetrics(): {
    bffEnabled: boolean
    lastLoadTime?: number
    cacheHitRate?: number
  } {
    const config = featureFlagService.getConfiguration()
    return {
      bffEnabled: config.bffEnabled && config.chartDataEnabled,
      // TODO: Implement performance tracking
      lastLoadTime: undefined,
      cacheHitRate: undefined,
    }
  }
}

// Export singleton instance
export const chartDataService = new ChartDataService()
