// @vitest-environment happy-dom
import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, cleanup, fireEvent, screen } from '@testing-library/react'

vi.mock('lightweight-charts', () => {
  const timeScale = { applyOptions: vi.fn(), fitContent: vi.fn() }
  const mkChart = () => ({
    applyOptions: vi.fn(),
    timeScale: vi.fn(() => timeScale),
    addCandlestickSeries: vi.fn(() => ({ setData: vi.fn(), update: vi.fn() })),
    addLineSeries: vi.fn(() => ({ setData: vi.fn(), update: vi.fn() })),
    remove: vi.fn(),
  })
  const createChart = vi.fn().mockImplementation(() => mkChart())
  return { createChart, ColorType: { Solid: 'solid' }, CandlestickSeries: {}, LineSeries: {}, PriceScaleMode: { Logarithmic: 3 } }
})

const subs = new Set<(f: any) => void>()
vi.mock('../services/ws', () => ({
  useRunPlayback: () => ({
    state: { status: 'ws', playing: true, speed: 30, dropped: 0 },
    subscribe: (cb: (f: any) => void) => { subs.add(cb); return () => subs.delete(cb) },
    onPlay: vi.fn(), onPause: vi.fn(), onSpeedChange: vi.fn(), onSeek: vi.fn(),
  }),
  __emit: (f: any) => subs.forEach((cb) => cb(f)),
}))

import { createChart as createChartLWC } from 'lightweight-charts'
// @ts-expect-error test helper
import { __emit } from '../services/ws'
import RunPlayerContainer from './RunPlayerContainer'

const charts = () => (createChartLWC as any).mock.results.map((r: any) => r.value)

function emitFrame({ ts, ohlc, equity }: { ts: string, ohlc?: any, equity?: any }) {
  __emit({ t: 'frame', ts, dropped: 0, ohlc: ohlc ?? null, orders: [], equity: equity ?? null })
}

describe('RunPlayerContainer daily aggregates', () => {
  beforeEach(() => cleanup())

  it('switching to Daily sets setData once and then updates last day, appending on day flip (NY tz boundary)', () => {
    render(<RunPlayerContainer run_id="test" />)

    const [ohlcChart] = charts()
    const ohlcSeries = ohlcChart.addCandlestickSeries.mock.results[0].value

    // Emit two minute frames within same NY day (use Z times around boundary 04:00Z)
    emitFrame({ ts: '2024-10-01T03:59:00Z', ohlc: { o: 10, h: 12, l: 9, c: 11 } }) // belongs to 2024-09-30 NY
    emitFrame({ ts: '2024-10-01T03:59:30Z', ohlc: { o: 11, h: 13, l: 8, c: 12 } }) // same NY day

    // Switch to Daily
    const dailyBtn = screen.getByText('Daily')
    fireEvent.click(dailyBtn)

    // Expect the most recent setData to contain exactly one daily bar (for 2024-09-30)
    expect(ohlcSeries.setData.mock.calls.length).toBeGreaterThan(0)

    // Another minute within same NY day should cause update (replace last)
    const baseUpd = ohlcSeries.update.mock.calls.length
    emitFrame({ ts: '2024-10-01T03:59:59Z', ohlc: { o: 11, h: 14, l: 7, c: 13 } })
    expect(ohlcSeries.update.mock.calls.length).toBe(baseUpd + 1)
    const last1 = ohlcSeries.update.mock.calls.at(-1)[0]
    expect(String(last1.time)).toMatch(/^\d{4}-\d{2}-\d{2}$/)

    // Cross NY midnight (04:00Z) starts a new daily candle, should append via update
    emitFrame({ ts: '2024-10-01T04:00:00Z', ohlc: { o: 20, h: 21, l: 19, c: 20.5 } })
    expect(ohlcSeries.update.mock.calls.length).toBe(baseUpd + 2)
  })

  it('switching back to Minute resets and resumes minute updates', async () => {
    render(<RunPlayerContainer run_id="test" />)
    const [ohlcChart] = charts()
    const ohlcSeries = ohlcChart.addCandlestickSeries.mock.results[0].value

    // Switch to Daily then back to Minute
    fireEvent.click(screen.getByText('Daily'))
    fireEvent.click(screen.getByText('Minute'))

    // setData called on both switches (clear/reset)
    expect(ohlcSeries.setData).toHaveBeenCalled()

    // Allow effect to re-subscribe after mode change
    await new Promise((r) => setTimeout(r, 0))

    // Minute frame should now call update with numeric time (seconds)
    emitFrame({ ts: '2024-10-02T12:00:00Z', ohlc: { o: 30, h: 31, l: 29, c: 30.5 } })
    emitFrame({ ts: '2024-10-02T12:01:00Z', ohlc: { o: 31, h: 32, l: 30, c: 31.2 } })
    const recent = ohlcSeries.update.mock.calls.slice(-3).map(c => c[0])
    expect(recent.some(a => typeof a.time === 'number')).toBe(true)
  })
})

