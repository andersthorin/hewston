# Hewston UI/UX Specification

Status: v0.1 (UX Expert) — Draft grounded in PRD, Architecture, Baselines, and Protocols.

## Introduction
This document defines user experience goals, information architecture, flows, wireframes, component inventory, accessibility, responsiveness, and performance considerations for Hewston’s Playback UI (Runs List and Run Detail). It aligns with presentational-only components and backend contracts.

## Overall UX Goals & Principles
- Target Persona: Owner‑Operator (single technical user on Apple Silicon); prioritizes speed, determinism, and clarity
- Usability Goals
  - Time‑to‑first‑insight: create→run→review in ≤ 2 minutes (cached data)
  - Immediate controls: no nested menus; keyboard shortcuts for play/pause/seek/speed
  - Error transparency: canonical error codes surfaced with actionable messages
- Design Principles
  - Clarity over cleverness; data‑first UI
  - Determinism‑first: reflect immutable artifacts; no hidden recomputation
  - Presentational‑only components; logic in containers/hooks/services
  - Fast feedback loops; visible playback state and dropped counter
  - Accessible by default (keyboard, contrast)

## Information Architecture (IA)
- Screens
  - Runs List (default)
  - Run Detail (open specific run)
  - Optional: Data Status (read‑only), Settings (local)
- Navigation
  - Primary: minimal top bar (Runs, optional Data Status/Settings)
  - Secondary: none; Run Detail may use in‑view tabs/anchors (Overview | Playback)
  - Breadcrumbs: not required (flat hierarchy)

## User Flows
- Create Run
  - Goal: submit baseline backtest; receive run_id
  - Entry: Runs List button; CLI exists (Makefile)
  - Success: 202 QUEUED or 200 EXISTS; row appears
  - Errors: VALIDATION, IDP_CONFLICT/CONFLICT, DATASET_NOT_FOUND
- Open Run Detail + Playback
  - Goal: inspect run and stream time‑compressed playback
  - Entry: click row in Runs List
  - Success: metadata loads; WS connects; frames stream; controls respond
  - Errors: RUN_NOT_FOUND; RANGE on bad seek; WS drop → SSE fallback
- Rerun from Manifest
  - Goal: reproduce inputs (optionally tweak speed/seed/params)
  - Entry: button in Run Detail; prefill from run_manifest.json

## Wireframes & Mockups (to be linked)
- Primary design files: (add Figma link)
- Runs List
  - Header: title “Runs”, filters (symbol, from, to, strategy), “Create baseline run”
  - Table: created_at, symbol, from, to, strategy_id, status, duration_ms
  - States: loading (skeleton rows), empty (CTA), error (code + retry)
- Run Detail
  - Header: run_id, status pill, “Rerun from manifest”
  - Meta: symbol, date range, strategy/params, seed, created_at
  - Controls: play/pause, seek, speed select (30/60/120)
  - Charts: OHLC (Lightweight Charts); overlays toggles (orders, fills); equity chart
  - Indicators: dropped counter; connection status (WS / SSE fallback)
  - States: loading, RUN_NOT_FOUND, waiting, playing, paused, end

## Component Library / Design System
- Approach: Tailwind CSS 4 utilities + small custom components
- Core Components
  - Button (primary/secondary/icon; default/hover/active/disabled/loading)
  - Input (text/date/select; default/focus/error)
  - Table (simple/sortable; loading skeleton/empty)
  - Badge/Pill (status: QUEUED/RUNNING/DONE/ERROR)
  - Chart wrappers: OHLCChart, EquityChart (props‑driven, presentational)
  - Playback Controls: PlayPauseButton, SpeedSelect, SeekBar (states by stream)

## Branding & Style Guide (pragmatic defaults)
- Visual Identity: technical, minimal, legible; no bespoke brand
- Colors (accessible defaults)
  - Primary #2563EB; Secondary #64748B; Accent #06B6D4; Success #16A34A; Warning #F59E0B; Error #DC2626; Neutral: #0F172A/#1E293B + light
- Typography: System UI stack; Mono for IDs/logs (ui‑monospace/SFMono)
- Layout: 12‑col grid; max width ~1200px desktop; spacing = Tailwind 4 scale (prefer 8px multiples)

## Accessibility Requirements
- Target: Pragmatic WCAG 2.1 AA where feasible
- Visual: contrast AA; visible focus rings; scalable text
- Interaction: full keyboard operability; shortcuts; aria labels; live region for status/errors
- Content: alt text/aria‑described summaries for charts; semantic headings; labeled forms
- Testing: ESLint a11y, keyboard‑only traversal, reduced‑motion checks, readable WS error toasts

## Responsiveness Strategy
- Breakpoints: Mobile 0–639; Tablet 640–1023; Desktop 1024–1439; Wide 1440+
- Adaptation
  - Layout: single‑column (mobile); stacked charts (tablet); side‑by‑side OHLC+equity (desktop)
  - Navigation: minimal; overflow menu on mobile
  - Priority: controls → chart → overlays/equity; collapse metadata under header on small screens

## Animation & Micro‑interactions
- Principles: informative; never block; honor prefers‑reduced‑motion
- Interactions: play/pause icon micro‑transition (≤150ms); seek highlight pulse (≤120ms);
  WS error/fallback toast (≤200ms); skeleton shimmer (≤800ms linear)

## Performance Considerations
- Goals: first interactive ≤ 2s desktop; control→effect ≤ 100ms median; target 60 FPS
- Strategies: Worker for WS/SSE parsing; server‑side decimation; render visible window; coalesce updates; virtualize tables; debounce filters; cache via TanStack Query; memoize props

## References
- Baselines: docs/prd/features/00-baselines.md
- API: docs/api/openapi.yaml; Errors: docs/api/error-codes.md; Protocol: docs/api/ws-protocol.md
- Architecture: docs/architecture.md; FE boundaries: docs/architecture/source-tree.md; Coding: docs/architecture/coding-standards.md
- UX User Journey: docs/ux/user-journey.md

## Next Steps
1) Create docs/ui/wireframes/ and add Runs List and Run Detail wireframes (normal/loading/error/empty)
2) Write docs/frontend/component-map.md defining presentational components and prop contracts
3) Confirm accessibility and responsive targets with PO/QA; review with Architect for protocol/contract alignment

