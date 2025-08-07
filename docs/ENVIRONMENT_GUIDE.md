# Environment Configuration Guide

## Overview

Second Brain v4.0.0 uses a **single, unified environment configuration system** with:
- One template file: `.env.example`
- One local file: `.env` (gitignored)
- Centralized management: `app/core/env_manager.py`
- Type-safe access: `app/config.py`

## Quick Start

### 1. Local Development Setup

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your actual values
nano .env  # or use your preferred editor

# Add your OpenAI API key (required for AI features)
OPENAI_API_KEY=sk-proj-your_actual_key_here
```

### 2. Minimal Configuration

For basic local development, you only need:

```bash
# .env
OPENAI_API_KEY=sk-proj-your_actual_key_here
```

Everything else has sensible defaults!

## Environment Files

### Files We Use

| File | Purpose | Tracked in Git | When to Use |
|------|---------|----------------|-------------|
| `.env.example` | Template with all options | ✅ Yes | Reference for all available settings |
| `.env` | Your local configuration | ❌ No | Local development |

### Files We DON'T Use Anymore

We've eliminated these redundant files:
- ❌ `.env.development` - Use `.env` instead
- ❌ `.env.staging` - Use environment variables in staging
- ❌ `.env.test` - Use `.env` or CI environment variables
- ❌ `.env.local` - Use `.env` instead
- ❌ `.env.production` - Use environment variables in production

## Configuration Categories

### 🔧 Core Settings

```bash
# Environment mode
ENVIRONMENT=development  # development, staging, production

# Database (PostgreSQL)
DATABASE_URL=postgresql://user:password@localhost:5432/secondbrain
# OR use individual settings:
POSTGRES_USER=postgres
POSTGRES_PASSWORD=yourpassword
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=secondbrain
```

### 🤖 AI Configuration

```bash
# OpenAI (Required for AI features)
OPENAI_API_KEY=sk-proj-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-4

# Anthropic (Optional)
ANTHROPIC_API_KEY=sk-ant-...
```

### 🔒 Security

```bash
# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here  # Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_ALGORITHM=HS256
JWT_EXPIRATION_DELTA=3600

# API Authentication
API_TOKENS=token1,token2,token3
```

### 🚀 Application

```bash
# Server
HOST=127.0.0.1  # Use 127.0.0.1 for security, not 0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
```

### 🎛️ Feature Flags

```bash
# Mocking (for development/testing)
USE_MOCK_DATABASE=false  # Use in-memory database
USE_MOCK_OPENAI=false    # Mock AI responses

# Features
FEATURE_SESSIONS_ENABLED=true
FEATURE_ATTACHMENTS_ENABLED=true
ENABLE_TELEMETRY=false
ENABLE_ANALYTICS=false
```

## Environment-Specific Configuration

### Development

```bash
# .env for local development
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
USE_MOCK_DATABASE=false  # Set to true if no PostgreSQL
ENABLE_HOT_RELOAD=true
```

### Production

```bash
# Use environment variables from your hosting provider
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
HOST=127.0.0.1  # Never use 0.0.0.0 in production
JWT_SECRET_KEY=<strong-random-key>
DATABASE_URL=<production-database-url>
```

### Testing

```bash
# For automated tests
ENVIRONMENT=test
USE_MOCK_DATABASE=true
USE_MOCK_OPENAI=true
LOG_LEVEL=ERROR
```

## Accessing Configuration in Code

### Using the Config Class

```python
from app.config import Config

# Access configuration
if Config.IS_DEVELOPMENT:
    print("Running in development mode")

# Check features
if Config.is_ai_enabled():
    # Use OpenAI
    api_key = Config.OPENAI_API_KEY

# Validate for production
issues = Config.validate()
if issues:
    print(f"Configuration issues: {issues}")
```

### Using Environment Manager Directly

```python
from app.core.env_manager import get_env_manager

env = get_env_manager()

# Type-safe access
port = env.get_int("PORT", 8000)
debug = env.get_bool("DEBUG", False)
tokens = env.get_list("API_TOKENS", [])

# Check environment
if env.is_production():
    # Production-specific logic
    pass
```

## Production Deployment

### Best Practices

1. **Never commit `.env` files with real values**
2. **Use environment variables from your hosting provider**
3. **Rotate secrets regularly**
4. **Use secret management services:**
   - AWS Secrets Manager
   - Azure Key Vault
   - Google Secret Manager
   - HashiCorp Vault

### Example: Heroku

```bash
heroku config:set ENVIRONMENT=production
heroku config:set DATABASE_URL=<your-database-url>
heroku config:set OPENAI_API_KEY=<your-api-key>
heroku config:set JWT_SECRET_KEY=<strong-random-key>
```

### Example: Docker

```dockerfile
# Dockerfile
ENV ENVIRONMENT=production

# docker-compose.yml
services:
  app:
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=${DATABASE_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
```

### Example: Kubernetes

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: second-brain-secrets
stringData:
  OPENAI_API_KEY: "your-api-key"
  JWT_SECRET_KEY: "your-secret-key"
---
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: second-brain
        envFrom:
        - secretRef:
            name: second-brain-secrets
```

## Validation

### Run Configuration Check

```python
# In your app startup
from app.config import Config

# Check configuration
summary = Config.get_summary()
print(f"Configuration: {summary}")

# Validate for production
if Config.IS_PRODUCTION:
    issues = Config.validate()
    if issues:
        raise ValueError(f"Production configuration issues: {issues}")
```

### Security Check Script

```bash
# Check for exposed secrets
python scripts/check_secrets.py
```

## Troubleshooting

### Common Issues

#### Issue: "OPENAI_API_KEY not set"
**Solution**: Add your OpenAI API key to `.env`:
```bash
OPENAI_API_KEY=sk-proj-your_actual_key_here
```

#### Issue: "Database connection failed"
**Solution**: Either:
1. Set up PostgreSQL and configure `DATABASE_URL`
2. Use mock database: `USE_MOCK_DATABASE=true`

#### Issue: "JWT_SECRET_KEY using default"
**Solution**: Generate a secure key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Environment Precedence

1. System environment variables (highest priority)
2. `.env` file
3. Default values in code (lowest priority)

## Migration from Old System

If you're upgrading from an older version:

1. **Delete old env files:**
   ```bash
   rm -f .env.development .env.staging .env.test .env.local
   ```

2. **Create new `.env` from template:**
   ```bash
   cp .env.example .env
   ```

3. **Copy your API keys and settings to `.env`**

4. **Test configuration:**
   ```python
   from app.config import Config
   print(Config.get_summary())
   ```

## Summary

The new environment system provides:
- ✅ **Single source of truth** (`.env.example`)
- ✅ **Type-safe access** (env_manager.py)
- ✅ **Automatic validation** (production checks)
- ✅ **Secure by default** (sensitive value masking)
- ✅ **Environment-aware** (dev/staging/prod modes)
- ✅ **Backward compatible** (existing code works)

No more confusion with multiple env files!