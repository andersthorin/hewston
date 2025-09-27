import { useEffect, useRef, forwardRef, useImperativeHandle } from 'react'
import { createChart as createChartLWC, ColorType, CandlestickSeries, PriceScaleMode } from 'lightweight-charts'
import type { CandlestickData, DeepPartial, ChartOptions, Time } from 'lightweight-charts'
import type {
  ChartOHLCProps,
  CandlestickChartAPI,
  ChartInstance,
  CandlestickSeriesApi
} from '../types/charts'

export const ChartOHLC = forwardRef<CandlestickChartAPI, ChartOHLCProps>(function ChartOHLC(_props, ref) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<ChartInstance | null>(null)
  const seriesRef = useRef<CandlestickSeriesApi | null>(null)

  const FIXED_BAR_SPACING = 10

  useEffect(() => {
    if (!containerRef.current) return

    // const fmtTimeLocal = (t: any, locale?: string) => {
    //   if (formatTime) return formatTime(t, locale)
    //   try {
    //     let d: Date
    //     if (typeof t === 'number') d = new Date(t * 1000)
    //     else if (typeof t === 'string') d = new Date(t)
    //     else if (t && typeof t === 'object' && 'year' in t && 'month' in t && 'day' in t) {
    //       d = new Date(Date.UTC((t as any).year, (t as any).month - 1, (t as any).day))
    //     } else return String(t)
    //     return new Intl.DateTimeFormat(locale || undefined, {
    //       month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
    //     }).format(d)
    //   } catch {
    //     return String(t)
    //   }
    // }

    if (!chartRef.current) {
      try {
        const chartConfig: DeepPartial<ChartOptions> = {
          height: 300,
          layout: {
            textColor: '#334155',
            background: { type: ColorType.Solid, color: '#fff' }
          },
          timeScale: {
            timeVisible: false,
            secondsVisible: false,
            barSpacing: FIXED_BAR_SPACING
          },
        }
        const chart = createChartLWC(containerRef.current!, chartConfig) as ChartInstance

        // Try different methods to add candlestick series for compatibility
        let series: CandlestickSeriesApi
        if ('addSeries' in chart) {
          series = chart.addSeries(CandlestickSeries) as CandlestickSeriesApi
        } else if ('addCandlestickSeries' in chart) {
          series = (chart as unknown as { addCandlestickSeries: () => CandlestickSeriesApi }).addCandlestickSeries()
        } else {
          throw new Error('lightweight-charts: no series add method found')
        }
        chartRef.current = chart
        seriesRef.current = series
        try {
          chart.applyOptions({
            rightPriceScale: { mode: PriceScaleMode.Normal },
            timeScale: { barSpacing: FIXED_BAR_SPACING }
          })
        } catch (error) {
          console.warn('Failed to apply chart options:', error)
        }

        const w = containerRef.current!.clientWidth
        try {
          chart.applyOptions({ width: w, timeScale: { barSpacing: FIXED_BAR_SPACING } })
        } catch (error) {
          console.warn('Failed to apply width options:', error)
        }
        try {
          chart.resize(w, 300)
        } catch (error) {
          console.warn('Failed to resize chart:', error)
        }

        const ro = new ResizeObserver(() => {
          const cw = containerRef.current?.clientWidth || w
          try {
            chart.applyOptions({ width: cw, timeScale: { barSpacing: FIXED_BAR_SPACING } })
          } catch (error) {
            console.warn('Failed to apply resize options:', error)
          }
          try {
            chart.resize(cw, 300)
          } catch (error) {
            console.warn('Failed to resize chart during observation:', error)
          }
        })
        ro.observe(containerRef.current)
        ;(chart as unknown as { __ro: ResizeObserver }).__ro = ro
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
        console.debug('[ChartOHLC] reset (no fitContent)', { points: initial.length })
      } catch (error) {
        console.warn('Failed to reset chart data:', error)
      }
    },
    update: (dp: CandlestickData) => {
      try {
        seriesRef.current?.update(dp)
      } catch (error) {
        console.warn('Failed to update chart data:', error)
      }
    },
    scrollToLatest: () => {
      try {
        chartRef.current?.timeScale().scrollToRealTime()
      } catch (error) {
        console.warn('Failed to scroll to latest:', error)
      }
    },
    setVisibleRange: (from: Time, to: Time) => {
      try {
        chartRef.current?.timeScale().setVisibleRange({ from, to })
      } catch (error) {
        console.warn('Failed to set visible range:', error)
      }
    },
    setBarSpacing: (px: number) => {
      try {
        chartRef.current?.applyOptions({ timeScale: { barSpacing: px } })
      } catch (error) {
        console.warn('Failed to set bar spacing:', error)
      }
    },
  }), [])

  useEffect(() => () => {
    try {
      (chartRef.current as unknown as { __ro?: ResizeObserver })?.__ro?.disconnect?.()
    } catch (error) {
      console.warn('Failed to disconnect resize observer:', error)
    }
    try {
      chartRef.current?.remove()
      chartRef.current = null
      seriesRef.current = null
    } catch (error) {
      console.warn('Failed to cleanup chart:', error)
    }
  }, [])

  return <div ref={containerRef} className="w-full border border-slate-200 rounded" />
})

export default ChartOHLC
