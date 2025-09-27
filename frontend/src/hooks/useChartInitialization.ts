import { useEffect, useRef } from 'react'
import { createChart as createChartLWC, ColorType, CandlestickSeries, LineSeries, PriceScaleMode } from 'lightweight-charts'
import type { DeepPartial, ChartOptions } from 'lightweight-charts'
import type { ChartInstance, CandlestickSeriesApi, LineSeriesApi } from '../types/charts'

export interface ChartConfig {
  height?: number
  fixedBarSpacing?: number
  backgroundColor?: string
  textColor?: string
  timeVisible?: boolean
  secondsVisible?: boolean
}

export interface UseChartInitializationResult {
  chartRef: React.MutableRefObject<ChartInstance | null>
  seriesRef: React.MutableRefObject<CandlestickSeriesApi | LineSeriesApi | null>
  containerRef: React.MutableRefObject<HTMLDivElement | null>
}

/**
 * Custom hook for initializing lightweight-charts with consistent configuration
 * and error handling. Handles chart creation, series setup, and resize observer.
 */
export function useChartInitialization(
  config: ChartConfig = {},
  seriesType: 'candlestick' | 'line' = 'candlestick'
): UseChartInitializationResult {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<ChartInstance | null>(null)
  const seriesRef = useRef<CandlestickSeriesApi | LineSeriesApi | null>(null)

  const {
    height = 300,
    fixedBarSpacing = 10,
    backgroundColor = '#fff',
    textColor = '#334155',
    timeVisible = false,
    secondsVisible = false
  } = config

  useEffect(() => {
    if (!containerRef.current || chartRef.current) return

    try {
      const chartConfig: DeepPartial<ChartOptions> = {
        height,
        layout: {
          textColor,
          background: { type: ColorType.Solid, color: backgroundColor }
        },
        timeScale: {
          timeVisible,
          secondsVisible,
          barSpacing: fixedBarSpacing
        },
      }

      const chart = createChartLWC(containerRef.current, chartConfig) as ChartInstance

      // Create appropriate series based on type
      let series: CandlestickSeriesApi | LineSeriesApi
      if (seriesType === 'candlestick') {
        // Try different methods for candlestick series compatibility
        if ('addSeries' in chart) {
          series = chart.addSeries(CandlestickSeries) as CandlestickSeriesApi
        } else if ('addCandlestickSeries' in chart) {
          series = (chart as unknown as { addCandlestickSeries: () => CandlestickSeriesApi }).addCandlestickSeries()
        } else {
          throw new Error('lightweight-charts: no candlestick series add method found')
        }
      } else {
        // Line series
        if ('addSeries' in chart) {
          series = chart.addSeries(LineSeries, { color: '#2563EB', lineWidth: 2 }) as LineSeriesApi
        } else if ('addLineSeries' in chart) {
          series = (chart as unknown as { addLineSeries: (options: { color: string; lineWidth: number }) => LineSeriesApi }).addLineSeries({ color: '#2563EB', lineWidth: 2 })
        } else {
          throw new Error('lightweight-charts: no line series add method found')
        }
      }

      chartRef.current = chart
      seriesRef.current = series

      // Apply additional chart options
      try {
        chart.applyOptions({
          rightPriceScale: { mode: PriceScaleMode.Normal },
          timeScale: { barSpacing: fixedBarSpacing }
        })
      } catch (error) {
        console.warn('Failed to apply chart options:', error)
      }

      // Set initial size
      const width = containerRef.current.clientWidth
      try {
        chart.applyOptions({ width, timeScale: { barSpacing: fixedBarSpacing } })
        chart.resize(width, height)
      } catch (error) {
        console.warn('Failed to set initial chart size:', error)
      }

      // Set up resize observer
      const resizeObserver = new ResizeObserver(() => {
        const currentWidth = containerRef.current?.clientWidth || width
        try {
          chart.applyOptions({ width: currentWidth, timeScale: { barSpacing: fixedBarSpacing } })
          chart.resize(currentWidth, height)
        } catch (error) {
          console.warn('Failed to resize chart:', error)
        }
      })

      resizeObserver.observe(containerRef.current)
      
      // Store resize observer for cleanup
      ;(chart as unknown as { __ro: ResizeObserver }).__ro = resizeObserver

    } catch (error) {
      console.warn(`Chart initialization failed (${seriesType}):`, error)
    }

    // Cleanup function
    return () => {
      if (chartRef.current) {
        try {
          const ro = (chartRef.current as unknown as { __ro?: ResizeObserver }).__ro
          if (ro) {
            ro.disconnect()
          }
          chartRef.current.remove?.()
        } catch (error) {
          console.warn('Chart cleanup failed:', error)
        }
        chartRef.current = null
        seriesRef.current = null
      }
    }
  }, [height, fixedBarSpacing, backgroundColor, textColor, timeVisible, secondsVisible, seriesType])

  return {
    chartRef,
    seriesRef,
    containerRef
  }
}

/**
 * Specialized hook for candlestick charts with OHLC-specific defaults
 */
export function useCandlestickChart(config: ChartConfig = {}): UseChartInitializationResult {
  return useChartInitialization(config, 'candlestick')
}

/**
 * Specialized hook for line charts with equity-specific defaults
 */
export function useLineChart(config: ChartConfig = {}): UseChartInitializationResult {
  return useChartInitialization(config, 'line')
}
