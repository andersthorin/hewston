import { forwardRef, useEffect, useImperativeHandle } from 'react'
import type { CandlestickData, Time } from 'lightweight-charts'
import type {
  ChartOHLCProps,
  CandlestickChartAPI,
  CandlestickSeriesApi
} from '../types/charts'
import { useCandlestickChart } from '../hooks/useChartInitialization'

export const ChartOHLC = forwardRef<CandlestickChartAPI, ChartOHLCProps>(function ChartOHLC(_props, ref) {
  const FIXED_BAR_SPACING = 14

  const { chartRef, seriesRef, containerRef } = useCandlestickChart({
    height: 300,
    fixedBarSpacing: FIXED_BAR_SPACING,
    backgroundColor: '#fff',
    textColor: '#334155',
    timeVisible: false,
    secondsVisible: false
  })
  // Apply time axis formatter if provided
  useEffect(() => {
    try {
      if (_props.formatTime && chartRef.current) {
        const fmt = _props.formatTime
        // Apply both chart-level localization and timeScale tick formatter for compatibility
        chartRef.current.applyOptions?.({ localization: { timeFormatter: (t: Time) => fmt(t) } })
        chartRef.current.timeScale()?.applyOptions?.({ tickMarkFormatter: (t: Time) => fmt(t) })
      }
    } catch (error) {
      console.warn('Failed to apply time formatter:', error)
    }
  }, [_props.formatTime, chartRef])


  useImperativeHandle(ref, () => ({
    reset: (initial: CandlestickData[]) => {
      try {
        // Only seed data; do NOT call fitContent here to avoid auto-zoom changing bar width
        const series = seriesRef.current as CandlestickSeriesApi | null
        series?.setData(initial)
        // Reduce noisy logging in dev to avoid jank
        // if ((import.meta as { env?: { DEV?: boolean } }).env?.DEV) console.debug('[ChartOHLC] reset', { points: initial.length })
      } catch (error) {
        console.warn('Failed to reset chart data:', error)
      }
    },
    update: (dp: CandlestickData) => {
      try {
        const series = seriesRef.current as CandlestickSeriesApi | null
        series?.update(dp)
        // Suppress per-frame logging; it can cause jank at ~7fps
      } catch (error) {
        console.warn('Failed to update chart data:', error)
      }
    },
    setMarkers: (markers: Array<{ time: Time; text?: string; position?: 'aboveBar'|'belowBar'|'inBar'; color?: string; shape?: string; }>) => {
      try {
        const series = seriesRef.current as CandlestickSeriesApi | null
        const s = series as unknown as { setMarkers?: (m: Array<{ time: Time; text?: string; position?: 'aboveBar'|'belowBar'|'inBar'; color?: string; shape?: string; }>) => void }
        s?.setMarkers?.(markers)
      } catch (error) {
        console.warn('Failed to set markers:', error)
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
        chartRef.current?.applyOptions({ timeScale: { barSpacing: px, minBarSpacing: px } })
      } catch (error) {
        console.warn('Failed to set bar spacing:', error)
      }
    },
  }), [chartRef, seriesRef])

  // Cleanup is now handled by the useChartInitialization hook

  return <div ref={containerRef} className="w-full border border-slate-200 rounded" />
})

export default ChartOHLC
export type { CandlestickChartAPI }
