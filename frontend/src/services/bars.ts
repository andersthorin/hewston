import { z } from 'zod'

export const DailyBarSchema = z.object({
  t: z.string(),
  o: z.number(),
  h: z.number(),
  l: z.number(),
  c: z.number(),
  v: z.number().optional().default(0),
  n: z.number().optional().default(0),
})
export type DailyBar = z.infer<typeof DailyBarSchema>

export const DailyResponseSchema = z.object({
  symbol: z.string(),
  bars: z.array(DailyBarSchema),
})
export type DailyResponse = z.infer<typeof DailyResponseSchema>

export async function fetchDaily(symbol: string, from?: string, to?: string): Promise<DailyResponse> {
  const params = new URLSearchParams({ symbol })
  if (from) params.set('from', from)
  if (to) params.set('to', to)
  const res = await fetch(`/bars/daily?${params.toString()}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const json = await res.json()
  return DailyResponseSchema.parse(json)
}

export const MinuteBarSchema = z.object({
  t: z.string(),
  o: z.number(),
  h: z.number(),
  l: z.number(),
  c: z.number(),
  v: z.number().optional().default(0),
})
export type MinuteBar = z.infer<typeof MinuteBarSchema>

export const MinuteResponseSchema = z.object({
  symbol: z.string(),
  bars: z.array(MinuteBarSchema),
  meta: z.object({ stride_minutes: z.number().optional(), points: z.number().optional() }).optional().nullable(),
})
export type MinuteResponse = z.infer<typeof MinuteResponseSchema>

export async function fetchMinute(symbol: string, from: string, to: string, rth_only: boolean = true): Promise<MinuteResponse> {
  const params = new URLSearchParams({ symbol, from, to })
  if (rth_only) params.set('rth_only', '1')
  const res = await fetch(`/bars/minute?${params.toString()}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const json = await res.json()
  return MinuteResponseSchema.parse(json)
}

export async function fetchMinuteDecimated(symbol: string, from: string, to: string, target = 10000, rth_only: boolean = true): Promise<MinuteResponse> {
  const params = new URLSearchParams({ symbol, from, to, target: String(target) })
  if (rth_only) params.set('rth_only', '1')
  const res = await fetch(`/bars/minute_decimated?${params.toString()}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const json = await res.json()
  return MinuteResponseSchema.parse(json)
}

export const HourBarSchema = z.object({
  t: z.string(),
  o: z.number(),
  h: z.number(),
  l: z.number(),
  c: z.number(),
  v: z.number(),
})
export type HourBar = z.infer<typeof HourBarSchema>

export const HourResponseSchema = z.object({
  symbol: z.string(),
  bars: z.array(HourBarSchema),
})
export type HourResponse = z.infer<typeof HourResponseSchema>

export async function fetchHour(symbol: string, from: string, to: string, rth_only: boolean = true): Promise<HourResponse> {
  const params = new URLSearchParams({ symbol, from, to })
  if (rth_only) params.set('rth_only', '1')
  const res = await fetch(`/bars/hour?${params.toString()}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const json = await res.json()
  return HourResponseSchema.parse(json)
}

