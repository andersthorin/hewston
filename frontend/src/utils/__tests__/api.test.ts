/**
 * Tests for frontend/src/utils/api.ts utility functions.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  apiRequest,
  apiGet,
  apiPost,
  apiPut,
  apiDelete,
  apiGetWithFlags,
  apiPostWithFlags
} from '../api'

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

// Mock API router first (hoisted)
vi.mock('../apiRouter', () => ({
  apiRouter: {
    routeAPICall: vi.fn(),
  }
}))

// Mock the constants module
vi.mock('../../constants', () => ({
  API_BASE_URL: 'http://127.0.0.1:8000'
}))

describe('API Utilities', () => {
  let mockApiRouter: any

  beforeEach(async () => {
    mockFetch.mockClear()
    // Get the mocked router
    const module = await import('../apiRouter')
    mockApiRouter = module.apiRouter
    vi.mocked(mockApiRouter.routeAPICall).mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('apiRequest', () => {
    it('should make a successful GET request', async () => {
      const mockResponse = { data: 'test' }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValueOnce(mockResponse),
      })

      const result = await apiRequest('/test', { method: 'GET' })

      expect(mockFetch).toHaveBeenCalledWith('http://127.0.0.1:8000/test', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      expect(result).toEqual(mockResponse)
    })

    it('should make a POST request with body', async () => {
      const requestBody = { name: 'test' }
      const mockResponse = { id: 1, name: 'test' }
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: vi.fn().mockResolvedValueOnce(mockResponse),
      })

      const result = await apiRequest('/test', {
        method: 'POST',
        body: requestBody,
      })

      expect(mockFetch).toHaveBeenCalledWith('http://127.0.0.1:8000/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      })
      expect(result).toEqual(mockResponse)
    })

    it('should handle custom headers', async () => {
      const customHeaders = { 'Authorization': 'Bearer token123' }
      const mockResponse = { data: 'authorized' }
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValueOnce(mockResponse),
      })

      await apiRequest('/protected', {
        method: 'GET',
        headers: customHeaders,
      })

      expect(mockFetch).toHaveBeenCalledWith('http://127.0.0.1:8000/protected', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer token123',
        },
      })
    })

    it('should throw error for non-ok responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: vi.fn().mockResolvedValueOnce({ error: 'Resource not found' }),
      })

      await expect(apiRequest('/nonexistent', { method: 'GET' }))
        .rejects.toThrow('HTTP 404: Not Found')
    })

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'))

      await expect(apiRequest('/test', { method: 'GET' }))
        .rejects.toThrow('Network error')
    })

    it('should handle JSON parsing errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: vi.fn().mockRejectedValueOnce(new Error('Invalid JSON')),
      })

      await expect(apiRequest('/test', { method: 'GET' }))
        .rejects.toThrow('Invalid JSON')
    })
  })

  describe('apiGet', () => {
    it('should make a GET request', async () => {
      const mockResponse = { data: 'get test' }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValueOnce(mockResponse),
      })

      const result = await apiGet('/test')

      expect(mockFetch).toHaveBeenCalledWith('http://127.0.0.1:8000/test', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      expect(result).toEqual(mockResponse)
    })

    it('should pass through additional options', async () => {
      const mockResponse = { data: 'get with options' }
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValueOnce(mockResponse),
      })

      await apiGet('/test', { 'Custom-Header': 'value' })

      expect(mockFetch).toHaveBeenCalledWith('http://127.0.0.1:8000/test', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Custom-Header': 'value',
        },
      })
    })
  })

  describe('apiPost', () => {
    it('should make a POST request with data', async () => {
      const requestData = { name: 'test post' }
      const mockResponse = { id: 1, name: 'test post' }
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: vi.fn().mockResolvedValueOnce(mockResponse),
      })

      const result = await apiPost('/test', requestData)

      expect(mockFetch).toHaveBeenCalledWith('http://127.0.0.1:8000/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
      })
      expect(result).toEqual(mockResponse)
    })

    it('should handle POST without data', async () => {
      const mockResponse = { success: true }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValueOnce(mockResponse),
      })

      const result = await apiPost('/test')

      expect(mockFetch).toHaveBeenCalledWith('http://127.0.0.1:8000/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      expect(result).toEqual(mockResponse)
    })
  })

  describe('apiPut', () => {
    it('should make a PUT request with data', async () => {
      const requestData = { id: 1, name: 'updated' }
      const mockResponse = { id: 1, name: 'updated' }
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValueOnce(mockResponse),
      })

      const result = await apiPut('/test/1', requestData)

      expect(mockFetch).toHaveBeenCalledWith('http://127.0.0.1:8000/test/1', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
      })
      expect(result).toEqual(mockResponse)
    })
  })

  describe('apiDelete', () => {
    it('should make a DELETE request', async () => {
      const mockResponse = { success: true }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValueOnce(mockResponse),
      })

      const result = await apiDelete('/test/1')

      expect(mockFetch).toHaveBeenCalledWith('http://127.0.0.1:8000/test/1', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      expect(result).toEqual(mockResponse)
    })

    it('should handle DELETE with additional options', async () => {
      const mockResponse = { deleted: true }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
        json: vi.fn().mockResolvedValueOnce(mockResponse),
      })

      await apiDelete('/test/1', { 'Authorization': 'Bearer token' })

      expect(mockFetch).toHaveBeenCalledWith('http://127.0.0.1:8000/test/1', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer token',
        },
      })
    })
  })

  describe('Error Handling', () => {
    it('should handle 400 Bad Request', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: vi.fn().mockResolvedValueOnce({ error: 'Invalid input' }),
      })

      await expect(apiGet('/test'))
        .rejects.toThrow('HTTP 400: Bad Request')
    })

    it('should handle 401 Unauthorized', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: vi.fn().mockResolvedValueOnce({ error: 'Authentication required' }),
      })

      await expect(apiGet('/protected'))
        .rejects.toThrow('HTTP 401: Unauthorized')
    })

    it('should handle 500 Internal Server Error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: vi.fn().mockResolvedValueOnce({ error: 'Server error' }),
      })

      await expect(apiGet('/test'))
        .rejects.toThrow('HTTP 500: Internal Server Error')
    })
  })

  describe('Feature Flag-Enabled API Functions', () => {
    it('should use API router for feature flag GET requests', async () => {
      vi.mocked(mockApiRouter.routeAPICall).mockResolvedValue({ data: 'bff-test' })

      const result = await apiGetWithFlags('/bars/daily', 'chartData')

      expect(vi.mocked(mockApiRouter.routeAPICall)).toHaveBeenCalledWith(
        'chartData',
        '/bars/daily',
        expect.objectContaining({
          method: 'GET',
          allowFallback: true
        })
      )
      expect(result).toEqual({ data: 'bff-test' })
    })

    it('should use API router for feature flag POST requests', async () => {
      vi.mocked(mockApiRouter.routeAPICall).mockResolvedValue({ id: 456 })

      const result = await apiPostWithFlags(
        '/backtests',
        'runData',
        { strategy: 'test' }
      )

      expect(vi.mocked(mockApiRouter.routeAPICall)).toHaveBeenCalledWith(
        'runData',
        '/backtests',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ strategy: 'test' }),
          allowFallback: true
        })
      )
      expect(result).toEqual({ id: 456 })
    })

    it('should handle custom headers in feature flag requests', async () => {
      vi.mocked(mockApiRouter.routeAPICall).mockResolvedValue({ data: 'authorized' })

      await apiGetWithFlags('/bars/daily', 'chartData', {
        'Authorization': 'Bearer token'
      })

      expect(vi.mocked(mockApiRouter.routeAPICall)).toHaveBeenCalledWith(
        'chartData',
        '/bars/daily',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer token'
          })
        })
      )
    })

    it('should propagate errors from API router', async () => {
      vi.mocked(mockApiRouter.routeAPICall).mockRejectedValue(
        new Error('BFF unavailable')
      )

      await expect(
        apiGetWithFlags('/bars/daily', 'chartData')
      ).rejects.toThrow('BFF unavailable')
    })
  })

  describe('Backward Compatibility with Feature Flags', () => {
    it('should use direct API call when useFeatureFlags is false', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ data: 'direct' })
      })

      const result = await apiRequest('/test-endpoint', {
        endpointGroup: 'chartData',
        useFeatureFlags: false
      })

      expect(mockFetch).toHaveBeenCalled()
      expect(vi.mocked(mockApiRouter.routeAPICall)).not.toHaveBeenCalled()
      expect(result).toEqual({ data: 'direct' })
    })

    it('should use direct API call when endpointGroup not specified', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ data: 'direct' })
      })

      const result = await apiRequest('/test-endpoint', {
        useFeatureFlags: true
        // endpointGroup not specified
      })

      expect(mockFetch).toHaveBeenCalled()
      expect(vi.mocked(mockApiRouter.routeAPICall)).not.toHaveBeenCalled()
      expect(result).toEqual({ data: 'direct' })
    })
  })
})
