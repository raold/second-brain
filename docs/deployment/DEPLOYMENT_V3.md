# Second Brain v3.0.0 - Deployment Guide

## Overview

This guide covers deployment options for Second Brain v3.0.0, from local development to production cloud deployments.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Cloud Deployments](#cloud-deployments)
6. [Configuration Management](#configuration-management)
7. [Monitoring & Observability](#monitoring--observability)
8. [Backup & Recovery](#backup--recovery)
9. [Security Considerations](#security-considerations)

## Prerequisites

### System Requirements
- **CPU**: 2+ cores (4+ recommended for production)
- **RAM**: 4GB minimum (8GB+ recommended)
- **Storage**: 20GB+ (depends on usage)
- **OS**: Linux, macOS, or Windows with WSL2

### Required Services
- PostgreSQL 16+ with pgvector extension
- Redis 7+
- RabbitMQ 3.12+
- MinIO or S3-compatible storage

### Optional Services
- OpenTelemetry Collector
- Prometheus
- Grafana
- Nginx (for reverse proxy)

## Local Development

### Using Docker Compose

```bash
# Clone repository
git clone https://github.com/yourusername/second-brain.git
cd second-brain

# Copy environment configuration
cp .env.example .env

# Start all services
docker-compose -f docker-compose.dev.yml up -d

# Check service health
docker-compose ps

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

### Manual Setup

```bash
# Install Python dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements-v3.txt

# Start PostgreSQL with pgvector
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=secondbrain \
  -p 5432:5432 \
  ankane/pgvector:v0.5.1-pg16

# Start Redis
docker run -d \
  --name redis \
  -p 6379:6379 \
  redis:7-alpine

# Start RabbitMQ
docker run -d \
  --name rabbitmq \
  -e RABBITMQ_DEFAULT_USER=admin \
  -e RABBITMQ_DEFAULT_PASS=password \
  -p 5672:5672 \
  -p 15672:15672 \
  rabbitmq:3-management

# Start MinIO
docker run -d \
  --name minio \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  -p 9000:9000 \
  -p 9001:9001 \
  minio/minio server /data --console-address ":9001"

# Run database migrations
alembic upgrade head

# Start the application
uvicorn src.main:app --reload
```

## Docker Deployment

### Production Docker Image

```dockerfile
# Build production image
docker build -f docker/Dockerfile -t secondbrain:v3.0.0 .

# Run with environment variables
docker run -d \
  --name secondbrain \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e REDIS_URL=redis://host:6379 \
  -e RABBITMQ_URL=amqp://user:pass@host:5672/ \
  -e MINIO_ENDPOINT=host:9000 \
  -e MINIO_ACCESS_KEY=access_key \
  -e MINIO_SECRET_KEY=secret_key \
  -e OPENAI_API_KEY=your_key \
  secondbrain:v3.0.0
```

### Docker Compose Production

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  api:
    image: secondbrain:v3.0.0
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/secondbrain
      - REDIS_URL=redis://redis:6379
      - RABBITMQ_URL=amqp://admin:password@rabbitmq:5672/
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=minioadmin
      - MINIO_SECRET_KEY=minioadmin
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
      minio:
        condition: service_healthy
    ports:
      - "8000:8000"
    restart: unless-stopped

  worker:
    image: secondbrain:v3.0.0
    command: python -m src.cli.worker
    environment:
      # Same as API
    depends_on:
      - api
    restart: unless-stopped

  postgres:
    image: ankane/pgvector:v0.5.1-pg16
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=secondbrain
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  rabbitmq:
    image: rabbitmq:3-management
    environment:
      - RABBITMQ_DEFAULT_USER=admin
      - RABBITMQ_DEFAULT_PASS=password
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 5

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - api

volumes:
  postgres_data:
  redis_data:
  rabbitmq_data:
  minio_data:
```

## Kubernetes Deployment

### Helm Chart Installation

```bash
# Add Helm repository
helm repo add secondbrain https://charts.secondbrain.io
helm repo update

# Install with custom values
helm install secondbrain secondbrain/secondbrain \
  --namespace secondbrain \
  --create-namespace \
  --values values.yaml
```

### Manual Kubernetes Deployment

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: secondbrain

---
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: secondbrain-config
  namespace: secondbrain
data:
  APP_ENV: "production"
  OTEL_SERVICE_NAME: "secondbrain"
  OTEL_EXPORTER_OTLP_ENDPOINT: "http://otel-collector:4317"

---
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: secondbrain-secrets
  namespace: secondbrain
type: Opaque
stringData:
  DATABASE_URL: "postgresql://user:pass@postgres:5432/secondbrain"
  REDIS_URL: "redis://redis:6379"
  RABBITMQ_URL: "amqp://admin:password@rabbitmq:5672/"
  OPENAI_API_KEY: "your-api-key"
  MINIO_ACCESS_KEY: "minioadmin"
  MINIO_SECRET_KEY: "minioadmin"

---
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secondbrain-api
  namespace: secondbrain
spec:
  replicas: 3
  selector:
    matchLabels:
      app: secondbrain-api
  template:
    metadata:
      labels:
        app: secondbrain-api
    spec:
      containers:
      - name: api
        image: secondbrain:v3.0.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: secondbrain-secrets
              key: DATABASE_URL
        envFrom:
        - configMapRef:
            name: secondbrain-config
        - secretRef:
            name: secondbrain-secrets
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: secondbrain-api
  namespace: secondbrain
spec:
  selector:
    app: secondbrain-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP

---
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: secondbrain-ingress
  namespace: secondbrain
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.secondbrain.example.com
    secretName: secondbrain-tls
  rules:
  - host: api.secondbrain.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: secondbrain-api
            port:
              number: 80

---
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: secondbrain-api-hpa
  namespace: secondbrain
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: secondbrain-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Cloud Deployments

### AWS Deployment

#### Using ECS Fargate

```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_URI
docker build -t secondbrain:v3.0.0 .
docker tag secondbrain:v3.0.0 $ECR_URI/secondbrain:v3.0.0
docker push $ECR_URI/secondbrain:v3.0.0

# Deploy using CloudFormation
aws cloudformation create-stack \
  --stack-name secondbrain \
  --template-body file://aws/cloudformation.yml \
  --parameters \
    ParameterKey=ImageUri,ParameterValue=$ECR_URI/secondbrain:v3.0.0 \
    ParameterKey=DatabasePassword,ParameterValue=secure_password
```

#### AWS Architecture
- **Compute**: ECS Fargate or EKS
- **Database**: RDS PostgreSQL with pgvector
- **Cache**: ElastiCache Redis
- **Queue**: Amazon MQ (RabbitMQ) or SQS
- **Storage**: S3
- **Load Balancer**: ALB
- **CDN**: CloudFront

### Google Cloud Platform

#### Using Cloud Run

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/$PROJECT_ID/secondbrain:v3.0.0

# Deploy to Cloud Run
gcloud run deploy secondbrain \
  --image gcr.io/$PROJECT_ID/secondbrain:v3.0.0 \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="DATABASE_URL=$DB_URL,REDIS_URL=$REDIS_URL"
```

#### GCP Architecture
- **Compute**: Cloud Run or GKE
- **Database**: Cloud SQL PostgreSQL
- **Cache**: Memorystore Redis
- **Queue**: Pub/Sub
- **Storage**: Cloud Storage
- **Load Balancer**: Cloud Load Balancing
- **CDN**: Cloud CDN

### Azure Deployment

#### Using Container Instances

```bash
# Build and push to ACR
az acr build --registry $ACR_NAME --image secondbrain:v3.0.0 .

# Deploy container group
az container create \
  --resource-group secondbrain-rg \
  --name secondbrain \
  --image $ACR_NAME.azurecr.io/secondbrain:v3.0.0 \
  --cpu 2 \
  --memory 4 \
  --environment-variables \
    DATABASE_URL=$DB_URL \
    REDIS_URL=$REDIS_URL
```

#### Azure Architecture
- **Compute**: Container Instances or AKS
- **Database**: Database for PostgreSQL
- **Cache**: Cache for Redis
- **Queue**: Service Bus
- **Storage**: Blob Storage
- **Load Balancer**: Application Gateway
- **CDN**: Azure CDN

## Configuration Management

### Environment Variables

```bash
# Core Configuration
APP_ENV=production
APP_PORT=8000
LOG_LEVEL=info

# Database
DATABASE_URL=postgresql://user:password@host:5432/secondbrain
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Redis
REDIS_URL=redis://host:6379
REDIS_MAX_CONNECTIONS=50
REDIS_TTL=3600

# RabbitMQ
RABBITMQ_URL=amqp://user:password@host:5672/
RABBITMQ_PREFETCH_COUNT=10

# MinIO/S3
MINIO_ENDPOINT=host:9000
MINIO_ACCESS_KEY=access_key
MINIO_SECRET_KEY=secret_key
MINIO_BUCKET=secondbrain
MINIO_SECURE=true

# OpenAI
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=text-embedding-3-small

# Authentication
JWT_SECRET_KEY=your_secret_key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_DELTA=3600

# Observability
OTEL_SERVICE_NAME=secondbrain
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_TRACES_EXPORTER=otlp
OTEL_METRICS_EXPORTER=otlp
PROMETHEUS_PORT=9090

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=1000
RATE_LIMIT_SEARCH=100
RATE_LIMIT_UPLOAD=50
```

### Configuration Best Practices

1. **Use Secrets Management**
   ```bash
   # Kubernetes Secrets
   kubectl create secret generic secondbrain-secrets \
     --from-literal=DATABASE_URL=$DATABASE_URL \
     --from-literal=OPENAI_API_KEY=$OPENAI_API_KEY

   # AWS Secrets Manager
   aws secretsmanager create-secret \
     --name secondbrain/production \
     --secret-string file://secrets.json

   # HashiCorp Vault
   vault kv put secret/secondbrain \
     database_url=$DATABASE_URL \
     openai_api_key=$OPENAI_API_KEY
   ```

2. **Configuration Validation**
   ```python
   # src/config.py
   from pydantic import BaseSettings, validator

   class Settings(BaseSettings):
       database_url: str
       redis_url: str
       
       @validator("database_url")
       def validate_database_url(cls, v):
           if not v.startswith("postgresql://"):
               raise ValueError("Invalid database URL")
           return v
   ```

## Monitoring & Observability

### Prometheus Metrics

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'secondbrain'
    static_configs:
      - targets: ['secondbrain-api:9090']
    metrics_path: '/metrics'
```

### Grafana Dashboards

Import the provided dashboards:
- `dashboards/secondbrain-overview.json`
- `dashboards/secondbrain-performance.json`
- `dashboards/secondbrain-errors.json`

### Alerts

```yaml
# alerts.yml
groups:
  - name: secondbrain
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: High error rate detected

      - alert: HighMemoryUsage
        expr: process_resident_memory_bytes / 1024 / 1024 > 500
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: High memory usage detected
```

## Backup & Recovery

### Database Backup

```bash
# PostgreSQL backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Automated backup with cron
0 2 * * * pg_dump $DATABASE_URL | gzip > /backups/db_$(date +\%Y\%m\%d).sql.gz

# Restore
psql $DATABASE_URL < backup.sql
```

### MinIO/S3 Backup

```bash
# Sync to backup bucket
aws s3 sync s3://secondbrain s3://secondbrain-backup --delete

# MinIO mirror
mc mirror source/secondbrain backup/secondbrain --overwrite
```

### Disaster Recovery Plan

1. **RPO (Recovery Point Objective)**: 1 hour
2. **RTO (Recovery Time Objective)**: 4 hours
3. **Backup Schedule**:
   - Database: Every hour
   - Object Storage: Daily
   - Configuration: On change
4. **Recovery Steps**:
   - Provision new infrastructure
   - Restore database from backup
   - Restore object storage
   - Deploy application
   - Verify functionality

## Security Considerations

### Network Security

```yaml
# Network Policy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: secondbrain-network-policy
spec:
  podSelector:
    matchLabels:
      app: secondbrain-api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: nginx
    ports:
    - protocol: TCP
      port: 8000
```

### TLS Configuration

```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name api.secondbrain.example.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://secondbrain-api;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Security Checklist

- [ ] Enable TLS/SSL for all connections
- [ ] Use strong passwords and rotate regularly
- [ ] Enable firewall rules
- [ ] Implement rate limiting
- [ ] Enable audit logging
- [ ] Regular security updates
- [ ] Vulnerability scanning
- [ ] Penetration testing

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Check connectivity
   pg_isready -h $DB_HOST -p 5432

   # Check pgvector extension
   psql $DATABASE_URL -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
   ```

2. **Redis Connection Issues**
   ```bash
   # Test connection
   redis-cli -h $REDIS_HOST ping

   # Check memory usage
   redis-cli -h $REDIS_HOST info memory
   ```

3. **High Memory Usage**
   ```bash
   # Profile memory
   python -m memory_profiler src/main.py

   # Adjust worker processes
   export WEB_CONCURRENCY=2
   ```

### Performance Tuning

1. **Database Optimization**
   ```sql
   -- Create indexes
   CREATE INDEX idx_memories_user_created 
   ON memories(user_id, created_at DESC);

   -- Optimize pgvector
   SET ivfflat.probes = 10;
   ```

2. **Application Tuning**
   ```python
   # Increase connection pool
   DATABASE_POOL_SIZE=50
   DATABASE_MAX_OVERFLOW=100

   # Adjust worker threads
   WEB_CONCURRENCY=4
   WORKER_THREADS=8
   ```

## Support

For deployment assistance:
- Documentation: [/docs](../../docs)
- Issues: [GitHub Issues](https://github.com/yourusername/second-brain/issues)
- Community: [Discord](https://discord.gg/secondbrain)