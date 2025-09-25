import { useEffect, useRef, forwardRef, useImperativeHandle } from 'react'
import { createChart as createChartLWC, ColorType, CandlestickSeries, PriceScaleMode } from 'lightweight-charts'
import type { CandlestickData } from 'lightweight-charts'



export type ChartOHLCProps = {
  formatTime?: (t: any, locale?: string) => string
}

export type CandlestickChartAPI = {
  reset: (initial: CandlestickData[]) => void
  update: (dp: CandlestickData) => void
}

export const ChartOHLC = forwardRef<CandlestickChartAPI, ChartOHLCProps>(function ChartOHLC({ formatTime }, ref) {
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
          timeScale: { timeVisible: false, secondsVisible: false, barSpacing: 12 },
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
          // Use default time formatting for dates; no custom time/tick formatters
          chart.applyOptions({ rightPriceScale: { mode: PriceScaleMode.Normal } } as any)
        } catch {}

        const w = containerRef.current.clientWidth
        try { (chart as any).applyOptions?.({ width: w }) } catch {}
        try { (chart as any).resize?.(w, 300) } catch {}

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
  }, [])

  useImperativeHandle(ref, () => ({
    reset: (initial: CandlestickData[]) => {
      try {
        seriesRef.current?.setData(initial)
        chartRef.current?.timeScale().fitContent()
      } catch {}
    },
    update: (dp: CandlestickData) => {
      try { seriesRef.current?.update(dp) } catch {}
    },
  }), [])

  useEffect(() => () => {
    try { (chartRef.current as any)?.__ro?.disconnect?.() } catch {}
    chartRef.current?.remove(); chartRef.current = null; seriesRef.current = null
  }, [])

  return <div ref={containerRef} className="w-full border border-slate-200 rounded" />
})

export default ChartOHLC

