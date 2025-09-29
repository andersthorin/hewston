/**
 * Backtest Data Service - BFF-only backtest data fetching.
 *
 * Canonical backtests endpoints only. No legacy "runs" support.
 */

import { z } from 'zod'
import { apiGetWithFlags, apiPostWithFlags } from '../utils/api'
import { featureFlagService } from './featureFlags'
import type { CreateRunRequest, CreateRunResponse, ListRunsQuery } from './api'

// Complete backtest data in a single response (BFF aggregated)
export const BFFAggregatedBacktestResponseSchema = z.object({
  backtest_id: z.string(),
  dataset_id: z.string().optional().nullable(),
  strategy_id: z.string(),
  status: z.string(),
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
  metrics: z.object({
    total_return: z.number().optional(),
    sharpe_ratio: z.number().optional(),
    max_drawdown: z.number().optional(),
    win_rate: z.number().optional(),
    profit_factor: z.number().optional(),
    total_trades: z.number().optional(),
    avg_trade_duration: z.number().optional(),
  }).optional().nullable(),

  // Aggregated equity curve data
  equity: z.array(z.object({ ts: z.string(), value: z.number() })).optional().nullable(),

  // Aggregated orders data
  orders: z.array(z.object({
    ts: z.string(),
    side: z.enum(['buy', 'sell']),
    quantity: z.number(),
    price: z.number(),
    order_type: z.string().optional(),
    status: z.string().optional(),
  })).optional().nullable(),

  // BFF metadata
  meta: z.object({
    aggregated: z.boolean().default(true),
    cache_hit: z.boolean().optional().default(false),
    load_time_ms: z.number().optional(),
    source: z.enum(['bff']).default('bff'),
    components_loaded: z.array(z.string()).optional(),
  }).optional(),
})
export type BFFAggregatedBacktestResponse = z.infer<typeof BFFAggregatedBacktestResponseSchema>

// Backtest list with metadata (BFF-enhanced)
export const BFFBacktestListResponseSchema = z.object({
  items: z.array(z.object({
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
  })),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
  meta: z.object({
    cache_hit: z.boolean().optional().default(false),
    load_time_ms: z.number().optional(),
    source: z.enum(['bff']).optional().default('bff'),
  }).optional(),
})
export type BFFBacktestListResponse = z.infer<typeof BFFBacktestListResponseSchema>

export class BacktestDataService {
  public async listBacktests(query: ListRunsQuery = {}): Promise<BFFBacktestListResponse> {
    const params = new URLSearchParams()
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && v !== '') params.set(k, String(v))
    }
    const response = await apiGetWithFlags(`/backtests?${params.toString()}`, 'runData')
    // Normalize any legacy/nested shapes to ensure backtest_id is present before Zod parsing
    if (response && Array.isArray(response.items)) {
      response.items = response.items.map((it: any) => {
        const run = it && typeof it === 'object' ? (it.run || {}) : {}
        const normalized = {
          backtest_id: it?.backtest_id ?? it?.run_id ?? it?.id ?? run?.run_id ?? run?.id,
          created_at: it?.created_at ?? run?.created_at ?? it?.createdAt,
          strategy_id: it?.strategy_id ?? run?.strategy_id ?? it?.strategyId,
          status: it?.status ?? run?.status,
          symbol: it?.symbol ?? run?.symbol,
          run_from: it?.run_from ?? it?.from_date ?? run?.run_from ?? run?.from_date,
          run_to: it?.run_to ?? it?.to_date ?? run?.run_to ?? run?.to_date,
          duration_ms: it?.duration_ms ?? run?.duration_ms ?? it?.durationMs,
        }
        return { ...it, ...normalized }
      })
    }
    return BFFBacktestListResponseSchema.parse(response)
  }

  public async getCompleteBacktest(backtest_id: string): Promise<BFFAggregatedBacktestResponse> {
    const response = await apiGetWithFlags(`/backtests/${backtest_id}/complete`, 'runData')
    // Normalize any legacy keys in case of fallback/misroute
    if (response && typeof response === 'object') {
      const r: any = response
      const run = r.run || {}
      r.backtest_id = r.backtest_id ?? r.run_id ?? r.id ?? run.run_id ?? run.id ?? backtest_id
      r.strategy_id = r.strategy_id ?? run.strategy_id ?? r.strategyId
      r.status = r.status ?? run.status
      r.symbol = r.symbol ?? run.symbol
      r.run_from = r.run_from ?? r.from_date ?? run.run_from ?? run.from_date
      r.run_to = r.run_to ?? r.to_date ?? run.run_to ?? run.to_date
      r.duration_ms = r.duration_ms ?? run.duration_ms ?? r.durationMs
      r.params = r.params ?? run.params
      r.dataset_id = r.dataset_id ?? run.dataset_id
    }
    return BFFAggregatedBacktestResponseSchema.parse(response)
  }

  public async createBacktest(
    request: CreateRunRequest,
    idempotencyKey?: string
  ): Promise<CreateRunResponse & { backtest_id?: string }> {
    return await apiPostWithFlags('/backtests', 'runData', request, { idempotencyKey })
  }

  public getPerformanceMetrics(): { bffEnabled: boolean; lastLoadTime?: number; aggregationBenefit?: number } {
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
