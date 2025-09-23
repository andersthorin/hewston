# Wireframe — Runs List

Status: v0.1 (UX)

## Layout (Normal)
- Header
  - Title: Runs
  - Filters: symbol (input), strategy (select)
  - Actions: Create baseline run (button)
- Table (20 per page)
  - Columns: run_id, created_at, strategy_id, status, symbol, from, to, duration_ms, action
  - Row action: View → navigates to /runs/{run_id}
- Footer
  - Pagination: prev/next, page size

## Loading
- Replace table with 10 skeleton rows (monospace widths aligned to columns)

## Empty
- Illustration/placeholder
- Message: “No runs yet.”
- CTA: Create baseline run

## Error
- Banner: “Error loading runs” + error code/message
- Retry button

## Interaction notes
- Filters debounce 300ms; Enter key focuses table
- Table rows keyboard navigable; Enter opens detail
- Responsive: Filters wrap on mobile; table scrolls horizontally if needed

