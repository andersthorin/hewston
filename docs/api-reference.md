# API Reference Guide

**Status**: v0.1 — Consolidated API documentation for Hewston trading platform  
**Last Updated**: 2025-01-27

## Table of Contents

1. [Runs Catalog Overview](#1-runs-catalog-overview)
2. [Error Codes & Handling](#2-error-codes--handling)
3. [WebSocket Protocol](#3-websocket-protocol)
4. [Schema References](#4-schema-references)

---

## 1. Runs Catalog Overview

**Purpose**: Lightweight local catalog to index datasets and runs for listing, filtering, and retrieving artifacts. SQLite chosen for simplicity and determinism.

### Database Tables

#### datasets
- **dataset_id** (PK), symbol, from_date, to_date
- **products_json** ["TRADES","TBBO"], calendar_version, tz
- **raw_dbn_json** (paths), bars_parquet_json (paths), bars_manifest_path
- **generated_at** (UTC), size_bytes, status (READY|BUILDING|ERROR)
- **Indices**: (symbol, from_date, to_date), (generated_at)

#### runs
- **run_id** (PK), dataset_id (FK → datasets)
- **strategy_id**, params_json, seed, slippage_fees_json, speed
- **code_hash**, created_at (UTC), status, duration_ms
- **metrics_path**, equity_path, orders_path, fills_path, run_manifest_path
- **input_hash** (deterministic hash of inputs), idempotency_key
- **Indices**: (dataset_id), (strategy_id, created_at), (created_at)

#### run_metrics
- **run_id** (PK, FK → runs), total_return, cagr, max_drawdown, sharpe, sortino
- **hit_rate**, avg_win, avg_loss, turnover, slippage_share, fees_paid, computed_at
- **Indices**: (sharpe), (max_drawdown)

#### View: runs_list
- Joins runs with datasets for convenient listing (symbol, from_date, to_date)

### Common Queries

**Count runs by symbol**
```sql
SELECT d.symbol, COUNT(*) AS n
FROM runs r
JOIN datasets d ON d.dataset_id = r.dataset_id
GROUP BY d.symbol
ORDER BY n DESC;
```

**List last N runs**
```sql
SELECT * FROM runs_list
ORDER BY created_at DESC
LIMIT 20;
```

**Filter runs (symbol + date overlap)**
```sql
SELECT *
FROM runs_list
WHERE symbol = 'AAPL'
  AND from_date >= '2023-01-01'
  AND to_date   <= '2023-12-31'
ORDER BY created_at DESC;
```

**Get run detail with artifact paths**
```sql
SELECT r.*, d.symbol, d.from_date, d.to_date
FROM runs r
JOIN datasets d ON d.dataset_id = r.dataset_id
WHERE r.run_id = ?;
```

### Operational Notes
- PRAGMA foreign_keys = ON; (enabled in schema script)
- Keep JSON fields stable (sorted keys) if used in input_hash calculations
- Run VACUUM/ANALYZE periodically for health if catalog grows

---

## 2. Error Codes & Handling

**Purpose**: Canonical error codes for consistent REST and WebSocket error handling.

### Error Payload Format

**REST and WebSocket**
```json
{ "error": { "code": "...", "message": "...", "details": { } } }
```

**WebSocket Alternative**
```json
{ "t":"err", "code": "...", "msg": "...", "details": { } }
```

### Error Codes and HTTP Mappings

| Code | HTTP Status | Description |
|------|-------------|-------------|
| **VALIDATION** | 422 Unprocessable Entity | Input shape or types invalid; include field errors in details |
| **CONFLICT** | 409 Conflict | Resource state conflicts (e.g., duplicate `input_hash` without idempotency key) |
| **IDP_CONFLICT** | 409 Conflict | Idempotency-Key collides with different payload; safe to retry with correct key |
| **RUN_NOT_FOUND** | 404 Not Found | Unknown run id |
| **DATASET_NOT_FOUND** | 404 Not Found | Unknown dataset id or unresolved symbol/range |
| **RANGE** | 400 Bad Request | Out-of-range seek or invalid window for playback |
| **BUSY** | 503 Service Unavailable | System is overloaded or job queue not accepting new work |
| **INTERNAL** | 500 Internal Server Error | Unhandled server error; message should not leak internals |

### Error Examples

**Validation (422)**
```json
{ "error": { "code": "VALIDATION", "message": "Invalid body.", "details": { "seed": "must be integer" } } }
```

**Run not found (404)**
```json
{ "error": { "code": "RUN_NOT_FOUND", "message": "Run abc123 not found" } }
```

**Conflict (409)**
```json
{ "error": { "code": "CONFLICT", "message": "input_hash already exists for a different run" } }
```

**WebSocket out-of-range (RANGE)**
```json
{ "t": "err", "code": "RANGE", "msg": "seek timestamp out of range", "details": { "min": "2023-01-03T14:30:00Z", "max": "2023-12-29T20:00:00Z" } }
```

---

## 3. WebSocket Protocol

**Purpose**: Playback streaming protocol for real-time backtest visualization.

### Endpoints
- **WebSocket (primary)**: `GET /backtests/{id}/ws`
- **SSE fallback**: `GET /backtests/{id}/stream?speed=60`

### Goals and Constraints
- Target: ~1 year of data → ~60 seconds playback
- Server decimates to ≈30 FPS target; client drops oldest on lag
- Bidirectional control only over WebSocket; SSE is server→client only

### Message Formats

#### Client → Server (WebSocket Control)
```json
{ "t": "ctrl", "cmd": "play|pause|seek|speed", "pos": "ISO-UTC|frameIndex?", "val": number? }
```

**Commands:**
- **play**: Resume streaming
- **pause**: Pause streaming (server may continue preparing next frame)
- **speed**: Set target compression factor (e.g., 60 ⇒ ~1y→~60s)
- **seek**: Jump to timestamp or frame index; server snaps to nearest frame within range

#### Server → Client (WebSocket/SSE)

**Frame**
```json
{ "t":"frame", "ts":"ISO-UTC", "ohlc": { ... }, "orders": [ ... ], "equity": number, "dropped": integer }
```

**Heartbeat**
```json
{ "t": "hb" }
```

**End of stream**
```json
{ "t": "end" }
```

**Error**
```json
{ "t": "err", "code": "RANGE|RUN_NOT_FOUND|...", "msg": "human-readable", "details": { ... } }
```

### SSE Framing
- **Content-Type**: `text/event-stream`
- **Event name**: `frame`
- **Payload**: StreamFrame JSON (one per event)

**Example SSE event**
```
event: frame

data: {"t":"frame","ts":"2023-03-01T14:30:00Z","ohlc":{...},"orders":[],"equity":123.4,"dropped":0}
```

### Connection Management

#### Heartbeats and Timeouts
- Server sends `{ "t":"hb" }` every 5s when idle or paused
- Client may echo `{ "t":"hb" }` (optional)
- Server drops connections after idle timeout (e.g., 30s without any message)

#### Backpressure and Performance
- Server decimates frames to ≈30 FPS
- On server lag, coalesce/skip older frames
- Client should drop oldest buffered frames if UI can't keep up
- Surface the `dropped` counter from frames for monitoring

#### Connection Lifecycle
1. Connect → (optional) pause → play → stream frames
2. Seek/speed adjustments as needed → end → close
3. **Reconnect behavior**: Client may reconnect and resume; server should support resuming from last known position when feasible

### Error Handling
- Use canonical codes from [Error Codes section](#2-error-codes--handling)
- **RANGE** — out-of-range seek or before run is ready
- **RUN_NOT_FOUND** — unknown id
- **VALIDATION** — bad control payload
- On fatal errors, server may send `{ "t":"err" }` then close

---

## 4. Schema References

### JSON Schema Files
- **Dataset Manifest**: [`docs/api/schemas/dataset-manifest.schema.json`](./api/schemas/dataset-manifest.schema.json)
- **Run Manifest**: [`docs/api/schemas/run-manifest.schema.json`](./api/schemas/run-manifest.schema.json)

### OpenAPI Specification
- **Complete API Spec**: [`docs/api/openapi.yaml`](./api/openapi.yaml)

### Cross-References
- **Authoritative DDL**: `scripts/catalog_init.sql`
- **Metrics Definitions**: [`docs/metrics/run-metrics-definitions.md`](./metrics/run-metrics-definitions.md)
- **PRD Features**: [`docs/prd/features/00-baselines.md`](./prd/features/00-baselines.md)
- **Architecture**: [`docs/architecture.md`](./architecture.md)

---

**Note**: This document consolidates API documentation previously scattered across multiple files. For detailed implementation examples and additional context, refer to the cross-referenced documents above.
