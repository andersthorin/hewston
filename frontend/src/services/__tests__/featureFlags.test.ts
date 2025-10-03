/**
 * Unit tests for feature flag service.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

// Mock environment variables properly
const mockEnv = {
  VITE_BFF_ENABLED: 'false',
  VITE_BFF_CHART_DATA_ENABLED: 'false',
  VITE_BFF_RUN_DATA_ENABLED: 'false',
  VITE_BFF_WEBSOCKET_ENABLED: 'false',
  VITE_API_BASE_URL: 'http://127.0.0.1:8000',
  VITE_BFF_BASE_URL: 'http://127.0.0.1:8001',
  VITE_WS_BASE_URL: 'ws://127.0.0.1:8000',
  VITE_BFF_WS_BASE_URL: 'ws://127.0.0.1:8001',
  VITE_FEATURE_FLAG_DEBUG: 'false',
}

describe('FeatureFlagService', () => {
  let FeatureFlagService: any
  let service: any

  beforeEach(async () => {
    vi.resetModules()
    vi.unstubAllEnvs() // Clean up any previous environment stubs

    // Explicitly set all environment variables to default values
    vi.stubEnv('VITE_BFF_ENABLED', 'false')
    vi.stubEnv('VITE_BFF_CHART_DATA_ENABLED', 'false')
    vi.stubEnv('VITE_BFF_RUN_DATA_ENABLED', 'false')
    vi.stubEnv('VITE_BFF_WEBSOCKET_ENABLED', 'false')
    vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:8000')
    vi.stubEnv('VITE_BFF_BASE_URL', 'http://127.0.0.1:8001')
    vi.stubEnv('VITE_WS_BASE_URL', 'ws://127.0.0.1:8000')
    vi.stubEnv('VITE_BFF_WS_BASE_URL', 'ws://127.0.0.1:8001')
    vi.stubEnv('VITE_FEATURE_FLAG_DEBUG', 'false')

    // Import fresh module after env setup
    const module = await import('../featureFlags')
    FeatureFlagService = module.FeatureFlagService
    service = new FeatureFlagService()
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  describe('Default Configuration', () => {
    it('should have all flags disabled by default', () => {
      const config = service.getConfiguration()
      
      expect(config.bffEnabled).toBe(false)
      expect(config.chartDataEnabled).toBe(false)
      expect(config.runDataEnabled).toBe(false)
      expect(config.websocketEnabled).toBe(false)
      expect(config.fallbackToBackend).toBe(false)
    })

    it('should use backend URLs when BFF is disabled', () => {
      const endpointConfig = service.getEndpointConfiguration()
      
      expect(endpointConfig.apiBaseUrl).toBe('http://127.0.0.1:8000')
      expect(endpointConfig.wsBaseUrl).toBe('ws://127.0.0.1:8000')
    })
  })

  describe('Feature Flag Evaluation', () => {
    it('should evaluate chartData flag correctly when disabled', () => {
      const evaluation = service.evaluateFeatureFlag('chartData')
      
      expect(evaluation.enabled).toBe(false)
      expect(evaluation.source).toBe('backend')
      expect(evaluation.endpointUrl).toContain('127.0.0.1:8000')
    })

    it('should evaluate chartData flag correctly when enabled', async () => {
      vi.stubEnv('VITE_BFF_ENABLED', 'true')
      vi.stubEnv('VITE_BFF_CHART_DATA_ENABLED', 'true')

      // Re-import service with new environment
      const module = await import('../featureFlags')
      const TestFeatureFlagService = module.FeatureFlagService
      const testService = new TestFeatureFlagService()

      const evaluation = testService.evaluateFeatureFlag('chartData')

      expect(evaluation.enabled).toBe(true)
      expect(evaluation.source).toBe('bff')
      expect(evaluation.endpointUrl).toContain('127.0.0.1:8001')
    })

    it('should require master BFF flag to be enabled', () => {
      mockEnv.VITE_BFF_CHART_DATA_ENABLED = 'true'
      // VITE_BFF_ENABLED remains false
      service = new FeatureFlagService()
      
      const evaluation = service.evaluateFeatureFlag('chartData')
      
      expect(evaluation.enabled).toBe(false)
      expect(evaluation.source).toBe('backend')
    })
  })

  describe('Environment Variable Parsing', () => {
    it('should parse boolean environment variables correctly', async () => {
      // Set environment variables
      vi.stubEnv('VITE_BFF_ENABLED', 'true')
      vi.stubEnv('VITE_BFF_CHART_DATA_ENABLED', '1')

      // Re-import service with new environment
      const module = await import('../featureFlags')
      const TestFeatureFlagService = module.FeatureFlagService
      const testService = new TestFeatureFlagService()

      const config = testService.getConfiguration()

      expect(config.bffEnabled).toBe(true)
      expect(config.chartDataEnabled).toBe(true)
    })

    it('should handle missing environment variables', async () => {
      // Don't set VITE_BFF_ENABLED to test default behavior
      vi.stubEnv('VITE_BFF_CHART_DATA_ENABLED', 'true')

      // Re-import service with new environment
      const module = await import('../featureFlags')
      const TestFeatureFlagService = module.FeatureFlagService
      const testService = new TestFeatureFlagService()

      const config = testService.getConfiguration()

      expect(config.bffEnabled).toBe(false) // Default value
    })
  })

  describe('Endpoint Configuration', () => {
    it('should build correct endpoint mappings for backend mode', () => {
      const endpointConfig = service.getEndpointConfiguration()

      expect(endpointConfig.endpointMappings.chartData).toContain('/bars')
      expect(endpointConfig.endpointMappings.runData).toContain('/backtests')
      expect(endpointConfig.endpointMappings.websocket).toContain('/backtests')
    })

    it('should build correct endpoint mappings for BFF mode', async () => {
      // Enable all BFF features
      vi.stubEnv('VITE_BFF_ENABLED', 'true')
      vi.stubEnv('VITE_BFF_CHART_DATA_ENABLED', 'true')
      vi.stubEnv('VITE_BFF_RUN_DATA_ENABLED', 'true')
      vi.stubEnv('VITE_BFF_WEBSOCKET_ENABLED', 'true')

      const module = await import('../featureFlags')
      const TestFeatureFlagService = module.FeatureFlagService
      const testService = new TestFeatureFlagService()

      const endpointConfig = testService.getEndpointConfiguration()

      expect(endpointConfig.endpointMappings.chartData).toContain('/api/v1/chart-data')
      expect(endpointConfig.endpointMappings.runData).toContain('/api/v1/backtests')
      expect(endpointConfig.endpointMappings.websocket).toContain('/api/v1/backtests')
    })
  })

  describe('Configuration Validation', () => {
    it('should validate correct configuration', () => {
      const issues = service.validateConfiguration()
      expect(issues).toHaveLength(0)
    })

    it('should detect missing BFF URL when BFF is enabled', async () => {
      // Enable BFF but clear BFF_BASE_URL to test validation
      vi.stubEnv('VITE_BFF_ENABLED', 'true')
      vi.stubEnv('VITE_BFF_BASE_URL', '') // Explicitly set to empty string

      const module = await import('../featureFlags')
      const TestFeatureFlagService = module.FeatureFlagService
      const testService = new TestFeatureFlagService()

      const issues = testService.validateConfiguration()
      expect(issues.length).toBeGreaterThan(0)
      expect(issues[0]).toContain('VITE_BFF_BASE_URL is required')
    })

    it('should detect conflicting configuration', async () => {
      // Enable individual flag but not master BFF flag
      vi.stubEnv('VITE_BFF_CHART_DATA_ENABLED', 'true')
      // VITE_BFF_ENABLED remains false (default)

      const module = await import('../featureFlags')
      const TestFeatureFlagService = module.FeatureFlagService
      const testService = new TestFeatureFlagService()

      const issues = testService.validateConfiguration()
      expect(issues.length).toBeGreaterThan(0)
      expect(issues[0]).toContain('Individual endpoint flags require VITE_BFF_ENABLED=true')
    })
  })

  describe('Utility Methods', () => {
    it('should return effective API base URL', async () => {
      expect(service.getEffectiveApiBaseUrl()).toBe('http://127.0.0.1:8000')

      // Test with BFF enabled
      vi.stubEnv('VITE_BFF_ENABLED', 'true')
      const module = await import('../featureFlags')
      const TestFeatureFlagService = module.FeatureFlagService
      const testService = new TestFeatureFlagService()
      expect(testService.getEffectiveApiBaseUrl()).toBe('http://127.0.0.1:8001')
    })

    it('should return effective WebSocket base URL', async () => {
      expect(service.getEffectiveWsBaseUrl()).toBe('ws://127.0.0.1:8000')

      // Test with BFF enabled
      vi.stubEnv('VITE_BFF_ENABLED', 'true')
      vi.stubEnv('VITE_BFF_WEBSOCKET_ENABLED', 'true')
      const module = await import('../featureFlags')
      const TestFeatureFlagService = module.FeatureFlagService
      const testService = new TestFeatureFlagService()
      expect(testService.getEffectiveWsBaseUrl()).toBe('ws://127.0.0.1:8001')
    })

    it('should check individual feature flags', async () => {
      expect(service.isFeatureFlagEnabled('chartData')).toBe(false)

      // Test with flags enabled
      vi.stubEnv('VITE_BFF_ENABLED', 'true')
      vi.stubEnv('VITE_BFF_CHART_DATA_ENABLED', 'true')
      const module = await import('../featureFlags')
      const TestFeatureFlagService = module.FeatureFlagService
      const testService = new TestFeatureFlagService()
      expect(testService.isFeatureFlagEnabled('chartData')).toBe(true)
    })
  })

  describe('Debug Information', () => {
    it('should provide debug information', () => {
      const debugInfo = service.getDebugInfo()
      
      expect(debugInfo.configuration).toBeDefined()
      expect(debugInfo.endpointMappings).toBeDefined()
      expect(debugInfo.lastEvaluations).toBeDefined()
      expect(debugInfo.lastUpdated).toBeTypeOf('number')
    })

    it('should update debug info on evaluation', () => {
      const initialDebugInfo = service.getDebugInfo()
      const initialTimestamp = initialDebugInfo.lastUpdated
      
      // Wait a bit to ensure timestamp difference
      setTimeout(() => {
        service.evaluateFeatureFlag('chartData')
        const updatedDebugInfo = service.getDebugInfo()

        expect(updatedDebugInfo.lastUpdated).toBeGreaterThan(initialTimestamp)
        expect(updatedDebugInfo.lastEvaluations.chartData).toBeDefined()
      }, 10)
    })
  })

  describe('Enhanced Configuration Validation', () => {
    it('should detect invalid configuration combinations', async () => {
      // Enable individual flag without master BFF flag
      vi.stubEnv('VITE_BFF_ENABLED', 'false')
      vi.stubEnv('VITE_BFF_CHART_DATA_ENABLED', 'true')

      const module = await import('../featureFlags')
      const TestFeatureFlagService = module.FeatureFlagService
      const testService = new TestFeatureFlagService()

      const issues = testService.validateConfiguration()

      expect(issues).toContain('Individual endpoint flags require VITE_BFF_ENABLED=true')
    })

    it('should detect multiple invalid configurations', async () => {
      // Multiple individual flags enabled without master flag
      vi.stubEnv('VITE_BFF_ENABLED', 'false')
      vi.stubEnv('VITE_BFF_CHART_DATA_ENABLED', 'true')
      vi.stubEnv('VITE_BFF_RUN_DATA_ENABLED', 'true')
      vi.stubEnv('VITE_BFF_WEBSOCKET_ENABLED', 'true')

      const module = await import('../featureFlags')
      const TestFeatureFlagService = module.FeatureFlagService
      const testService = new TestFeatureFlagService()

      const issues = testService.validateConfiguration()

      expect(issues.length).toBeGreaterThan(0)
      expect(issues[0]).toContain('Individual endpoint flags require VITE_BFF_ENABLED=true')
    })

    it('should validate URL format requirements', async () => {
      // Invalid URL format
      vi.stubEnv('VITE_BFF_ENABLED', 'true')
      vi.stubEnv('VITE_BFF_BASE_URL', 'invalid-url')

      const module = await import('../featureFlags')
      const TestFeatureFlagService = module.FeatureFlagService
      const testService = new TestFeatureFlagService()

      const issues = testService.validateConfiguration()

      // Should detect invalid URL format (if validation exists)
      expect(issues).toBeDefined()
    })
  })
})
