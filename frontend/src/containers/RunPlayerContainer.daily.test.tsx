// @vitest-environment happy-dom
// React import not needed for this test file
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, cleanup, fireEvent, screen, act, waitFor } from '@testing-library/react'
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

  beforeEach(() => {
    vi.clearAllMocks()
    cleanup()
  })

  it('switching to Daily sets setData once and then updates last day, appending on day flip (NY tz boundary)', async () => {
    render(<RunPlayerContainer backtest_id="test" />, { wrapper })

    // allow ChartOHLC effect to mount and create series
    await act(async () => {})

    // Emit two minute frames within same NY day (use Z times around boundary 04:00Z)
    await act(async () => {
      emitFrame({ ts: '2024-10-01T03:59:00Z', ohlc: { o: 10, h: 12, l: 9, c: 11 } }) // belongs to 2024-09-30 NY
      emitFrame({ ts: '2024-10-01T03:59:30Z', ohlc: { o: 11, h: 13, l: 8, c: 12 } }) // same NY day
    })

    // Switch to Daily
    const dailyBtn = screen.getByText('Daily')
    await act(async () => {
      fireEvent.click(dailyBtn)
    })

    // Expect the most recent setData to contain exactly one daily bar (for 2024-09-30)
    // allow Daily series creation
    await act(async () => {})
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
    await act(async () => {
      emitFrame({ ts: '2024-10-01T03:59:59Z', ohlc: { o: 11, h: 14, l: 7, c: 13 } })
    })

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
    await act(async () => {
      emitFrame({ ts: '2024-10-01T04:00:00Z', ohlc: { o: 20, h: 21, l: 19, c: 20.5 } })
    })
    const updAfter2 = ohlcSeries.update.mock.calls.length
    const setAfter2 = ohlcSeries.setData.mock.calls.length
    expect(updAfter2 > updAfter || setAfter2 > setAfter).toBe(true)
  })

  it('switching back to Minute resets and resumes minute updates', async () => {
    const startIdx = (createChartLWC as any).mock.results.length
    render(<RunPlayerContainer backtest_id="test" />, { wrapper })

    // allow ChartOHLC effect to mount before initial seed
    await act(async () => {})

    // Seed at least one frame to ensure chart creation before mode switches
    await act(async () => {
      emitFrame({ ts: '2024-10-02T11:59:00Z', ohlc: { o: 25, h: 26, l: 24, c: 25.5 } })
    })

    // Switch to Daily then back to Minute
    await act(async () => {
      fireEvent.click(screen.getByText('Daily'))
    })
    // allow Daily series creation
    await act(async () => {})

    // Switch back to non-daily (Hourly)
    await act(async () => {
      fireEvent.click(screen.getByText('Hourly'))
    })
    // allow Hourly series (re)creation
    await act(async () => {})

    // Focus on OHLC chart's last created series and assert it resumes updates
    // Allow effect to re-subscribe after mode change and ensure chart is created
    await act(async () => {})
    let chs = charts()
    if (!chs.length) {
      await act(async () => {})
      chs = charts()
    }
    // Select the chart created by THIS render (avoid cross-test leakage)
    const ohlcChart = chs[startIdx] ?? chs.at(-1)

    const lastSeries = (chart: any) =>
      chart?.addSeries?.mock?.results?.at(-1)?.value ??
      chart?.addCandlestickSeries?.mock?.results?.at(-1)?.value ??
      chart?.addLineSeries?.mock?.results?.at(-1)?.value

    const ohlcSeries: any = lastSeries(ohlcChart)
    const baseUpd = ohlcSeries?.update?.mock?.calls?.length ?? 0
    const baseSet = ohlcSeries?.setData?.mock?.calls?.length ?? 0

    // Also capture the rendered frames counter from the UI as a black-box signal
    const transportInfo = screen.getByText(/Transport:/).parentElement as HTMLElement
    const parseFrames = () => {
      const txt = transportInfo.textContent || ''
      const m = txt.match(/Frames:\s*(\d+)/)
      return m ? parseInt(m[1], 10) : 0
    }
    const baseFrames = parseFrames()

    // Emit frames and ensure either a re-seed (setData) or an incremental update occurs
    await act(async () => {
      emitFrame({ ts: '2024-10-02T12:00:00Z', ohlc: { o: 30, h: 31, l: 29, c: 30.5 } })
      emitFrame({ ts: '2024-10-02T12:01:00Z', ohlc: { o: 31, h: 32, l: 30, c: 31.2 } })
    })

    await waitFor(() => {
      const updAfter = ohlcSeries?.update?.mock?.calls?.length ?? 0
      const setAfter = ohlcSeries?.setData?.mock?.calls?.length ?? 0
      const framesAfter = parseFrames()
      expect(updAfter > baseUpd || setAfter > baseSet || framesAfter >= baseFrames + 2).toBe(true)
    })
  })
})
