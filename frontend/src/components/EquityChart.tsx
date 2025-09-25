import { useEffect, useRef, forwardRef, useImperativeHandle } from 'react'
import { createChart as createChartLWC, ColorType, LineSeries, PriceScaleMode } from 'lightweight-charts'
import type { LineData } from 'lightweight-charts'



export type EquityChartProps = {
  formatTime?: (t: any, locale?: string) => string
}

export type LineChartAPI = {
  reset: (initial: LineData[]) => void
  update: (dp: LineData) => void
}

export const EquityChart = forwardRef<LineChartAPI, EquityChartProps>(function EquityChart({ formatTime }, ref) {
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
          timeScale: { timeVisible: true, secondsVisible: false, barSpacing: 12 },
        }
        const chart = createChartLWC(containerRef.current, base as any)
        let series: any
        if ((chart as any).addSeries) {
          series = (chart as any).addSeries(LineSeries as any, { color: '#2563EB', lineWidth: 2 } as any)
        } else if ((chart as any).addLineSeries) {
          series = (chart as any).addLineSeries({ color: '#2563EB', lineWidth: 2 })
        } else {
          throw new Error('lightweight-charts: no series add method found')
        }
        chartRef.current = chart
        seriesRef.current = series
        try {
          chart.applyOptions({ localization: { timeFormatter: (t: any) => fmtTimeLocal(t) } } as any)
          chart.timeScale().applyOptions({ tickMarkFormatter: (t: any) => fmtTimeLocal(t) })
          chart.applyOptions({ rightPriceScale: { mode: PriceScaleMode.Logarithmic } } as any)
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
        console.warn('EquityChart init failed:', err)
        return
      }
    }
  }, [])

  useImperativeHandle(ref, () => ({
    reset: (initial: LineData[]) => {
      try {
        seriesRef.current?.setData(initial)
        chartRef.current?.timeScale().fitContent()
      } catch {}
    },
    update: (dp: LineData) => {
      try { seriesRef.current?.update(dp) } catch {}
    },
  }), [])

  useEffect(() => () => {
    try { (chartRef.current as any)?.__ro?.disconnect?.() } catch {}
    chartRef.current?.remove(); chartRef.current = null; seriesRef.current = null
  }, [])

  return <div ref={containerRef} className="w-full border border-slate-200 rounded" />
})

export default EquityChart

