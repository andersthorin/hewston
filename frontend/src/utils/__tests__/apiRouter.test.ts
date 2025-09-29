/**
 * Unit tests for API router.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { apiRouter } from '../apiRouter'

// Create a new instance for testing
const APIClientRouter = (apiRouter as any).constructor

// Mock fetch
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

// Mock feature flag service
const mockFeatureFlagService = {
  evaluateFeatureFlag: vi.fn(),
  getConfiguration: vi.fn(),
  validateConfiguration: vi.fn(),
}

vi.mock('../services/featureFlags', () => ({
  featureFlagService: mockFeatureFlagService
}))

// Mock import.meta.env
vi.stubGlobal('import', {
  meta: {
    env: {
      VITE_API_BASE_URL: 'http://127.0.0.1:8000',
      VITE_BFF_BASE_URL: 'http://127.0.0.1:8001',
      VITE_FEATURE_FLAG_DEBUG: 'false',
    }
  }
})

describe('APIClientRouter', () => {
  let router: InstanceType<typeof APIClientRouter>

  beforeEach(() => {
    router = new APIClientRouter()
    mockFetch.mockClear()
    mockFeatureFlagService.evaluateFeatureFlag.mockClear()
    mockFeatureFlagService.getConfiguration.mockClear()
    mockFeatureFlagService.validateConfiguration.mockClear()
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  describe('Route API Call', () => {
    it('should route to backend when feature flag is disabled', async () => {
      mockFeatureFlagService.evaluateFeatureFlag.mockReturnValue({
        enabled: false,
        endpointUrl: 'http://127.0.0.1:8000/bars',
        source: 'backend'
      })
      
      mockFeatureFlagService.getConfiguration.mockReturnValue({
        bffEnabled: false
      })

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ data: 'test' })
      })

      const result = await router.routeAPICall('chartData', '/bars/daily')

      expect(mockFetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8000/bars/daily',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          })
        })
      )
      expect(result).toEqual({ data: 'test' })
    })

    it('should route to BFF when feature flag is enabled', async () => {
      mockFeatureFlagService.evaluateFeatureFlag.mockReturnValue({
        enabled: true,
        endpointUrl: 'http://127.0.0.1:8001/api/v1/chart-data',
        source: 'bff'
      })
      
      mockFeatureFlagService.getConfiguration.mockReturnValue({
        bffEnabled: true
      })

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ data: 'bff-test' })
      })

      const result = await router.routeAPICall('chartData', '/bars/daily')

      expect(mockFetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8001/api/v1/chart-data',
        expect.objectContaining({
          method: 'GET'
        })
      )
      expect(result).toEqual({ data: 'bff-test' })
    })

    it('should handle fallback when BFF fails', async () => {
      mockFeatureFlagService.evaluateFeatureFlag.mockReturnValue({
        enabled: true,
        endpointUrl: 'http://127.0.0.1:8001/api/v1/chart-data',
        source: 'bff'
      })
      
      mockFeatureFlagService.getConfiguration.mockReturnValue({
        bffEnabled: true
      })

      // First call (BFF) fails, second call (backend) succeeds
      mockFetch
        .mockRejectedValueOnce(new Error('BFF unavailable'))
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ data: 'fallback-test' })
        })

      const result = await router.routeAPICall('chartData', '/bars/daily', {
        allowFallback: true
      })

      expect(mockFetch).toHaveBeenCalledTimes(2)
      expect(result).toEqual({ data: 'fallback-test' })
    })

    it('should not fallback when disabled', async () => {
      mockFeatureFlagService.evaluateFeatureFlag.mockReturnValue({
        enabled: true,
        endpointUrl: 'http://127.0.0.1:8001/api/v1/chart-data',
        source: 'bff'
      })

      mockFetch.mockRejectedValue(new Error('BFF unavailable'))

      await expect(
        router.routeAPICall('chartData', '/bars/daily', {
          allowFallback: false
        })
      ).rejects.toThrow('BFF unavailable')

      expect(mockFetch).toHaveBeenCalledTimes(1)
    })
  })

  describe('Endpoint Transformation', () => {
    it('should transform chart data endpoints for BFF', async () => {
      mockFeatureFlagService.evaluateFeatureFlag.mockReturnValue({
        enabled: true,
        endpointUrl: 'http://127.0.0.1:8001/api/v1/chart-data',
        source: 'bff'
      })
      
      mockFeatureFlagService.getConfiguration.mockReturnValue({
        bffEnabled: true
      })

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({})
      })

      await router.routeAPICall('chartData', 'bars/daily')

      expect(mockFetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8001/api/v1/chart-data',
        expect.any(Object)
      )
    })

    it('should transform run data endpoints for BFF', async () => {
      mockFeatureFlagService.evaluateFeatureFlag.mockReturnValue({
        enabled: true,
        endpointUrl: 'http://127.0.0.1:8001/api/v1/runs',
        source: 'bff'
      })
      
      mockFeatureFlagService.getConfiguration.mockReturnValue({
        bffEnabled: true
      })

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({})
      })

      await router.routeAPICall('runData', 'backtests/123')

      expect(mockFetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8001/api/v1/runs/123/complete',
        expect.any(Object)
      )
    })

    it('should transform WebSocket endpoints for BFF', async () => {
      mockFeatureFlagService.evaluateFeatureFlag.mockReturnValue({
        enabled: true,
        endpointUrl: 'http://127.0.0.1:8001/api/v1/runs',
        source: 'bff'
      })
      
      mockFeatureFlagService.getConfiguration.mockReturnValue({
        bffEnabled: true
      })

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({})
      })

      await router.routeAPICall('websocket', 'backtests/123/ws')

      expect(mockFetch).toHaveBeenCalledWith(
        'http://127.0.0.1:8001/api/v1/runs/123/stream',
        expect.any(Object)
      )
    })
  })

  describe('Error Handling', () => {
    it('should handle HTTP errors', async () => {
      mockFeatureFlagService.evaluateFeatureFlag.mockReturnValue({
        enabled: false,
        endpointUrl: 'http://127.0.0.1:8000/bars',
        source: 'backend'
      })

      mockFetch.mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found'
      })

      await expect(
        router.routeAPICall('chartData', '/bars/daily')
      ).rejects.toThrow('HTTP 404: Not Found')
    })

    it('should handle network errors', async () => {
      mockFeatureFlagService.evaluateFeatureFlag.mockReturnValue({
        enabled: false,
        endpointUrl: 'http://127.0.0.1:8000/bars',
        source: 'backend'
      })

      mockFetch.mockRejectedValue(new Error('Network error'))

      await expect(
        router.routeAPICall('chartData', '/bars/daily')
      ).rejects.toThrow('Network error')
    })

    it('should handle timeout', async () => {
      mockFeatureFlagService.evaluateFeatureFlag.mockReturnValue({
        enabled: false,
        endpointUrl: 'http://127.0.0.1:8000/bars',
        source: 'backend'
      })

      // Mock a slow response
      mockFetch.mockImplementation(() => 
        new Promise(resolve => setTimeout(resolve, 2000))
      )

      await expect(
        router.routeAPICall('chartData', '/bars/daily', { timeout: 100 })
      ).rejects.toThrow()
    })
  })

  describe('Utility Methods', () => {
    it('should get effective base URL', () => {
      mockFeatureFlagService.evaluateFeatureFlag.mockReturnValue({
        enabled: false,
        endpointUrl: 'http://127.0.0.1:8000/bars',
        source: 'backend'
      })

      const baseUrl = router.getEffectiveBaseURL('chartData')
      expect(baseUrl).toBe('http://127.0.0.1:8000')
    })

    it('should validate configuration', () => {
      mockFeatureFlagService.validateConfiguration.mockReturnValue(['test issue'])

      const issues = router.validateConfiguration()
      expect(issues).toEqual(['test issue'])
    })
  })

  describe('Error Handling', () => {
    it('should handle BFF service unavailable gracefully', async () => {
      mockFeatureFlagService.evaluateFeatureFlag.mockReturnValue({
        enabled: true,
        endpointUrl: 'http://127.0.0.1:8001/api/v1/chart-data',
        source: 'bff'
      })

      // Mock BFF failure
      mockFetch.mockRejectedValue(new Error('ECONNREFUSED'))

      await expect(
        router.routeAPICall('chartData', '/bars/daily', { allowFallback: false })
      ).rejects.toThrow('ECONNREFUSED')
    })

    it('should handle network timeouts gracefully', async () => {
      mockFeatureFlagService.evaluateFeatureFlag.mockReturnValue({
        enabled: true,
        endpointUrl: 'http://127.0.0.1:8001/api/v1/chart-data',
        source: 'bff'
      })

      // Mock timeout error
      mockFetch.mockRejectedValue(new Error('ETIMEDOUT'))

      await expect(
        router.routeAPICall('chartData', '/bars/daily', { allowFallback: false })
      ).rejects.toThrow('ETIMEDOUT')
    })

    it('should handle invalid JSON responses', async () => {
      mockFeatureFlagService.evaluateFeatureFlag.mockReturnValue({
        enabled: true,
        endpointUrl: 'http://127.0.0.1:8001/api/v1/chart-data',
        source: 'bff'
      })

      // Mock response with invalid JSON
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.reject(new Error('Unexpected token'))
      } as Response)

      await expect(
        router.routeAPICall('chartData', '/bars/daily')
      ).rejects.toThrow('Unexpected token')
    })
  })
})
