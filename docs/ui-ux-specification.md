# UI/UX Specification

**Status**: v1.0 — Consolidated UI/UX documentation for Hewston trading platform  
**Last Updated**: 2025-01-27

## Table of Contents

1. [User Journey & Flows](#1-user-journey--flows)
2. [Component Architecture Map](#2-component-architecture-map)
3. [Wireframes & Layouts](#3-wireframes--layouts)
4. [Design System Guidelines](#4-design-system-guidelines)

---

## 1. User Journey & Flows

**Purpose**: End-to-end flow aligning frontend/backend with API contracts.

### Primary Flow: Create → List → Detail → Playback → Rerun

#### 1. Create Run (Backend/API)
- **Endpoint**: `POST /backtests`
- **Payload**: `{ dataset_id OR (symbol, from, to), strategy_id, params, seed, slippage_fees, speed }`
- **Response**: 
  - `202 { run_id, status: "QUEUED" }` (new run)
  - `200 { run_id, status: "EXISTS" }` (existing run)
- **Error codes**: VALIDATION, CONFLICT, IDP_CONFLICT
- **Artifacts path**: `data/backtests/{run_id}/`

#### 2. List Runs (UI: Runs List)
- **Endpoint**: `GET /backtests?symbol=&from=&to=&strategy_id=&limit=&offset=`
- **Display**: Table with symbol, date range, strategy, status, created_at, duration
- **States**: 
  - **Empty**: Guidance to create a run
  - **Error**: Render error code/message

#### 3. View Run (UI: Run Detail)
- **Endpoint**: `GET /backtests/{id}` → metadata and artifact refs
- **Display**: Equity chart, overlays for orders/fills (when available)
- **Actions**: Connect to playback; rerun from manifest

#### 4. Playback (WebSocket Primary; SSE Fallback)
- **WebSocket**: `GET /backtests/{id}/ws`
  - **Control**: `ctrl (play/pause/seek/speed)`
  - **Frames**: `ohlc, orders, equity, dropped`
  - **Events**: `hb, end, err`
- **SSE**: `GET /backtests/{id}/stream?speed=60`
  - **Event**: `frame` with StreamFrame payload
- **Performance Targets**: 
  - Avg ≈30 FPS
  - p95 dropped ≤5%
  - p99 latency ≤200 ms

#### 5. Rerun from Manifest (UI Action)
- Read `run_manifest.json`
- Prefill `POST /backtests` body
- Submit to create new run

### UI States to Design
- **Runs List**: normal, empty, loading, error
- **Run Detail**: loading metadata, error (RUN_NOT_FOUND), waiting for playback, playing, paused, end
- **Controls**: play/pause, seek, speed; show error toast on `{t:"err"}`

---

## 2. Component Architecture Map

**Purpose**: Current implementation structure following architectural principles.

### Architecture Principles
- **Presentational components only** (no fetch/mutate/side effects)
- **Containers/services/hooks** own data fetching and state management
- **Type-safe props** with TypeScript and Zod validation
- **Imperative chart APIs** for performance-critical chart operations

### Core UI Components

#### RunsTable
- **Props**: `{ items: RunSummary[], onView?: (run_id: string) => void }`
- **Features**: Displays run list with standardized `run_from`/`run_to` fields
- **States**: loading, empty, error (handled by container)

#### FiltersBar
- **Props**: `{ initial: FilterState, onApply: (filters: FilterState) => void }`
- **Features**: Symbol, strategy, date range filtering

#### PlaybackControls
- **Props**: `{ playing: boolean, speed: number, onPlay: () => void, onPause: () => void, onSpeedChange: (speed: number) => void }`
- **Features**: Play/pause, speed control for backtesting playback

### Chart Components (Imperative APIs)

#### ChartOHLC
- **Props**: `{ height?: number, onReady?: (api: CandlestickChartAPI) => void }`
- **Features**: TradingView Lightweight Charts integration, imperative API for performance
- **API**: `updateCandles()`, `updateOrders()`, `setVisibleRange()`, `scrollToTime()`

#### EquityChart
- **Props**: `{ height?: number, onReady?: (api: EquityChartAPI) => void }`
- **Features**: Equity curve visualization with imperative updates
- **API**: `updateEquity()`, `setVisibleRange()`, `scrollToTime()`

### Containers & Views (Data Layer)

#### Containers
- **RunsListContainer**
  - **Uses**: `@tanstack/react-query` for data fetching, `services/api.listBacktests`
  - **Features**: Pagination, filtering, create run functionality
  - **Manages**: Loading states, error handling, query parameters

- **RunPlayerContainer**
  - **Uses**: `services/ws.useRunPlayback` for WebSocket streaming
  - **Features**: Real-time playback control, frame streaming, chart coordination
  - **Manages**: WebSocket connection, playback state, chart API refs

#### Views
- **RunDetailView**
  - **Route**: `/runs/:run_id`
  - **Features**: Run metadata display, embedded RunPlayerContainer
  - **Uses**: `useQuery` for run details, `useParams` for routing

### TypeScript Types (Post-Standardization)

#### API Types (Zod-validated)
```typescript
RunSummary: {
  run_id: string
  created_at: string
  strategy_id: string
  status: string
  symbol?: string | null
  run_from?: string | null  // Standardized field name
  run_to?: string | null    // Standardized field name
  duration_ms?: number | null
}

RunDetail: {
  run_id: string
  dataset_id?: string | null
  strategy_id: string
  status: string
  code_hash?: string | null
  seed?: number | null
  speed?: number | null
  duration_ms?: number | null
  params?: Record<string, any> | null
  slippage_fees?: Record<string, any> | null
  artifacts?: ArtifactsType | null
  manifest?: ManifestType | null
  run_from?: string | null  // Enriched from run manifest
  run_to?: string | null    // Enriched from run manifest
}
```

#### Streaming Types
```typescript
StreamFrameData: {
  t: 'frame'
  ts: string
  ohlc?: OHLCData | null
  orders: OrderData[]
  equity?: EquityData | null
  dropped: number
}

OrderData: {
  ts: string
  side: 'BUY' | 'SELL'
  qty: number
  price: number
  id: string
}
```

#### Chart API Types
```typescript
CandlestickChartAPI: {
  updateCandles: (candles: CandleData[]) => void
  updateOrders: (orders: OrderData[]) => void
  setVisibleRange: (range: TimeRange) => void
  scrollToTime: (time: string) => void
}

EquityChartAPI: {
  updateEquity: (points: EquityPoint[]) => void
  setVisibleRange: (range: TimeRange) => void
  scrollToTime: (time: string) => void
}
```

### File Structure (Current Implementation)
```
frontend/src/
├── components/           # Presentational components
│   ├── ChartOHLC.tsx    # Candlestick chart with imperative API
│   ├── EquityChart.tsx  # Equity curve chart
│   ├── FiltersBar.tsx   # Run filtering UI
│   ├── PlaybackControls.tsx # Playback control buttons
│   └── RunsTable.tsx    # Runs list table
├── containers/          # Data-connected containers
│   ├── RunsListContainer.tsx # Runs list with data fetching
│   └── RunPlayerContainer.tsx # Playback with WebSocket
├── views/               # Route-level views
│   └── RunDetail.tsx    # Individual run detail page
├── services/            # API and data services
│   ├── api.ts          # REST API client with Zod validation
│   ├── ws.ts           # WebSocket hook for streaming
│   ├── bars.ts         # Bar data fetching
│   └── transport.ts    # HTTP transport utilities
├── hooks/               # Custom React hooks
│   └── useChartInitialization.ts # Chart setup logic
├── types/               # TypeScript type definitions
│   ├── charts.ts       # Chart-related types
│   └── streaming.ts    # WebSocket/streaming types
├── schemas/             # Zod validation schemas
│   └── stream.ts       # Stream frame validation
├── workers/             # Web Workers
│   └── streamParser.ts # Stream parsing off main thread
├── utils/               # Utility functions
│   └── api.ts          # API helper functions
└── constants.ts         # Application constants
```

---

## 3. Wireframes & Layouts

### Runs List Wireframe

#### Layout (Normal)
- **Header**
  - Title: "Runs"
  - Filters: symbol (input), strategy (select)
  - Actions: Create baseline run (button)
- **Table** (20 per page)
  - Columns: run_id, created_at, strategy_id, status, symbol, from, to, duration_ms, action
  - Row action: "View" → navigates to `/runs/{run_id}`
- **Footer**
  - Pagination: prev/next, page size

#### States
- **Loading**: Replace table with 10 skeleton rows (monospace widths aligned to columns)
- **Empty**: 
  - Illustration/placeholder
  - Message: "No runs yet."
  - CTA: Create baseline run
- **Error**: 
  - Banner: "Error loading runs" + error code/message
  - Retry button

#### Interaction Notes
- Filters debounce 300ms; Enter key focuses table
- Table rows keyboard navigable; Enter opens detail
- Responsive: Filters wrap on mobile; table scrolls horizontally if needed

### Run Detail Wireframe

#### Layout (Playing)
- **Header**
  - Left: run_id, status pill (QUEUED/RUNNING/DONE/ERROR)
  - Right: "Rerun from manifest" (button)
- **Meta Panel**
  - symbol, date range, strategy_id/params, seed, created_at
- **Controls Bar**
  - Play/Pause, Seek (slider + datetime input), Speed (30/60/120)
  - Indicators: WS connected | SSE fallback; Dropped: N
- **Charts**
  - OHLC main chart with overlays toggles (orders, fills)
  - Equity mini-chart below

#### States
- **Loading metadata**: Skeletons for header/meta; disabled controls
- **Error (RUN_NOT_FOUND)**: Banner + back link to Runs List
- **Waiting for playback**: Metadata visible; controls enabled; chart placeholder
- **Playing**: Live frames; dropped counter visible
- **Paused**: Controls show paused; charts static
- **End**: Toast "End of stream"; controls allow seek/replay

#### Error Events During Playback
- Toast: code + short message on `{t:"err"}`; non-blocking unless fatal

#### Interaction Notes
- Keyboard shortcuts: Space (play/pause), ←/→ seek, +/- speed
- Focus ring visible; live region announces connection changes
- Responsive: Controls wrap; charts stack on small screens

---

## 4. Design System Guidelines

### Component Development
- **Presentational components**: Pure functions, no side effects
- **Props validation**: Use TypeScript interfaces, avoid `any`
- **Event handling**: Pass callbacks from containers
- **Styling**: TailwindCSS classes, consistent spacing

### Data Flow
- **API calls**: Use `@tanstack/react-query` in containers
- **State management**: React state + TanStack Query cache
- **WebSocket**: Custom hook in `services/ws.ts`
- **Validation**: Zod schemas at API boundaries

### Performance
- **Chart updates**: Imperative APIs for high-frequency updates
- **Stream parsing**: Web Worker for frame processing
- **Memoization**: React.memo for expensive components

### Accessibility
- **Keyboard navigation**: All interactive elements accessible via keyboard
- **Focus management**: Visible focus rings, logical tab order
- **Screen readers**: ARIA labels, live regions for dynamic content
- **Color contrast**: WCAG AA compliance for all text/background combinations

### Responsive Design
- **Mobile-first**: Design for mobile, enhance for desktop
- **Breakpoints**: Use TailwindCSS responsive utilities
- **Touch targets**: Minimum 44px for touch interactions
- **Content priority**: Most important content visible on small screens

---

**Cross-References**
- **API Documentation**: [`docs/api-reference.md`](./api-reference.md)
- **Architecture**: [`docs/architecture.md`](./architecture.md)
- **PRD Features**: [`docs/prd/features/00-baselines.md`](./prd/features/00-baselines.md)
- **Frontend Implementation**: [`frontend/src/`](../frontend/src/)

---

**Note**: This document consolidates UI/UX documentation previously scattered across multiple files. Component implementations should follow the patterns and principles outlined here.
