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
  ts: z.string().optional(),
  ohlc: z
    .object({ o: z.number().optional(), h: z.number().optional(), l: z.number().optional(), c: z.number().optional(), v: z.number().optional() })
    .nullable()
    .optional(),
  orders: z.array(z.any()).nullable().optional(),
  equity: z.any().nullable().optional(),
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

