import { useEffect, useRef, forwardRef, useImperativeHandle } from 'react'
import { createChart as createChartLWC, ColorType, LineSeries, PriceScaleMode } from 'lightweight-charts'
import type { LineData, DeepPartial, ChartOptions, Time } from 'lightweight-charts'
import type {
  EquityChartProps,
  EquityChartAPI,
  ChartInstance,
  LineSeriesApi
} from '../types/charts'

export const EquityChart = forwardRef<EquityChartAPI, EquityChartProps>(function EquityChart({ formatTime }, ref) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<ChartInstance | null>(null)
  const seriesRef = useRef<LineSeriesApi | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const fmtTimeLocal = (t: Time, locale?: string) => {
      if (formatTime) return formatTime(t, locale)
      try {
        let d: Date
        if (typeof t === 'number') d = new Date(t * 1000)
        else if (typeof t === 'string') d = new Date(t)
        else if (t && typeof t === 'object' && 'year' in t && 'month' in t && 'day' in t) {
          const timeObj = t as { year: number; month: number; day: number }
          d = new Date(Date.UTC(timeObj.year, timeObj.month - 1, timeObj.day))
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
        const chartConfig: DeepPartial<ChartOptions> = {
          height: 300,
          layout: {
            textColor: '#334155',
            background: { type: ColorType.Solid, color: '#fff' }
          },
          timeScale: {
            timeVisible: true,
            secondsVisible: false,
            barSpacing: 12
          },
        }
        const chart = createChartLWC(containerRef.current!, chartConfig) as ChartInstance

        // Try different methods to add line series for compatibility
        let series: LineSeriesApi
        if ('addSeries' in chart) {
          series = chart.addSeries(LineSeries, { color: '#2563EB', lineWidth: 2 }) as LineSeriesApi
        } else if ('addLineSeries' in chart) {
          series = (chart as unknown as { addLineSeries: (options: { color: string; lineWidth: number }) => LineSeriesApi }).addLineSeries({ color: '#2563EB', lineWidth: 2 })
        } else {
          throw new Error('lightweight-charts: no series add method found')
        }
        chartRef.current = chart
        seriesRef.current = series
        try {
          chart.applyOptions({
            localization: { timeFormatter: (t: Time) => fmtTimeLocal(t) },
            rightPriceScale: { mode: PriceScaleMode.Logarithmic }
          })
          chart.timeScale().applyOptions({ tickMarkFormatter: (t: Time) => fmtTimeLocal(t) })
        } catch (error) {
          console.warn('Failed to apply chart options:', error)
        }

        const w = containerRef.current!.clientWidth
        try {
          chart.applyOptions({ width: w })
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
            chart.applyOptions({ width: cw })
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
      } catch (error) {
        console.warn('Failed to reset equity chart data:', error)
      }
    },
    update: (dp: LineData) => {
      try {
        seriesRef.current?.update(dp)
      } catch (error) {
        console.warn('Failed to update equity chart data:', error)
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
  }, [formatTime])

  return <div ref={containerRef} className="w-full border border-slate-200 rounded" />
})

export default EquityChart

