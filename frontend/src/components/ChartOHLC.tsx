import { forwardRef, useImperativeHandle } from 'react'
import type { CandlestickData, Time } from 'lightweight-charts'
import type {
  ChartOHLCProps,
  CandlestickChartAPI,
  CandlestickSeriesApi
} from '../types/charts'
import { useCandlestickChart } from '../hooks/useChartInitialization'

export const ChartOHLC = forwardRef<CandlestickChartAPI, ChartOHLCProps>(function ChartOHLC(_props, ref) {
  const FIXED_BAR_SPACING = 10

  const { chartRef, seriesRef, containerRef } = useCandlestickChart({
    height: 300,
    fixedBarSpacing: FIXED_BAR_SPACING,
    backgroundColor: '#fff',
    textColor: '#334155',
    timeVisible: false,
    secondsVisible: false
  })

  useImperativeHandle(ref, () => ({
    reset: (initial: CandlestickData[]) => {
      try {
        // Only seed data; do NOT call fitContent here to avoid auto-zoom changing bar width
        const series = seriesRef.current as CandlestickSeriesApi | null
        series?.setData(initial)
        console.debug('[ChartOHLC] reset (no fitContent)', { points: initial.length })
      } catch (error) {
        console.warn('Failed to reset chart data:', error)
      }
    },
    update: (dp: CandlestickData) => {
      try {
        const series = seriesRef.current as CandlestickSeriesApi | null
        series?.update(dp)
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

  // Cleanup is now handled by the useChartInitialization hook

  return <div ref={containerRef} className="w-full border border-slate-200 rounded" />
})

export default ChartOHLC
