/**
 * Chart-related TypeScript interfaces and types.
 * 
 * This module provides proper type definitions for chart components
 * to replace any types and improve type safety.
 */

import type {
  ISeriesApi,
  CandlestickData,
  LineData,
  ChartOptions,
  DeepPartial,
  Time,
  TimeScaleOptions,
  PriceScaleOptions
} from 'lightweight-charts'

// Series API types are defined below as interfaces

// Chart instance interfaces
export interface ChartInstance {
  applyOptions: (options: DeepPartial<ChartOptions>) => void
  resize: (width: number, height: number) => void
  timeScale: () => TimeScaleApi
  remove?: () => void
  addSeries?: (seriesType: any, options?: any) => any
  addCandlestickSeries?: () => CandlestickSeriesApi
  addLineSeries?: (options?: any) => LineSeriesApi
}

export interface TimeScaleApi {
  scrollToRealTime: () => void
  setVisibleRange: (range: { from: Time; to: Time }) => void
  applyOptions: (options: DeepPartial<TimeScaleOptions>) => void
}

export interface CandlestickSeriesApi extends ISeriesApi<'Candlestick'> {
  setData: (data: CandlestickData[]) => void
  update: (data: CandlestickData) => void
}

export interface LineSeriesApi extends ISeriesApi<'Line'> {
  setData: (data: LineData[]) => void
  update: (data: LineData) => void
}

// Chart configuration interfaces
export interface ChartConfiguration {
  height: number
  layout: {
    textColor: string
    background: {
      type: 'solid' | 'gradient'
      color: string
    }
  }
  timeScale: DeepPartial<TimeScaleOptions>
  rightPriceScale?: DeepPartial<PriceScaleOptions>
}

// Chart API interfaces for imperative control
export interface CandlestickChartAPI {
  reset: (initial: CandlestickData[]) => void
  update: (dp: CandlestickData) => void
  scrollToLatest: () => void
  setVisibleRange: (from: Time, to: Time) => void
  setBarSpacing: (px: number) => void
}

export interface EquityChartAPI {
  reset: (initial: LineData[]) => void
  update: (dp: LineData) => void
  scrollToLatest: () => void
  setVisibleRange: (from: Time, to: Time) => void
}

// Chart props interfaces
export interface ChartOHLCProps {
  formatTime?: (t: Time, locale?: string) => string
}

export interface EquityChartProps {
  formatTime?: (t: Time, locale?: string) => string
}

// Mock interfaces for testing (using Vitest)
export interface MockChart {
  applyOptions: any
  resize: any
  timeScale: any
  addSeries?: any
  addCandlestickSeries?: any
  addLineSeries?: any
  remove?: any
}

export interface MockTimeScale {
  scrollToRealTime: any
  setVisibleRange: any
  applyOptions: any
  fitContent?: any
}

export interface MockSeries {
  setData: any
  update: any
}

// Chart creation function type
export type CreateChartFunction = (
  container: HTMLElement,
  options?: DeepPartial<ChartOptions>
) => ChartInstance
