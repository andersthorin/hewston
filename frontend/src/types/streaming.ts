/**
 * Streaming data TypeScript interfaces and types.
 * 
 * This module provides proper type definitions for streaming data
 * to replace any types in StreamFrame and related interfaces.
 */

// OHLC data structure
export interface OHLCData {
  o?: number  // open
  h?: number  // high
  l?: number  // low
  c?: number  // close
  v?: number  // volume
}

// Equity data structure
export interface EquityData {
  ts: string    // timestamp in ISO format
  value: number // equity value
}

// Order data structure
export interface OrderData {
  ts_utc: string           // timestamp in UTC
  side?: 'buy' | 'sell'    // order side
  quantity?: number        // order quantity
  price?: number          // order price
  order_id?: string       // unique order identifier
  symbol?: string         // trading symbol
  status?: 'pending' | 'filled' | 'cancelled' | 'rejected'
  fill_price?: number     // actual fill price
  fill_quantity?: number  // actual fill quantity
  commission?: number     // commission paid
  [key: string]: unknown  // Allow additional fields for flexibility
}

// Stream frame structure
export interface StreamFrameData {
  t: 'frame'                    // frame type identifier
  ts: string                    // timestamp in ISO format
  ohlc?: OHLCData | null       // OHLC bar data
  orders: OrderData[]          // array of orders for this timestamp
  equity?: EquityData | null   // equity curve data point
  dropped: number              // number of dropped frames
}

// WebSocket message types
export type WebSocketMessage = 
  | StreamFrameData
  | HeartbeatMessage
  | ErrorMessage
  | EndMessage

export interface HeartbeatMessage {
  t: 'hb'  // heartbeat type
}

export interface ErrorMessage {
  t: 'err'
  error?: string | Error
  details?: unknown
}

export interface EndMessage {
  t: 'end'
}

// Transport configuration
export interface TransportConfig {
  url: string
  reconnectDelay?: number
  maxReconnectAttempts?: number
  heartbeatInterval?: number
}

// Streaming state
export interface StreamingState {
  isConnected: boolean
  isPlaying: boolean
  currentSpeed: number
  currentPosition?: string  // ISO timestamp
  totalFrames?: number
  processedFrames: number
  droppedFrames: number
  lastError?: string
}

// Stream control interface
export interface StreamController {
  start: () => void
  pause: () => void
  setSpeed: (speed: number) => void
  seek: (timestamp: string) => void
  onFrame: (callback: (frame: StreamFrameData) => void) => void
  onError: (callback: (error: Error) => void) => void
  onStateChange: (callback: (state: StreamingState) => void) => void
}

// Worker message types for stream parser
export type WorkerInMessage =
  | { type: 'init'; fps?: number }
  | { type: 'frame'; payload: unknown }
  | { type: 'hb' }
  | { type: 'end' }
  | { type: 'err'; error?: unknown }

export type WorkerOutMessage =
  | { type: 'frame'; data: StreamFrameData }
  | { type: 'error'; error: string }
  | { type: 'ready' }
