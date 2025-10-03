import React from 'react'
import { describe, it, expect, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { render, screen } from '@testing-library/react'

vi.mock('../../hooks/useRunData', () => ({
  useBacktestDetail: (id: string) => ({
    data: { backtest_id: id, strategy_id: 'sma_crossover', status: 'ERROR', error_message: 'ImportError: nautilus-trader not installed' },
    isLoading: false,
    isError: false,
    error: undefined,
  }),
}))

vi.mock('../../containers/RunPlayerContainer', () => ({
  default: () => <div data-testid="player-stub" />,
}))


import BacktestDetailView from '../BacktestDetail'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/backtests/:backtest_id" element={<BacktestDetailView />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('BacktestDetailView (error)', () => {
  it('shows error banner and hides playback on ERROR', async () => {
    renderAt('/backtests/err1')
    expect(await screen.findByText(/Backtest failed to start:/)).toBeInTheDocument()
    // The RunPlayerContainer renders a Transport label; ensure it is not present
    expect(screen.queryByText(/Transport:/)).toBeNull()
  })
})

