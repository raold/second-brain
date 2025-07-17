# Deployment Guide - Second Brain v2.3.0

## Overview

Second Brain v2.3.0 is designed for simple, straightforward deployment with minimal infrastructure requirements. The system consists of a single FastAPI application and PostgreSQL database with pgvector extension.

## Prerequisites

### **System Requirements**
- Python 3.10+
- PostgreSQL 15+ with pgvector extension
- OpenAI API key
- 512MB RAM minimum (1GB recommended)
- 1GB disk space for application and database

### **Dependencies**
```bash
# Core dependencies only (5 packages)
pip install -r requirements-minimal.txt
```

## Local Development

### **Quick Start**
```bash
# Clone repository
git clone https://github.com/raold/second-brain.git
cd second-brain

# Install dependencies
pip install -r requirements-minimal.txt

# Setup environment
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python setup_db.py

# Run application
python -m app.app
```

### **Environment Configuration**
Create a `.env` file with the following variables:

```bash
# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=secondbrain
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Authentication
API_TOKENS=your_comma_separated_tokens_here
```

### **Database Setup**
```bash
# Ensure PostgreSQL is running
# Install pgvector extension
# Run database setup script
python setup_db.py
```

## Docker Deployment

### **Docker Compose (Recommended)**
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_HOST=db
      - POSTGRES_PORT=5432
      - POSTGRES_DB=secondbrain
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - API_TOKENS=${API_TOKENS}
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: pgvector/pgvector:pg15
    environment:
      - POSTGRES_DB=secondbrain
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

volumes:
  postgres_data:
```

### **Build and Run**
```bash
# Build and start services
docker-compose up -d

# Initialize database
docker-compose exec app python setup_db.py

# View logs
docker-compose logs -f app
```

## Production Deployment

### **Environment Variables**
```bash
# Production Environment
export POSTGRES_HOST=your_postgres_host
export POSTGRES_PORT=5432
export POSTGRES_DB=secondbrain
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=secure_password

export OPENAI_API_KEY=your_openai_api_key
export OPENAI_EMBEDDING_MODEL=text-embedding-3-small

export API_TOKENS=secure_production_tokens
```

### **PostgreSQL Setup**
```sql
-- Install pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create database
CREATE DATABASE secondbrain;

-- Create user (if needed)
CREATE USER postgres WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE secondbrain TO postgres;
```

### **Application Deployment**
```bash
# Install dependencies
pip install -r requirements-minimal.txt

# Initialize database
python setup_db.py

# Run with production server
uvicorn app.app:app --host v2.3.0.0 --port 8000 --workers 4
```

## Cloud Deployment

### **AWS Deployment**
```bash
# RDS PostgreSQL with pgvector
aws rds create-db-instance \
  --db-instance-identifier secondbrain-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15.4 \
  --master-username postgres \
  --master-user-password secure_password \
  --allocated-storage 20

# ECS or Lambda deployment
# Set environment variables in AWS console
```

### **Google Cloud Deployment**
```bash
# Cloud SQL PostgreSQL
gcloud sql instances create secondbrain-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# Cloud Run deployment
gcloud run deploy secondbrain \
  --image gcr.io/project-id/secondbrain:latest \
  --platform managed \
  --region us-central1 \
  --set-env-vars POSTGRES_HOST=db_host
```

### **Azure Deployment**
```bash
# Azure Database for PostgreSQL
az postgres server create \
  --resource-group myResourceGroup \
  --name secondbrain-db \
  --location eastus \
  --admin-user postgres \
  --admin-password secure_password \
  --sku-name B_Gen5_1

# Container Instances deployment
az container create \
  --resource-group myResourceGroup \
  --name secondbrain-app \
  --image secondbrain:latest \
  --ports 8000 \
  --environment-variables POSTGRES_HOST=db_host
```

## Configuration

### **Environment Variables**
| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `localhost` | PostgreSQL host address |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `secondbrain` | Database name |
| `POSTGRES_USER` | `postgres` | Database user |
| `POSTGRES_PASSWORD` | `postgres` | Database password |
| `OPENAI_API_KEY` | Required | OpenAI API key |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `API_TOKENS` | Required | Comma-separated API tokens |

### **Database Configuration**
```python
# Connection pool settings (in database.py)
pool = await asyncpg.create_pool(
    db_url,
    min_size=1,    # Minimum connections
    max_size=10,   # Maximum connections
    command_timeout=60
)
```

## Monitoring

### **Health Checks**
```bash
# Health check endpoint
curl http://localhost:8000/health

# Response format
{
    "status": "healthy",
    "service": "second-brain"
}
```

### **Logging**
```python
# Application logs
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://v2.3.0.0:8000
```

### **Metrics**
- Response time monitoring
- Database connection health
- OpenAI API call success rates
- Memory usage and performance

## Scaling

### **Horizontal Scaling**
```bash
# Multiple application instances
uvicorn app.app:app --host v2.3.0.0 --port 8000 --workers 4

# Load balancer configuration
# Route traffic to multiple instances
```

### **Database Scaling**
```sql
-- PostgreSQL read replicas
CREATE PUBLICATION secondbrain_pub FOR TABLE memories;

-- Connection pooling
-- Use pgbouncer or similar for connection management
```

### **Caching (Optional)**
```python
# Optional Redis for frequently accessed data
# Can be added in future versions if needed
```

## Security

### **Authentication**
- Use strong API tokens
- Rotate tokens regularly
- Implement rate limiting in production
- Use HTTPS in production

### **Database Security**
- Use strong database passwords
- Enable SSL/TLS connections
- Restrict database access to application only
- Regular security updates

### **Network Security**
- Firewall configuration
- VPC/subnet isolation
- Security groups and network ACLs
- Regular security audits

## Backup and Recovery

### **Database Backup**
```bash
# PostgreSQL backup
pg_dump -h localhost -U postgres secondbrain > backup.sql

# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h $POSTGRES_HOST -U $POSTGRES_USER $POSTGRES_DB > "backup_$DATE.sql"
```

### **Restore Process**
```bash
# Restore from backup
psql -h localhost -U postgres secondbrain < backup.sql

# Verify restore
python -c "
import asyncio
from app.database import get_database

async def verify():
    db = await get_database()
    memories = await db.get_all_memories(limit=10)
    print(f'Restored {len(memories)} memories')

asyncio.run(verify())
"
```

## Troubleshooting

### **Common Issues**

#### **Database Connection Failed**
```bash
# Check PostgreSQL is running
systemctl status postgresql

# Check connection
psql -h localhost -U postgres -d secondbrain

# Check pgvector extension
psql -d secondbrain -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

#### **OpenAI API Errors**
```bash
# Check API key
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models

# Check rate limits
# Monitor API usage in OpenAI dashboard
```

#### **Application Startup Issues**
```bash
# Check environment variables
env | grep -E "(POSTGRES|OPENAI|API_TOKENS)"

# Check logs
tail -f /var/log/secondbrain/app.log

# Test database connection
python -c "
import asyncio
from app.database import get_database
asyncio.run(get_database())
"
```

### **Performance Issues**
```bash
# Check database performance
SELECT * FROM pg_stat_activity WHERE datname = 'secondbrain';

# Monitor memory usage
top -p $(pgrep -f "app.app")

# Check API response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health
```

## Maintenance

### **Regular Tasks**
- Monitor database size and performance
- Rotate API tokens
- Update dependencies
- Backup database regularly
- Monitor OpenAI API usage

### **Updates**
```bash
# Update application
git pull origin main
pip install -r requirements-minimal.txt

# Run tests
python -m pytest test_refactored.py -v

# Restart application
systemctl restart secondbrain
```

---

**Second Brain v2.3.0** - Simple, Scalable, and Secure Deployment
