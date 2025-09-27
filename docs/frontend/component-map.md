# Frontend Component Map (Current Implementation)

Status: v1.0 (Post-Cleanup) - Updated after comprehensive code cleanup

## Architecture Principles
- **Presentational components only** (no fetch/mutate/side effects)
- **Containers/services/hooks** own data fetching and state management
- **Type-safe props** with TypeScript and Zod validation
- **Imperative chart APIs** for performance-critical chart operations

## Current Components

### Core UI Components
- **RunsTable**
  - Props: `{ items: RunSummary[], onView?: (run_id: string) => void }`
  - Features: Displays run list with standardized `run_from`/`run_to` fields
  - States: loading, empty, error (handled by container)

- **FiltersBar**
  - Props: `{ initial: FilterState, onApply: (filters: FilterState) => void }`
  - Features: Symbol, strategy, date range filtering

- **PlaybackControls**
  - Props: `{ playing: boolean, speed: number, onPlay: () => void, onPause: () => void, onSpeedChange: (speed: number) => void }`
  - Features: Play/pause, speed control for backtesting playback

### Chart Components (Imperative APIs)
- **ChartOHLC**
  - Props: `{ height?: number, onReady?: (api: CandlestickChartAPI) => void }`
  - Features: TradingView Lightweight Charts integration, imperative API for performance
  - API: `updateCandles()`, `updateOrders()`, `setVisibleRange()`, `scrollToTime()`

- **EquityChart**
  - Props: `{ height?: number, onReady?: (api: EquityChartAPI) => void }`
  - Features: Equity curve visualization with imperative updates
  - API: `updateEquity()`, `setVisibleRange()`, `scrollToTime()`

## Containers & Views (Data Layer)

### Containers
- **RunsListContainer**
  - Uses: `@tanstack/react-query` for data fetching, `services/api.listBacktests`
  - Features: Pagination, filtering, create run functionality
  - Manages: Loading states, error handling, query parameters

- **RunPlayerContainer**
  - Uses: `services/ws.useRunPlayback` for WebSocket streaming
  - Features: Real-time playback control, frame streaming, chart coordination
  - Manages: WebSocket connection, playback state, chart API refs

### Views
- **RunDetailView**
  - Route: `/runs/:run_id`
  - Features: Run metadata display, embedded RunPlayerContainer
  - Uses: `useQuery` for run details, `useParams` for routing

## Current TypeScript Types (Post-Standardization)

### API Types (Zod-validated)
```typescript
// Standardized field names (run_from/run_to)
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

### Streaming Types
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

### Chart API Types
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

## Current File Structure (Actual Implementation)
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

## Development Guidelines

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

