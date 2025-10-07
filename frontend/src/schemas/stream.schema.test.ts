import { describe, it, expect } from 'vitest'
import { StreamFrameSchema } from './stream'

describe('StreamFrameSchema with metrics (E13)', () => {
  it('accepts frames with new metrics fields and equity object', () => {
    const frame = {
      t: 'frame',
      ts: '2024-01-01T00:00:00Z',
      ohlc: null,
      orders: [],
      equity: { ts: '2024-01-01T00:00:00Z', value: 100 },
      metrics: {
        return: null,
        realized_pnl: 5.0,
        total_return: 0.1,
        drawdown: 0.05,
        sharpe: 1.2,
        win_rate: 0.6,
      },
      dropped: 0,
    }
    const parsed = StreamFrameSchema.parse(frame)
    expect(parsed.metrics?.total_return).toBe(0.1)
    expect(parsed.metrics?.realized_pnl).toBe(5.0)
  })


  it('accepts frames with legacy metrics fields (back-compat)', () => {
    const frame = {
      t: 'frame', ts: '2024-01-01T00:00:00Z', ohlc: null, orders: [], equity: { ts: '2024-01-01T00:00:00Z', value: 100 },
      metrics: { total_return_so_far: 0.1, max_drawdown_so_far: 0.05, sharpe_so_far: 1.2 }, dropped: 0,
    }
    const parsed = StreamFrameSchema.parse(frame)
    expect(parsed.metrics?.total_return_so_far).toBe(0.1)
  })

  it('accepts frames without metrics (graceful)', () => {
    const frame = {
      t: 'frame', ts: '2024-01-01T00:00:00Z', ohlc: null, orders: [], equity: { ts: '2024-01-01T00:00:00Z', value: 100 }, dropped: 0,
    }
    const parsed = StreamFrameSchema.parse(frame)
    expect(parsed.metrics).toBeUndefined()
  })
})

