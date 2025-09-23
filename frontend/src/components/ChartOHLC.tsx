import { useEffect, useMemo, useRef } from 'react'
import type { StreamFrame } from '../services/api'
import { createOptionsChart, createChart as createChartLWC, CandlestickSeries, ColorType } from 'lightweight-charts'
import type { CandlestickData } from 'lightweight-charts'

export type ChartOHLCProps = { frames: StreamFrame[] }

export function ChartOHLC({ frames }: ChartOHLCProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<any>(null)
  const seriesRef = useRef<any>(null)

  const data: CandlestickData[] = useMemo(() => {
    return frames
      .filter((f) => f.ohlc)
      .map((f) => ({ time: (new Date(f.ts).getTime() / 1000) as any, open: f.ohlc!.o ?? 0, high: f.ohlc!.h ?? 0, low: f.ohlc!.l ?? 0, close: f.ohlc!.c ?? 0 }))
  }, [frames])

  useEffect(() => {
    if (!containerRef.current) return
    if (!chartRef.current) {
      try {
        const chart = createOptionsChart
          ? createOptionsChart(containerRef.current, { height: 240, layout: { textColor: '#94a3b8', background: { type: ColorType.Solid, color: '#fff' } } })
          : createChartLWC(containerRef.current, { height: 240, layout: { textColor: '#94a3b8', background: { type: ColorType.Solid, color: '#fff' } } })
        try { console.log('ChartOHLC createChart result keys:', Object.keys(chart as any)); } catch {}
        try { console.log('ChartOHLC addSeries typeof:', typeof (chart as any).addSeries) } catch {}
        const series = (chart as any).addSeries
          ? (chart as any).addSeries(CandlestickSeries as any)
          : (chart as any).addCandlestickSeries
          ? (chart as any).addCandlestickSeries()
          : undefined
        if (!series) throw new Error('lightweight-charts add series API not available')
        chartRef.current = chart
        seriesRef.current = series
      } catch (err) {
        console.warn('ChartOHLC init failed:', err)
        return
      }
    }
    try {
      seriesRef.current?.setData(data)
      chartRef.current?.timeScale().fitContent()
    } catch (err) {
      console.warn('ChartOHLC update failed:', err)
    }
  }, [data])

  useEffect(() => () => { chartRef.current?.remove(); chartRef.current = null; seriesRef.current = null }, [])

  return <div ref={containerRef} style={{ border: '1px solid #e2e8f0' }} />
}

export default ChartOHLC

