# Second Brain - Port & Service Map

## Service Architecture

```
Windows Host Machine
├── Browser (http://localhost:8000)
├── LM Studio (port 1234)
├── CLIP Service (port 8002)
├── LLaVA Service (port 8003)
└── Docker Desktop
    └── Docker Network (second-brain_default)
        ├── secondbrain-app (port 8000)
        ├── secondbrain-postgres (port 5432)
        └── secondbrain-adminer (port 8080)
```

## Port Assignments

| Service | Port | Location | URL from Host | URL from Container |
|---------|------|----------|---------------|-------------------|
| **Main App (FastAPI)** | 8000 | Docker | http://localhost:8000 | http://app:8000 |
| **PostgreSQL + pgvector** | 5432 | Docker | localhost:5432 | postgres:5432 |
| **Adminer (DB UI)** | 8080 | Docker | http://localhost:8080 | http://adminer:8080 |
| **LM Studio** | 1234 | Windows | http://localhost:1234 | http://host.docker.internal:1234 |
| **CLIP Service** | 8002 | Windows | http://localhost:8002 | http://host.docker.internal:8002 |
| **LLaVA Service** | 8003 | Windows | http://localhost:8003 | http://host.docker.internal:8003 |

## Web Interfaces

### From Windows Browser
- **Main App**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Photo Pipeline**: http://localhost:8000/static/photo-pipeline.html
- **Database Admin**: http://localhost:8080
- **LM Studio**: http://localhost:1234

### API Endpoints
- **Health Check**: http://localhost:8000/health
- **Photo Pipeline Status**: http://localhost:8000/api/photo-pipeline/status
- **WebSocket (Photo Pipeline)**: ws://localhost:8000/api/photo-pipeline/ws

## Starting Services

### 1. Docker Services (Always First)
```bash
# Windows Command Prompt or PowerShell
docker-compose up -d

# Or use convenience script
./manage.bat start
```

### 2. GPU Services on Windows Host

#### CLIP Service (Image Embeddings)
```bash
cd services/gpu/clip
python clip_api.py
# Runs on http://localhost:8002
```

#### LLaVA Service (Vision Analysis)
```bash
cd services/gpu/llava
python llava_api.py
# Runs on http://localhost:8003
```

#### LM Studio (Text Generation & Embeddings)
1. Open LM Studio application
2. Load models:
   - `text-embedding-nomic-embed-text-v1.5` for embeddings
   - `llava-v1.6-34b` or `llava-1.6-mistral-7b` for vision
3. Start server (automatically runs on port 1234)

## Network Troubleshooting

### Container Can't Reach Windows Host Services
**Symptom**: "Cannot connect to host localhost:8002"
**Solution**: Use `host.docker.internal` instead of `localhost`

### Windows Can't Reach Docker Services
**Symptom**: "Connection refused" on localhost:8000
**Solution**: 
1. Check Docker Desktop is running
2. Verify port mapping: `docker ps`
3. Check firewall isn't blocking

### Service Discovery Between Containers
Containers can reach each other by service name:
- `app` → `postgres:5432` ✅
- `app` → `localhost:5432` ❌

### Checking What's Running

```bash
# See all Docker containers and ports
docker ps

# Check specific port on Windows
netstat -an | findstr :8000

# Check if service is responding
curl http://localhost:8000/health
```

## Environment Variables

Set in `docker-compose.override.yml` for Windows development:
```yaml
environment:
  - CLIP_SERVICE_URL=http://host.docker.internal:8002
  - LLAVA_SERVICE_URL=http://host.docker.internal:8003
  - LM_STUDIO_URL=http://host.docker.internal:1234
```

## Quick Commands

```bash
# View logs
docker logs secondbrain-app -f

# Restart app container
docker-compose restart app

# Rebuild after code changes
docker-compose up -d --build app

# Stop everything
docker-compose down

# Clean restart
docker-compose down && docker-compose up -d
```