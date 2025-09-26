import { useEffect, useRef, forwardRef, useImperativeHandle } from 'react'
import { createChart as createChartLWC, ColorType, CandlestickSeries, PriceScaleMode } from 'lightweight-charts'
import type { CandlestickData } from 'lightweight-charts'

export type ChartOHLCProps = {
  formatTime?: (t: any, locale?: string) => string
}

export type CandlestickChartAPI = {
  reset: (initial: CandlestickData[]) => void
  update: (dp: CandlestickData) => void
  scrollToLatest: () => void
  setVisibleRange: (from: any, to: any) => void
  setBarSpacing: (px: number) => void
}

export const ChartOHLC = forwardRef<CandlestickChartAPI, ChartOHLCProps>(function ChartOHLC({ formatTime }, ref) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<any>(null)
  const seriesRef = useRef<any>(null)

  const FIXED_BAR_SPACING = 10

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
          timeScale: { timeVisible: false, secondsVisible: false, barSpacing: FIXED_BAR_SPACING },
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
          chart.applyOptions({ rightPriceScale: { mode: PriceScaleMode.Normal }, timeScale: { barSpacing: FIXED_BAR_SPACING } } as any)
        } catch {}

        const w = containerRef.current.clientWidth
        try { (chart as any).applyOptions?.({ width: w, timeScale: { barSpacing: FIXED_BAR_SPACING } }) } catch {}
        try { (chart as any).resize?.(w, 300) } catch {}

        const ro = new ResizeObserver(() => {
          const cw = containerRef.current?.clientWidth || w
          try { (chart as any).applyOptions?.({ width: cw, timeScale: { barSpacing: FIXED_BAR_SPACING } }) } catch {}
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
        // Only seed data; do NOT call fitContent here to avoid auto-zoom changing bar width
        seriesRef.current?.setData(initial)
        try { console.debug('[ChartOHLC] reset (no fitContent)', { points: initial.length }) } catch {}
      } catch {}
    },
    update: (dp: CandlestickData) => {
      try { seriesRef.current?.update(dp) } catch {}
    },
    scrollToLatest: () => {
      try { chartRef.current?.timeScale().scrollToRealTime() } catch {}
    },
    setVisibleRange: (from: any, to: any) => {
      try { chartRef.current?.timeScale().setVisibleRange({ from, to }) } catch {}
    },
    setBarSpacing: (px: number) => {
      try { chartRef.current?.applyOptions({ timeScale: { barSpacing: px } }) } catch {}
    },
  }), [])

  useEffect(() => () => {
    try { (chartRef.current as any)?.__ro?.disconnect?.() } catch {}
    chartRef.current?.remove(); chartRef.current = null; seriesRef.current = null
  }, [])

  return <div ref={containerRef} className="w-full border border-slate-200 rounded" />
})

export default ChartOHLC
