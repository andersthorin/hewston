import { describe, it, expect, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { render, screen } from '@testing-library/react'

vi.mock('../../hooks/useRunData', () => ({
  useBacktestDetail: (id: string) => ({
    data: { backtest_id: id, strategy_id: 'sma_crossover', status: 'DONE' },
    isLoading: false,
    isError: false,
    error: undefined,
  }),
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

describe('BacktestDetailView', () => {
  it('shows engine label on DONE', async () => {
    renderAt('/backtests/abc123')
    expect(await screen.findByText(/Engine: Nautilus Trader/)).toBeInTheDocument()
  })
})

