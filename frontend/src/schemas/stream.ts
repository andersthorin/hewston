import { z } from 'zod'

export const CtrlSchema = z.object({
  t: z.literal('ctrl'),
  cmd: z.enum(['play', 'pause', 'seek', 'speed']),
  ts: z.string().optional(),
  speed: z.number().optional(),
})
export type Ctrl = z.infer<typeof CtrlSchema>

export const StreamFrameSchema = z.object({
  t: z.literal('frame'),
  ts: z.string(),
  ohlc: z
    .object({ o: z.number().optional(), h: z.number().optional(), l: z.number().optional(), c: z.number().optional(), v: z.number().optional() })
    .nullable()
    .optional(),
  orders: z.array(z.any()),
  equity: z.object({ ts: z.string(), value: z.number() }).nullable().optional(),
  dropped: z.number().int().nonnegative(),
})
export type StreamFrameT = z.infer<typeof StreamFrameSchema>

