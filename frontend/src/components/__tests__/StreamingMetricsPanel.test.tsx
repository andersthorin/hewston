// @vitest-environment happy-dom
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import StreamingMetricsPanel from '../StreamingMetricsPanel'
import playbackStore, { PlaybackProvider } from '../../store/playbackClock'

function seedFrameWithMetrics() {
  const ts = '2024-01-01T00:00:00Z'
  // @ts-ignore test shaping
  playbackStore._setFrame({
    t: 'frame', ts, dropped: 0, ohlc: null,
    orders: [], equity: { ts, value: 110 },
    metrics: { total_return_so_far: 0.1, max_drawdown_so_far: 0.02, sharpe_so_far: 1.25 },
  })
}

describe('StreamingMetricsPanel', () => {
  it('renders Performance section and shows mapped metrics', () => {
    seedFrameWithMetrics()
    const { getByText } = render(
      <PlaybackProvider>
        <StreamingMetricsPanel />
      </PlaybackProvider>
    )
    expect(getByText('Performance')).toBeInTheDocument()
    // Total return formatted as percentage
    expect(getByText(/10.0%/)).toBeInTheDocument()
  })
})

