# Secrets and Environment Configuration

Status: v0.1 — Guidance for configuring local development without leaking secrets.

## Principles
- Never commit real secrets (API keys, tokens) to the repo.
- Prefer environment variables for configuration; document required vars.
- Keep an example file (.env.example) checked in for discoverability.

## Required/Useful variables
- DATABENTO_API_KEY — required for data ingest jobs
- HEWSTON_API_HOST (default: 127.0.0.1)
- HEWSTON_API_PORT (default: 8000)
- HEWSTON_WS_URL (default: ws://localhost:8000)
- SQLITE_CATALOG_PATH (default: data/catalog.sqlite)

## Local setup
1) Copy the example file and edit:
```
cp .env.example .env
edit .env
```
2) Export into your shell (bash/zsh):
```
export $(grep -v '^#' .env | xargs)
```
3) Verify:
```
echo $DATABENTO_API_KEY
```

Notes
- If you later add code to auto-load .env (e.g., python-dotenv or frontend Vite env conventions), keep the variables consistent with this document.
- Do not print secrets in logs. Avoid echoing variables containing keys except when necessary for debugging.

## References
- .env.example (root)
- docs/architecture.md and shards for broader context

