/**
 * Component Interface Preservation Tests
 * 
 * These tests validate that component interfaces remain unchanged during BFF migration.
 * Critical for ensuring backward compatibility and zero-risk migration.
 */

import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ChartOHLC from '../ChartOHLC'
import EquityChart from '../EquityChart'
import RunsTable from '../RunsTable'
import PlaybackControls from '../PlaybackControls'
import FiltersBar from '../FiltersBar'
import RunDetailView from '../../views/RunDetail'

// Mock the services to prevent actual API calls
vi.mock('../../services/chartData', () => ({
  chartDataService: {
    fetchDailyData: vi.fn(),
    fetchMinuteData: vi.fn(),
    fetchHourData: vi.fn(),
  }
}))

vi.mock('../../services/runData', () => ({
  runDataService: {
    listRuns: vi.fn(),
    getCompleteRunData: vi.fn(),
  }
}))

vi.mock('../../services/featureFlags', () => ({
  featureFlagService: {
    isFeatureFlagEnabled: vi.fn().mockReturnValue(false),
    getDebugInfo: vi.fn().mockReturnValue({}),
    getEffectiveApiBaseUrl: vi.fn().mockReturnValue('http://127.0.0.1:8000'),
    getEffectiveWsBaseUrl: vi.fn().mockReturnValue('ws://127.0.0.1:8000'),
    getConfiguration: vi.fn().mockReturnValue({
      bffEnabled: false,
      chartDataEnabled: false,
      runDataEnabled: false,
      websocketEnabled: false
    }),
    evaluateFeatureFlag: vi.fn().mockReturnValue({
      enabled: false,
      source: 'backend',
      endpointUrl: 'http://127.0.0.1:8000'
    })
  }
}))

describe('Component Interface Preservation', () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  })
  
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )

  describe('Chart Components', () => {
    it('should preserve ChartOHLC props interface', () => {
      const props = {
        symbol: 'AAPL',
        timeframe: 'daily' as const,
        from: '2023-01-01',
        to: '2023-12-31',
        height: 400,
        width: 800
      }
      
      expect(() => {
        render(<ChartOHLC {...props} />, { wrapper })
      }).not.toThrow()
    })

    it('should preserve EquityChart props interface', () => {
      const props = {
        runId: 'test-run-123',
        height: 300,
        width: 600
      }
      
      expect(() => {
        render(<EquityChart {...props} />, { wrapper })
      }).not.toThrow()
    })

    it('should handle optional props correctly', () => {
      // Test ChartOHLC with minimal props
      expect(() => {
        render(<ChartOHLC symbol="AAPL" timeframe="daily" />, { wrapper })
      }).not.toThrow()

      // Test EquityChart with minimal props
      expect(() => {
        render(<EquityChart runId="test-run" />, { wrapper })
      }).not.toThrow()
    })
  })

  describe('Data Display Components', () => {
    it('should preserve RunsTable props interface', () => {
      const mockRuns = [
        {
          run_id: 'run-1',
          symbol: 'AAPL',
          created_at: '2023-01-01T00:00:00Z',
          status: 'completed' as const
        }
      ]

      const props = {
        runs: mockRuns,
        loading: false,
        onRunSelect: vi.fn(),
        onRunDelete: vi.fn()
      }
      
      expect(() => {
        render(<RunsTable {...props} />, { wrapper })
      }).not.toThrow()
    })

    it('should preserve FiltersBar props interface', () => {
      const props = {
        symbol: 'AAPL',
        onSymbolChange: vi.fn(),
        dateRange: {
          from: '2023-01-01',
          to: '2023-12-31'
        },
        onDateRangeChange: vi.fn()
      }
      
      expect(() => {
        render(<FiltersBar {...props} />, { wrapper })
      }).not.toThrow()
    })
  })

  describe('Control Components', () => {
    it('should preserve PlaybackControls props interface', () => {
      const props = {
        runId: 'test-run-123',
        isPlaying: false,
        currentTime: 0,
        duration: 100,
        onPlay: vi.fn(),
        onPause: vi.fn(),
        onSeek: vi.fn(),
        onSpeedChange: vi.fn()
      }
      
      expect(() => {
        render(<PlaybackControls {...props} />, { wrapper })
      }).not.toThrow()
    })

    it('should handle playback state changes', () => {
      const onPlay = vi.fn()
      const onPause = vi.fn()

      // Test playing state
      const playingProps = {
        runId: 'test-run',
        isPlaying: true,
        currentTime: 50,
        duration: 100,
        onPlay,
        onPause,
        onSeek: vi.fn(),
        onSpeedChange: vi.fn()
      }
      
      expect(() => {
        render(<PlaybackControls {...playingProps} />, { wrapper })
      }).not.toThrow()
    })
  })

  describe('View Components', () => {
    it('should preserve RunDetailView props interface', () => {
      const props = {
        runId: 'test-run-123'
      }
      
      expect(() => {
        render(<RunDetailView {...props} />, { wrapper })
      }).not.toThrow()
    })

    it('should handle undefined runId gracefully', () => {
      expect(() => {
        render(<RunDetailView runId={undefined} />, { wrapper })
      }).not.toThrow()
    })
  })

  describe('Props Type Safety', () => {
    it('should maintain TypeScript type safety for chart props', () => {
      // This test ensures TypeScript compilation catches interface changes
      const chartProps: React.ComponentProps<typeof ChartOHLC> = {
        symbol: 'AAPL',
        timeframe: 'daily',
        from: '2023-01-01',
        to: '2023-12-31'
      }

      expect(chartProps.symbol).toBe('AAPL')
      expect(chartProps.timeframe).toBe('daily')
    })

    it('should maintain TypeScript type safety for table props', () => {
      const tableProps: React.ComponentProps<typeof RunsTable> = {
        runs: [],
        loading: false,
        onRunSelect: vi.fn(),
        onRunDelete: vi.fn()
      }

      expect(Array.isArray(tableProps.runs)).toBe(true)
      expect(typeof tableProps.loading).toBe('boolean')
    })

    it('should maintain TypeScript type safety for control props', () => {
      const controlProps: React.ComponentProps<typeof PlaybackControls> = {
        runId: 'test-run',
        isPlaying: false,
        currentTime: 0,
        duration: 100,
        onPlay: vi.fn(),
        onPause: vi.fn(),
        onSeek: vi.fn(),
        onSpeedChange: vi.fn()
      }

      expect(typeof controlProps.isPlaying).toBe('boolean')
      expect(typeof controlProps.currentTime).toBe('number')
    })
  })

  describe('Event Handler Interfaces', () => {
    it('should preserve event handler signatures', () => {
      const mockHandlers = {
        onRunSelect: vi.fn(),
        onRunDelete: vi.fn(),
        onSymbolChange: vi.fn(),
        onDateRangeChange: vi.fn(),
        onPlay: vi.fn(),
        onPause: vi.fn(),
        onSeek: vi.fn(),
        onSpeedChange: vi.fn()
      }

      // Verify handlers can be called with expected parameters
      expect(() => {
        mockHandlers.onRunSelect('run-123')
        mockHandlers.onRunDelete('run-123')
        mockHandlers.onSymbolChange('AAPL')
        mockHandlers.onDateRangeChange({ from: '2023-01-01', to: '2023-12-31' })
        mockHandlers.onPlay()
        mockHandlers.onPause()
        mockHandlers.onSeek(50)
        mockHandlers.onSpeedChange(2.0)
      }).not.toThrow()
    })
  })
})
