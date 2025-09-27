"""
Backend constants and configuration values.

This module centralizes hardcoded values, magic numbers, and configuration
to improve maintainability and consistency across the backend.
"""

# API Configuration
API_TITLE = "Hewston API"
API_VERSION = "0.1.0"

# Server Configuration
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
CORS_ORIGINS = ["http://127.0.0.1:5173", "http://localhost:5173"]

# Database Configuration
DEFAULT_CATALOG_PATH = "data/catalog.sqlite"
DEFAULT_DATA_DIR = "data"

# Streaming Configuration
DEFAULT_FPS = 30
DEFAULT_SPEED = 60
HEARTBEAT_SECONDS = 5.0

# Playback Configuration
DEFAULT_PLAYBACK_SPEED = 60  # ~1 year → ~60 seconds target

# Data Processing Configuration
DEFAULT_TIMEZONE = "America/New_York"
DEFAULT_CALENDAR_VERSION = "NASDAQ-v1"
DEFAULT_INTERVAL = "1m"

# File Paths and Extensions
PARQUET_EXTENSION = ".parquet"
JSON_EXTENSION = ".json"
DBN_EXTENSION = ".dbn.zst"

# Artifact File Names
METRICS_FILENAME = "metrics.json"
EQUITY_FILENAME = "equity.parquet"
ORDERS_FILENAME = "orders.parquet"
FILLS_FILENAME = "fills.parquet"
RUN_MANIFEST_FILENAME = "run-manifest.json"
BARS_MANIFEST_FILENAME = "bars_manifest.json"

# Default Products
DEFAULT_PRODUCTS = ["TRADES", "TBBO"]

# Baseline Configuration (from docs/prd/features/00-baselines.md)
BASELINE_SYMBOL = "AAPL"
BASELINE_YEAR = 2023
BASELINE_FROM_DATE = "2023-01-01"
BASELINE_TO_DATE = "2023-12-31"
BASELINE_STRATEGY = "sma_crossover"
BASELINE_FAST_PERIOD = 20
BASELINE_SLOW_PERIOD = 50
BASELINE_SEED = 42

# Pagination Defaults
DEFAULT_LIMIT = 20
MAX_LIMIT = 500
DEFAULT_OFFSET = 0

# Timeout and Retry Configuration
DEFAULT_TIMEOUT_SECONDS = 30
MAX_RETRY_ATTEMPTS = 3

# Logging Configuration
LOG_FORMAT = "iso"
LOG_UTC = True
