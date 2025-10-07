import { z } from 'zod'

export const CtrlSchema = z.object({
  t: z.literal('ctrl'),
  cmd: z.enum(['play', 'pause', 'seek', 'speed']),
  ts: z.string().optional(),
  speed: z.number().optional(),
})
export type Ctrl = z.infer<typeof CtrlSchema>

export const EquitySchema = z.object({
  ts: z.string(),
  // Be lenient: some transports may serialize numbers as strings; coerce to number
  value: z.union([
    z.number(),
    z.string().transform((s) => Number(s)).refine((n) => Number.isFinite(n), { message: 'equity.value must be a number' })
  ]),
})

// Be permissive about orders so we don't drop entire frames due to a single malformed order
export const OrderSchema = z.object({
  // Accept either ts_utc or ts; both optional. Downstream uses ts_utc || ts || frame.ts
  ts_utc: z.string().nullable().optional(),
  ts: z.string().nullable().optional(),
  side: z.enum(['buy', 'sell']).nullable().optional(),
  quantity: z.number().nullable().optional(),
  price: z.number().nullable().optional(),
  order_id: z.string().nullable().optional(),
  symbol: z.string().nullable().optional(),
  status: z.enum(['pending', 'filled', 'cancelled', 'rejected']).nullable().optional(),
  fill_price: z.number().nullable().optional(),
  fill_quantity: z.number().nullable().optional(),
  commission: z.number().nullable().optional(),
}).passthrough() // Allow additional fields

export const StreamFrameSchema = z.object({
  t: z.literal('frame'),
  ts: z.string().optional(),
  ohlc: z
    .object({ o: z.number().optional(), h: z.number().optional(), l: z.number().optional(), c: z.number().optional(), v: z.number().optional() })
    .nullable()
    .optional(),
  // Performance: avoid deep validation of every order item; accept any objects and default to []
  orders: z.array(z.any()).optional().default([]),
  equity: EquitySchema.nullable().optional(),
  metrics: z
    .object({
      return: z.number().nullable().optional(),
      realized_pnl: z.number().nullable().optional(),
      total_return: z.number().nullable().optional(),
      drawdown: z.number().nullable().optional(),
      sharpe: z.number().nullable().optional(),
      win_rate: z.number().nullable().optional(),
      // Backward compatibility: accept old fields if present; ignored by UI mapping
      total_return_so_far: z.number().nullable().optional(),
      max_drawdown_so_far: z.number().nullable().optional(),
      sharpe_so_far: z.number().nullable().optional(),
    })
    .nullable()
    .optional(),
  total_frames: z.number().int().positive().nullable().optional(),
  dropped: z.number().int().nonnegative().optional(),
})
export type StreamFrameT = z.infer<typeof StreamFrameSchema>

