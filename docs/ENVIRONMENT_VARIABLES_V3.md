# Second Brain v3.0.0 - Environment Variables Guide

## Overview

This guide documents all environment variables used in Second Brain v3.0.0, their purposes, default values, and configuration examples.

## Required Environment Variables

These variables MUST be set for the application to function properly:

### Database Configuration

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@localhost:5432/secondbrain` | ✅ |
| `DATABASE_POOL_SIZE` | Connection pool size | `20` | ❌ (default: 10) |
| `DATABASE_MAX_OVERFLOW` | Max overflow connections | `40` | ❌ (default: 20) |
| `DATABASE_POOL_TIMEOUT` | Connection timeout (seconds) | `30` | ❌ (default: 30) |
| `DATABASE_ECHO` | Enable SQL logging | `false` | ❌ (default: false) |

### Redis Configuration

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` | ✅ |
| `REDIS_MAX_CONNECTIONS` | Max connection pool size | `50` | ❌ (default: 50) |
| `REDIS_DECODE_RESPONSES` | Decode responses to strings | `true` | ❌ (default: true) |
| `REDIS_SOCKET_TIMEOUT` | Socket timeout (seconds) | `5` | ❌ (default: 5) |
| `REDIS_CONNECTION_TIMEOUT` | Connection timeout (seconds) | `10` | ❌ (default: 10) |

### RabbitMQ Configuration

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `RABBITMQ_URL` | RabbitMQ connection string | `amqp://user:pass@localhost:5672/` | ✅ |
| `RABBITMQ_EXCHANGE` | Exchange name | `secondbrain` | ❌ (default: secondbrain) |
| `RABBITMQ_EXCHANGE_TYPE` | Exchange type | `topic` | ❌ (default: topic) |
| `RABBITMQ_PREFETCH_COUNT` | Prefetch count for consumers | `10` | ❌ (default: 10) |
| `RABBITMQ_HEARTBEAT` | Heartbeat interval (seconds) | `600` | ❌ (default: 600) |

### MinIO/S3 Configuration

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `MINIO_ENDPOINT` | MinIO/S3 endpoint | `localhost:9000` | ✅ |
| `MINIO_ACCESS_KEY` | Access key | `minioadmin` | ✅ |
| `MINIO_SECRET_KEY` | Secret key | `minioadmin` | ✅ |
| `MINIO_BUCKET` | Default bucket name | `secondbrain` | ❌ (default: secondbrain) |
| `MINIO_SECURE` | Use HTTPS | `false` | ❌ (default: false) |
| `MINIO_REGION` | AWS region (S3 only) | `us-east-1` | ❌ (default: us-east-1) |

### OpenAI Configuration

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` | ✅ |
| `OPENAI_MODEL` | Embedding model | `text-embedding-3-small` | ❌ (default: text-embedding-3-small) |
| `OPENAI_EMBEDDING_DIMS` | Embedding dimensions | `1536` | ❌ (default: 1536) |
| `OPENAI_MAX_RETRIES` | Max retry attempts | `3` | ❌ (default: 3) |
| `OPENAI_TIMEOUT` | Request timeout (seconds) | `30` | ❌ (default: 30) |

## Application Configuration

### General Settings

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `APP_ENV` | Environment name | `production` | ❌ (default: development) |
| `APP_PORT` | Application port | `8000` | ❌ (default: 8000) |
| `APP_HOST` | Application host | `0.0.0.0` | ❌ (default: 0.0.0.0) |
| `APP_WORKERS` | Number of workers | `4` | ❌ (default: 1) |
| `APP_RELOAD` | Enable auto-reload | `false` | ❌ (default: false) |
| `APP_DEBUG` | Debug mode | `false` | ❌ (default: false) |

### Authentication & Security

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `JWT_SECRET_KEY` | JWT signing key | `your-secret-key` | ✅ |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` | ❌ (default: HS256) |
| `JWT_EXPIRATION_DELTA` | Token expiration (seconds) | `3600` | ❌ (default: 3600) |
| `JWT_REFRESH_DELTA` | Refresh token expiration | `604800` | ❌ (default: 604800) |
| `CORS_ORIGINS` | Allowed CORS origins | `["http://localhost:3000"]` | ❌ (default: ["*"]) |
| `CORS_ALLOW_CREDENTIALS` | Allow credentials | `true` | ❌ (default: true) |
| `API_KEY_HEADER` | API key header name | `X-API-Key` | ❌ (default: X-API-Key) |

### Logging Configuration

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `LOG_LEVEL` | Logging level | `INFO` | ❌ (default: INFO) |
| `LOG_FORMAT` | Log format | `json` | ❌ (default: json) |
| `LOG_FILE` | Log file path | `/var/log/secondbrain.log` | ❌ (default: none) |
| `LOG_MAX_BYTES` | Max log file size | `10485760` | ❌ (default: 10MB) |
| `LOG_BACKUP_COUNT` | Log file backup count | `5` | ❌ (default: 5) |

## Observability Configuration

### OpenTelemetry

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `OTEL_SERVICE_NAME` | Service name | `secondbrain` | ❌ (default: secondbrain) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP endpoint | `http://localhost:4317` | ❌ |
| `OTEL_EXPORTER_OTLP_HEADERS` | OTLP headers | `api-key=your-key` | ❌ |
| `OTEL_TRACES_EXPORTER` | Traces exporter | `otlp` | ❌ (default: otlp) |
| `OTEL_METRICS_EXPORTER` | Metrics exporter | `otlp` | ❌ (default: otlp) |
| `OTEL_LOGS_EXPORTER` | Logs exporter | `otlp` | ❌ (default: otlp) |
| `OTEL_RESOURCE_ATTRIBUTES` | Resource attributes | `env=prod,region=us-east` | ❌ |

### Prometheus Metrics

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `PROMETHEUS_PORT` | Metrics port | `9090` | ❌ (default: 9090) |
| `PROMETHEUS_ENABLED` | Enable metrics | `true` | ❌ (default: true) |
| `PROMETHEUS_PATH` | Metrics path | `/metrics` | ❌ (default: /metrics) |

## Performance & Optimization

### Caching Configuration

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `CACHE_TTL_DEFAULT` | Default cache TTL (seconds) | `300` | ❌ (default: 300) |
| `CACHE_TTL_MEMORY` | Memory cache TTL | `600` | ❌ (default: 600) |
| `CACHE_TTL_SEARCH` | Search cache TTL | `120` | ❌ (default: 120) |
| `CACHE_TTL_USER` | User cache TTL | `1800` | ❌ (default: 1800) |
| `CACHE_STRATEGY` | Cache strategy | `cache-aside` | ❌ (default: cache-aside) |

### Rate Limiting

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `RATE_LIMIT_ENABLED` | Enable rate limiting | `true` | ❌ (default: true) |
| `RATE_LIMIT_DEFAULT` | Default requests/hour | `1000` | ❌ (default: 1000) |
| `RATE_LIMIT_SEARCH` | Search requests/hour | `100` | ❌ (default: 100) |
| `RATE_LIMIT_UPLOAD` | Upload requests/hour | `50` | ❌ (default: 50) |
| `RATE_LIMIT_STORAGE` | Rate limit storage | `redis` | ❌ (default: redis) |

### Worker Configuration

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `WORKER_CONCURRENCY` | Worker concurrency | `4` | ❌ (default: 4) |
| `WORKER_PREFETCH_MULTIPLIER` | Prefetch multiplier | `2` | ❌ (default: 2) |
| `WORKER_MAX_TASKS_PER_CHILD` | Max tasks per child | `1000` | ❌ (default: 1000) |
| `WORKER_TASK_TIME_LIMIT` | Task time limit (seconds) | `300` | ❌ (default: 300) |

## Feature Flags

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `FEATURE_SESSIONS_ENABLED` | Enable sessions | `true` | ❌ (default: true) |
| `FEATURE_ATTACHMENTS_ENABLED` | Enable attachments | `true` | ❌ (default: true) |
| `FEATURE_SEARCH_HIGHLIGHTS` | Enable search highlights | `true` | ❌ (default: true) |
| `FEATURE_BULK_OPERATIONS` | Enable bulk operations | `true` | ❌ (default: true) |
| `FEATURE_WEBHOOKS` | Enable webhooks | `false` | ❌ (default: false) |

## Development & Testing

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `USE_MOCK_OPENAI` | Use mock OpenAI client | `true` | ❌ (default: false) |
| `USE_MOCK_DATABASE` | Use in-memory database | `true` | ❌ (default: false) |
| `TEST_DATABASE_URL` | Test database URL | `postgresql://...` | ❌ |
| `CI_ENVIRONMENT` | CI environment flag | `true` | ❌ (default: false) |

## Example Configuration Files

### Development (.env.development)

```bash
# Core Services
DATABASE_URL=postgresql://postgres:password@localhost:5432/secondbrain_dev
REDIS_URL=redis://localhost:6379/0
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# OpenAI
OPENAI_API_KEY=sk-development-key

# Security
JWT_SECRET_KEY=development-secret-key

# Application
APP_ENV=development
APP_DEBUG=true
APP_RELOAD=true
LOG_LEVEL=DEBUG

# Features
USE_MOCK_OPENAI=false
FEATURE_WEBHOOKS=true
```

### Production (.env.production)

```bash
# Core Services
DATABASE_URL=postgresql://prod_user:strong_password@db.example.com:5432/secondbrain
REDIS_URL=redis://:redis_password@redis.example.com:6379/0
RABBITMQ_URL=amqp://prod_user:strong_password@mq.example.com:5672/production
MINIO_ENDPOINT=s3.amazonaws.com
MINIO_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
MINIO_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
MINIO_SECURE=true

# OpenAI
OPENAI_API_KEY=sk-production-key

# Security
JWT_SECRET_KEY=ultra-secure-production-secret-key-change-me
CORS_ORIGINS=["https://app.example.com"]

# Application
APP_ENV=production
APP_DEBUG=false
APP_WORKERS=4
LOG_LEVEL=INFO

# Performance
DATABASE_POOL_SIZE=20
REDIS_MAX_CONNECTIONS=100
CACHE_TTL_DEFAULT=600
RATE_LIMIT_DEFAULT=10000

# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.example.com:4317
OTEL_EXPORTER_OTLP_HEADERS=api-key=your-observability-key
```

### Docker Compose Override

```yaml
# docker-compose.override.yml
version: '3.8'

services:
  api:
    env_file:
      - .env.development
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/secondbrain
      - REDIS_URL=redis://redis:6379/0
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
      - MINIO_ENDPOINT=minio:9000
```

## Environment Variable Validation

The application validates environment variables on startup:

```python
# src/config.py
from pydantic_settings import BaseSettings
from pydantic import validator

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    rabbitmq_url: str
    openai_api_key: str
    jwt_secret_key: str
    
    @validator("database_url")
    def validate_database_url(cls, v):
        if not v.startswith("postgresql://"):
            raise ValueError("Database URL must be PostgreSQL")
        return v
    
    @validator("jwt_secret_key")
    def validate_jwt_secret(cls, v):
        if len(v) < 32:
            raise ValueError("JWT secret must be at least 32 characters")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

## Security Best Practices

1. **Never commit `.env` files** to version control
2. **Use strong, unique values** for secrets and keys
3. **Rotate secrets regularly** (especially JWT keys)
4. **Use environment-specific** configuration files
5. **Encrypt sensitive values** in production
6. **Limit access** to production environment variables
7. **Audit access** to configuration regularly

## Troubleshooting

### Common Issues

1. **Missing Required Variable**
   ```
   ValueError: DATABASE_URL environment variable is required
   ```
   Solution: Ensure all required variables are set

2. **Invalid URL Format**
   ```
   ValueError: Invalid Redis URL format
   ```
   Solution: Check URL format matches expected pattern

3. **Connection Refused**
   ```
   ConnectionError: Cannot connect to Redis at localhost:6379
   ```
   Solution: Verify service is running and accessible

### Debug Environment Loading

```python
# Debug script
import os
from dotenv import load_dotenv

load_dotenv()

# Print all environment variables
for key, value in os.environ.items():
    if key.startswith(('DATABASE', 'REDIS', 'RABBITMQ')):
        # Mask sensitive values
        masked = value[:4] + '***' + value[-4:] if len(value) > 8 else '***'
        print(f"{key}={masked}")
```

## References

- [12-Factor App Configuration](https://12factor.net/config)
- [Pydantic Settings](https://docs.pydantic.dev/latest/usage/pydantic_settings/)
- [Docker Environment Variables](https://docs.docker.com/compose/environment-variables/)