import { useEffect, useMemo, useRef } from 'react'
import type { StreamFrame } from '../services/api'
import { createOptionsChart, createChart as createChartLWC, LineSeries, ColorType } from 'lightweight-charts'
import type { LineData } from 'lightweight-charts'

export type EquityChartProps = { frames: StreamFrame[] }

export function EquityChart({ frames }: EquityChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<any>(null)
  const seriesRef = useRef<any>(null)

  const data: LineData[] = useMemo(() => {
    return frames
      .filter((f) => f.equity)
      .map((f) => ({ time: (new Date(f.ts).getTime() / 1000) as any, value: f.equity!.value }))
  }, [frames])

  useEffect(() => {
    if (!containerRef.current) return
    if (!chartRef.current) {
      try {
        const chart = createOptionsChart
          ? createOptionsChart(containerRef.current, { height: 240, layout: { textColor: '#94a3b8', background: { type: ColorType.Solid, color: '#fff' } } })
          : createChartLWC(containerRef.current, { height: 240, layout: { textColor: '#94a3b8', background: { type: ColorType.Solid, color: '#fff' } } })
        try {
          console.log('EquityChart createChart result keys:', Object.keys(chart as any));
          console.log('LineSeries export:', LineSeries);
          console.log('LineSeries keys:', Object.keys((LineSeries as any) || {}));
          console.log('LineSeries typeof/type:', typeof (LineSeries as any), (LineSeries as any)?.type);
          console.log('LineSeries has _internal_createPaneView:', (LineSeries as any) && '_internal_createPaneView' in (LineSeries as any));
        } catch {}
        try { console.log('EquityChart addSeries typeof:', typeof (chart as any).addSeries) } catch {}
        const series = (chart as any).addSeries
          ? (chart as any).addSeries(LineSeries as any)
          : (chart as any).addLineSeries
          ? (chart as any).addLineSeries({ color: '#2563EB', lineWidth: 2 })
          : undefined
        if (!series) throw new Error('lightweight-charts add series API not available')
        chartRef.current = chart
        seriesRef.current = series
      } catch (err) {
        console.warn('EquityChart init failed:', err)
        return
      }
    }
    try {
      seriesRef.current?.setData(data)
      chartRef.current?.timeScale().fitContent()
    } catch (err) {
      console.warn('EquityChart update failed:', err)
    }
  }, [data])

  useEffect(() => () => { chartRef.current?.remove(); chartRef.current = null; seriesRef.current = null }, [])

  return <div ref={containerRef} style={{ border: '1px solid #e2e8f0' }} />
}

export default EquityChart

