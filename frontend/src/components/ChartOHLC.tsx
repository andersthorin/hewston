import { useEffect, useRef } from 'react'
import { createChart as createChartLWC, ColorType, CandlestickSeries } from 'lightweight-charts'
import type { CandlestickData } from 'lightweight-charts'

export type ChartOHLCProps = {
  data: CandlestickData[]
  formatTime?: (t: any, locale?: string) => string
}

export function ChartOHLC({ data, formatTime }: ChartOHLCProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<any>(null)
  const seriesRef = useRef<any>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const fmtTimeLocal = (t: any, locale?: string) => {
      if (formatTime) return formatTime(t, locale)
      try {
        let d: Date
        if (typeof t === 'number') d = new Date(t * 1000)
        else if (typeof t === 'string') d = new Date(t)
        else if (t && typeof t === 'object' && 'year' in t && 'month' in t && 'day' in t) {
          d = new Date(Date.UTC((t as any).year, (t as any).month - 1, (t as any).day))
        } else return String(t)
        return new Intl.DateTimeFormat(locale || undefined, {
          month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
        }).format(d)
      } catch {
        return String(t)
      }
    }

    if (!chartRef.current) {
      try {
        const base = {
          height: 300,
          layout: { textColor: '#334155', background: { type: ColorType.Solid, color: '#fff' } },
          timeScale: { timeVisible: true, secondsVisible: false },
        }
        const chart = createChartLWC(containerRef.current, base as any)
        let series: any
        if ((chart as any).addSeries) {
          series = (chart as any).addSeries(CandlestickSeries as any)
        } else if ((chart as any).addCandlestickSeries) {
          series = (chart as any).addCandlestickSeries()
        } else {
          throw new Error('lightweight-charts: no series add method found')
        }
        chartRef.current = chart
        seriesRef.current = series
        try {
          chart.applyOptions({ localization: { timeFormatter: (t: any) => fmtTimeLocal(t) } } as any)
          chart.timeScale().applyOptions({ tickMarkFormatter: (t: any) => fmtTimeLocal(t) })
        } catch {}

        // initial width
        const w = containerRef.current.clientWidth
        try { (chart as any).applyOptions?.({ width: w }) } catch {}
        try { (chart as any).resize?.(w, 300) } catch {}

        // observe resizes
        const ro = new ResizeObserver(() => {
          const cw = containerRef.current?.clientWidth || w
          try { (chart as any).applyOptions?.({ width: cw }) } catch {}
          try { (chart as any).resize?.(cw, 300) } catch {}
        })
        ro.observe(containerRef.current)
        ;(chart as any).__ro = ro
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

  useEffect(() => () => {
    try { (chartRef.current as any)?.__ro?.disconnect?.() } catch {}
    chartRef.current?.remove(); chartRef.current = null; seriesRef.current = null
  }, [])

  return <div ref={containerRef} className="w-full border border-slate-200 rounded" />
}

export default ChartOHLC

