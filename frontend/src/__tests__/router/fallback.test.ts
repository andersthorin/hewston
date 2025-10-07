import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

// Minimal test to verify env-gated fallback behavior in apiRouter

describe('API Router fallback (env-gated)', () => {
  const mockFetch = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.resetModules()
    vi.unstubAllEnvs()
    mockFetch.mockClear()
    vi.stubGlobal('fetch', mockFetch)
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('does not fallback to backend when BFF fails (policy: no fallbacks)', async () => {
    // Enable BFF and even if env says fallback, we should not fallback
    vi.stubEnv('VITE_BFF_ENABLED', 'true')
    vi.stubEnv('VITE_BFF_CHART_DATA_ENABLED', 'true')
    vi.stubEnv('VITE_BFF_BASE_URL', 'http://127.0.0.1:8001')
    vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:8000')
    vi.stubEnv('VITE_BFF_FALLBACK_ENABLED', 'true')

    // BFF call fails
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 502,
      statusText: 'Bad Gateway',
    } as Response)

    const { apiRouter } = await import('../../utils/apiRouter')
    await expect(
      apiRouter.routeAPICall<any>('chartData', '/chart-data?symbol=AAPL', {
        method: 'GET',
        allowFallback: true,
      }),
    ).rejects.toThrow('HTTP 502')

    // Only one fetch call (to BFF); no backend fallback call
    expect(mockFetch).toHaveBeenCalledTimes(1)
    expect(mockFetch.mock.calls[0][0]).toContain('127.0.0.1:8001')
    expect(mockFetch.mock.calls[0][0]).toContain('/api/v1/chart-data?symbol=AAPL')
  })
})
