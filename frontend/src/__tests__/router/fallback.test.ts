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

  it('falls back to backend when BFF fails and VITE_BFF_FALLBACK_ENABLED=true', async () => {
    // Enable BFF and fallback
    vi.stubEnv('VITE_BFF_ENABLED', 'true')
    vi.stubEnv('VITE_BFF_CHART_DATA_ENABLED', 'true')
    vi.stubEnv('VITE_BFF_BASE_URL', 'http://127.0.0.1:8001')
    vi.stubEnv('VITE_API_BASE_URL', 'http://127.0.0.1:8000')
    vi.stubEnv('VITE_BFF_FALLBACK_ENABLED', 'true')

    // First call (BFF) fails
    mockFetch
      .mockResolvedValueOnce({ ok: false, status: 502, statusText: 'Bad Gateway' } as Response)
      // Second call (backend) succeeds
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ ok: true }) } as Response)

    const { apiRouter } = await import('../../utils/apiRouter')
    const result = await apiRouter.routeAPICall<any>('chartData', '/chart-data?symbol=AAPL', {
      method: 'GET',
      allowFallback: true,
    })

    // Two fetch calls: first to BFF, second to backend
    expect(mockFetch).toHaveBeenCalledTimes(2)
    expect(mockFetch.mock.calls[0][0]).toContain('127.0.0.1:8001')
    expect(mockFetch.mock.calls[0][0]).toContain('/api/v1/chart-data?symbol=AAPL')

    expect(mockFetch.mock.calls[1][0]).toContain('127.0.0.1:8000')
    // Backend-mapped path should be /bars
    expect(mockFetch.mock.calls[1][0]).toContain('/bars?symbol=AAPL')

    expect(result).toEqual({ ok: true })
  })
})

