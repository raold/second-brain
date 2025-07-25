# Second Brain Staging Deployment Guide

## Overview

This guide provides instructions for deploying and managing the Second Brain staging environment using Docker Compose.

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- 4GB RAM minimum (8GB recommended)
- 20GB free disk space
- Valid OpenAI API key

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/second-brain.git
cd second-brain
```

### 2. Configure Environment

Copy the staging environment template and update values:

```bash
cp .env.staging .env
```

Edit `.env` and set:
- `OPENAI_API_KEY` - Your OpenAI API key
- `SECRET_KEY` - Generate a secure secret key
- Database and Redis passwords
- Any other environment-specific settings

### 3. Start Staging Environment

```bash
# Start all services
docker-compose -f docker-compose.staging.yml up -d

# Or start with build
docker-compose -f docker-compose.staging.yml up -d --build

# View logs
docker-compose -f docker-compose.staging.yml logs -f
```

### 4. Verify Deployment

Check service health:

```bash
# Check running containers
docker-compose -f docker-compose.staging.yml ps

# Test application health
curl http://localhost:8000/health

# Access services
# - Application: http://localhost:8000
# - Adminer: http://localhost:8081
# - Grafana: http://localhost:3001
```

## Services

### Core Services

1. **PostgreSQL Database** (`staging-secondbrain-postgres`)
   - Port: 5432 (internal only)
   - Database: secondbrain_staging
   - Includes pgvector extension

2. **Redis Cache** (`staging-secondbrain-redis`)
   - Port: 6379 (internal only)
   - Configured with persistence and memory limits

3. **Application** (`staging-secondbrain-app`)
   - Port: 8000
   - Auto-restarts on failure
   - Runs migrations on startup

### Supporting Services

4. **Nginx Reverse Proxy** (`staging-secondbrain-nginx`)
   - HTTP: Port 80
   - HTTPS: Port 443 (if configured)
   - Rate limiting and caching

5. **Prometheus** (`staging-secondbrain-prometheus`)
   - Metrics collection
   - 15-second scrape interval

6. **Grafana** (`staging-secondbrain-grafana`)
   - Port: 3001
   - Default login: admin / (see .env)
   - Pre-configured dashboards

7. **Adminer** (`staging-secondbrain-adminer`)
   - Port: 8081
   - Database administration UI

## Common Operations

### View Logs

```bash
# All services
docker-compose -f docker-compose.staging.yml logs -f

# Specific service
docker-compose -f docker-compose.staging.yml logs -f app

# Last 100 lines
docker-compose -f docker-compose.staging.yml logs --tail=100 app
```

### Execute Commands

```bash
# Run database migrations
docker-compose -f docker-compose.staging.yml exec app alembic upgrade head

# Access application shell
docker-compose -f docker-compose.staging.yml exec app python

# Database shell
docker-compose -f docker-compose.staging.yml exec postgres psql -U secondbrain -d secondbrain_staging
```

### Scale Services

```bash
# Scale application instances
docker-compose -f docker-compose.staging.yml up -d --scale app=3
```

### Backup Database

```bash
# Create backup
docker-compose -f docker-compose.staging.yml exec postgres \
  pg_dump -U secondbrain secondbrain_staging > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
docker-compose -f docker-compose.staging.yml exec -T postgres \
  psql -U secondbrain secondbrain_staging < backup_20240101_120000.sql
```

## Monitoring

### Metrics

- Application metrics: http://localhost:8000/metrics
- Prometheus: http://localhost:9090
- Grafana dashboards: http://localhost:3001

### Health Checks

All services include health checks:

```bash
# Check health status
docker-compose -f docker-compose.staging.yml ps

# Manual health check
curl http://localhost:8000/health
```

### Logs

Application logs are stored in:
- Container logs: `docker-compose logs`
- Application logs: `staging_logs` volume
- Nginx logs: `staging_nginx_logs` volume

## Troubleshooting

### Service Won't Start

1. Check logs: `docker-compose -f docker-compose.staging.yml logs [service]`
2. Verify environment variables: `docker-compose -f docker-compose.staging.yml config`
3. Check port conflicts: `netstat -tulpn | grep [port]`

### Database Connection Issues

```bash
# Test database connection
docker-compose -f docker-compose.staging.yml exec app python scripts/wait_for_db.py

# Check database logs
docker-compose -f docker-compose.staging.yml logs postgres
```

### Performance Issues

1. Check resource usage:
   ```bash
   docker stats
   ```

2. Review application metrics in Grafana

3. Check slow queries in PostgreSQL

### Reset Environment

```bash
# Stop and remove everything
docker-compose -f docker-compose.staging.yml down -v

# Remove all data
docker volume rm staging_secondbrain_postgres_data
docker volume rm staging_secondbrain_redis_data

# Rebuild and start fresh
docker-compose -f docker-compose.staging.yml up -d --build
```

## Security Considerations

1. **Change Default Passwords**: Update all passwords in `.env` before deployment
2. **Network Isolation**: Services communicate on internal network
3. **Non-root Containers**: Application runs as non-root user
4. **Environment Variables**: Never commit `.env` files
5. **SSL/TLS**: Configure nginx with SSL certificates for production

## Maintenance

### Regular Tasks

1. **Monitor disk usage**: Volumes can grow over time
2. **Update images**: Pull latest base images regularly
3. **Backup data**: Schedule regular database backups
4. **Review logs**: Check for errors and warnings
5. **Update dependencies**: Keep packages up to date

### Updating the Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.staging.yml up -d --build

# Run migrations if needed
docker-compose -f docker-compose.staging.yml exec app alembic upgrade head
```

## Advanced Configuration

### Custom Nginx Configuration

Edit `nginx/staging.conf` and restart:

```bash
docker-compose -f docker-compose.staging.yml restart nginx
```

### Add SSL Certificates

1. Place certificates in `nginx/ssl/`
2. Uncomment HTTPS server block in `nginx/staging.conf`
3. Update `NGINX_HTTPS_PORT` in `.env`
4. Restart nginx

### Configure Monitoring Alerts

1. Access Grafana: http://localhost:3001
2. Configure alert channels
3. Set up alert rules in dashboards

## Support

For issues or questions:
1. Check logs first
2. Review this documentation
3. Check GitHub issues
4. Contact the development team