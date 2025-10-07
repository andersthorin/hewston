/**
 * BFF WebSocket Service - Enhanced WebSocket connection management with BFF integration.
 *
 * This service provides WebSocket connections that can route to either BFF proxy
 * or direct backend based on feature flag configuration, with enhanced connection
 * management features like auto-reconnection and health monitoring.
 */

import { featureFlagService } from './featureFlags'
import { BFF_WS_URL, BACKEND_WS_URL } from '../constants'

/**
 * WebSocket connection state.
 */
export type WebSocketState =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'error'
  | 'closed'

/**
 * WebSocket connection health metrics.
 */
export interface WebSocketHealth {
  state: WebSocketState
  lastConnected?: number
  reconnectAttempts: number
  messagesReceived: number
  messagesSent: number
  latency?: number
  droppedFrames: number
  connectionSource: 'bff' | 'backend'
}

/**
 * WebSocket connection options.
 */
export interface WebSocketOptions {
  /** Enable automatic reconnection */
  autoReconnect?: boolean
  /** Maximum reconnection attempts */
  maxReconnectAttempts?: number
  /** Initial reconnection delay in ms */
  reconnectDelay?: number
  /** Maximum reconnection delay in ms */
  maxReconnectDelay?: number
  /** Enable message queuing during disconnections */
  enableMessageQueue?: boolean
  /** Maximum queued messages */
  maxQueueSize?: number
  /** Connection timeout in ms */
  connectionTimeout?: number
}

/**
 * Default WebSocket options.
 */
const DEFAULT_OPTIONS: Required<WebSocketOptions> = {
  autoReconnect: true,
  maxReconnectAttempts: 5,
  reconnectDelay: 1000,
  maxReconnectDelay: 30000,
  enableMessageQueue: true,
  maxQueueSize: 100,
  connectionTimeout: 10000,
}

/**
 * Enhanced WebSocket connection manager with BFF integration.
 */
export class BFFWebSocketManager {
  private ws: WebSocket | null = null
  private state: WebSocketState = 'idle'
  private health: WebSocketHealth
  private options: Required<WebSocketOptions>
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private connectionTimer: ReturnType<typeof setTimeout> | null = null
  private messageQueue: string[] = []
  private eventListeners: Map<string, Set<Function>> = new Map()
  private lastPingTime: number = 0
  private backtestId: string

  constructor(backtestId: string, options: WebSocketOptions = {}) {
    this.options = { ...DEFAULT_OPTIONS, ...options }
    this.backtestId = backtestId
    this.health = {
      state: 'idle',
      reconnectAttempts: 0,
      messagesReceived: 0,
      messagesSent: 0,
      droppedFrames: 0,
      connectionSource: this.getConnectionSource(),
    }

    this.setupEventListeners()
  }

  /**
   * Determine connection source based on feature flags.
   */
  private getConnectionSource(): 'bff' | 'backend' {
    return featureFlagService.isFeatureFlagEnabled('websocket') ? 'bff' : 'backend'
  }

  /**
   * Get the appropriate WebSocket URL based on feature flags.
   */
  private getWebSocketUrl(): string {
    const useBFF = featureFlagService.isFeatureFlagEnabled('websocket')
    const baseUrl = useBFF ? BFF_WS_URL : BACKEND_WS_URL

    if (useBFF) {
      // BFF WebSocket endpoint: ws://127.0.0.1:8001/api/v1/backtests/{id}/stream
      return `${baseUrl}/api/v1/backtests/${this.backtestId}/stream`
    } else {
      // Backend WebSocket endpoint: ws://127.0.0.1:8000/backtests/{id}/ws
      return `${baseUrl}/backtests/${this.backtestId}/ws`
    }
  }

  /**
   * Setup event listener management.
   */
  private setupEventListeners(): void {
    this.eventListeners.set('open', new Set())
    this.eventListeners.set('message', new Set())
    this.eventListeners.set('close', new Set())
    this.eventListeners.set('error', new Set())
    this.eventListeners.set('stateChange', new Set())
    this.eventListeners.set('healthUpdate', new Set())
  }

  /**
   * Add event listener.
   */
  public addEventListener(event: string, listener: Function): () => void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, new Set())
    }
    this.eventListeners.get(event)!.add(listener)

    return () => {
      this.eventListeners.get(event)?.delete(listener)
    }
  }

  /**
   * Emit event to all listeners.
   */
  private emit(event: string, ...args: any[]): void {
    this.eventListeners.get(event)?.forEach((listener) => {
      try {
        listener(...args)
      } catch (error) {
        console.warn(`WebSocket event listener error for ${event}:`, error)
      }
    })
  }

  /**
   * Update connection state and emit events.
   */
  private setState(newState: WebSocketState): void {
    if (this.state !== newState) {
      const oldState = this.state
      this.state = newState
      this.health.state = newState

      this.emit('stateChange', { oldState, newState, health: this.health })
      this.emit('healthUpdate', this.health)

      this.logStateChange(oldState, newState)
    }
  }

  /**
   * Log state changes for debugging.
   */
  private logStateChange(oldState: WebSocketState, newState: WebSocketState): void {
    if (import.meta.env.DEV || featureFlagService.getConfiguration().bffEnabled) {
      console.log(
        `🔌 WebSocket [${this.backtestId}] ${oldState} → ${newState} (${this.health.connectionSource})`,
      )
    }
  }

  /**
   * Connect to WebSocket with enhanced error handling.
   */
  public connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        resolve()
        return
      }

      this.setState('connecting')
      const url = this.getWebSocketUrl()
      this.health.connectionSource = this.getConnectionSource()

      try {
        this.ws = new WebSocket(url)

        // Connection timeout
        this.connectionTimer = setTimeout(() => {
          if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
            this.ws.close()
            this.setState('error')
            reject(new Error('WebSocket connection timeout'))
          }
        }, this.options.connectionTimeout)

        this.ws.onopen = () => {
          if (this.connectionTimer) {
            clearTimeout(this.connectionTimer)
            this.connectionTimer = null
          }

          this.setState('connected')
          this.health.lastConnected = Date.now()
          this.health.reconnectAttempts = 0

          // Process queued messages
          this.processMessageQueue()

          this.emit('open')
          resolve()
        }

        this.ws.onmessage = (event) => {
          this.health.messagesReceived++

          // Calculate latency if this is a pong response
          if (this.lastPingTime > 0) {
            this.health.latency = Date.now() - this.lastPingTime
            this.lastPingTime = 0
          }

          this.emit('message', event)
        }

        this.ws.onclose = (event) => {
          if (this.connectionTimer) {
            clearTimeout(this.connectionTimer)
            this.connectionTimer = null
          }

          this.setState('closed')
          this.emit('close', event)

          // Auto-reconnect if enabled and not manually closed
          if (this.options.autoReconnect && !event.wasClean) {
            this.scheduleReconnect()
          }
        }

        this.ws.onerror = (error) => {
          if (this.connectionTimer) {
            clearTimeout(this.connectionTimer)
            this.connectionTimer = null
          }

          this.setState('error')
          this.emit('error', error)
          reject(error)
        }
      } catch (error) {
        this.setState('error')
        reject(error)
      }
    })
  }

  /**
   * Schedule reconnection with exponential backoff.
   */
  private scheduleReconnect(): void {
    if (this.health.reconnectAttempts >= this.options.maxReconnectAttempts) {
      console.warn(`WebSocket max reconnection attempts reached for backtest ${this.backtestId}`)
      return
    }

    this.setState('reconnecting')
    this.health.reconnectAttempts++

    const delay = Math.min(
      this.options.reconnectDelay * Math.pow(2, this.health.reconnectAttempts - 1),
      this.options.maxReconnectDelay,
    )

    this.reconnectTimer = setTimeout(() => {
      this.connect().catch((error) => {
        console.warn(`WebSocket reconnection failed for backtest ${this.backtestId}:`, error)
        this.scheduleReconnect()
      })
    }, delay)
  }

  /**
   * Send message with queuing support.
   */
  public send(message: string): boolean {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(message)
        this.health.messagesSent++
        return true
      } catch (error) {
        console.warn('Failed to send WebSocket message:', error)
        this.queueMessage(message)
        return false
      }
    } else {
      this.queueMessage(message)
      return false
    }
  }

  /**
   * Queue message for later delivery.
   */
  private queueMessage(message: string): void {
    if (!this.options.enableMessageQueue) return

    if (this.messageQueue.length >= this.options.maxQueueSize) {
      this.messageQueue.shift() // Remove oldest message
    }

    this.messageQueue.push(message)
  }

  /**
   * Process queued messages after reconnection.
   */
  private processMessageQueue(): void {
    while (this.messageQueue.length > 0 && this.ws?.readyState === WebSocket.OPEN) {
      const message = this.messageQueue.shift()!
      try {
        this.ws.send(message)
        this.health.messagesSent++
      } catch (error) {
        console.warn('Failed to send queued message:', error)
        // Put message back at front of queue
        this.messageQueue.unshift(message)
        break
      }
    }
  }

  /**
   * Send ping to measure latency.
   */
  public ping(): void {
    this.lastPingTime = Date.now()
    this.send(JSON.stringify({ t: 'ping', ts: this.lastPingTime }))
  }

  /**
   * Close WebSocket connection.
   */
  public close(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    if (this.connectionTimer) {
      clearTimeout(this.connectionTimer)
      this.connectionTimer = null
    }

    if (this.ws) {
      this.ws.close(1000, 'Client closing')
      this.ws = null
    }

    this.setState('closed')
    this.messageQueue = []
  }

  /**
   * Get current connection health.
   */
  public getHealth(): WebSocketHealth {
    return { ...this.health }
  }

  /**
   * Get current connection state.
   */
  public getState(): WebSocketState {
    return this.state
  }

  /**
   * Check if connection is ready for sending messages.
   */
  public isReady(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  /**
   * Force reconnection.
   */
  public reconnect(): Promise<void> {
    this.close()
    return this.connect()
  }
}

/**
 * Create BFF-aware WebSocket manager instance.
 */
export function createWebSocketManager(
  runId: string,
  options?: WebSocketOptions,
): BFFWebSocketManager {
  return new BFFWebSocketManager(runId, options)
}
