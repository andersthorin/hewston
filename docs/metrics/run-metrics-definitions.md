# Run Metrics Definitions (Authoritative)

Status: v0.1 — Exact formulas and conventions for computed run metrics used in catalog and UI.

## Conventions
- Time base: UTC
- Returns are arithmetic on equity series unless specified
- Prices and equity in base currency (USD)

## Metrics
- total_return
  - Definition: (equity_end / equity_start) - 1
  - Range: [-1, ∞)

- cagr (Compound Annual Growth Rate)
  - Let T_years = (t_end - t_start) / 365.2425 days
  - Definition: (equity_end / equity_start)^(1 / T_years) - 1
  - Edge cases: if equity_end ≤ 0 → undefined; record null

- max_drawdown
  - Definition: max over t of (peak_to_date - equity_t) / peak_to_date
  - Algorithm: track running peak; compute trough ratio; take max

- sharpe
  - Inputs: per-period returns r_t at 1m bar frequency; risk-free r_f = 0 (MVP)
  - Definition: mean(r_t) / stddev(r_t) * sqrt(P), P = periods per year (≈ 252 * 390)
  - Edge cases: stddev=0 → null

- sortino
  - Inputs: downside stddev uses min(r_t, 0)
  - Definition: mean(r_t) / stddev_downside(r_t) * sqrt(P)
  - Edge cases: downside stddev=0 → null

- hit_rate
  - Definition: wins / (wins + losses); win if trade PnL > 0
  - Source: aggregated from fills/orders; define trade as round-trip position

- avg_win, avg_loss
  - Definition: mean PnL over winning trades; mean |PnL| over losing trades
  - Units: currency

- turnover
  - Definition: sum(abs(delta_position) * price) / average_equity
  - Units: 1/time window; report per run (dimensionless)

- slippage_share
  - Definition: (sum(|slippage_amount|)) / (sum(|gross_pnl|) + eps)
  - Where slippage_amount = (fill_price - ref_price) * signed_qty, ref_price = mid ± k_spread*spread_mean

- fees_paid
  - Definition: sum(fee_amount) from fills; fee_amount = notional * fees_bps / 1e4 per side

## Series construction (for metrics)
- equity series: cumulative PnL over time with initial equity normalized to 1.0 (or configured amount)
- r_t: per-minute return = equity_t / equity_{t-1} - 1
- Trading sessions: exclude out-of-session bars; use NASDAQ calendar

## Storage and Precision
- Store metrics in run_metrics table, see scripts/catalog_init.sql
- Use float64 for computations; round to 6 decimals for reporting; store raw where possible

## Validation
- Determinism: repeated runs with identical manifests produce identical metrics within tolerance |Δ| ≤ 0.0005 (0.05%)
- Provide unit tests for formulas with synthetic series

