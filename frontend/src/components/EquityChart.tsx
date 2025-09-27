import { useEffect, forwardRef, useImperativeHandle } from 'react'
import type { LineData, Time } from 'lightweight-charts'
import type {
  EquityChartProps,
  EquityChartAPI,
  LineSeriesApi
} from '../types/charts'
import { useLineChart } from '../hooks/useChartInitialization'

export const EquityChart = forwardRef<EquityChartAPI, EquityChartProps>(function EquityChart({ formatTime }, ref) {
  const { chartRef, seriesRef, containerRef } = useLineChart({
    height: 300,
    fixedBarSpacing: 12,
    backgroundColor: '#fff',
    textColor: '#334155',
    timeVisible: true,
    secondsVisible: false
  })

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

  useEffect(() => {
    if (!chartRef.current || !seriesRef.current) return

    try {
      // Apply equity-specific styling to the line series
      const series = seriesRef.current as LineSeriesApi
      series.applyOptions({ color: '#2563EB', lineWidth: 2 })

      // Apply equity-specific chart options
      chartRef.current.applyOptions({
        localization: { timeFormatter: (t: Time) => fmtTimeLocal(t) },
        rightPriceScale: { mode: 1 } // PriceScaleMode.Logarithmic
      })
      chartRef.current.timeScale().applyOptions({ tickMarkFormatter: (t: Time) => fmtTimeLocal(t) })
    } catch (error) {
      console.warn('Failed to apply equity chart customizations:', error)
    }
  }, [formatTime])

  useImperativeHandle(ref, () => ({
    reset: (initial: LineData[]) => {
      try {
        const series = seriesRef.current as LineSeriesApi | null
        series?.setData(initial)
        chartRef.current?.timeScale().fitContent()
      } catch (error) {
        console.warn('Failed to reset equity chart data:', error)
      }
    },
    update: (dp: LineData) => {
      try {
        const series = seriesRef.current as LineSeriesApi | null
        series?.update(dp)
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

  // Cleanup is now handled by the useChartInitialization hook

  return <div ref={containerRef} className="w-full border border-slate-200 rounded" />
})

export default EquityChart

