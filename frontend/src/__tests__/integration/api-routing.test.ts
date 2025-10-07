/**
 * Integration tests for API routing with feature flags.
 * Tests that API calls are routed correctly based on feature flag configuration.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

// Mock fetch for integration testing
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

describe('API Routing Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.resetModules()
    vi.unstubAllEnvs()
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('should route to BFF when flags enabled', async () => {
    // Set environment for BFF mode
    vi.stubEnv('VITE_BFF_ENABLED', 'true')
    vi.stubEnv('VITE_BFF_CHART_DATA_ENABLED', 'true')
    vi.stubEnv('VITE_BFF_BASE_URL', 'http://127.0.0.1:8001')
    vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:8000')

    // Import modules after environment setup
    const { apiGetWithFlags } = await import('../../utils/api')

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: 'bff-response' }),
    } as Response)

    await apiGetWithFlags('/bars/daily', 'chartData')

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('127.0.0.1:8001'),
      expect.any(Object),
    )
  })

  it('should route to backend when flags disabled', async () => {
    // Set environment for backend mode
    vi.stubEnv('VITE_BFF_ENABLED', 'false')
    vi.stubEnv('VITE_BFF_CHART_DATA_ENABLED', 'false')
    vi.stubEnv('VITE_BFF_BASE_URL', 'http://127.0.0.1:8001')
    vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:8000')

    // Import modules after environment setup
    const { apiGetWithFlags } = await import('../../utils/api')

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: 'backend-response' }),
    } as Response)

    await apiGetWithFlags('/bars/daily', 'chartData')

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('127.0.0.1:8000'),
      expect.any(Object),
    )
  })

  it('should route run data to BFF when enabled', async () => {
    // Set environment for BFF run data mode
    vi.stubEnv('VITE_BFF_ENABLED', 'true')
    vi.stubEnv('VITE_BFF_RUN_DATA_ENABLED', 'true')
    vi.stubEnv('VITE_BFF_BASE_URL', 'http://127.0.0.1:8001')
    vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:8000')

    // Import modules after environment setup
    const { apiGetWithFlags } = await import('../../utils/api')

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ runs: [] }),
    } as Response)

    await apiGetWithFlags('/backtests', 'runData')

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('127.0.0.1:8001'),
      expect.any(Object),
    )
  })

  it('should handle mixed flag configurations', async () => {
    // Enable BFF but only for chart data, not run data
    vi.stubEnv('VITE_BFF_ENABLED', 'true')
    vi.stubEnv('VITE_BFF_CHART_DATA_ENABLED', 'true')
    vi.stubEnv('VITE_BFF_RUN_DATA_ENABLED', 'false')
    vi.stubEnv('VITE_BFF_BASE_URL', 'http://127.0.0.1:8001')
    vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:8000')

    // Import modules after environment setup
    const { apiGetWithFlags } = await import('../../utils/api')

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: 'response' }),
    } as Response)

    // Chart data should go to BFF
    await apiGetWithFlags('/bars/daily', 'chartData')
    expect(mockFetch).toHaveBeenLastCalledWith(
      expect.stringContaining('127.0.0.1:8001'),
      expect.any(Object),
    )

    // Run data should go to backend
    await apiGetWithFlags('/backtests', 'runData')
    expect(mockFetch).toHaveBeenLastCalledWith(
      expect.stringContaining('127.0.0.1:8000'),
      expect.any(Object),
    )
  })

  it('should handle feature flag evaluation errors gracefully', async () => {
    // Set up environment
    vi.stubEnv('VITE_BFF_ENABLED', 'true')
    vi.stubEnv('VITE_BFF_CHART_DATA_ENABLED', 'true')
    vi.stubEnv('VITE_BFF_BASE_URL', 'http://127.0.0.1:8001')
    vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:8000')

    // Import modules after environment setup
    const { apiGetWithFlags } = await import('../../utils/api')

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: 'response' }),
    } as Response)

    // Should not throw even with invalid flag name
    await expect(apiGetWithFlags('/some/endpoint', 'invalidFlag' as any)).resolves.toBeDefined()
  })
})
