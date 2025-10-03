// @vitest-environment happy-dom
import { describe, it, expect } from 'vitest'
import playbackStore, { selectors } from '../playbackClock'

function seedFrame(orders: Array<any>) {
  // @ts-ignore test shape
  playbackStore._setFrame({ t: 'frame', ts: '2024-01-01T00:00:00Z', dropped: 0, ohlc: null, equity: null, orders })
}

describe('Playback Clock symbol focus filtering', () => {
  it('filters markers by focused symbol when markersMeta present', () => {
    seedFrame([
      { ts: '2024-01-01T00:00:00Z', symbol: 'AAPL' },
      { ts: '2024-01-01T00:10:00Z', symbol: 'MSFT' },
      { ts: '2024-01-01T00:20:00Z', symbol: 'AAPL' },
    ])

    // No focus -> all markers
    let all = selectors.filteredMarkers(playbackStore.getState())
    expect(all).toEqual(['2024-01-01T00:00:00Z', '2024-01-01T00:10:00Z', '2024-01-01T00:20:00Z'])

    // Focus AAPL -> only AAPL markers
    // @ts-ignore internal
    playbackStore.setFocus('AAPL')
    let aapl = selectors.filteredMarkers(playbackStore.getState())
    expect(aapl).toEqual(['2024-01-01T00:00:00Z', '2024-01-01T00:20:00Z'])

    // Focus cleared -> back to all
    // @ts-ignore internal
    playbackStore.setFocus(null)
    all = selectors.filteredMarkers(playbackStore.getState())
    expect(all).toEqual(['2024-01-01T00:00:00Z', '2024-01-01T00:10:00Z', '2024-01-01T00:20:00Z'])
  })
})

