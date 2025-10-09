# UX Copy — Agentic Plan Preview and Duplicate Handling

Plan Preview (collapsed summary)
- "Agentic Mode will auto-select symbols and strategies for your date range within guardrails."

Plan Preview (expanded)
- "Included symbols" (badges): e.g., AAPL, MSFT, GOOG
- "Excluded symbols" with reasons:
  - TSLA — COVERAGE_LOW (observed 15/22 trading days; missing: 2024-10-05, ...)
- Strategies & params table (defaults shown)
- Guardrail checks: Pass/Fail with tooltips (coverage, min trades, turnover, max DD, no NaNs)

Start button states
- Enabled: all guardrails pass
- Disabled: guardrails failed — hover shows primary reason(s)

Duplicate plan handling
- Message: "This plan was already submitted. Opening the existing run(s)."
- Action: Navigate to existing run list/detail; no new jobs queued

Consent (first-time)
- Title: "Agentic Auto-Selection"
- Body: "I understand this will auto-select universe and strategies within guardrails."
- CTA: "I Agree"

