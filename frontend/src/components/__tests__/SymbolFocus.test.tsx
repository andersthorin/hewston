// @vitest-environment happy-dom
import { describe, it, expect } from 'vitest'
import { render, fireEvent, screen } from '@testing-library/react'
import SymbolFocus from '../SymbolFocus'
import playbackStore, { PlaybackProvider } from '../../store/playbackClock'

describe('SymbolFocus', () => {
  it('lists seen symbols and updates focus on change', async () => {
    // Seed symbols
    // @ts-ignore internal test shaping
    playbackStore._addSymbols(['AAPL', 'MSFT'])

    render(
      <PlaybackProvider>
        <SymbolFocus />
      </PlaybackProvider>
    )

    // Should include All + seeded symbols
    expect(screen.getByRole('combobox')).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'All' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'AAPL' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'MSFT' })).toBeInTheDocument()

    // Change to AAPL
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'AAPL' } })
    // @ts-ignore test access to state
    expect(playbackStore.getState().focusedSymbol).toBe('AAPL')
  })
})

