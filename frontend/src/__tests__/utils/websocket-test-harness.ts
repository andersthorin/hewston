/**
 * WebSocket Test Harness
 *
 * Comprehensive testing utilities for WebSocket functionality.
 * Provides mock WebSocket implementation and testing helpers.
 */

import { vi } from 'vitest'

export type WebSocketState = 'idle' | 'connecting' | 'connected' | 'closed' | 'error'

export class WebSocketTestHarness {
  private messageQueue: any[] = []
  private connectionState: WebSocketState = 'idle'
  private eventHandlers: Map<string, Function[]> = new Map()
  private mockWebSocketInstance: any = null

  constructor() {
    this.setupMockWebSocket()
  }

  private setupMockWebSocket() {
    // Mock WebSocket constructor
    const MockWebSocketClass = class MockWebSocket {
      static CONNECTING = 0
      static OPEN = 1
      static CLOSING = 2
      static CLOSED = 3

      readyState = MockWebSocket.CONNECTING
      url: string
      onopen: ((event: Event) => void) | null = null
      onmessage: ((event: MessageEvent) => void) | null = null
      onclose: ((event: Event) => void) | null = null
      onerror: ((event: Event) => void) | null = null

      constructor(url: string) {
        this.url = url
        // Store reference to this instance
        // @ts-ignore - accessing private property for testing
        window.__mockWebSocketInstance = this

        // Simulate async connection
        setTimeout(() => {
          this.readyState = MockWebSocket.OPEN
          this.onopen?.(new Event('open'))
        }, 10)
      }

      send(data: string) {
        if (this.readyState === MockWebSocket.OPEN) {
          // Echo back for testing
          setTimeout(() => {
            this.onmessage?.(new MessageEvent('message', { data }))
          }, 5)
        }
      }

      close() {
        this.readyState = MockWebSocket.CLOSED
        setTimeout(() => {
          const evt = new Event('close') as any
          evt.code = 1000
          evt.reason = 'normal'
          evt.wasClean = true
          this.onclose?.(evt)
        }, 5)
      }
    }

    vi.stubGlobal('WebSocket', MockWebSocketClass)
  }

  async simulateConnection(url: string): Promise<void> {
    this.connectionState = 'connecting'
    // Simulate connection delay
    await new Promise((resolve) => setTimeout(resolve, 10))
    this.connectionState = 'connected'
  }

  async simulateMessage(data: any): Promise<void> {
    if (this.connectionState === 'connected') {
      this.messageQueue.push(data)
      // Trigger message event on the mock instance
      const mockInstance = (window as any).__mockWebSocketInstance
      if (mockInstance && mockInstance.onmessage) {
        const event = new MessageEvent('message', { data: JSON.stringify(data) })
        mockInstance.onmessage(event)
      }
    }
  }

  async simulateDisconnection(): Promise<void> {
    this.connectionState = 'closed'
    const mockInstance = (window as any).__mockWebSocketInstance
    if (mockInstance && mockInstance.onclose) {
      const evt = new Event('close') as any
      evt.code = 1000
      evt.reason = 'normal'
      evt.wasClean = true
      mockInstance.onclose(evt)
    }
  }

  async simulateReconnection(): Promise<void> {
    await this.simulateConnection('mock-url')
  }

  async simulateError(error?: string): Promise<void> {
    this.connectionState = 'error'
    const mockInstance = (window as any).__mockWebSocketInstance
    if (mockInstance && mockInstance.onerror) {
      const event = new Event('error')
      // @ts-ignore - adding error message for testing
      event.message = error || 'WebSocket error'
      mockInstance.onerror(event)
    }
  }

  getConnectionState(): WebSocketState {
    return this.connectionState
  }

  getMessageQueue(): any[] {
    return [...this.messageQueue]
  }

  clearMessageQueue(): void {
    this.messageQueue = []
  }

  getMockWebSocketInstance(): any {
    return (window as any).__mockWebSocketInstance
  }

  cleanup(): void {
    this.messageQueue = []
    this.connectionState = 'idle'
    this.eventHandlers.clear()
    delete (window as any).__mockWebSocketInstance
  }

  // Helper methods for testing specific scenarios
  async simulatePlaybackCommand(command: string, params?: any): Promise<void> {
    const message = {
      type: 'command',
      command,
      params,
      timestamp: Date.now(),
    }
    await this.simulateMessage(message)
  }

  async simulateStreamingData(data: any): Promise<void> {
    const message = {
      type: 'data',
      payload: data,
      timestamp: Date.now(),
    }
    await this.simulateMessage(message)
  }

  async simulatePerformanceData(fps: number, latency: number): Promise<void> {
    const message = {
      type: 'performance',
      fps,
      latency,
      timestamp: Date.now(),
    }
    await this.simulateMessage(message)
  }

  // Performance testing helpers
  async measureConnectionTime(): Promise<number> {
    const startTime = Date.now()
    await this.simulateConnection('test-url')
    return Date.now() - startTime
  }

  async measureMessageLatency(message: any): Promise<number> {
    const startTime = Date.now()
    await this.simulateMessage(message)
    return Date.now() - startTime
  }

  // Validation helpers
  expectConnectionState(expectedState: WebSocketState): void {
    if (this.connectionState !== expectedState) {
      throw new Error(`Expected connection state ${expectedState}, got ${this.connectionState}`)
    }
  }

  expectMessageCount(expectedCount: number): void {
    if (this.messageQueue.length !== expectedCount) {
      throw new Error(`Expected ${expectedCount} messages, got ${this.messageQueue.length}`)
    }
  }

  expectLastMessage(expectedMessage: any): void {
    const lastMessage = this.messageQueue[this.messageQueue.length - 1]
    if (JSON.stringify(lastMessage) !== JSON.stringify(expectedMessage)) {
      throw new Error(
        `Expected last message ${JSON.stringify(expectedMessage)}, got ${JSON.stringify(lastMessage)}`,
      )
    }
  }
}

// Export singleton instance for convenience
export const webSocketTestHarness = new WebSocketTestHarness()

// Export factory function for creating new instances
export function createWebSocketTestHarness(): WebSocketTestHarness {
  return new WebSocketTestHarness()
}
