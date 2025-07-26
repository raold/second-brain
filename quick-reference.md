# Second Brain v3.0.0 - Developer Quick Reference

## 🚀 Essential Commands

### Setup & Environment
```bash
make setup           # One-command setup (Docker + fallback)
make status          # Check environment health
make shell           # Open development shell
```

### Development
```bash
make dev             # Start all services
make dev-logs        # View application logs
make dev-stop        # Stop all services
make restart         # Restart application
```

### Testing
```bash
make test            # Run all tests
make test-unit       # Unit tests only (fast)
make test-integration # Integration tests
make test-validation # Environment health check
make test-watch      # Watch mode
```

### Database
```bash
make db-shell        # PostgreSQL CLI
make db-migrate      # Run migrations
make db-rollback     # Rollback last migration
make db-reset        # Reset database (WARNING: data loss)
```

### Code Quality
```bash
make format          # Format code (black + ruff)
make lint            # Run linters
make type-check      # Type checking (mypy)
make security        # Security scan (bandit)
make pre-commit      # Run all pre-commit hooks
```

## 📁 Key Directories

```
second-brain/
├── app/             # Application code
│   ├── models/      # Domain models
│   ├── services/    # Business logic
│   ├── routes/      # API endpoints
│   └── utils/       # Utilities
├── tests/           # Test suites
├── migrations/      # Database migrations
├── scripts/         # Utility scripts
├── docker/          # Docker configs
└── docs/            # Documentation
```

## 🔌 Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| API | http://localhost:8000 | - |
| API Docs | http://localhost:8000/docs | - |
| PostgreSQL | localhost:5432 | postgres/password |
| Redis | localhost:6379 | - |
| RabbitMQ | localhost:5672 | guest/guest |
| RabbitMQ UI | http://localhost:15672 | guest/guest |
| MinIO | http://localhost:9000 | minioadmin/minioadmin |

## 🎯 Common API Endpoints

```bash
# Create memory
POST /api/v1/memories
{
  "content": "Memory content",
  "tags": ["tag1", "tag2"]
}

# Search memories
POST /api/v1/memories/search
{
  "query": "search term",
  "limit": 10
}

# Upload file
POST /api/v1/ingest/upload
Form-data: file=@document.pdf

# Health check
GET /health

# Metrics
GET /metrics
```

## 🐛 Quick Debugging

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f app
docker-compose logs --tail=100 postgres

# Enter container
docker-compose exec app bash
docker-compose exec postgres psql -U postgres

# Python shell with app context
docker-compose exec app python
>>> from app.models import Memory
>>> Memory.query.all()

# Clear Redis cache
docker-compose exec redis redis-cli FLUSHALL

# Restart service
docker-compose restart app
```

## 🔧 Environment Variables

```bash
# Quick edits
nano .env                    # Edit environment
source .env                  # Load in shell
docker-compose up -d         # Restart with new env

# Common variables
DATABASE_URL=postgresql://postgres:password@localhost:5432/secondbrain
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=your-key-here
DEBUG=true
LOG_LEVEL=INFO
```

## 📝 Git Workflow

```bash
# Feature development
git checkout develop
git pull origin develop
git checkout -b feature/my-feature

# Commit with conventional commits
git add .
git commit -m "feat: add new feature"
git commit -m "fix: resolve bug"
git commit -m "docs: update README"
git commit -m "test: add unit tests"

# Push and create PR
git push origin feature/my-feature
```

## 🆘 Emergency Commands

```bash
# Full reset (WARNING: deletes all data)
make clean-all
make setup

# Force rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d

# Fix permissions (Linux/macOS)
sudo chown -R $USER:$USER .

# Kill all Docker containers
docker kill $(docker ps -q)

# Remove all Docker volumes
docker volume prune -f
```

## 💡 Pro Tips

1. **Use `make` commands** - They handle cross-platform differences
2. **Check `make status`** - Before reporting issues
3. **Use `.env.development`** - For local overrides
4. **Enable pre-commit** - `pre-commit install`
5. **Use Docker logs** - `docker-compose logs -f app`
6. **Test in container** - `make shell` then run tests
7. **Profile queries** - Enable `SQLALCHEMY_ECHO=true`
8. **Monitor performance** - Check `/metrics` endpoint

---

**Need help?** Run `make help` or check [CONTRIBUTING.md](CONTRIBUTING.md)