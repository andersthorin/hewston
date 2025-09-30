import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import MetricsSummary from '../MetricsSummary'

describe('MetricsSummary', () => {
  it('renders key metrics with formatting', () => {
    render(<MetricsSummary metrics={{ total_return: 0.123, win_rate: 0.56, max_drawdown: -0.08, sharpe_ratio: 1.23, profit_factor: 1.75, total_trades: 42 }} />)
    expect(screen.getByText('Performance')).toBeInTheDocument()
    expect(screen.getByText('Total return')).toBeInTheDocument()
    expect(screen.getByText('12.3%')).toBeInTheDocument()
    expect(screen.getByText('Win rate')).toBeInTheDocument()
    expect(screen.getByText('56.0%')).toBeInTheDocument()
    expect(screen.getByText('Max drawdown')).toBeInTheDocument()
    expect(screen.getByText('-8.0%')).toBeInTheDocument()
    expect(screen.getByText('Sharpe')).toBeInTheDocument()
    expect(screen.getByText('1.23')).toBeInTheDocument()
    expect(screen.getByText('Profit factor')).toBeInTheDocument()
    expect(screen.getByText('1.75')).toBeInTheDocument()
    expect(screen.getByText('Trades')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
  })

  it('renders placeholders when metrics missing', () => {
    render(<MetricsSummary metrics={{}} />)
    // There are multiple '—' cells; check at least one is present
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
  })
})

