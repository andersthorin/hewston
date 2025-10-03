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
  value: z.number(),
})

export const OrderSchema = z.object({
  ts_utc: z.string(),
  side: z.enum(['buy', 'sell']).optional(),
  quantity: z.number().optional(),
  price: z.number().optional(),
  order_id: z.string().optional(),
  symbol: z.string().optional(),
  status: z.enum(['pending', 'filled', 'cancelled', 'rejected']).optional(),
  fill_price: z.number().optional(),
  fill_quantity: z.number().optional(),
  commission: z.number().optional(),
}).passthrough() // Allow additional fields

export const StreamFrameSchema = z.object({
  t: z.literal('frame'),
  ts: z.string().optional(),
  ohlc: z
    .object({ o: z.number().optional(), h: z.number().optional(), l: z.number().optional(), c: z.number().optional(), v: z.number().optional() })
    .nullable()
    .optional(),
  orders: z.array(OrderSchema).optional().default([]),
  equity: EquitySchema.nullable().optional(),
  metrics: z
    .object({
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

