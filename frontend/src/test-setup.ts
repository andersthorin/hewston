import '@testing-library/jest-dom'
import { afterEach, beforeEach, vi } from 'vitest'

// Global lightweight-charts mock to provide a consistent, complete surface across tests
vi.mock('lightweight-charts', () => {
  const timeScale = {
    applyOptions: vi.fn(),
    fitContent: vi.fn(),
    setVisibleRange: vi.fn(),
    scrollToRealTime: vi.fn(),
  }
  const candlestickSeries = { setData: vi.fn(), update: vi.fn(), setMarkers: vi.fn?.() || vi.fn() }
  const lineSeries = { setData: vi.fn(), update: vi.fn() }

  // Placeholders to allow addSeries(CandlestickSeries/LineSeries) detection
  const CandlestickSeries = {}
  const LineSeries = {}

  const chart = {
    applyOptions: vi.fn(),
    timeScale: vi.fn(() => timeScale),
    addCandlestickSeries: vi.fn(() => candlestickSeries),
    addLineSeries: vi.fn(() => lineSeries),
    addSeries: vi.fn((SeriesCtor: unknown) =>
      SeriesCtor === CandlestickSeries ? candlestickSeries : lineSeries,
    ),
    resize: vi.fn(),
    remove: vi.fn(),
  }

  return {
    // Factory
    createChart: vi.fn(() => chart),

    // Enums/exports referenced by our hooks
    ColorType: { Solid: 'solid' },
    PriceScaleMode: { Normal: 'normal' },

    // Series type tokens used by addSeries
    CandlestickSeries,
    LineSeries,
  }
})

// Focused strictness: fail tests only on React act() warnings.
let __consoleErrors: string[] = []
let __consoleWarnings: string[] = []

const origError = console.error.bind(console)
const origWarn = console.warn.bind(console)

beforeEach(() => {
  __consoleErrors = []
  __consoleWarnings = []
  vi.spyOn(console, 'error').mockImplementation((...args: any[]) => {
    const msg = args.map(String).join(' ')
    __consoleErrors.push(msg)
    origError(...args)
  })
  vi.spyOn(console, 'warn').mockImplementation((...args: any[]) => {
    const msg = args.map(String).join(' ')
    __consoleWarnings.push(msg)
    origWarn(...args)
  })
})

afterEach(() => {
  const all = [...__consoleErrors, ...__consoleWarnings]
  vi.restoreAllMocks()
  const actIssues = all.filter((m) => m.toLowerCase().includes('not wrapped in act'))
  if (actIssues.length) {
    throw new Error(`React act() warning(s) occurred during test:\n${actIssues.join('\n')}`)
  }
})
