# Frontend Component Map (MVP)

Status: v0.1 (UX)

Principles
- Presentational components only (no fetch/mutate)
- Containers/services/hooks own data and side-effects
- Type-safe props; events passed as callbacks

## Components
- RunsTable
  - Props: { rows: RunSummary[], total: number, limit: number, offset: number, onPage: (o:number)=>void, onView:(runId:string)=>void }
  - States: loading (skeleton), empty, error (via wrapper)
- FiltersBar
  - Props: { symbol?: string, strategyId?: string, onChange:(p:{symbol?:string,strategyId?:string})=>void }
- PlaybackControls
  - Props: { playing: boolean, speed: number, onPlay:()=>void, onPause:()=>void, onSeek:(ts:string)=>void, onSpeedChange:(n:number)=>void }
- ChartOHLC
  - Props: { candles: Candle[], overlays:{orders?:Order[],fills?:Fill[]}, lastTs?: string }
- EquityChart
  - Props: { series: EquityPoint[], lastTs?: string }
- StatusPill
  - Props: { status: "QUEUED"|"RUNNING"|"DONE"|"ERROR" }

## Containers / Views (non-presentational)
- RunsListContainer
  - Uses services/api.listBacktests; maps query params; passes to RunsTable
- RunPlayerContainer
  - Uses services/ws.useRunPlayback; subscribes to frames; maps to charts/controls props
- RunDetail view
  - Fetches run metadata; composes RunPlayerContainer and presentational components

## Types (TS shapes)
- RunSummary: { run_id: string, created_at: string, strategy_id: string, status: string, symbol: string, from: string, to: string, duration_ms?: number }
- Candle: { ts: string, o: number, h: number, l: number, c: number, v?: number }
- Order: { ts: string, side: "BUY"|"SELL", qty: number, price: number, id: string }
- Fill: { ts: string, order_id: string, qty: number, price: number, id: string, slippage?: number, fee?: number }
- EquityPoint: { ts: string, value: number }

## Files (suggested)
- frontend/src/components/{RunsTable,FiltersBar,PlaybackControls,ChartOHLC,EquityChart,StatusPill}.tsx
- frontend/src/containers/{RunsListContainer,RunPlayerContainer}.tsx
- frontend/src/views/RunDetail.tsx
- frontend/src/services/{api,ws,sse}.ts; frontend/src/workers/streamParser.ts
- frontend/src/schemas/{runs,stream}.ts (Zod)

