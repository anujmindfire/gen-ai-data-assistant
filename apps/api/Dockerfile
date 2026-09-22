# Production Dockerfile for GenAI Data Assistant API
FROM python:3.12-slim AS base

# Install uv package manager binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Environment configurations
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

# Install curl for container utilities if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency configuration files for layer caching
COPY pyproject.toml /app/pyproject.toml
COPY apps/api/pyproject.toml /app/apps/api/pyproject.toml

# Cache & install production python dependencies using uv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -r /app/apps/api/pyproject.toml

# Copy application source code and packages
COPY packages /app/packages
COPY apps/api /app/apps/api

# Security: Run as non-root user
RUN addgroup --system appuser && adduser --system --group appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Health check instruction
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "apps.api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
