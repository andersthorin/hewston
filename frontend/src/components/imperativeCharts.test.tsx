// @vitest-environment happy-dom

import React, { createRef } from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, cleanup } from '@testing-library/react'

vi.mock('lightweight-charts', () => {
  const timeScale = { applyOptions: vi.fn(), fitContent: vi.fn() }
  const chart = {
    applyOptions: vi.fn(),
    timeScale: vi.fn(() => timeScale),
    addCandlestickSeries: vi.fn(() => ({ setData: vi.fn(), update: vi.fn() })),
    addLineSeries: vi.fn(() => ({ setData: vi.fn(), update: vi.fn() })),
    remove: vi.fn(),
  }
  return {
    createChart: vi.fn(() => chart),
    ColorType: { Solid: 'solid' },
    CandlestickSeries: {},
    LineSeries: {},
  }
})

import { createChart as createChartLWC } from 'lightweight-charts'
import ChartOHLC, { type CandlestickChartAPI } from './ChartOHLC'
import EquityChart, { type LineChartAPI } from './EquityChart'

const getChartMock = () => (createChartLWC as any).mock.results[0].value

describe('imperative charts API', () => {
  beforeEach(() => cleanup())

  it('ChartOHLC exposes reset/update and calls setData/update', () => {
    const ref = createRef<CandlestickChartAPI>()
    render(<ChartOHLC ref={ref} />)
    const chart = getChartMock()
    const series = chart.addCandlestickSeries.mock.results[0].value

    const initial = [{ time: 1 as any, open: 1, high: 2, low: 0.5, close: 1.5 }]
    ref.current!.reset(initial as any)
    expect(series.setData).toHaveBeenCalledWith(initial)

    const dp = { time: 2 as any, open: 2, high: 3, low: 1, close: 2.5 }
    ref.current!.update(dp as any)
    expect(series.update).toHaveBeenCalledWith(dp)
  })

  it('EquityChart exposes reset/update and calls setData/update', () => {
    const ref = createRef<LineChartAPI>()
    render(<EquityChart ref={ref} />)
    const chart = getChartMock()
    const series = chart.addLineSeries.mock.results[0].value

    const initial = [{ time: 1 as any, value: 10 }]
    ref.current!.reset(initial as any)
    expect(series.setData).toHaveBeenCalledWith(initial)

    const dp = { time: 2 as any, value: 12 }
    ref.current!.update(dp as any)
    expect(series.update).toHaveBeenCalledWith(dp)
  })
})

