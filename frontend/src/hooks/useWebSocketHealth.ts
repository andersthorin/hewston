/**
 * WebSocket health monitoring hooks for BFF integration.
 * 
 * These hooks provide real-time monitoring of WebSocket connection health,
 * performance metrics, and connection management capabilities.
 */

import { useState, useEffect, useCallback } from 'react'
import { useRunPlayback } from '../services/ws'
import type { WebSocketHealth } from '../services/websocket'
import { featureFlagService } from '../services/featureFlags'

/**
 * WebSocket performance metrics.
 */
export interface WebSocketPerformanceMetrics {
  /** Current frames per second */
  currentFPS: number
  /** Average frames per second over last 10 seconds */
  averageFPS: number
  /** Total frames received */
  totalFrames: number
  /** Total dropped frames */
  droppedFrames: number
  /** Connection uptime in milliseconds */
  uptime: number
  /** Current latency in milliseconds */
  latency?: number
  /** Connection source (BFF or backend) */
  connectionSource: 'bff' | 'backend'
  /** Whether BFF features are enabled */
  bffFeaturesEnabled: boolean
}

/**
 * WebSocket connection status.
 */
export interface WebSocketConnectionStatus {
  /** Current connection state */
  state: 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'error' | 'closed'
  /** Whether connection is ready for sending messages */
  isReady: boolean
  /** Number of reconnection attempts */
  reconnectAttempts: number
  /** Last successful connection time */
  lastConnected?: number
  /** Connection health information */
  health?: WebSocketHealth
}

/**
 * Hook for monitoring WebSocket health and performance.
 */
export function useWebSocketHealth(runId: string) {
  const playback = useRunPlayback(runId)
  const [performanceMetrics, setPerformanceMetrics] = useState<WebSocketPerformanceMetrics>({
    currentFPS: 0,
    averageFPS: 0,
    totalFrames: 0,
    droppedFrames: 0,
    uptime: 0,
    connectionSource: featureFlagService.isFeatureFlagEnabled('websocket') ? 'bff' : 'backend',
    bffFeaturesEnabled: featureFlagService.isFeatureFlagEnabled('websocket'),
  })
  
  const [connectionStatus, setConnectionStatus] = useState<WebSocketConnectionStatus>({
    state: 'idle',
    isReady: false,
    reconnectAttempts: 0,
  })

  const [frameTimestamps, setFrameTimestamps] = useState<number[]>([])
  const [connectionStartTime, setConnectionStartTime] = useState<number | null>(null)

  // Track frame rate
  useEffect(() => {
    let frameCount = 0
    const startTime = Date.now()
    
    const unsubscribe = playback.subscribe((frame) => {
      frameCount++
      const now = Date.now()
      
      // Update frame timestamps for FPS calculation
      setFrameTimestamps(prev => {
        const newTimestamps = [...prev, now]
        // Keep only last 10 seconds of timestamps
        return newTimestamps.filter(ts => now - ts <= 10000)
      })
      
      // Update performance metrics
      setPerformanceMetrics(prev => ({
        ...prev,
        totalFrames: frameCount,
        droppedFrames: frame.dropped || 0,
        uptime: connectionStartTime ? now - connectionStartTime : 0,
      }))
    })

    return unsubscribe
  }, [playback, connectionStartTime])

  // Calculate FPS from frame timestamps
  useEffect(() => {
    const now = Date.now()
    const recentFrames = frameTimestamps.filter(ts => now - ts <= 1000) // Last 1 second
    const averageFrames = frameTimestamps.filter(ts => now - ts <= 10000) // Last 10 seconds
    
    setPerformanceMetrics(prev => ({
      ...prev,
      currentFPS: recentFrames.length,
      averageFPS: averageFrames.length / 10, // Average over 10 seconds
    }))
  }, [frameTimestamps])

  // Monitor connection status
  useEffect(() => {
    const health = playback.getConnectionHealth?.()
    
    setConnectionStatus(prev => ({
      ...prev,
      state: health?.state || 'idle',
      isReady: health?.state === 'connected',
      reconnectAttempts: health?.reconnectAttempts || 0,
      lastConnected: health?.lastConnected,
      health,
    }))

    // Track connection start time
    if (health?.state === 'connected' && !connectionStartTime) {
      setConnectionStartTime(Date.now())
    } else if (health?.state === 'closed' || health?.state === 'error') {
      setConnectionStartTime(null)
    }

    // Update performance metrics with health data
    if (health) {
      setPerformanceMetrics(prev => ({
        ...prev,
        latency: health.latency,
        connectionSource: health.connectionSource,
        droppedFrames: health.droppedFrames,
      }))
    }
  }, [playback.state, connectionStartTime, playback.getConnectionHealth])

  // Manual reconnection
  const reconnect = useCallback(async () => {
    try {
      await playback.reconnect?.()
      setConnectionStartTime(Date.now())
    } catch (error) {
      console.warn('Manual reconnection failed:', error)
    }
  }, [playback])

  // Ping for latency measurement
  const ping = useCallback(() => {
    playback.ping?.()
  }, [playback])

  // Get detailed health report
  const getHealthReport = useCallback(() => {
    const health = playback.getConnectionHealth?.()
    return {
      connection: connectionStatus,
      performance: performanceMetrics,
      health,
      bffEnabled: featureFlagService.isFeatureFlagEnabled('websocket'),
      timestamp: Date.now(),
    }
  }, [connectionStatus, performanceMetrics, playback])

  return {
    performanceMetrics,
    connectionStatus,
    reconnect,
    ping,
    getHealthReport,
    // Convenience flags
    isConnected: connectionStatus.isReady,
    isUsingBFF: performanceMetrics.connectionSource === 'bff',
    hasGoodPerformance: performanceMetrics.averageFPS >= 25, // Good if >= 25 FPS
    hasHighLatency: (performanceMetrics.latency || 0) > 100, // High if > 100ms
  }
}

/**
 * Hook for WebSocket performance monitoring with alerts.
 */
export function useWebSocketPerformanceMonitor(
  runId: string,
  options: {
    fpsThreshold?: number
    latencyThreshold?: number
    droppedFrameThreshold?: number
    onPerformanceAlert?: (alert: PerformanceAlert) => void
  } = {}
) {
  const {
    fpsThreshold = 25,
    latencyThreshold = 100,
    droppedFrameThreshold = 10,
    onPerformanceAlert
  } = options

  const { performanceMetrics, connectionStatus } = useWebSocketHealth(runId)
  const [alerts, setAlerts] = useState<PerformanceAlert[]>([])

  // Monitor performance and generate alerts
  useEffect(() => {
    const newAlerts: PerformanceAlert[] = []

    // FPS alert
    if (performanceMetrics.averageFPS < fpsThreshold && connectionStatus.isReady) {
      newAlerts.push({
        type: 'fps',
        severity: 'warning',
        message: `Low FPS: ${performanceMetrics.averageFPS.toFixed(1)} (threshold: ${fpsThreshold})`,
        value: performanceMetrics.averageFPS,
        threshold: fpsThreshold,
        timestamp: Date.now(),
      })
    }

    // Latency alert
    if (performanceMetrics.latency && performanceMetrics.latency > latencyThreshold) {
      newAlerts.push({
        type: 'latency',
        severity: performanceMetrics.latency > latencyThreshold * 2 ? 'error' : 'warning',
        message: `High latency: ${performanceMetrics.latency}ms (threshold: ${latencyThreshold}ms)`,
        value: performanceMetrics.latency,
        threshold: latencyThreshold,
        timestamp: Date.now(),
      })
    }

    // Dropped frames alert
    if (performanceMetrics.droppedFrames > droppedFrameThreshold) {
      newAlerts.push({
        type: 'droppedFrames',
        severity: 'warning',
        message: `Dropped frames: ${performanceMetrics.droppedFrames} (threshold: ${droppedFrameThreshold})`,
        value: performanceMetrics.droppedFrames,
        threshold: droppedFrameThreshold,
        timestamp: Date.now(),
      })
    }

    setAlerts(newAlerts)

    // Notify callback of new alerts
    if (onPerformanceAlert && newAlerts.length > 0) {
      newAlerts.forEach(onPerformanceAlert)
    }
  }, [
    performanceMetrics,
    connectionStatus.isReady,
    fpsThreshold,
    latencyThreshold,
    droppedFrameThreshold,
    onPerformanceAlert
  ])

  return {
    performanceMetrics,
    connectionStatus,
    alerts,
    hasAlerts: alerts.length > 0,
    criticalAlerts: alerts.filter(a => a.severity === 'error'),
    warningAlerts: alerts.filter(a => a.severity === 'warning'),
  }
}

/**
 * Performance alert interface.
 */
export interface PerformanceAlert {
  type: 'fps' | 'latency' | 'droppedFrames'
  severity: 'warning' | 'error'
  message: string
  value: number
  threshold: number
  timestamp: number
}

/**
 * Hook for WebSocket feature flag status.
 */
export function useWebSocketFeatureFlags() {
  const [flags, setFlags] = useState({
    bffEnabled: featureFlagService.isFeatureFlagEnabled('websocket'),
    masterEnabled: featureFlagService.getConfiguration().bffEnabled,
  })

  useEffect(() => {
    // Update flags when configuration changes
    const interval = setInterval(() => {
      setFlags({
        bffEnabled: featureFlagService.isFeatureFlagEnabled('websocket'),
        masterEnabled: featureFlagService.getConfiguration().bffEnabled,
      })
    }, 1000)

    return () => clearInterval(interval)
  }, [])

  return flags
}
