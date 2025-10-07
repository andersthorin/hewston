# Epic 13 — Acceptance Checklist: Relevant Backtest Metrics with Playback

Status: Complete
Owner: QA
Related: Epic 13; Stories 13.1, 13.2, 13.3

## A. Source Integrity
- [x] Metrics derived only from Nautilus outputs (returns, equity, realized PnL; optional analyzer stats)
- [x] Bar interval recorded in manifest; annualization factor P derived correctly
- [x] Currency fixed to USD for realized PnL

## B. Correctness (Cumulative-to-date)
- [x] return_t = equity_t / equity_{t-1} - 1
- [x] total_return_t = equity_t / equity_0 - 1
- [x] drawdown_t = (peak_to_date - equity_t) / peak_to_date (≥ 0)
- [x] sharpe_t = sqrt(P) × mean(r_1..t) / std(r_1..t) with r_f = 0; std=0 ⇒ null
- [x] win_rate_t from realized PnL deltas (Δ>0 win; Δ<0 loss; Δ=0 ignored)

## C. Determinism & Stability
- [x] Re-running on identical inputs yields identical metrics within tolerance (≤ 1e-9)
- [x] Playback shows identical sequences over repeated replays
- [x] Missing data handled gracefully (nulls, not errors)

## D. Performance & Compatibility
- [x] Frame latency budget maintained; FPS target unchanged
- [x] StreamFrame `metrics` is optional and additive (older clients OK)
- [x] Metrics artifact size reasonable (<5 MB typical; warn if larger)

## E. UX & Accessibility
- [x] Frontend shows values in readable formats (%, decimals, currency)
- [x] No sorting/filtering added in this epic
- [x] Keyboard/ARIA unaffected; metrics region readable with reduced motion

## F. Documentation & Traceability
- [x] docs/api/openapi.yaml updated with StreamFrame.metrics schema
- [x] docs/front-end-spec.md updated with Playback Metrics Panel
- [x] Stories trace to this checklist and to tests

