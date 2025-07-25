# Second Brain v3.0.0 - Production-Ready Multi-Stage Dockerfile
# Designed for: Security, Performance, Observability, and K8s-readiness

# Build stage 1: Dependencies
FROM python:3.11-slim-bookworm AS dependencies
LABEL stage=dependencies

# Security: Run as non-root from the start
RUN useradd -m -r -u 1001 secondbrain && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Cache dependencies layer
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements-dev.txt

# Build stage 2: Application build
FROM python:3.11-slim-bookworm AS builder
LABEL stage=builder

COPY --from=dependencies /usr/local /usr/local
WORKDIR /app

# Copy application code
COPY . .

# Run security checks and tests at build time
RUN python -m black --check . && \
    python -m ruff check . && \
    python -m mypy . --strict && \
    python -m pytest tests/ -v --tb=short && \
    python -m bandit -r app/ -ll

# Build stage 3: Production runtime
FROM gcr.io/distroless/python3-debian12:nonroot AS runtime
LABEL stage=production
LABEL maintainer="Second Brain Team"
LABEL version="3.0.0"

# OpenTelemetry and observability labels
LABEL org.opencontainers.image.title="Second Brain"
LABEL org.opencontainers.image.description="Distributed memory augmentation system"
LABEL org.opencontainers.image.version="3.0.0"
LABEL org.opencontainers.image.vendor="Second Brain Project"

# Copy Python and dependencies from builder
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application with proper ownership
WORKDIR /app
COPY --from=builder --chown=nonroot:nonroot /app /app

# Environment variables for cloud-native deployment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Observability
    OTEL_SERVICE_NAME=secondbrain \
    OTEL_TRACES_EXPORTER=otlp \
    OTEL_METRICS_EXPORTER=otlp \
    OTEL_LOGS_EXPORTER=otlp \
    # App configuration
    APP_ENV=production \
    APP_PORT=8000 \
    # Federation ready
    FEDERATION_ENABLED=false \
    NODE_ID="" \
    CLUSTER_NAME="default"

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["/usr/local/bin/python", "-c", \
    "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]

# Expose ports
EXPOSE 8000 9090 8080

# Non-root user (from distroless)
USER nonroot

# Graceful shutdown support
STOPSIGNAL SIGTERM

# Entry point with signal handling
ENTRYPOINT ["python", "-m", "uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000"]

# Development stage (optional)
FROM python:3.11-slim-bookworm AS development
LABEL stage=development

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        vim \
        curl \
        git \
        postgresql-client \
        redis-tools \
        && rm -rf /var/lib/apt/lists/*

COPY --from=dependencies /usr/local /usr/local
WORKDIR /app

# Development tools
RUN pip install --no-cache-dir \
    ipython \
    ipdb \
    pytest-watch \
    black \
    ruff \
    mypy

VOLUME ["/app"]
CMD ["python", "-m", "uvicorn", "app.app:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]