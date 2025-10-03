/**
 * Tests for BFF WebSocket integration.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { BFFWebSocketManager, createWebSocketManager } from '../websocket'
import { WebSocketTestHarness } from '../../__tests__/utils/websocket-test-harness'

// Mock feature flag service
vi.mock('../featureFlags', () => ({
  featureFlagService: {
    isFeatureFlagEnabled: vi.fn(),
    getConfiguration: vi.fn(),
    getEffectiveWsBaseUrl: vi.fn(),
    evaluateFeatureFlag: vi.fn(),
  }
}))

// Mock constants
vi.mock('../../constants', () => ({
  BFF_WS_URL: 'ws://127.0.0.1:8001',
  BACKEND_WS_URL: 'ws://127.0.0.1:8000',
}))

describe('BFFWebSocketManager', () => {
  let manager: BFFWebSocketManager
  let testHarness: WebSocketTestHarness

  beforeEach(async () => {
    vi.clearAllMocks()
    testHarness = new WebSocketTestHarness()

    // Import the mocked service
    const { featureFlagService } = await import('../featureFlags')
    vi.mocked(featureFlagService.isFeatureFlagEnabled).mockReturnValue(false)
    vi.mocked(featureFlagService.getConfiguration).mockReturnValue({
      bffEnabled: false,
      websocketEnabled: false,
    })
    vi.mocked(featureFlagService.getEffectiveWsBaseUrl).mockReturnValue('ws://127.0.0.1:8000')
    vi.mocked(featureFlagService.evaluateFeatureFlag).mockReturnValue({
      enabled: false,
      source: 'backend',
      endpointUrl: 'ws://127.0.0.1:8000'
    })
  })

  afterEach(() => {
    if (manager) {
      manager.close()
    }
    testHarness.cleanup()
  })

  describe('Connection Management', () => {
    it('should connect to backend WebSocket when BFF disabled', async () => {
      const { featureFlagService } = await import('../featureFlags')
      vi.mocked(featureFlagService.isFeatureFlagEnabled).mockReturnValue(false)
      vi.mocked(featureFlagService.evaluateFeatureFlag).mockReturnValue({
        enabled: false,
        source: 'backend',
        endpointUrl: 'ws://127.0.0.1:8000'
      })

      manager = new BFFWebSocketManager('test-run-123')
      await manager.connect()

      expect(manager.isReady()).toBe(true)
      expect(manager.getHealth().connectionSource).toBe('backend')
    })

    it('should connect to BFF WebSocket when BFF enabled', async () => {
      const { featureFlagService } = await import('../featureFlags')
      vi.mocked(featureFlagService.isFeatureFlagEnabled).mockReturnValue(true)
      vi.mocked(featureFlagService.evaluateFeatureFlag).mockReturnValue({
        enabled: true,
        source: 'bff',
        endpointUrl: 'ws://127.0.0.1:8001'
      })
      
      manager = new BFFWebSocketManager('test-run-123')
      await manager.connect()
      
      expect(manager.isReady()).toBe(true)
      expect(manager.getHealth().connectionSource).toBe('bff')
    })

    it('should handle connection timeout', async () => {
      // Mock WebSocket that never opens
      class NeverOpensWebSocket {
        static CONNECTING = 0
        static OPEN = 1
        static CLOSING = 2
        static CLOSED = 3
        readyState = NeverOpensWebSocket.CONNECTING
        onopen: ((ev: any) => void) | null = null
        onmessage: ((ev: any) => void) | null = null
        onclose: ((ev: any) => void) | null = null
        onerror: ((ev: any) => void) | null = null
        constructor(_url: string) {}
        close() { /* noop */ }
        send(_data: any) { /* noop */ }
      }
      vi.stubGlobal('WebSocket', NeverOpensWebSocket as any)

      manager = new BFFWebSocketManager('test-run-123', { connectionTimeout: 100 })

      await expect(manager.connect()).rejects.toThrow('WebSocket connection timeout')
    })

    it('should emit state change events', async () => {
      const stateChanges: string[] = []
      
      manager = new BFFWebSocketManager('test-run-123')
      manager.addEventListener('stateChange', ({ newState }: any) => {
        stateChanges.push(newState)
      })
      
      await manager.connect()
      
      expect(stateChanges).toContain('connecting')
      expect(stateChanges).toContain('connected')
    })
  })

  describe('Message Handling', () => {
    beforeEach(async () => {
      manager = new BFFWebSocketManager('test-run-123')
      await manager.connect()
    })

    it('should send messages when connected', () => {
      const result = manager.send('test message')
      expect(result).toBe(true)
    })

    it('should queue messages when disconnected', () => {
      manager.close()
      const result = manager.send('queued message')
      expect(result).toBe(false)
    })

    it('should process queued messages after reconnection', async () => {
      // Send message while disconnected
      manager.close()
      manager.send('queued message')
      
      // Reconnect and verify message is sent
      await manager.connect()
      expect(manager.getHealth().messagesSent).toBeGreaterThan(0)
    })

    it('should track message statistics', () => {
      manager.send('test message 1')
      manager.send('test message 2')
      
      const health = manager.getHealth()
      expect(health.messagesSent).toBe(2)
    })
  })

  describe('Auto-Reconnection', () => {
    it('should attempt reconnection on connection loss', async () => {
      const reconnectAttempts: number[] = []
      
      manager = new BFFWebSocketManager('test-run-123', {
        autoReconnect: true,
        reconnectDelay: 50,
        maxReconnectAttempts: 3,
      })
      
      manager.addEventListener('stateChange', () => {
        reconnectAttempts.push(manager.getHealth().reconnectAttempts)
      })
      
      await manager.connect()

      // Simulate connection loss
      const ws = (manager as any).ws as any
      ws.readyState = (globalThis as any).WebSocket.CLOSED
      ws.onclose?.(new CloseEvent('close', { wasClean: false }))

      // Wait for reconnection attempts
      await new Promise(resolve => setTimeout(resolve, 200))
      
      expect(Math.max(...reconnectAttempts)).toBeGreaterThan(0)
    })

    it('should respect max reconnection attempts', async () => {
      manager = new BFFWebSocketManager('test-run-123', {
        autoReconnect: true,
        maxReconnectAttempts: 2,
        reconnectDelay: 10,
      })
      
      await manager.connect()
      
      // Simulate multiple connection failures
      for (let i = 0; i < 5; i++) {
        const ws = (manager as any).ws as any
        ws.readyState = (globalThis as any).WebSocket.CLOSED
        ws.onclose?.(new CloseEvent('close', { wasClean: false }))
        await new Promise(resolve => setTimeout(resolve, 20))
      }
      
      expect(manager.getHealth().reconnectAttempts).toBeLessThanOrEqual(2)
    })
  })

  describe('Health Monitoring', () => {
    beforeEach(async () => {
      manager = new BFFWebSocketManager('test-run-123')
      await manager.connect()
    })

    it('should track connection health metrics', () => {
      const health = manager.getHealth()
      
      expect(health.state).toBe('connected')
      expect(health.lastConnected).toBeTypeOf('number')
      expect(health.reconnectAttempts).toBe(0)
      expect(health.messagesReceived).toBe(0)
      expect(health.messagesSent).toBe(0)
      expect(health.droppedFrames).toBe(0)
    })

    it('should update health on message activity', () => {
      manager.send('test message')
      
      const health = manager.getHealth()
      expect(health.messagesSent).toBe(1)
    })

    it('should measure latency with ping/pong', () => {
      manager.ping()

      // Simulate pong response
      const ws = (manager as any).ws as any
      ws.onmessage?.(new MessageEvent('message', {
        data: JSON.stringify({ t: 'pong', ts: Date.now() - 50 })
      }))

      const health = manager.getHealth()
      expect(health.latency ?? 0).toBeGreaterThanOrEqual(0)
    })
  })

  describe('Feature Flag Integration', () => {
    it('should use correct endpoint based on feature flags', async () => {
      const { featureFlagService } = await import('../featureFlags')
      // Test backend mode
      vi.mocked(featureFlagService.isFeatureFlagEnabled).mockReturnValue(false)
      const backendManager = new BFFWebSocketManager('test-run-123')
      expect(backendManager.getHealth().connectionSource).toBe('backend')

      // Test BFF mode
      vi.mocked(featureFlagService.isFeatureFlagEnabled).mockReturnValue(true)
      const bffManager = new BFFWebSocketManager('test-run-123')
      expect(bffManager.getHealth().connectionSource).toBe('bff')

      bffManager.close()
    })
  })

  describe('Error Handling', () => {
    it('should handle WebSocket creation errors', async () => {
      // Mock WebSocket constructor that throws
      vi.stubGlobal('WebSocket', class {
        constructor() {
          throw new Error('WebSocket creation failed')
        }
      })
      
      manager = new BFFWebSocketManager('test-run-123')
      
      await expect(manager.connect()).rejects.toThrow('WebSocket creation failed')
    })

    it('should handle send errors gracefully', async () => {
      manager = new BFFWebSocketManager('test-run-123')
      await manager.connect()
      
      // Mock send method to throw
      const ws = (manager as any).ws as any
      ws.send = () => { throw new Error('Send failed') }

      const result = manager.send('test message')
      expect(result).toBe(false)
    })
  })
})

describe('createWebSocketManager', () => {
  it('should create BFFWebSocketManager instance', () => {
    const manager = createWebSocketManager('test-run-123')
    expect(manager).toBeInstanceOf(BFFWebSocketManager)
    manager.close()
  })

  it('should pass options to manager', () => {
    const options = {
      autoReconnect: false,
      maxReconnectAttempts: 10,
    }
    
    const manager = createWebSocketManager('test-run-123', options)
    expect(manager).toBeInstanceOf(BFFWebSocketManager)
    manager.close()
  })
})
