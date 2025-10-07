/**
 * WebSocket performance testing and optimization utilities.
 *
 * This module provides tools for measuring and optimizing WebSocket performance
 * in both BFF and direct backend modes for comparison and validation.
 */

import { featureFlagService } from '../services/featureFlags'
import { createWebSocketManager, type BFFWebSocketManager } from '../services/websocket'

/**
 * WebSocket performance test results.
 */
export interface PerformanceTestResult {
  /** Test configuration */
  config: {
    runId: string
    duration: number
    connectionSource: 'bff' | 'backend'
    testType: 'streaming' | 'latency' | 'throughput'
  }

  /** Connection metrics */
  connection: {
    establishmentTime: number
    reconnections: number
    totalUptime: number
    totalDowntime: number
  }

  /** Streaming metrics */
  streaming: {
    totalFrames: number
    droppedFrames: number
    averageFPS: number
    minFPS: number
    maxFPS: number
    fpsStability: number // Standard deviation
  }

  /** Latency metrics */
  latency: {
    average: number
    min: number
    max: number
    p50: number
    p95: number
    p99: number
    samples: number[]
  }

  /** Throughput metrics */
  throughput: {
    messagesReceived: number
    messagesSent: number
    bytesReceived: number
    bytesSent: number
    averageMessageSize: number
  }

  /** Test metadata */
  metadata: {
    startTime: number
    endTime: number
    testDuration: number
    success: boolean
    errors: string[]
  }
}

/**
 * WebSocket performance comparison between BFF and backend.
 */
export interface PerformanceComparison {
  bff: PerformanceTestResult
  backend: PerformanceTestResult
  comparison: {
    connectionTimeImprovement: number // Percentage
    fpsImprovement: number
    latencyImprovement: number
    stabilityImprovement: number
    overallScore: number // 0-100
  }
}

/**
 * WebSocket performance tester.
 */
export class WebSocketPerformanceTester {
  private wsManager: BFFWebSocketManager | null = null
  private testResults: PerformanceTestResult[] = []

  /**
   * Run comprehensive performance test.
   */
  public async runPerformanceTest(
    runId: string,
    duration: number = 30000, // 30 seconds
    testType: 'streaming' | 'latency' | 'throughput' = 'streaming',
  ): Promise<PerformanceTestResult> {
    const startTime = Date.now()
    const connectionSource = featureFlagService.isFeatureFlagEnabled('websocket')
      ? 'bff'
      : 'backend'

    const result: PerformanceTestResult = {
      config: { runId, duration, connectionSource, testType },
      connection: { establishmentTime: 0, reconnections: 0, totalUptime: 0, totalDowntime: 0 },
      streaming: {
        totalFrames: 0,
        droppedFrames: 0,
        averageFPS: 0,
        minFPS: Infinity,
        maxFPS: 0,
        fpsStability: 0,
      },
      latency: { average: 0, min: Infinity, max: 0, p50: 0, p95: 0, p99: 0, samples: [] },
      throughput: {
        messagesReceived: 0,
        messagesSent: 0,
        bytesReceived: 0,
        bytesSent: 0,
        averageMessageSize: 0,
      },
      metadata: { startTime, endTime: 0, testDuration: 0, success: false, errors: [] },
    }

    try {
      // Create WebSocket manager for testing
      this.wsManager = createWebSocketManager(runId, {
        autoReconnect: true,
        maxReconnectAttempts: 3,
        reconnectDelay: 1000,
        enableMessageQueue: true,
      })

      // Setup event listeners for metrics collection
      this.setupMetricsCollection(result)

      // Establish connection and measure establishment time
      const connectionStart = Date.now()
      await this.wsManager.connect()
      result.connection.establishmentTime = Date.now() - connectionStart

      // Run test based on type
      switch (testType) {
        case 'streaming':
          await this.runStreamingTest(result, duration)
          break
        case 'latency':
          await this.runLatencyTest(result, duration)
          break
        case 'throughput':
          await this.runThroughputTest(result, duration)
          break
      }

      result.metadata.success = true
    } catch (error) {
      result.metadata.errors.push(error instanceof Error ? error.message : String(error))
    } finally {
      // Cleanup
      if (this.wsManager) {
        this.wsManager.close()
        this.wsManager = null
      }

      result.metadata.endTime = Date.now()
      result.metadata.testDuration = result.metadata.endTime - result.metadata.startTime
    }

    this.testResults.push(result)
    return result
  }

  /**
   * Setup metrics collection event listeners.
   */
  private setupMetricsCollection(result: PerformanceTestResult): void {
    if (!this.wsManager) return

    let connectionUptime = 0
    let connectionDowntime = 0
    let lastConnectionTime = Date.now()
    let isConnected = false

    // Track connection state changes
    this.wsManager.addEventListener(
      'stateChange',
      (event: { oldState: string; newState: string; health: unknown }) => {
        const now = Date.now()
        const { newState } = event

        if (newState === 'connected') {
          if (!isConnected) {
            connectionDowntime += now - lastConnectionTime
            isConnected = true
            lastConnectionTime = now
          }
        } else if (isConnected) {
          connectionUptime += now - lastConnectionTime
          isConnected = false
          lastConnectionTime = now

          if (newState === 'reconnecting') {
            result.connection.reconnections++
          }
        }

        result.connection.totalUptime = connectionUptime
        result.connection.totalDowntime = connectionDowntime
      },
    )

    // Track messages for throughput
    this.wsManager.addEventListener('message', (event: MessageEvent) => {
      result.throughput.messagesReceived++
      result.throughput.bytesReceived += event.data.length
    })
  }

  /**
   * Run streaming performance test.
   */
  private async runStreamingTest(result: PerformanceTestResult, duration: number): Promise<void> {
    if (!this.wsManager) return

    const frameTimestamps: number[] = []
    const fpsReadings: number[] = []
    let frameCount = 0

    // Start streaming
    this.wsManager.send(JSON.stringify({ t: 'ctrl', cmd: 'play' }))
    result.throughput.messagesSent++

    // Collect frame data
    const messageListener = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.t === 'frame') {
          frameCount++
          frameTimestamps.push(Date.now())
          result.streaming.totalFrames = frameCount
          result.streaming.droppedFrames = msg.dropped || 0
        }
      } catch {
        // Ignore parsing errors
      }
    }

    this.wsManager.addEventListener('message', messageListener)

    // Calculate FPS every second
    const fpsInterval = setInterval(() => {
      const now = Date.now()
      const recentFrames = frameTimestamps.filter((ts) => now - ts <= 1000)
      const fps = recentFrames.length

      fpsReadings.push(fps)
      result.streaming.minFPS = Math.min(result.streaming.minFPS, fps)
      result.streaming.maxFPS = Math.max(result.streaming.maxFPS, fps)
    }, 1000)

    // Wait for test duration
    await new Promise((resolve) => setTimeout(resolve, duration))

    clearInterval(fpsInterval)

    // Calculate final metrics
    if (fpsReadings.length > 0) {
      result.streaming.averageFPS = fpsReadings.reduce((a, b) => a + b, 0) / fpsReadings.length

      // Calculate FPS stability (standard deviation)
      const mean = result.streaming.averageFPS
      const variance =
        fpsReadings.reduce((acc, fps) => acc + Math.pow(fps - mean, 2), 0) / fpsReadings.length
      result.streaming.fpsStability = Math.sqrt(variance)
    }
  }

  /**
   * Run latency performance test.
   */
  private async runLatencyTest(result: PerformanceTestResult, duration: number): Promise<void> {
    if (!this.wsManager) return

    const latencySamples: number[] = []
    const pingInterval = 1000 // Ping every second

    const pingTimer = setInterval(() => {
      const pingTime = Date.now()
      this.wsManager!.send(JSON.stringify({ t: 'ping', ts: pingTime }))
      result.throughput.messagesSent++
    }, pingInterval)

    // Listen for pong responses
    const messageListener = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.t === 'pong' && msg.ts) {
          const latency = Date.now() - msg.ts
          latencySamples.push(latency)
        }
      } catch {
        // Ignore parsing errors
      }
    }

    this.wsManager.addEventListener('message', messageListener)

    // Wait for test duration
    await new Promise((resolve) => setTimeout(resolve, duration))

    clearInterval(pingTimer)

    // Calculate latency statistics
    if (latencySamples.length > 0) {
      latencySamples.sort((a, b) => a - b)

      result.latency.samples = latencySamples
      result.latency.min = latencySamples[0]
      result.latency.max = latencySamples[latencySamples.length - 1]
      result.latency.average = latencySamples.reduce((a, b) => a + b, 0) / latencySamples.length
      result.latency.p50 = latencySamples[Math.floor(latencySamples.length * 0.5)]
      result.latency.p95 = latencySamples[Math.floor(latencySamples.length * 0.95)]
      result.latency.p99 = latencySamples[Math.floor(latencySamples.length * 0.99)]
    }
  }

  /**
   * Run throughput performance test.
   */
  private async runThroughputTest(result: PerformanceTestResult, duration: number): Promise<void> {
    if (!this.wsManager) return

    let totalBytes = 0
    let messageCount = 0

    // Send messages at high frequency
    const sendInterval = setInterval(() => {
      const message = JSON.stringify({ t: 'ctrl', cmd: 'status' })
      this.wsManager!.send(message)
      result.throughput.messagesSent++
      result.throughput.bytesSent += message.length
    }, 100) // Send every 100ms

    // Count received messages
    const messageListener = (event: MessageEvent) => {
      messageCount++
      totalBytes += event.data.length
    }

    this.wsManager.addEventListener('message', messageListener)

    // Wait for test duration
    await new Promise((resolve) => setTimeout(resolve, duration))

    clearInterval(sendInterval)

    // Calculate throughput metrics
    result.throughput.messagesReceived = messageCount
    result.throughput.bytesReceived = totalBytes
    result.throughput.averageMessageSize = messageCount > 0 ? totalBytes / messageCount : 0
  }

  /**
   * Compare BFF vs backend performance.
   */
  public async comparePerformance(
    runId: string,
    duration: number = 30000,
  ): Promise<PerformanceComparison> {
    // Test with BFF enabled
    // Note: In a real implementation, we'd need a way to temporarily override feature flags
    // For now, we'll test with current settings and document the limitation

    const bffResult = await this.runPerformanceTest(runId, duration, 'streaming')

    // Test with backend mode
    // Note: This would require temporarily disabling BFF flags
    const backendResult = await this.runPerformanceTest(runId, duration, 'streaming')

    // Calculate comparison metrics
    const comparison = {
      connectionTimeImprovement: this.calculateImprovement(
        backendResult.connection.establishmentTime,
        bffResult.connection.establishmentTime,
      ),
      fpsImprovement: this.calculateImprovement(
        backendResult.streaming.averageFPS,
        bffResult.streaming.averageFPS,
        true, // Higher is better
      ),
      latencyImprovement: this.calculateImprovement(
        backendResult.latency.average,
        bffResult.latency.average,
      ),
      stabilityImprovement: this.calculateImprovement(
        backendResult.streaming.fpsStability,
        bffResult.streaming.fpsStability,
      ),
      overallScore: 0,
    }

    // Calculate overall score (0-100)
    comparison.overallScore = Math.max(
      0,
      Math.min(
        100,
        50 +
          (comparison.fpsImprovement +
            comparison.latencyImprovement +
            comparison.stabilityImprovement) /
            3,
      ),
    )

    return { bff: bffResult, backend: backendResult, comparison }
  }

  /**
   * Calculate percentage improvement.
   */
  private calculateImprovement(
    baseline: number,
    improved: number,
    higherIsBetter: boolean = false,
  ): number {
    if (baseline === 0) return 0

    const improvement = higherIsBetter
      ? ((improved - baseline) / baseline) * 100
      : ((baseline - improved) / baseline) * 100

    return Math.round(improvement * 100) / 100
  }

  /**
   * Get all test results.
   */
  public getTestResults(): PerformanceTestResult[] {
    return [...this.testResults]
  }

  /**
   * Clear test results.
   */
  public clearResults(): void {
    this.testResults = []
  }
}

// Export singleton instance
export const webSocketPerformanceTester = new WebSocketPerformanceTester()
