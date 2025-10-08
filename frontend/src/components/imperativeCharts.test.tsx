// @vitest-environment happy-dom

import { createRef } from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, cleanup, waitFor } from '@testing-library/react'

// Use the global lightweight-charts mock from test-setup.ts
import { createChart as createChartLWC } from 'lightweight-charts'
import ChartOHLC, { type CandlestickChartAPI } from './ChartOHLC'
import type { MockChart } from '../types/charts'
import type { CandlestickData } from 'lightweight-charts'

const getChartMock = (): MockChart => (createChartLWC as any).mock.results[0].value

describe('imperative charts API', () => {
  beforeEach(() => cleanup())

  it('ChartOHLC exposes reset/update and calls setData/update', async () => {
    const ref = createRef<CandlestickChartAPI>()
    render(<ChartOHLC ref={ref} />)
    const chart = getChartMock()
    await waitFor(() => {
      const addSeriesCalls = (chart.addSeries as any)?.mock?.calls?.length || 0
      const addCandleCalls = (chart.addCandlestickSeries as any)?.mock?.calls?.length || 0
      expect(addSeriesCalls + addCandleCalls).toBeGreaterThan(0)
    })
    const series =
      (chart.addSeries as any)?.mock?.results?.[0]?.value ??
      (chart.addCandlestickSeries as any)?.mock?.results?.[0]?.value

    const initial: CandlestickData[] = [
      { time: 1 as CandlestickData['time'], open: 1, high: 2, low: 0.5, close: 1.5 },
    ]
    ref.current!.reset(initial)
    expect(series.setData).toHaveBeenCalledWith(initial)

    const dp: CandlestickData = {
      time: 2 as CandlestickData['time'],
      open: 2,
      high: 3,
      low: 1,
      close: 2.5,
    }
    ref.current!.update(dp)
    expect(series.update).toHaveBeenCalledWith(dp)
  })
})
