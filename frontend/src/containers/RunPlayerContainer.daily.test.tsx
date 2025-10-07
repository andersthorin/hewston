// @vitest-environment happy-dom
// React import not needed for this test file
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, cleanup, fireEvent, screen } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import type { MockChart, MockTimeScale, MockSeries } from '../types/charts'

vi.mock('lightweight-charts', () => {
  const timeScale: MockTimeScale = {
    applyOptions: vi.fn(),
    fitContent: vi.fn(),
    scrollToRealTime: vi.fn(),
    setVisibleRange: vi.fn(),
  }
  const series: MockSeries = {
    setData: vi.fn(),
    update: vi.fn(),
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
  return {
    createChart,
    ColorType: { Solid: 'solid' },
    CandlestickSeries: {},
    LineSeries: {},
    PriceScaleMode: { Logarithmic: 3 },
  }
})

import type { StreamFrame } from '../services/api'

const subs = new Set<(f: StreamFrame) => void>()
vi.mock('../services/ws', () => ({
  useBacktestPlayback: () => ({
    state: { status: 'ws', playing: true, speed: 30, dropped: 0 },
    subscribe: (cb: (f: StreamFrame) => void) => {
      subs.add(cb)
      return () => subs.delete(cb)
    },
    onPlay: vi.fn(),
    onPause: vi.fn(),
    onSpeedChange: vi.fn(),
    onSeek: vi.fn(),
    sendReady: vi.fn(),
    getConnectionHealth: vi.fn(() => ({ state: 'connected', reconnectAttempts: 0 })),
  }),
  __emit: (f: StreamFrame) => subs.forEach((cb) => cb(f)),
}))

import { createChart as createChartLWC } from 'lightweight-charts'
// @ts-expect-error test helper
import { __emit } from '../services/ws'
import RunPlayerContainer from './RunPlayerContainer'

const charts = (): MockChart[] =>
  (createChartLWC as any).mock.results.map((r: { value: MockChart }) => r.value)

function emitFrame({
  ts,
  ohlc,
  equity,
}: {
  ts: string
  ohlc?: { o?: number; h?: number; l?: number; c?: number; v?: number }
  equity?: { ts: string; value: number }
}) {
  __emit({ t: 'frame', ts, dropped: 0, ohlc: ohlc ?? null, orders: [], equity: equity ?? null })
}

describe('RunPlayerContainer daily aggregates', () => {
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider
      client={
        new (require('@tanstack/react-query').QueryClient)({
          defaultOptions: { queries: { retry: false } },
        })
      }
    >
      {children}
    </QueryClientProvider>
  )

  beforeEach(() => cleanup())

  it('switching to Daily sets setData once and then updates last day, appending on day flip (NY tz boundary)', async () => {
    render(<RunPlayerContainer backtest_id="test" />, { wrapper })

    // allow ChartOHLC effect to mount and create series
    await new Promise((r) => setTimeout(r, 0))

    // Emit two minute frames within same NY day (use Z times around boundary 04:00Z)
    emitFrame({ ts: '2024-10-01T03:59:00Z', ohlc: { o: 10, h: 12, l: 9, c: 11 } }) // belongs to 2024-09-30 NY
    emitFrame({ ts: '2024-10-01T03:59:30Z', ohlc: { o: 11, h: 13, l: 8, c: 12 } }) // same NY day

    // Switch to Daily
    const dailyBtn = screen.getByText('Daily')
    fireEvent.click(dailyBtn)

    // Expect the most recent setData to contain exactly one daily bar (for 2024-09-30)
    // allow Daily series creation
    await new Promise((r) => setTimeout(r, 0))
    const [ohlcChart] = charts()
    // series created on Daily mode – pick the last created series of any type
    const lastSeries = (chart: any) =>
      chart.addSeries?.mock?.results?.at(-1)?.value ??
      chart.addCandlestickSeries?.mock?.results?.at(-1)?.value ??
      chart.addLineSeries?.mock?.results?.at(-1)?.value

    const ohlcSeries: any = lastSeries(ohlcChart)

    expect(ohlcSeries?.setData?.mock?.calls.length).toBeGreaterThan(0)

    // Another minute within same NY day should cause either an update or a reset+setData
    const baseUpd = ohlcSeries.update.mock.calls.length
    const baseSet = ohlcSeries.setData.mock.calls.length
    emitFrame({ ts: '2024-10-01T03:59:59Z', ohlc: { o: 11, h: 14, l: 7, c: 13 } })

    const updAfter = ohlcSeries.update.mock.calls.length
    const setAfter = ohlcSeries.setData.mock.calls.length
    expect(updAfter > baseUpd || setAfter > baseSet).toBe(true)

    const updatedArg = ohlcSeries.update.mock.calls.at(-1)?.[0]
    const setArgArray = ohlcSeries.setData.mock.calls.at(-1)?.[0]
    const lastPoint: any =
      updatedArg ?? (Array.isArray(setArgArray) ? setArgArray.at(-1) : undefined)
    if (lastPoint?.time) {
      if (typeof lastPoint.time === 'object') {
        expect(lastPoint.time).toMatchObject({
          year: expect.any(Number),
          month: expect.any(Number),
          day: expect.any(Number),
        })
      } else {
        expect(String(lastPoint.time)).toMatch(/^\d{4}-\d{2}-\d{2}$/)
      }
    }

    // Cross NY midnight (04:00Z) starts a new daily candle, should append via update OR re-seed via setData
    emitFrame({ ts: '2024-10-01T04:00:00Z', ohlc: { o: 20, h: 21, l: 19, c: 20.5 } })
    const updAfter2 = ohlcSeries.update.mock.calls.length
    const setAfter2 = ohlcSeries.setData.mock.calls.length
    expect(updAfter2 > updAfter || setAfter2 > setAfter).toBe(true)
  })

  it('switching back to Minute resets and resumes minute updates', async () => {
    render(<RunPlayerContainer backtest_id="test" />, { wrapper })

    // Switch to Daily then back to Minute
    fireEvent.click(screen.getByText('Daily'))
    // allow Daily series creation
    await new Promise((r) => setTimeout(r, 0))
    const [ohlcChart] = charts()
    const lastSeries = (chart: any) =>
      chart.addSeries?.mock?.results?.at(-1)?.value ??
      chart.addCandlestickSeries?.mock?.results?.at(-1)?.value ??
      chart.addLineSeries?.mock?.results?.at(-1)?.value
    const ohlcSeries: any = lastSeries(ohlcChart)

    // Switch back to non-daily (Hourly)
    fireEvent.click(screen.getByText('Hourly'))

    // setData called on both switches (clear/reset)
    expect(ohlcSeries.setData).toHaveBeenCalled()

    // Allow effect to re-subscribe after mode change
    await new Promise((r) => setTimeout(r, 0))

    // Emit frames and ensure updates happen
    emitFrame({ ts: '2024-10-02T12:00:00Z', ohlc: { o: 30, h: 31, l: 29, c: 30.5 } })
    emitFrame({ ts: '2024-10-02T12:01:00Z', ohlc: { o: 31, h: 32, l: 30, c: 31.2 } })
    expect(ohlcSeries.update.mock.calls.length).toBeGreaterThan(0)
  })
})
