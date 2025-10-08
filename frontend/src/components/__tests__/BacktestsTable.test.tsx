/** @vitest-environment happy-dom */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BacktestsTable, type BacktestSummaryRow } from '../BacktestsTable'
import React from 'react'

function row(overrides: Partial<BacktestSummaryRow> = {}): BacktestSummaryRow {
  return {
    backtest_id: 'bt_1',
    created_at: '2025-01-01T00:00:00Z',
    strategy_id: 'sma',
    status: 'DONE',
    symbol: 'BTCUSDT',
    run_from: '2024-01-01',
    run_to: '2024-12-31',
    duration_ms: 1234,
    total_return: 0.1234,
    max_drawdown: -0.055,
    sharpe_ratio: 1.23,
    win_rate: 0.55,
    ...overrides,
  }
}

describe('BacktestsTable', () => {
  it('renders placeholder when no items', () => {
    render(<BacktestsTable items={[]} />)
    expect(screen.getByText(/No backtests yet/i)).toBeInTheDocument()
  })

  it('shows queued/running badges and hides View until terminal', () => {
    const items: BacktestSummaryRow[] = [
      row({ status: 'QUEUED' }),
      row({ status: 'RUNNING', backtest_id: 'bt_2' }),
    ]
    render(<BacktestsTable items={items} />)
    expect(screen.getAllByText('Queued').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Running').length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: /view/i })).not.toBeInTheDocument()
  })

  it('shows View button when DONE and calls onView', async () => {
    const onView = vi.fn()
    render(<BacktestsTable items={[row({ status: 'DONE' })]} onView={onView} />)
    const btn = await screen.findByRole('button', { name: /view/i })
    await userEvent.click(btn)
    expect(onView).toHaveBeenCalledWith('bt_1')
  })

  it('renders metrics only when terminal, with formatting', () => {
    const { rerender } = render(<BacktestsTable items={[row({ status: 'QUEUED' })]} />)
    // Placeholders
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)

    rerender(<BacktestsTable items={[row({ status: 'DONE' })]} />)
    // Total return as percentage
    expect(screen.getByText('12.34%')).toBeInTheDocument()
    // Max drawdown as percentage
    expect(screen.getByText('-5.50%')).toBeInTheDocument()
    // Sharpe with 2 decimals
    expect(screen.getByText('1.23')).toBeInTheDocument()
    // Win rate as percentage with 1 decimal
    expect(screen.getByText('55.0%')).toBeInTheDocument()
  })

  it('has aria-live on status badge for polite updates', () => {
    render(<BacktestsTable items={[row({ status: 'RUNNING' })]} />)
    const badge = screen.getByText('Running')
    expect(badge.getAttribute('aria-live')).toBe('polite')
  })
})
