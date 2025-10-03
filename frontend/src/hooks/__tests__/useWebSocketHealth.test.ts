/**
 * Tests for WebSocket health monitoring hooks.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useWebSocketHealth, useWebSocketPerformanceMonitor } from '../useWebSocketHealth'

// Import the mocked services to access them in tests
import { featureFlagService } from '../../services/featureFlags'

// Mock the WebSocket playback service
const mockPlayback = {
  state: { status: 'idle', playing: false, speed: 60, dropped: 0 },
  subscribe: vi.fn(),
  getConnectionHealth: vi.fn(),
  reconnect: vi.fn(),
  ping: vi.fn(),
}

vi.mock('../../services/ws', () => ({
  useBacktestPlayback: () => mockPlayback
}))

// Mock feature flag service
vi.mock('../../services/featureFlags', () => ({
  featureFlagService: {
    isFeatureFlagEnabled: vi.fn(),
    getConfiguration: vi.fn(),
  }
}))

describe('useWebSocketHealth', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(featureFlagService.isFeatureFlagEnabled).mockReturnValue(false)
    vi.mocked(featureFlagService.getConfiguration).mockReturnValue({
      bffEnabled: false,
      websocketEnabled: false,
    })
    
    mockPlayback.getConnectionHealth.mockReturnValue({
      state: 'connected',
      reconnectAttempts: 0,
      messagesReceived: 100,
      messagesSent: 50,
      latency: 25,
      droppedFrames: 2,
      connectionSource: 'backend',
      lastConnected: Date.now() - 10000,
    })
  })

  it('should initialize with default performance metrics', () => {
    const { result } = renderHook(() => useWebSocketHealth('test-run-123'))

    expect(result.current.performanceMetrics).toEqual({
      currentFPS: 0,
      averageFPS: 0,
      totalFrames: 0,
      droppedFrames: 2,
      uptime: 0,
      connectionSource: 'backend',
      bffFeaturesEnabled: false,
      latency: 25,
    })
  })

  it('should track frame rate from subscription', () => {
    let subscriptionCallback: any
    mockPlayback.subscribe.mockImplementation((cb) => {
      subscriptionCallback = cb
      return () => {} // unsubscribe function
    })

    const { result } = renderHook(() => useWebSocketHealth('test-run-123'))
    
    // Simulate receiving frames
    act(() => {
      subscriptionCallback({ dropped: 1 })
      subscriptionCallback({ dropped: 1 })
      subscriptionCallback({ dropped: 2 })
    })
    
    expect(result.current.performanceMetrics.totalFrames).toBe(3)
    expect(result.current.performanceMetrics.droppedFrames).toBe(2)
  })

  it('should update connection status from health data', () => {
    const { result } = renderHook(() => useWebSocketHealth('test-run-123'))
    
    expect(result.current.connectionStatus.state).toBe('connected')
    expect(result.current.connectionStatus.isReady).toBe(true)
    expect(result.current.connectionStatus.reconnectAttempts).toBe(0)
  })

  it('should provide reconnect functionality', async () => {
    mockPlayback.reconnect.mockResolvedValue(undefined)
    
    const { result } = renderHook(() => useWebSocketHealth('test-run-123'))
    
    await act(async () => {
      await result.current.reconnect()
    })
    
    expect(mockPlayback.reconnect).toHaveBeenCalled()
  })

  it('should provide ping functionality', () => {
    const { result } = renderHook(() => useWebSocketHealth('test-run-123'))
    
    act(() => {
      result.current.ping()
    })
    
    expect(mockPlayback.ping).toHaveBeenCalled()
  })

  it('should detect BFF usage', () => {
    vi.mocked(featureFlagService.isFeatureFlagEnabled).mockReturnValue(true)
    mockPlayback.getConnectionHealth.mockReturnValue({
      ...mockPlayback.getConnectionHealth(),
      connectionSource: 'bff',
    })
    
    const { result } = renderHook(() => useWebSocketHealth('test-run-123'))
    
    expect(result.current.isUsingBFF).toBe(true)
    expect(result.current.performanceMetrics.connectionSource).toBe('bff')
  })

  it('should calculate performance flags correctly', () => {
    // Mock good performance
    const { result: goodResult } = renderHook(() => useWebSocketHealth('test-run-123'))
    
    // Simulate good FPS
    act(() => {
      const subscriptionCallback = mockPlayback.subscribe.mock.calls[0][0]
      for (let i = 0; i < 30; i++) {
        subscriptionCallback({ dropped: 0 })
      }
    })

    expect(goodResult.current.hasGoodPerformance).toBe(false)

    // Mock high latency
    mockPlayback.getConnectionHealth.mockReturnValue({
      ...mockPlayback.getConnectionHealth(),
      latency: 150,
    })
    
    const { result: highLatencyResult } = renderHook(() => useWebSocketHealth('test-run-123'))
    expect(highLatencyResult.current.hasHighLatency).toBe(true)
  })
})

describe('useWebSocketPerformanceMonitor', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(featureFlagService.isFeatureFlagEnabled).mockReturnValue(false)
    
    mockPlayback.getConnectionHealth.mockReturnValue({
      state: 'connected',
      reconnectAttempts: 0,
      messagesReceived: 100,
      messagesSent: 50,
      latency: 25,
      droppedFrames: 2,
      connectionSource: 'backend',
      lastConnected: Date.now() - 10000,
    })
  })

  it('should generate FPS alerts when below threshold', () => {
    const onAlert = vi.fn()
    
    const { result } = renderHook(() => 
      useWebSocketPerformanceMonitor('test-run-123', {
        fpsThreshold: 25,
        onPerformanceAlert: onAlert,
      })
    )
    
    // Simulate low FPS by not sending enough frames
    act(() => {
      const subscriptionCallback = mockPlayback.subscribe.mock.calls[0][0]
      // Send only 10 frames (below 25 FPS threshold)
      for (let i = 0; i < 10; i++) {
        subscriptionCallback({ dropped: 0 })
      }
    })
    
    expect(result.current.hasAlerts).toBe(true)
    expect(result.current.warningAlerts).toHaveLength(1)
    expect(result.current.warningAlerts[0].type).toBe('fps')
  })

  it('should generate latency alerts when above threshold', () => {
    mockPlayback.getConnectionHealth.mockReturnValue({
      ...mockPlayback.getConnectionHealth(),
      latency: 150, // Above 100ms threshold
    })

    const { result } = renderHook(() =>
      useWebSocketPerformanceMonitor('test-run-123', {
        latencyThreshold: 100,
        fpsThreshold: 0,
      })
    )

    expect(result.current.hasAlerts).toBe(true)
    expect(result.current.warningAlerts).toHaveLength(1)
    expect(result.current.warningAlerts[0].type).toBe('latency')
  })

  it('should generate dropped frame alerts', () => {
    mockPlayback.getConnectionHealth.mockReturnValue({
      ...mockPlayback.getConnectionHealth(),
      droppedFrames: 15, // Above 10 threshold
    })

    const { result } = renderHook(() =>
      useWebSocketPerformanceMonitor('test-run-123', {
        droppedFrameThreshold: 10,
        fpsThreshold: 0,
      })
    )

    expect(result.current.hasAlerts).toBe(true)
    expect(result.current.warningAlerts).toHaveLength(1)
    expect(result.current.warningAlerts[0].type).toBe('droppedFrames')
  })

  it('should categorize alerts by severity', () => {
    mockPlayback.getConnectionHealth.mockReturnValue({
      ...mockPlayback.getConnectionHealth(),
      latency: 250, // Very high latency (2x threshold)
    })
    
    const { result } = renderHook(() => 
      useWebSocketPerformanceMonitor('test-run-123', {
        latencyThreshold: 100,
      })
    )
    
    expect(result.current.criticalAlerts).toHaveLength(1)
    expect(result.current.criticalAlerts[0].severity).toBe('error')
  })

  it('should call alert callback for new alerts', () => {
    const onAlert = vi.fn()
    
    renderHook(() => 
      useWebSocketPerformanceMonitor('test-run-123', {
        latencyThreshold: 50,
        onPerformanceAlert: onAlert,
      })
    )
    
    expect(onAlert).toHaveBeenCalled()
  })
})
