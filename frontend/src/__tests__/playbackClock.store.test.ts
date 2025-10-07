import { describe, it, expect, vi } from 'vitest'
import playbackStore, { selectors } from '../store/playbackClock'

const makeFrame = (ts: string) =>
  ({
    t: 'frame',
    ts,
    dropped: 0,
    ohlc: null,
    orders: [{ ts_utc: ts }],
    equity: { ts, value: 100 },
  }) as any

describe('playbackClock store', () => {
  it('subscribes and updates currentSimTime on frame', () => {
    let notified = 0
    const unsub = playbackStore.subscribe(() => {
      notified += 1
    })
    playbackStore._setFrame(makeFrame('2024-01-01T00:00:00Z'))
    expect(notified).toBe(1)
    const s = playbackStore.getState()
    expect(selectors.currentTs(s)).toBe('2024-01-01T00:00:00Z')
    expect(selectors.markers(s).length).toBeGreaterThan(0)
    unsub()
  })

  it('setControls wires through play/pause/seek', () => {
    const play = vi.fn()
    const pause = vi.fn()
    const seek = vi.fn()
    playbackStore.setControls({ play, pause, seek })
    playbackStore.play()
    playbackStore.pause()
    playbackStore.seek('2024-01-01T00:01:00Z')
    expect(play).toHaveBeenCalled()
    expect(pause).toHaveBeenCalled()
    expect(seek).toHaveBeenCalledWith('2024-01-01T00:01:00Z')
  })
})
