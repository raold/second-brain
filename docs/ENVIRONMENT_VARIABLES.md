# Environment Variables Management

This document explains how environment variables are managed across different deployment environments in our CI/CD pipeline.

## 🏗️ Environment Structure

We use a multi-environment approach with separate configurations for:
- **Development** (local)
- **Staging** (pre-production testing)
- **Production** (live environment)

## 🔐 Required Environment Variables

### Core Application Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `OPENAI_API_KEY` | OpenAI API key for embeddings | ✅ | `sk-...` |
| `API_TOKENS` | Authentication tokens | ✅ | `token1,token2` |
| `OPENAI_EMBEDDING_MODEL` | OpenAI embedding model | ❌ | `text-embedding-3-small` |
| `LOG_PATH` | Log file path | ❌ | `logs/processor.log` |
| `LOG_LEVEL` | Logging level | ❌ | `INFO` |

### Qdrant Configuration

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `QDRANT_HOST` | Qdrant server hostname | ❌ | `localhost` |
| `QDRANT_PORT` | Qdrant server port | ❌ | `6333` |
| `QDRANT_COLLECTION_NAME` | Collection name | ❌ | `memories` |

### Environment-Specific Variables

| Variable | Description | Environment | Example |
|----------|-------------|-------------|---------|
| `APP_ENV` | Application environment | All | `development`, `staging`, `production` |
| `STAGING_API_TOKENS` | Staging auth tokens | Staging | `staging-token1,staging-token2` |
| `PRODUCTION_API_TOKENS` | Production auth tokens | Production | `prod-token1,prod-token2` |
| `DOCKER_REGISTRY` | Docker registry URL | Staging/Production | `ghcr.io/username` |

## 🚀 GitHub Secrets Setup

### Required Secrets

Add these secrets in your GitHub repository settings:

1. **Go to**: `Settings` → `Secrets and variables` → `Actions`
2. **Add the following secrets**:

```bash
# Core Application
OPENAI_API_KEY=sk-your-openai-key-here

# Docker Registry
DOCKER_REGISTRY=ghcr.io/your-username

# Environment-Specific Tokens
STAGING_API_TOKENS=staging-token1,staging-token2
PRODUCTION_API_TOKENS=prod-token1,prod-token2
```

### Optional Secrets

```bash
# Additional configuration
STAGING_OPENAI_MODEL=text-embedding-3-small
PRODUCTION_OPENAI_MODEL=text-embedding-3-small
STAGING_LOG_LEVEL=INFO
PRODUCTION_LOG_LEVEL=WARNING
```

## 📁 Environment-Specific Configurations

### Development (Local)

**File**: `.env`
```bash
OPENAI_API_KEY=your_openai_key_here
API_TOKENS=your_token_here
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
LOG_PATH=logs/processor.log
LOG_LEVEL=INFO
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=memories
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=memories
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
TTS_API_KEY=elevenlabs-your-key-here
PLUGINS_ENABLED=reminder,webhook,file_search
ELECTRON_API_URL=http://localhost:8000
FEEDBACK_API_ENABLED=true
```

### Staging

**File**: `docker-compose.staging.yml`
```yaml
environment:
  APP_ENV: staging
  OPENAI_API_KEY: ${OPENAI_API_KEY}
  API_TOKENS: ${STAGING_API_TOKENS}
  OPENAI_EMBEDDING_MODEL: text-embedding-3-small
  LOG_PATH: logs/processor-staging.log
  LOG_LEVEL: INFO
  QDRANT_HOST: qdrant-staging
  QDRANT_PORT: 6333
  QDRANT_COLLECTION_NAME: memories-staging
```

### Production

**File**: `docker-compose.production.yml`
```yaml
environment:
  APP_ENV: production
  OPENAI_API_KEY: ${OPENAI_API_KEY}
  API_TOKENS: ${PRODUCTION_API_TOKENS}
  OPENAI_EMBEDDING_MODEL: text-embedding-3-small
  LOG_PATH: logs/processor-production.log
  LOG_LEVEL: WARNING
  QDRANT_HOST: qdrant-production
  QDRANT_PORT: 6333
  QDRANT_COLLECTION_NAME: memories-production
```

## 🔄 CI/CD Pipeline Integration

### Environment Variables in Workflows

The deployment workflow automatically uses the correct environment variables:

```yaml
- name: Deploy to staging
  env:
    DOCKER_REGISTRY: ${{ secrets.DOCKER_REGISTRY }}
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    STAGING_API_TOKENS: ${{ secrets.STAGING_API_TOKENS }}
  run: |
    docker-compose -f docker-compose.staging.yml up -d
```

### Environment Protection

GitHub Environments provide additional security:

1. **Staging Environment**: Requires approval for deployments
2. **Production Environment**: Requires approval and specific reviewers
3. **Secret Protection**: Environment-specific secrets are only available in their respective environments

## 🛡️ Security Best Practices

### 1. Secret Rotation
- Rotate API keys regularly
- Use different tokens for each environment
- Monitor secret usage

### 2. Access Control
- Limit who can access production secrets
- Use environment protection rules
- Audit secret access regularly

### 3. Validation
- Validate environment variables at startup
- Use default values where appropriate
- Log configuration (without sensitive data)

## 🔍 Troubleshooting

### Common Issues

1. **Missing Environment Variables**
   ```bash
   # Check if variable is set
   echo $VARIABLE_NAME
   
   # Check in Docker container
   docker exec container_name env | grep VARIABLE_NAME
   ```

2. **Incorrect Variable Names**
   - Ensure exact case matching
   - Check for typos in variable names
   - Verify in GitHub secrets

3. **Environment-Specific Issues**
   - Verify correct environment is being used
   - Check environment protection rules
   - Ensure secrets are available in the environment

### Debug Commands

```bash
# List all environment variables
env | sort

# Check specific variable
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:-NOT_SET}"

# Validate configuration
python -c "from app.config import settings; print(settings)"
```

## 📊 Monitoring and Validation

### Health Check Endpoints

Each environment has health check endpoints:

- **Development**: `http://localhost:8000/health`
- **Staging**: `http://localhost:8001/health`
- **Production**: `http://localhost:8000/health`

### Configuration Validation

The application validates configuration on startup:

```python
# Example validation
if not settings.openai_api_key:
    raise ValueError("OPENAI_API_KEY is required")
```

## 🎯 Next Steps

1. **Set up GitHub secrets** for your repository
2. **Configure environment protection rules**
3. **Test deployment to staging**
4. **Monitor environment variable usage**
5. **Set up alerts for missing variables**

## 📚 Additional Resources

- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [GitHub Environments](https://docs.github.com/en/actions/deployment/targeting-different-environments)
- [Docker Compose Environment Variables](https://docs.docker.com/compose/environment-variables/) 
- [Testing Guide](./TESTING.md) 