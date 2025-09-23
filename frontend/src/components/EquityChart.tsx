import { useEffect, useMemo, useRef } from 'react'
import type { StreamFrame } from '../services/api'
import { createChart, type LineData } from 'lightweight-charts'

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
      const chart = createChart(containerRef.current, { height: 240, layout: { textColor: '#94a3b8', background: { color: '#fff' } } })
      const series = (chart as any).addLineSeries({ color: '#2563EB', lineWidth: 2 })
      chartRef.current = chart
      seriesRef.current = series
    }
    seriesRef.current?.setData(data)
    chartRef.current?.timeScale().fitContent()
  }, [data])

  useEffect(() => () => { chartRef.current?.remove(); chartRef.current = null; seriesRef.current = null }, [])

  return <div ref={containerRef} style={{ border: '1px solid #e2e8f0' }} />
}

export default EquityChart

