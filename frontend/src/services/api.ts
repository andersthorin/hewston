import { z } from 'zod'
import { apiGet, apiPost } from '../utils/api'
import type { OrderData } from '../types/streaming'

export const RunSummarySchema = z.object({
  run_id: z.string(),
  created_at: z.string(),
  strategy_id: z.string(),
  status: z.string(),
  symbol: z.string().optional().nullable(),
  // Authoritative window from run manifest (must match RunDetail)
  run_from: z.string().optional().nullable(),
  run_to: z.string().optional().nullable(),
  duration_ms: z.number().optional().nullable(),
})
export type RunSummary = z.infer<typeof RunSummarySchema>

export const ListRunsResponseSchema = z.object({
  items: z.array(RunSummarySchema),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
})
export type ListRunsResponse = z.infer<typeof ListRunsResponseSchema>

export const RunDetailSchema = z.object({
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
  artifacts: z.object({
    metrics_path: z.string().optional().nullable(),
    equity_path: z.string().optional().nullable(),
    orders_path: z.string().optional().nullable(),
    fills_path: z.string().optional().nullable(),
    run_manifest_path: z.string().optional().nullable(),
  }).optional().nullable(),
  manifest: z.object({ path: z.string().optional().nullable() }).optional().nullable(),
  // Enriched by backend: window from run-manifest.json
  run_from: z.string().optional().nullable(),
  run_to: z.string().optional().nullable(),
})
export type RunDetail = z.infer<typeof RunDetailSchema>

export type ListRunsQuery = {
  symbol?: string
  strategy_id?: string
  from?: string
  to?: string
  limit?: number
  offset?: number
  order?: string
}

export async function listBacktests(query: ListRunsQuery = {}): Promise<ListRunsResponse> {
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null && v !== '') params.set(k, String(v))
  }
  const res = await fetch(`/backtests?${params.toString()}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const json = await res.json()
  return ListRunsResponseSchema.parse(json)
}

export type StreamFrame = {
  t: 'frame'
  ts: string
  ohlc?: { o?: number; h?: number; l?: number; c?: number; v?: number } | null
  orders: OrderData[]
  equity?: { ts: string; value: number } | null
  dropped: number
}

export async function getRunDetail(run_id: string): Promise<RunDetail> {
  const json = await apiGet(`/backtests/${run_id}`)
  return RunDetailSchema.parse(json)
}

// --- Create Backtest ---
export type CreateRunRequest = {
  strategy_id: string
  params?: Record<string, unknown>
  dataset_id?: string
  symbol?: string
  year?: number
  from?: string
  to?: string
  speed?: number
  seed?: number
}
export type CreateRunResponse = { run_id: string; status: string }

export async function createBacktest(
  req: CreateRunRequest,
  idempotencyKey?: string,
): Promise<CreateRunResponse> {
  return apiPost<CreateRunResponse>('/backtests', req, { idempotencyKey })
}
