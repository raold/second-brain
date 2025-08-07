# Second Brain - Docker-First Development Environment
# Multi-stage build for development and production
# Zero host Python dependencies required

# Development stage
FROM python:3.11-slim AS development

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Create app user
RUN groupadd -r app && useradd -r -g app app

# Install system dependencies for development
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libpq-dev \
    postgresql-client \
    # Multi-modal support
    tesseract-ocr \
    tesseract-ocr-eng \
    ffmpeg \
    libsm6 \
    libxext6 \
    libglib2.0-0 \
    libgomp1 \
    # Development tools
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements files
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs session_storage temp data .cache && \
    chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Development command (with hot reload)
CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Build stage for production
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    # Additional dependencies for multi-modal support
    libxml2-dev \
    libxslt1-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements files
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels \
    -r requirements.txt

# Runtime stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    # Multi-modal runtime dependencies
    tesseract-ocr \
    tesseract-ocr-eng \
    ffmpeg \
    libsm6 \
    libxext6 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy wheels from builder
COPY --from=builder /app/wheels /wheels

# Install Python packages
RUN pip install --upgrade pip && \
    pip install --no-cache /wheels/* && \
    rm -rf /wheels

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/temp && \
    chown -R appuser:appuser /app/data /app/logs /app/temp

# Set environment variables
ENV TEMP_DIR=/app/temp
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000"]
