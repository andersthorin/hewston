import { z } from 'zod'
import { apiGet, apiPost } from '../utils/api'
import type { OrderData } from '../types/streaming'

export const BacktestSummarySchema = z.object({
  backtest_id: z.string(),
  created_at: z.string(),
  strategy_id: z.string(),
  status: z.string(),
  symbol: z.string().optional().nullable(),
  // Authoritative window from backtest manifest (must match BacktestDetail)
  run_from: z.string().optional().nullable(),
  run_to: z.string().optional().nullable(),
  duration_ms: z.number().optional().nullable(),
})
export type BacktestSummary = z.infer<typeof BacktestSummarySchema>

export const BacktestListResponseSchema = z.object({
  items: z.array(BacktestSummarySchema),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
})
export type BacktestListResponse = z.infer<typeof BacktestListResponseSchema>

export const BacktestDetailSchema = z.object({
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
  artifacts: z.object({
    metrics_path: z.string().optional().nullable(),
    equity_path: z.string().optional().nullable(),
    orders_path: z.string().optional().nullable(),
    fills_path: z.string().optional().nullable(),
    run_manifest_path: z.string().optional().nullable(),
  }).optional().nullable(),
  manifest: z.object({ path: z.string().optional().nullable() }).optional().nullable(),
  // Enriched by backend: window from backtest-manifest.json
  run_from: z.string().optional().nullable(),
  run_to: z.string().optional().nullable(),
})
export type BacktestDetail = z.infer<typeof BacktestDetailSchema>

export type BacktestListQuery = {
  symbol?: string
  strategy_id?: string
  from?: string
  to?: string
  limit?: number
  offset?: number
  order?: string
}

export async function listBacktests(query: BacktestListQuery = {}): Promise<BacktestListResponse> {
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null && v !== '') params.set(k, String(v))
  }
  const res = await fetch(`/api/v1/backtests?${params.toString()}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const json = await res.json()
  return BacktestListResponseSchema.parse(json)
}

export type StreamFrame = {
  t: 'frame'
  ts: string
  ohlc?: { o?: number; h?: number; l?: number; c?: number; v?: number } | null
  orders: OrderData[]
  equity?: { ts: string; value: number } | null
  dropped: number
}

export async function getBacktestDetail(backtest_id: string): Promise<BacktestDetail> {
  const json = await apiGet(`/api/v1/backtests/${backtest_id}/complete`)
  return BacktestDetailSchema.parse(json)
}

// --- Create Backtest ---
export type CreateBacktestRequest = {
  strategy_id: string
  params?: Record<string, unknown>
  dataset_id?: string
  symbol?: string
  from?: string
  to?: string
  speed?: number
  seed?: number
}
export type CreateBacktestResponse = { backtest_id: string; status: string }

export async function createBacktest(
  req: CreateBacktestRequest,
  idempotencyKey?: string,
): Promise<CreateBacktestResponse> {
  return apiPost<CreateBacktestResponse>('/api/v1/backtests', req, { idempotencyKey })
}
