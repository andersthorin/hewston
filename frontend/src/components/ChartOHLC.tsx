import { useEffect, useMemo, useRef } from 'react'
import type { StreamFrame } from '../services/api'
import { createChart, type CandlestickData } from 'lightweight-charts'

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
      const chart = createChart(containerRef.current, { height: 240, layout: { textColor: '#94a3b8', background: { color: '#fff' } } })
      const series = (chart as any).addCandlestickSeries()
      chartRef.current = chart
      seriesRef.current = series
    }
    seriesRef.current?.setData(data)
    chartRef.current?.timeScale().fitContent()
  }, [data])

  useEffect(() => () => { chartRef.current?.remove(); chartRef.current = null; seriesRef.current = null }, [])

  return <div ref={containerRef} style={{ border: '1px solid #e2e8f0' }} />
}

export default ChartOHLC

