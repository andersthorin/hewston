/**
 * BFF Run Data Service - Unified run data fetching with feature flag support.
 * 
 * This service provides a unified interface for fetching run data that can
 * route to either BFF aggregated endpoints or direct backend endpoints based
 * on feature flag configuration.
 */

import { z } from 'zod'
import { apiGetWithFlags, apiPostWithFlags } from '../utils/api'
import { featureFlagService } from './featureFlags'
import type {
  CreateRunRequest,
  CreateRunResponse,
  ListRunsQuery
} from './api'

/**
 * BFF Aggregated Run Response Schema - Complete run data in single response.
 */
export const BFFAggregatedRunResponseSchema = z.object({
  run_id: z.string(),
  dataset_id: z.string().optional().nullable(),
  strategy_id: z.string(),
  status: z.string(),
  code_hash: z.string().optional().nullable(),
  seed: z.number().optional().nullable(),
  speed: z.number().optional().nullable(),
  duration_ms: z.number().optional().nullable(),
  params: z.record(z.string(), z.any()).optional().nullable(),
  slippage_fees: z.record(z.string(), z.any()).optional().nullable(),
  
  // Run window (from manifest)
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
  equity: z.array(z.object({
    ts: z.string(),
    value: z.number(),
  })).optional().nullable(),
  
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
    source: z.enum(['bff', 'backend']).optional().default('bff'),
    components_loaded: z.array(z.string()).optional(), // ['run', 'metrics', 'equity', 'orders']
  }).optional(),
})

export type BFFAggregatedRunResponse = z.infer<typeof BFFAggregatedRunResponseSchema>

/**
 * BFF Run List Response Schema - Enhanced run list with metadata.
 */
export const BFFRunListResponseSchema = z.object({
  items: z.array(z.object({
    run_id: z.string(),
    created_at: z.string(),
    strategy_id: z.string(),
    status: z.string(),
    symbol: z.string().optional().nullable(),
    run_from: z.string().optional().nullable(),
    run_to: z.string().optional().nullable(),
    duration_ms: z.number().optional().nullable(),
    // Enhanced with summary metrics
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
    source: z.enum(['bff', 'backend']).optional().default('bff'),
  }).optional(),
})

export type BFFRunListResponse = z.infer<typeof BFFRunListResponseSchema>

/**
 * Unified run data service with BFF integration.
 */
export class RunDataService {
  /**
   * List runs with automatic BFF/backend routing based on feature flags.
   */
  public async listRuns(query: ListRunsQuery = {}): Promise<BFFRunListResponse> {
    // BFF-only routing
    return await this.listRunsFromBFF(query)
  }

  /**
   * Get complete run data with automatic BFF/backend routing.
   */
  public async getCompleteRunData(run_id: string): Promise<BFFAggregatedRunResponse> {
    // BFF-only routing
    return await this.getCompleteRunFromBFF(run_id)
  }

  /**
   * Create run with automatic BFF/backend routing.
   */
  public async createRun(
    request: CreateRunRequest,
    idempotencyKey?: string
  ): Promise<CreateRunResponse> {
    // BFF-only routing
    return await this.createRunViaBFF(request, idempotencyKey)
  }

  /**
   * List runs from BFF endpoint.
   */
  private async listRunsFromBFF(query: ListRunsQuery): Promise<BFFRunListResponse> {
    const params = new URLSearchParams()
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && v !== '') params.set(k, String(v))
    }

    const response = await apiGetWithFlags(
      `/runs?${params.toString()}`,
      'runData'
    )

    return BFFRunListResponseSchema.parse(response)
  }

  /**
   * Get complete run data from BFF aggregated endpoint.
   */
  private async getCompleteRunFromBFF(run_id: string): Promise<BFFAggregatedRunResponse> {
    const response = await apiGetWithFlags(
      `/runs/${run_id}/complete`,
      'runData'
    )

    return BFFAggregatedRunResponseSchema.parse(response)
  }

  /**
   * Create run via BFF endpoint.
   */
  private async createRunViaBFF(
    request: CreateRunRequest,
    idempotencyKey?: string
  ): Promise<CreateRunResponse> {
    return await apiPostWithFlags(
      '/runs',
      'runData',
      request,
      { idempotencyKey }
    )
  }



  /**
   * Get run data loading performance metrics.
   */
  public getPerformanceMetrics(): {
    bffEnabled: boolean
    lastLoadTime?: number
    aggregationBenefit?: number // Reduction in API calls
  } {
    const config = featureFlagService.getConfiguration()
    return {
      bffEnabled: config.bffEnabled && config.runDataEnabled,
      // TODO: Implement performance tracking
      lastLoadTime: undefined,
      aggregationBenefit: config.runDataEnabled ? 3 : 1, // BFF: 1 call vs Backend: 3+ calls
    }
  }

  /**
   * Check if run data is using BFF aggregation.
   */
  public isUsingAggregation(): boolean {
    return true
  }
}

// Export singleton instance
export const runDataService = new RunDataService()
