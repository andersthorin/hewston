# Technical Baselines (Authoritative for MVP)

Status: v0.1 — Architect-approved defaults for ingestion, backtests, playback, and determinism. Changes require Architect sign-off and story updates.

## Scope
These baselines are cross-cutting constraints that unblock parallel work in data ingest/derive, backtests, API, and UI.

## Symbols, Date Ranges, Interval
- symbol: AAPL (baseline)
- from: 2023-01-01 (inclusive)
- to:   2023-12-31 (inclusive)
- interval: 1m (one-minute bars)
- timezone: America/New_York (persistence in UTC; UI renders NY time)

## Bars Schema (Derived per symbol-year)
- Source: Databento DBN — TRADES + TBBO
- Output format: Parquet
- Partitioning: data/derived/bars/{SYMBOL}/{YEAR}/
- Columns (authoritative):
  - ts_utc (timestamp[us, UTC]) — bar open time
  - open (float64)
  - high (float64)
  - low (float64)
  - close (float64)
  - volume (float64)
  - trades_count (int64)
  - bid_mean (float64) — minute average of best bid
  - ask_mean (float64) — minute average of best ask
  - spread_mean (float64) — minute average (ask_mean - bid_mean)

Notes
- Include explicit, stable sort by ts_utc ascending; one row per minute in session.
- Session/calendar handling: NASDAQ trading calendar, pinned version; explicit DST policy.

## Determinism & Calendars
- Market calendar: NASDAQ (pinned version; record value in manifests)
- Timezone: America/New_York for session rules; persist timestamps in UTC
- Hashing: SHA-256 for raw and derived artifacts; stable serialization
- Seeds: all stochastic steps must record `seed`

## Slippage & Fees (MVP defaults)
- k_spread: 0.5 (fills occur at mid ± k_spread × spread_mean)
- fees_bps: 1 (round-trip bps applied as configured)
- Rationale: simple, transparent model suitable for 1m bar fidelity; refined later if needed

## Baseline Strategy
- strategy_id: sma_crossover
- params:
  - fast: 20
  - slow: 50
- seed: 42

## Playback Defaults
- speed: 60 (≈ 1 year → ≈ 60 seconds target at server-side decimation ≈ 30 FPS)

## Identifiers & Catalog Conventions
- dataset_id: "AAPL-2023-1m"
- run_id: ULID (recommended) or UUIDv4; persist as string
- Catalog: SQLite schema in scripts/catalog_init.sql (authoritative)

## Manifests (Required Fields)

DatasetManifest (bars derivation provenance)
- dataset_id, symbol, interval ("1m"), from_date, to_date
- rebar_params: { clock: "NASDAQ", session_handling: "explicit-DST", aggregation: "TRADES→OHLCV", tbbo_agg: ["bid_mean", "ask_mean", "spread_mean"] }
- input_hashes: { trades_dbn_sha256, tbbo_dbn_sha256 }
- output_hashes: { bars_parquet_sha256 }
- calendar_version, tz
- created_at (UTC)

RunManifest (snapshot at backtest execution)
- run_id, dataset_id, strategy_id, params, seed
- slippage_fees { k_spread, fees_bps }
- speed
- data snapshot refs: { bars_manifest_path or bars_manifest_hashes }
- calendar_version, tz
- env_lock (Python/Node/packages), code_hash (git)
- created_at (UTC)

### Example: Run Create (API)
- POST /backtests body (baseline values):
```
{ "dataset_id": "AAPL-2023-1m", "strategy_id": "sma_crossover", "params": {"fast":20,"slow":50}, "seed": 42, "slippage_fees": {"k_spread":0.5, "fees_bps":1}, "speed": 60 }
```

## Filesystem Layout (authoritative paths)
- Raw DBN cache: data/raw/databento/{SYMBOL}/{YEAR}/{product}.dbn
- Derived bars: data/derived/bars/{SYMBOL}/{YEAR}/1m.parquet
- Bars manifest: data/derived/bars/{SYMBOL}/{YEAR}/manifest.json
- Run artifacts: data/backtests/{run_id}/
  - equity.parquet, orders.parquet, fills.parquet, metrics.json, run-manifest.json

## Acceptance Gates (for story/demo readiness)
- Bars produced for AAPL 2023 with the exact schema above; manifest includes calendar_version and input/output hashes
- Backtest completes with baseline strategy/params; artifacts written; run manifest recorded
- Catalog rows upserted per schema; list/get endpoints reflect the run
- Playback at speed=60 streams frames with hb/end/err control; dropped-frame ratio within budget

## Cross-References
- PRD: §2 (FR/NFR), §4 (Technical), §6 (Next Steps)
- Architecture: §Data Models, §API Contracts, §Non-Functional, §Source Tree
- OpenAPI: docs/api/openapi.yaml
- Catalog DDL: scripts/catalog_init.sql

