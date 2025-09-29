"""
BFF Configuration Management

Centralizes configuration values for the BFF service, following the pattern
established in backend/constants.py while providing BFF-specific settings.
"""

import os
from typing import List

# API Configuration
BFF_API_TITLE = "Hewston BFF API"
BFF_API_VERSION = "0.1.0"
BFF_API_DESCRIPTION = "Backend-for-Frontend service providing aggregated APIs for Hewston trading platform"

# Server Configuration
BFF_DEFAULT_HOST = "127.0.0.1"
BFF_DEFAULT_PORT = 8001  # Different from backend (8000) to avoid conflicts
BFF_CORS_ORIGINS = ["http://127.0.0.1:5173", "http://localhost:5173"]

# Backend Integration
BACKEND_BASE_URL = os.getenv("HEWSTON_BACKEND_URL", "http://127.0.0.1:8000")
BACKEND_TIMEOUT_SECONDS = int(os.getenv("BFF_BACKEND_TIMEOUT", "30"))

# Redis Configuration (Optional)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_ENABLED = os.getenv("BFF_REDIS_ENABLED", "false").lower() == "true"
REDIS_TTL_CHART_DATA = int(os.getenv("BFF_REDIS_TTL_CHART", "300"))  # 5 minutes
REDIS_TTL_RUN_DATA = int(os.getenv("BFF_REDIS_TTL_RUN", "60"))  # 1 minute

# Performance Configuration
DEFAULT_CHART_TARGET_POINTS = 10000
MAX_CONCURRENT_BACKEND_REQUESTS = 10
REQUEST_TIMEOUT_SECONDS = 30

# Health Check Configuration
HEALTH_CHECK_DEPENDENCIES = [
    "backend_api",
    "redis" if REDIS_ENABLED else None
]

# Remove None values
HEALTH_CHECK_DEPENDENCIES = [dep for dep in HEALTH_CHECK_DEPENDENCIES if dep is not None]

# Logging Configuration
LOG_LEVEL = os.getenv("BFF_LOG_LEVEL", "INFO")
LOG_FORMAT = "iso"
LOG_UTC = True

# Feature Flags (for gradual migration)
FEATURE_FLAGS = {
    "chart_data_aggregation": os.getenv("BFF_FEATURE_CHART_AGGREGATION", "true").lower() == "true",
    "run_data_aggregation": os.getenv("BFF_FEATURE_RUN_AGGREGATION", "true").lower() == "true",
    "websocket_proxy": os.getenv("BFF_FEATURE_WEBSOCKET_PROXY", "true").lower() == "true",
    "caching_enabled": REDIS_ENABLED,
}

# Environment Detection
ENVIRONMENT = os.getenv("BFF_ENVIRONMENT", "development")
IS_DEVELOPMENT = ENVIRONMENT.lower() in ("development", "dev", "local")
IS_PRODUCTION = ENVIRONMENT.lower() in ("production", "prod")

# Service Metadata
SERVICE_NAME = "hewston-bff"
SERVICE_VERSION = BFF_API_VERSION
BUILD_INFO = {
    "service": SERVICE_NAME,
    "version": SERVICE_VERSION,
    "environment": ENVIRONMENT,
    "backend_url": BACKEND_BASE_URL,
    "redis_enabled": REDIS_ENABLED,
    "feature_flags": FEATURE_FLAGS,
}
