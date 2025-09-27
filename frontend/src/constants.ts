/**
 * Frontend constants and configuration values.
 * 
 * This module centralizes hardcoded values, magic numbers, and configuration
 * to improve maintainability and consistency across the frontend.
 */

// API Configuration
export const API_BASE_URL = 'http://127.0.0.1:8000'
export const WS_BASE_URL = 'ws://127.0.0.1:8000'

// Chart Configuration
export const DEFAULT_CHART_HEIGHT = 400
export const CANDLESTICK_BAR_WIDTH = 14  // Fixed daily bar width (12-16px range)
export const CHART_MARGIN = { top: 10, right: 30, bottom: 30, left: 60 }

// Streaming Configuration
export const DEFAULT_FPS = 30
export const DEFAULT_SPEED = 60
export const HEARTBEAT_INTERVAL_MS = 5000
export const RECONNECT_DELAY_MS = 1000
export const MAX_RECONNECT_ATTEMPTS = 5

// Worker Configuration
export const STREAM_PARSER_TARGET_MS = 1000 / 30  // 30 FPS target
export const MIN_FRAME_INTERVAL_MS = 16  // ~60 FPS max

// Query Configuration
export const DEFAULT_STALE_TIME = 5 * 60 * 1000  // 5 minutes
export const DEFAULT_CACHE_TIME = 10 * 60 * 1000  // 10 minutes

// Pagination
export const DEFAULT_PAGE_SIZE = 20
export const MAX_PAGE_SIZE = 100

// Date/Time Configuration
export const DEFAULT_TIMEZONE = 'America/New_York'
export const DATE_FORMAT = 'YYYY-MM-DD'
export const DATETIME_FORMAT = 'YYYY-MM-DD HH:mm:ss'
export const ISO_FORMAT = 'YYYY-MM-DDTHH:mm:ss[Z]'

// UI Configuration
export const DEBOUNCE_DELAY_MS = 300
export const TOAST_DURATION_MS = 3000
export const LOADING_SPINNER_DELAY_MS = 200

// Chart Colors
export const CHART_COLORS = {
  BULLISH: '#22c55e',    // green-500
  BEARISH: '#ef4444',    // red-500
  NEUTRAL: '#6b7280',    // gray-500
  BACKGROUND: '#ffffff',
  GRID: '#f3f4f6',       // gray-100
  TEXT: '#374151',       // gray-700
} as const

// Baseline Values (from docs/prd/features/00-baselines.md)
export const BASELINE_SYMBOL = 'AAPL'
export const BASELINE_YEAR = 2023
export const BASELINE_FROM_DATE = '2023-01-01'
export const BASELINE_TO_DATE = '2023-12-31'
export const BASELINE_STRATEGY = 'sma_crossover'
export const BASELINE_FAST_PERIOD = 20
export const BASELINE_SLOW_PERIOD = 50

// Error Messages
export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network error occurred. Please try again.',
  WEBSOCKET_ERROR: 'WebSocket connection failed. Falling back to SSE.',
  INVALID_DATA: 'Invalid data received from server.',
  TIMEOUT: 'Request timed out. Please try again.',
  UNKNOWN: 'An unknown error occurred.',
} as const

// Route Paths
export const ROUTES = {
  HOME: '/',
  RUNS: '/runs',
  RUN_DETAIL: '/runs/:id',
  SETTINGS: '/settings',
} as const
