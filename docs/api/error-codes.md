# API and Streaming Error Codes (Canonical)

Status: v0.1 — Use these codes consistently in REST and WS/SSE error payloads.

## Error payload shape (REST and WS)
```json
{ "error": { "code": "...", "message": "...", "details": { } } }
```
- For WS, the envelope may be `{ "t":"err", "code": "...", "msg": "...", "details": { } }`

## Codes and HTTP mappings
- VALIDATION — 422 Unprocessable Entity
  - Input shape or types invalid; include field errors in details
- CONFLICT — 409 Conflict
  - Resource state conflicts (e.g., duplicate `input_hash` without idempotency key)
- IDP_CONFLICT — 409 Conflict
  - Idempotency-Key collides with different payload; safe to retry with correct key
- RUN_NOT_FOUND — 404 Not Found
  - Unknown run id
- DATASET_NOT_FOUND — 404 Not Found
  - Unknown dataset id or unresolved symbol/range
- RANGE — 400 Bad Request
  - Out-of-range seek or invalid window for playback (WS may use this as `{t:"err"}`)
- BUSY — 503 Service Unavailable
  - System is overloaded or job queue not accepting new work
- INTERNAL — 500 Internal Server Error
  - Unhandled server error; message should not leak internals

## Examples

Validation (422)
```json
{ "error": { "code": "VALIDATION", "message": "Invalid body.", "details": { "seed": "must be integer" } } }
```

Run not found (404)
```json
{ "error": { "code": "RUN_NOT_FOUND", "message": "Run abc123 not found" } }
```

Conflict (409)
```json
{ "error": { "code": "CONFLICT", "message": "input_hash already exists for a different run" } }
```

WS out-of-range (RANGE)
```json
{ "t": "err", "code": "RANGE", "msg": "seek timestamp out of range", "details": { "min": "2023-01-03T14:30:00Z", "max": "2023-12-29T20:00:00Z" } }
```

