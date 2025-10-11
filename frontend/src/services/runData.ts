/**
 * Backtest Data Service - BFF-only backtest data fetching.
 *
 * Canonical backtests endpoints only. No legacy "runs" support.
 */

import { z } from 'zod'
import { apiGetWithFlags, apiPostWithFlags } from '../utils/api'
import { featureFlagService } from './featureFlags'
import type { CreateBacktestRequest, CreateBacktestResponse, BacktestListQuery } from './api'

// Complete backtest data in a single response (BFF aggregated)
export const BFFAggregatedBacktestResponseSchema = z.object({
  backtest_id: z.string(),
  dataset_id: z.string().optional().nullable(),
  strategy_id: z.string(),
  status: z.string(),
  error_message: z.string().optional().nullable(),
  code_hash: z.string().optional().nullable(),
  seed: z.number().optional().nullable(),
  speed: z.number().optional().nullable(),
  duration_ms: z.number().optional().nullable(),
  params: z.record(z.string(), z.any()).optional().nullable(),
  slippage_fees: z.record(z.string(), z.any()).optional().nullable(),

  // Backtest window (from manifest)
  run_from: z.string().optional().nullable(),
  run_to: z.string().optional().nullable(),

  // Aggregated metrics data
  metrics: z
    .object({
      total_return: z.number().optional().nullable(),
      sharpe_ratio: z.number().optional().nullable(),
      max_drawdown: z.number().optional().nullable(),
      win_rate: z.number().optional().nullable(),
      profit_factor: z.number().optional().nullable(),
      total_trades: z.number().optional().nullable(),
      avg_trade_duration: z.number().optional().nullable(),
    })
    .optional()
    .nullable(),

  // Aggregated equity curve data
  equity: z
    .array(z.object({ ts: z.string(), value: z.number() }))
    .optional()
    .nullable(),

  // Aggregated orders data
  orders: z
    .array(
      z.object({
        ts: z.string(),
        side: z.union([
          z.enum(['buy', 'sell']),
          z.enum(['BUY', 'SELL']).transform((s) => s.toLowerCase() as 'buy' | 'sell'),
        ]),
        quantity: z.number(),
        price: z.number(),
        order_type: z.string().optional(),
        status: z.string().optional(),
      }),
    )
    .optional()
    .nullable(),

  // BFF metadata
  meta: z
    .object({
      aggregated: z.boolean().default(true),
      cache_hit: z.boolean().optional().default(false),
      load_time_ms: z.number().optional(),
      source: z.enum(['bff']).default('bff'),
      components_loaded: z.array(z.string()).optional(),
    })
    .optional(),
})
export type BFFAggregatedBacktestResponse = z.infer<typeof BFFAggregatedBacktestResponseSchema>

// Backtest list with metadata (BFF-enhanced)
export const BFFBacktestListResponseSchema = z.object({
  items: z.array(
    z.object({
      backtest_id: z.string(),
      created_at: z.string(),
      strategy_id: z.string(),
      status: z.string(),
      symbol: z.string().optional().nullable(),
      run_from: z.string().optional().nullable(),
      run_to: z.string().optional().nullable(),
      duration_ms: z.number().optional().nullable(),
      total_return: z.number().optional().nullable(),
      sharpe_ratio: z.number().optional().nullable(),
      max_drawdown: z.number().optional().nullable(),
      win_rate: z.number().optional().nullable(),
      // Portfolio surfacing (optional)
      instruments_count: z.number().optional().nullable(),
      strategies_count: z.number().optional().nullable(),
      is_portfolio: z.boolean().optional().nullable(),
    }),
  ),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
  meta: z
    .object({
      cache_hit: z.boolean().optional().default(false),
      load_time_ms: z.number().optional(),
      source: z.enum(['bff']).optional().default('bff'),
    })
    .optional(),
})
export type BFFBacktestListResponse = z.infer<typeof BFFBacktestListResponseSchema>

export class BacktestDataService {
  public async listBacktests(query: BacktestListQuery = {}): Promise<BFFBacktestListResponse> {
    const params = new URLSearchParams()
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && v !== '') params.set(k, String(v))
    }
    const response: any = await apiGetWithFlags<any>(`/backtests?${params.toString()}`, 'runData')
    // Normalize any legacy/nested shapes to ensure backtest_id is present before Zod parsing
    if (response && Array.isArray(response.items)) {
      response.items = response.items.map((it: any) => {
        const run = it && typeof it === 'object' ? it.run || {} : {}
        const normalized = {
          backtest_id: it?.backtest_id ?? it?.run_id ?? it?.id ?? run?.run_id ?? run?.id,
          created_at: it?.created_at ?? run?.created_at ?? it?.createdAt,
          strategy_id: it?.strategy_id ?? run?.strategy_id ?? it?.strategyId,
          status: it?.status ?? run?.status,
          symbol: it?.symbol ?? run?.symbol,
          run_from: it?.run_from ?? run?.run_from,
          run_to: it?.run_to ?? run?.run_to,
          duration_ms: it?.duration_ms ?? run?.duration_ms ?? it?.durationMs,
        }
        return { ...it, ...normalized }
      })
    }
    return BFFBacktestListResponseSchema.parse(response)
  }

  public async getCompleteBacktest(backtest_id: string): Promise<BFFAggregatedBacktestResponse> {
    const response: any = await apiGetWithFlags<any>(
      `/backtests/${backtest_id}/complete`,
      'runData',
    )
    // Normalize any legacy keys in case of fallback/misroute
    if (response && typeof response === 'object') {
      const r: any = response
      const run = r.run || {}
      r.backtest_id = r.backtest_id ?? r.run_id ?? r.id ?? run.run_id ?? run.id ?? backtest_id
      r.strategy_id = r.strategy_id ?? run.strategy_id ?? r.strategyId
      r.status = r.status ?? run.status
      r.symbol = r.symbol ?? run.symbol
      r.run_from = r.run_from ?? run.run_from
      r.run_to = r.run_to ?? run.run_to
      r.duration_ms = r.duration_ms ?? run.duration_ms ?? r.durationMs
      r.params = r.params ?? run.params
      r.dataset_id = r.dataset_id ?? run.dataset_id
      r.error_message = r.error_message ?? run.error_message
    }
    return BFFAggregatedBacktestResponseSchema.parse(response)
  }

  public async createBacktest(
    request: CreateBacktestRequest,
    idempotencyKey?: string,
  ): Promise<CreateBacktestResponse & { backtest_id?: string }> {
    return await apiPostWithFlags('/backtests', 'runData', request, { idempotencyKey })
  }

  public getPerformanceMetrics(): {
    bffEnabled: boolean
    lastLoadTime?: number
    aggregationBenefit?: number
  } {
    const config = featureFlagService.getConfiguration()
    return {
      bffEnabled: config.bffEnabled && config.runDataEnabled,
      lastLoadTime: undefined,
      aggregationBenefit: config.runDataEnabled ? 3 : 1,
    }
  }

  public isUsingAggregation(): boolean {
    return true
  }
}

export const backtestDataService = new BacktestDataService()
