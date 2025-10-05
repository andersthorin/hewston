import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'

import { MetricsSummary } from '../metrics-summary'

describe('MetricsSummary', () => {
  it('renders key metrics with formatting', () => {
    render(<MetricsSummary metrics={{ total_return: 0.123, return: 0.01, win_rate: 0.56, max_drawdown: -0.08, sharpe_ratio: 1.23, realized_pnl: 1234.56 }} />)
    expect(screen.getByText('Performance')).toBeInTheDocument()
    expect(screen.getByText('Total return')).toBeInTheDocument()
    expect(screen.getByText('12.3%')).toBeInTheDocument()
    expect(screen.getByText('Return (bar)')).toBeInTheDocument()
    expect(screen.getByText('1.0%')).toBeInTheDocument()
    expect(screen.getByText('Win rate')).toBeInTheDocument()
    expect(screen.getByText('56.0%')).toBeInTheDocument()
    expect(screen.getByText('Max drawdown')).toBeInTheDocument()
    expect(screen.getByText('-8.0%')).toBeInTheDocument()
    expect(screen.getByText('Sharpe')).toBeInTheDocument()
    expect(screen.getByText('1.23')).toBeInTheDocument()
    expect(screen.getByText('Realized PnL')).toBeInTheDocument()
    expect(screen.getByText('$1,234.56')).toBeInTheDocument()
  })

  it('renders placeholders when metrics missing', () => {
    render(<MetricsSummary metrics={{}} />)
    // There are multiple '—' cells; check at least one is present
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
  })
})

