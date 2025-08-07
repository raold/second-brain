# Second Brain v3.0.0 - Deployment Guide

## Overview

This guide covers deployment options for Second Brain v3.0.0, from local development to production deployments using Docker.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Production Deployment](#production-deployment)
5. [Configuration Management](#configuration-management)
6. [Database Setup](#database-setup)
7. [Monitoring & Health Checks](#monitoring--health-checks)
8. [Backup & Recovery](#backup--recovery)
9. [Security Considerations](#security-considerations)
10. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements
- **CPU**: 2+ cores (4+ recommended for production)
- **RAM**: 4GB minimum (8GB+ recommended)
- **Storage**: 20GB+ (depends on usage)
- **OS**: Linux, macOS, or Windows with WSL2

### Required Services
- PostgreSQL 16+ with pgvector extension
- Redis 7+
- Python 3.10+ (for local development)

### Optional Services
- Nginx (for reverse proxy)
- Prometheus/Grafana (for monitoring)

## Local Development

### Using Virtual Environment

```bash
# Clone repository
git clone https://github.com/yourusername/second-brain.git
cd second-brain

# Create virtual environment
python -m venv .venv
.venv/Scripts/activate  # Windows
source .venv/bin/activate  # Unix/macOS

# Install dependencies
.venv/Scripts/python.exe -m pip install -r config/requirements.txt

# Setup environment
cp .env.example .env.development
# Edit .env.development with your settings

# Start PostgreSQL and Redis (using Docker)
docker run -d --name postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=secondbrain \
  -p 5432:5432 \
  postgres:16

docker run -d --name redis \
  -p 6379:6379 \
  redis:7-alpine

# Run application
.venv/Scripts/python.exe -m uvicorn app.app:app --reload --host 0.0.0.0 --port 8000
```

## Docker Deployment

### Development Setup with Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:16
    container_name: secondbrain-postgres
    environment:
      POSTGRES_DB: secondbrain
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: secondbrain-redis
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: secondbrain-app
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/secondbrain
      REDIS_URL: redis://redis:6379
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      API_TOKENS: ${API_TOKENS}
      ENVIRONMENT: development
      LOG_LEVEL: INFO
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./app:/app/app  # For development hot-reload

volumes:
  postgres_data:
```

### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY config/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app
COPY .env.example .env

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Commands

```bash
# Build and start all services
docker-compose up --build -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down

# Remove everything including volumes
docker-compose down -v

# Execute commands in container
docker exec -it secondbrain-app /bin/bash

# Run tests in container
docker exec secondbrain-app pytest tests/
```

## Production Deployment

### Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  postgres:
    image: postgres:16
    container_name: secondbrain-postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - secondbrain-network
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: secondbrain-redis
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - secondbrain-network
    restart: unless-stopped

  app:
    image: secondbrain:latest
    container_name: secondbrain-app
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      API_TOKENS: ${API_TOKENS}
      SECRET_KEY: ${SECRET_KEY}
      ENVIRONMENT: production
      LOG_LEVEL: WARNING
    networks:
      - secondbrain-network
    restart: unless-stopped
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1'
          memory: 1G

  nginx:
    image: nginx:alpine
    container_name: secondbrain-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    networks:
      - secondbrain-network
    depends_on:
      - app
    restart: unless-stopped

networks:
  secondbrain-network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
```

### Nginx Configuration

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream secondbrain_app {
        server app:8000;
    }

    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        location / {
            proxy_pass http://secondbrain_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /health {
            proxy_pass http://secondbrain_app/health;
            access_log off;
        }
    }
}
```

## Configuration Management

### Environment Variables

Create `.env` file for production:

```bash
# Database
POSTGRES_DB=secondbrain
POSTGRES_USER=sbuser
POSTGRES_PASSWORD=secure-password-here
DATABASE_URL=postgresql://sbuser:secure-password-here@postgres:5432/secondbrain

# Redis
REDIS_PASSWORD=redis-secure-password
REDIS_URL=redis://:redis-secure-password@redis:6379

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Security
API_TOKENS=token1,token2,token3
SECRET_KEY=your-secret-key-for-jwt

# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### Configuration Best Practices

1. **Use Environment Variables**: Never hardcode secrets
2. **Separate Configs**: Different files for dev/staging/prod
3. **Validate on Startup**: Check all required configs
4. **Use Secrets Management**: Consider AWS Secrets Manager or similar

## Database Setup

### PostgreSQL with pgvector

```bash
# Install pgvector extension
docker exec -it secondbrain-postgres psql -U postgres -d secondbrain -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Verify installation
docker exec -it secondbrain-postgres psql -U postgres -d secondbrain -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

### Database Migrations

```bash
# Run migrations manually
docker exec -it secondbrain-app python scripts/migrate_database.py

# Or include in startup script
#!/bin/bash
# startup.sh
python scripts/migrate_database.py
uvicorn app.app:app --host 0.0.0.0 --port 8000
```

## Monitoring & Health Checks

### Health Check Endpoints

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed status
curl -H "api-key: your-token" http://localhost:8000/status

# Metrics
curl -H "api-key: your-token" http://localhost:8000/metrics
```

### Docker Health Checks

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Logging

```bash
# View application logs
docker-compose logs -f app

# Save logs to file
docker-compose logs app > app.log

# Log rotation (in docker-compose.yml)
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

## Backup & Recovery

### Database Backup

```bash
# Backup PostgreSQL
docker exec secondbrain-postgres pg_dump -U postgres secondbrain > backup_$(date +%Y%m%d_%H%M%S).sql

# Automated daily backup script
#!/bin/bash
BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker exec secondbrain-postgres pg_dump -U postgres secondbrain > "$BACKUP_DIR/backup_$TIMESTAMP.sql"

# Keep only last 7 days
find $BACKUP_DIR -name "backup_*.sql" -mtime +7 -delete
```

### Restore Database

```bash
# Restore from backup
docker exec -i secondbrain-postgres psql -U postgres secondbrain < backup_20250126_120000.sql
```

### Redis Backup

```bash
# Save Redis data
docker exec secondbrain-redis redis-cli BGSAVE

# Copy backup file
docker cp secondbrain-redis:/data/dump.rdb ./redis_backup.rdb
```

## Security Considerations

### 1. Network Security

```yaml
# Use internal networks
networks:
  internal:
    internal: true
  external:
    internal: false
```

### 2. Environment Variables

```bash
# Use Docker secrets for sensitive data
docker secret create db_password ./db_password.txt

# Reference in compose file
secrets:
  db_password:
    external: true
```

### 3. API Security

- Always use HTTPS in production
- Rotate API tokens regularly
- Implement rate limiting
- Use strong passwords

### 4. Container Security

```dockerfile
# Run as non-root user
USER appuser

# Minimal base images
FROM python:3.10-slim

# Security scanning
docker scan secondbrain:latest
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed

```bash
# Check PostgreSQL is running
docker-compose ps

# Test connection
docker exec -it secondbrain-app python -c "
from app.database import get_database
import asyncio
asyncio.run(get_database())
"
```

#### 2. Redis Connection Issues

```bash
# Test Redis connection
docker exec -it secondbrain-redis redis-cli ping

# Check Redis logs
docker logs secondbrain-redis
```

#### 3. Application Won't Start

```bash
# Check logs
docker-compose logs app

# Verify environment variables
docker exec secondbrain-app env | grep DATABASE_URL

# Run in debug mode
docker-compose run --rm app python -m app.app
```

#### 4. Performance Issues

```bash
# Check resource usage
docker stats

# Increase resources
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
```

### Debug Commands

```bash
# Interactive shell
docker exec -it secondbrain-app /bin/bash

# Python shell
docker exec -it secondbrain-app python

# Database shell
docker exec -it secondbrain-postgres psql -U postgres secondbrain

# Redis CLI
docker exec -it secondbrain-redis redis-cli
```

## Deployment Checklist

- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] pgvector extension installed
- [ ] SSL certificates configured
- [ ] Backups scheduled
- [ ] Monitoring setup
- [ ] Health checks passing
- [ ] Security scan completed
- [ ] Documentation updated

---

This deployment guide provides practical steps for deploying Second Brain v3.0.0. Always test deployments in a staging environment first.