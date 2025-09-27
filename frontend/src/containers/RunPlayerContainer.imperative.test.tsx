// @vitest-environment happy-dom

import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, cleanup } from '@testing-library/react'

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
  return { createChart, ColorType: { Solid: 'solid' }, CandlestickSeries: {}, LineSeries: {} }
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
// @ts-expect-error - test helper exposed by mock
import { __emit } from '../services/ws'
import RunPlayerContainer from './RunPlayerContainer'

const charts = () => (createChartLWC as any).mock.results.map((r: any) => r.value)

describe('RunPlayerContainer imperative updates', () => {
  beforeEach(() => cleanup())

  it('updates series via update() and ignores out-of-order frames', async () => {
    render(<RunPlayerContainer run_id="test" />)

    const t1 = '2024-01-01T00:00:00Z'
    const t0 = '2023-12-31T23:59:00Z'

    __emit({ t: 'frame', ts: t1, dropped: 0, ohlc: { o: 1, h: 2, l: 0.5, c: 1.5 }, orders: [], equity: null })
    __emit({ t: 'frame', ts: t0, dropped: 0, ohlc: { o: 2, h: 3, l: 1, c: 2.5 }, orders: [], equity: null }) // out-of-order
    __emit({ t: 'frame', ts: t1, dropped: 0, ohlc: null, orders: [], equity: { ts: t1, value: 10 } })

    const [ohlcChart, equityChart] = charts()
    const ohlcSeries = ohlcChart.addCandlestickSeries.mock.results[0].value
    const equitySeries = equityChart.addLineSeries.mock.results[0].value

    expect(ohlcSeries.update).toHaveBeenCalledTimes(1)
    expect(equitySeries.update).toHaveBeenCalledTimes(1)
  })
})

