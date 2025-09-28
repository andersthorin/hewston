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
   * Fetch chart data - force BFF path exclusively for diagnostics.
   */
  public async fetchChartData(request: ChartDataRequest): Promise<BFFChartDataResponse> {
    return await this.fetchFromBFF(request)
  }

  /**
   * Fetch chart data from BFF aggregated endpoint.
   */
  private async fetchFromBFF(request: ChartDataRequest): Promise<BFFChartDataResponse> {
    const params = new URLSearchParams({
      symbol: request.symbol,
      // Map UI timeframe to BFF enum values
      timeframe: request.timeframe === 'daily' ? '1D' : request.timeframe === 'hour' ? '1H' : request.timeframe === 'minute' ? '1M' : request.timeframe,
    })

    if (request.from) params.set('from', request.from)
    if (request.to) params.set('to', request.to)
    // BFF expects target_points, not target
    if (request.target !== undefined) params.set('target_points', String(request.target))
    if (request.rth_only !== undefined) params.set('rth_only', String(request.rth_only))

    const raw = await apiGetWithFlags(
      `/chart-data?${params.toString()}`,
      'chartData',
      undefined,
      15000, // Cap BFF attempt at 15s for profiling; no fallback (diagnostics)
      false
    )

    // Normalize BFF response (timestamp/open/high/low/close) to frontend shape (t/o/h/l/c)
    const timeframeOut: 'daily' | 'minute' | 'hour' =
      raw?.timeframe === '1D' ? 'daily' : raw?.timeframe === '1H' ? 'hour' : raw?.timeframe === '1M' ? 'minute' : request.timeframe

    const bars = Array.isArray(raw?.bars) ? raw.bars : []
    const barsOut = bars.map((b: any) => ({
      t: b?.t ?? b?.timestamp,
      o: b?.o ?? b?.open ?? 0,
      h: b?.h ?? b?.high ?? 0,
      l: b?.l ?? b?.low ?? 0,
      c: b?.c ?? b?.close ?? 0,
      v: Number(b?.v ?? b?.volume ?? 0) || 0,
      n: Number(b?.n ?? 0) || 0,
    }))

    const out = {
      symbol: raw?.symbol ?? request.symbol,
      timeframe: timeframeOut,
      bars: barsOut,
      meta: {
        from: raw?.from_date ?? request.from,
        to: raw?.to_date ?? request.to,
        stride_minutes: undefined,
        points: barsOut.length,
        decimated: Boolean(raw?.metadata?.decimated),
        cache_hit: Boolean(raw?.metadata?.cache_hit),
        load_time_ms: typeof raw?.metadata?.load_time_ms === 'number' ? raw.metadata.load_time_ms : undefined,
        source: 'bff' as const,
      },
    }

    return BFFChartDataResponseSchema.parse(out)
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
