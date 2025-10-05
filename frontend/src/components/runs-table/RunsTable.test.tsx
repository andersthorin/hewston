import React from 'react'
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import RunsTable from './RunsTable'
import type { RunSummary } from '../../services/api'

function makeItem(partial: Partial<RunSummary> = {}): RunSummary {
  return {
    run_id: partial.run_id ?? 'r1',
    created_at: partial.created_at ?? '2025-01-01T00:00:00Z',
    strategy_id: partial.strategy_id ?? 'sma_crossover',
    status: partial.status ?? 'DONE',
    symbol: partial.symbol ?? 'AAPL',
    run_from: ('run_from' in partial) ? partial.run_from : '2024-10-01',
    run_to: ('run_to' in partial) ? partial.run_to : '2024-10-31',
    duration_ms: ('duration_ms' in partial) ? partial.duration_ms : 1234,
  }
}

describe('RunsTable', () => {
  it('renders run_from/run_to from manifest fields', () => {
    const items: RunSummary[] = [makeItem({ run_id: 'r1' })]
    render(<RunsTable items={items} />)
    expect(screen.getByText('2024-10-01')).toBeInTheDocument()
    expect(screen.getByText('2024-10-31')).toBeInTheDocument()
  })

  it('shows — when run_from/run_to are missing (no incorrect fallback)', () => {
    const items: RunSummary[] = [makeItem({ run_id: 'r2', run_from: undefined, run_to: undefined })]
    render(<RunsTable items={items} />)
    // two em dashes for the two cells
    const dashes = screen.getAllByText('—')
    expect(dashes.length).toBeGreaterThanOrEqual(2)
  })
})

