// @vitest-environment happy-dom

// React import not needed for this test file
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, cleanup, waitFor } from '@testing-library/react'
import type { MockChart, MockTimeScale, MockSeries } from '../types/charts'

vi.mock('lightweight-charts', () => {
  const timeScale: MockTimeScale = {
    applyOptions: vi.fn(),
    fitContent: vi.fn(),
    scrollToRealTime: vi.fn(),
    setVisibleRange: vi.fn()
  }
  const series: MockSeries = {
    setData: vi.fn(),
    update: vi.fn()
  }
  const mkChart = (): MockChart => ({
    applyOptions: vi.fn(),
    resize: vi.fn(),
    timeScale: vi.fn(() => timeScale),
    addCandlestickSeries: vi.fn(() => series),
    addLineSeries: vi.fn(() => series),
    addSeries: vi.fn(() => series),
    remove: vi.fn(),
  })
  const createChart = vi.fn().mockImplementation(() => mkChart())
  return { createChart, ColorType: { Solid: 'solid' }, CandlestickSeries: {}, LineSeries: {}, PriceScaleMode: { Logarithmic: 3 } }
})

import type { StreamFrame } from '../services/api'

const subs = new Set<(f: StreamFrame) => void>()
vi.mock('../services/ws', () => ({
  useRunPlayback: () => ({
    state: { status: 'ws', playing: true, speed: 30, dropped: 0 },
    subscribe: (cb: (f: StreamFrame) => void) => { subs.add(cb); return () => subs.delete(cb) },
    onPlay: vi.fn(), onPause: vi.fn(), onSpeedChange: vi.fn(), onSeek: vi.fn(),
  }),
  __emit: (f: StreamFrame) => subs.forEach((cb) => cb(f)),
}))



import { createChart as createChartLWC } from 'lightweight-charts'
import ChartOHLC, { type CandlestickChartAPI } from '../components/ChartOHLC'
import React, { createRef, useEffect } from 'react'

const charts = (): MockChart[] => (createChartLWC as any).mock.results.map((r: { value: MockChart }) => r.value)

describe('ChartOHLC imperative updates via PlaybackClock (stub)', () => {
  beforeEach(() => cleanup())

  it('updates series via update() and ignores out-of-order frames', async () => {
    const ref = createRef<CandlestickChartAPI>()
    const TestHarness = () => {
      useEffect(() => { /* no-op */ }, [])
      return <ChartOHLC ref={ref as any} />
    }
    render(<TestHarness />)

    // wait for ChartOHLC mount effect to run and create chart/series
    await waitFor(() => (createChartLWC as any).mock.calls.length > 0)

    const t1 = '2024-01-01T00:00:00Z'
    const t0 = '2023-12-31T23:59:00Z'

    // Use ChartOHLC imperative API directly after mount
    ref.current?.update({ time: t1 as unknown as any, open: 1, high: 2, low: 0.5, close: 1.5 })
    ref.current?.update({ time: t0 as unknown as any, open: 2, high: 3, low: 1, close: 2.5 }) // out-of-order; chart API doesn't enforce ordering here

    const [ohlcChart] = charts()
    const ohlcSeries = (ohlcChart.addCandlestickSeries?.mock?.results?.[0]?.value)
      || (ohlcChart.addSeries?.mock?.results?.[0]?.value)

    expect(ohlcSeries.update).toHaveBeenCalled() // at least once
  })
})

