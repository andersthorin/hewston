// @vitest-environment happy-dom
import { describe, it, expect } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import TimelineScrubber from '../TimelineScrubber'
import playbackStore, { PlaybackProvider } from '../../store/playbackClock'

describe('TimelineScrubber', () => {
  it('renders and seeks on click', () => {
    const seekCalls: string[] = []
    playbackStore.setControls({ play: () => {}, pause: () => {}, seek: (ts) => { seekCalls.push(ts) } })
    // seed range and current
    // @ts-ignore
    playbackStore._setRange({ start: '2024-01-01T00:00:00Z', end: '2024-01-01T01:00:00Z' })
    // @ts-ignore
    playbackStore._setFrame({ t: 'frame', ts: '2024-01-01T00:00:00Z', dropped: 0, orders: [], ohlc: null, equity: { ts: '2024-01-01T00:00:00Z', value: 100 } })

    const { getByRole } = render(
      <PlaybackProvider>
        <TimelineScrubber />
      </PlaybackProvider>
    )
    const slider = getByRole('slider')
    fireEvent.click(slider, { clientX: (slider as any).getBoundingClientRect().left + 10 })
    expect(seekCalls.length).toBeGreaterThan(0)
  })
})

