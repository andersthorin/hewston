# BFF Service Dockerfile
# Multi-stage build for production deployment

FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create app user
RUN groupadd -r app && useradd -r -g app app

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Development stage
FROM base as development

# Install uv for faster dependency management
RUN pip install uv

# Copy requirements first for better caching
COPY bff/requirements.txt .

# Install Python dependencies
RUN uv pip install --system -r requirements.txt

# Copy BFF source code
COPY bff/ ./bff/
COPY backend/app/logging_setup.py ./backend/app/

# Create necessary directories
RUN mkdir -p backend/app && \
    touch backend/__init__.py backend/app/__init__.py

# Change ownership to app user
RUN chown -R app:app /app

# Switch to app user
USER app

# Expose BFF port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/api/v1/health/live || exit 1

# Default command
CMD ["uvicorn", "bff.app.main:app", "--host", "0.0.0.0", "--port", "8001"]

# Production stage
FROM base as production

# Install only production dependencies
COPY bff/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY bff/ ./bff/
COPY backend/app/logging_setup.py ./backend/app/

# Create necessary directories
RUN mkdir -p backend/app && \
    touch backend/__init__.py backend/app/__init__.py

# Change ownership to app user
RUN chown -R app:app /app

# Switch to app user
USER app

# Expose BFF port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/api/v1/health/live || exit 1

# Production command with optimizations
CMD ["uvicorn", "bff.app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
