/**
 * BFF Performance Monitor Component
 * 
 * Development component for monitoring and comparing BFF vs backend performance.
 * Only rendered in development mode with feature flag debugging enabled.
 */

import React, { useState, useEffect } from 'react'
import { useWebSocketHealth, useWebSocketPerformanceMonitor } from '../../hooks/useWebSocketHealth'
import { useChartDataMetrics } from '../../hooks/useChartData'
import { useBacktestDataMetrics as useRunDataMetrics } from '../../hooks/useRunData'
import { featureFlagService } from '../../services/featureFlags'
import { webSocketPerformanceTester } from '../../utils/websocketPerformance'
import type { PerformanceTestResult } from '../../utils/websocketPerformance'

interface BFFPerformanceMonitorProps {
  runId?: string
  className?: string
}

export function BFFPerformanceMonitor({ runId = 'demo-run', className = '' }: BFFPerformanceMonitorProps) {
  const [isVisible, setIsVisible] = useState(false)
  const [testResults, setTestResults] = useState<PerformanceTestResult[]>([])
  const [isRunningTest, setIsRunningTest] = useState(false)

  // Only show in development with debug enabled
  useEffect(() => {
    const isDev = import.meta.env.DEV
    const debugEnabled = import.meta.env.VITE_FEATURE_FLAG_DEBUG === 'true'
    setIsVisible(isDev && debugEnabled)
  }, [])

  // Get performance metrics from hooks
  const wsHealth = useWebSocketHealth(runId)
  const wsMonitor = useWebSocketPerformanceMonitor(runId, {
    fpsThreshold: 25,
    latencyThreshold: 50,
    droppedFrameThreshold: 5,
  })
  const chartMetrics = useChartDataMetrics()
  const runMetrics = useRunDataMetrics()

  // Run performance test
  const runPerformanceTest = async () => {
    setIsRunningTest(true)
    try {
      const result = await webSocketPerformanceTester.runPerformanceTest(runId, 10000, 'streaming')
      setTestResults(prev => [...prev, result])
    } catch (error) {
      console.error('Performance test failed:', error)
    } finally {
      setIsRunningTest(false)
    }
  }

  // Clear test results
  const clearResults = () => {
    setTestResults([])
    webSocketPerformanceTester.clearResults()
  }

  if (!isVisible) {
    return null
  }

  return (
    <div className={`fixed bottom-4 right-4 bg-gray-900 text-white p-4 rounded-lg shadow-lg max-w-md z-50 ${className}`}>
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-lg font-semibold">🎛️ BFF Performance Monitor</h3>
        <button
          onClick={() => setIsVisible(false)}
          className="text-gray-400 hover:text-white"
        >
          ✕
        </button>
      </div>

      {/* Feature Flag Status */}
      <div className="mb-4 p-2 bg-gray-800 rounded">
        <h4 className="font-medium mb-2">Feature Flags</h4>
        <div className="text-sm space-y-1">
          <div className="flex justify-between">
            <span>BFF Master:</span>
            <span className={featureFlagService.getConfiguration().bffEnabled ? 'text-green-400' : 'text-red-400'}>
              {featureFlagService.getConfiguration().bffEnabled ? 'ON' : 'OFF'}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Chart Data:</span>
            <span className={chartMetrics.featureFlags.chartDataEnabled ? 'text-green-400' : 'text-red-400'}>
              {chartMetrics.featureFlags.chartDataEnabled ? 'BFF' : 'Backend'}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Run Data:</span>
            <span className={runMetrics.featureFlags.runDataEnabled ? 'text-green-400' : 'text-red-400'}>
              {runMetrics.featureFlags.runDataEnabled ? 'BFF' : 'Backend'}
            </span>
          </div>
          <div className="flex justify-between">
            <span>WebSocket:</span>
            <span className={wsHealth.isUsingBFF ? 'text-green-400' : 'text-red-400'}>
              {wsHealth.isUsingBFF ? 'BFF' : 'Backend'}
            </span>
          </div>
        </div>
      </div>

      {/* WebSocket Performance */}
      <div className="mb-4 p-2 bg-gray-800 rounded">
        <h4 className="font-medium mb-2">WebSocket Performance</h4>
        <div className="text-sm space-y-1">
          <div className="flex justify-between">
            <span>Status:</span>
            <span className={wsHealth.isConnected ? 'text-green-400' : 'text-red-400'}>
              {wsHealth.connectionStatus.state}
            </span>
          </div>
          <div className="flex justify-between">
            <span>FPS:</span>
            <span className={wsHealth.hasGoodPerformance ? 'text-green-400' : 'text-yellow-400'}>
              {wsHealth.performanceMetrics.averageFPS.toFixed(1)}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Latency:</span>
            <span className={wsHealth.hasHighLatency ? 'text-red-400' : 'text-green-400'}>
              {wsHealth.performanceMetrics.latency || 0}ms
            </span>
          </div>
          <div className="flex justify-between">
            <span>Dropped:</span>
            <span className={wsHealth.performanceMetrics.droppedFrames > 5 ? 'text-red-400' : 'text-green-400'}>
              {wsHealth.performanceMetrics.droppedFrames}
            </span>
          </div>
        </div>
      </div>

      {/* Performance Alerts */}
      {wsMonitor.hasAlerts && (
        <div className="mb-4 p-2 bg-red-900 rounded">
          <h4 className="font-medium mb-2">⚠️ Performance Alerts</h4>
          <div className="text-sm space-y-1">
            {wsMonitor.alerts.map((alert, index) => (
              <div key={index} className="text-red-300">
                {alert.type}: {alert.message}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* API Performance */}
      <div className="mb-4 p-2 bg-gray-800 rounded">
        <h4 className="font-medium mb-2">API Performance</h4>
        <div className="text-sm space-y-1">
          <div className="flex justify-between">
            <span>Chart Data:</span>
            <span>{chartMetrics.bffEnabled ? 'Aggregated' : 'Direct'}</span>
          </div>
          <div className="flex justify-between">
            <span>Run Data:</span>
            <span>{runMetrics.isUsingAggregation ? 'Aggregated' : 'Direct'}</span>
          </div>
          <div className="flex justify-between">
            <span>API Reduction:</span>
            <span className="text-green-400">
              {runMetrics.aggregationBenefit}x fewer calls
            </span>
          </div>
        </div>
      </div>

      {/* Performance Testing */}
      <div className="mb-4 p-2 bg-gray-800 rounded">
        <h4 className="font-medium mb-2">Performance Testing</h4>
        <div className="flex gap-2 mb-2">
          <button
            onClick={runPerformanceTest}
            disabled={isRunningTest}
            className="px-3 py-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded text-sm"
          >
            {isRunningTest ? 'Testing...' : 'Run Test'}
          </button>
          <button
            onClick={clearResults}
            className="px-3 py-1 bg-gray-600 hover:bg-gray-700 rounded text-sm"
          >
            Clear
          </button>
        </div>
        {testResults.length > 0 && (
          <div className="text-sm">
            <div>Tests: {testResults.length}</div>
            <div>Last: {testResults[testResults.length - 1].streaming.averageFPS.toFixed(1)} FPS</div>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="flex gap-2 text-sm">
        <button
          onClick={() => wsHealth.ping()}
          className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded"
        >
          Ping
        </button>
        <button
          onClick={() => wsHealth.reconnect()}
          className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded"
        >
          Reconnect
        </button>
        <button
          onClick={() => console.log('Health Report:', wsHealth.getHealthReport())}
          className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded"
        >
          Log Health
        </button>
      </div>

      {/* Console Commands Reminder */}
      <div className="mt-3 pt-2 border-t border-gray-700 text-xs text-gray-400">
        Console: __FF_STATUS__(), __FF_WEBSOCKET__(), __FF_HELP__()
      </div>
    </div>
  )
}

/**
 * Hook to conditionally render the performance monitor.
 */
export function useBFFPerformanceMonitor() {
  const [shouldShow, setShouldShow] = useState(false)

  useEffect(() => {
    const isDev = import.meta.env.DEV
    const debugEnabled = import.meta.env.VITE_FEATURE_FLAG_DEBUG === 'true'
    setShouldShow(isDev && debugEnabled)

    // Add keyboard shortcut to toggle
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'P') {
        setShouldShow(prev => !prev)
      }
    }

    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [])

  return { shouldShow, setShouldShow }
}

export default BFFPerformanceMonitor
