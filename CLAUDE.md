# Second Brain Project Context

## Project Overview
Second Brain v5.0 - A **100% local AI-powered** knowledge management system with multimodal search, Google Drive integration, and knowledge graph visualization. NO API KEYS REQUIRED for core functionality.

## Development Environment

### Quick Setup
1. **Docker Required**: All development uses Docker - no Python installation needed
2. **Default Port**: 8000 for all services
3. **Database**: PostgreSQL with pgvector (managed by Docker)
4. **GPU Services**: Run on Windows host (CLIP:8002, LLaVA:8003, LM Studio:1234)

### Network Architecture (Windows + Docker)
```
Windows Host (your machine)
├── Browser → http://localhost:8000 (accesses Docker container)
├── CLIP Service (port 8002) - GPU image embeddings
├── LM Studio (port 1234) - Text generation & embeddings
└── Docker Containers
    ├── secondbrain-app (8000) → uses host.docker.internal:8002 for CLIP
    ├── secondbrain-postgres (5432) - Vector database
    └── secondbrain-adminer (8080) - Database UI
```

**Key Point**: Containers use `host.docker.internal` to reach Windows services

### Key Commands
```bash
# Start all services (port 8000)
docker-compose up -d                # Start full stack
docker-compose logs -f app          # View logs
docker-compose down                 # Stop services
docker-compose restart app          # Restart after code changes

# Run commands inside container
docker exec -it secondbrain-app python -m pytest tests/unit/ -v
docker exec -it secondbrain-app ruff check .
docker exec -it secondbrain-app black .

# Database access
docker exec -it secondbrain-postgres psql -U secondbrain
```

### Platform Optimizations

#### Windows 11 with WSL2
- **Docker Management**: Always use `wsl docker-compose` for better performance
- **File Operations**: Consider `wsl` prefix for grep, find, and other Unix tools
- **PostgreSQL**: Run `wsl psql` for database access
- **Performance**: WSL2 provides near-native Linux performance for containers

Example Windows workflow:
```bash
# Use WSL2 for Docker (faster, more reliable)
wsl docker-compose up -d
wsl docker ps
wsl docker-compose logs -f app

# But use native Windows for Python (better IDE integration)
.venv\Scripts\python.exe scripts\run_dev.py
```

#### All Platforms
- **Direct Python paths** work best (`.venv/Scripts/python.exe` on Windows, `.venv/bin/python` on Unix)
- **Port Conflicts**: Check with `netstat` (Windows) or `lsof` (Unix)

## Common Platform Pitfalls & Solutions

### Issue: "command not found" errors
- **Windows**: You're in Git Bash, use `cmd.exe /c` for Windows commands or `wsl` for Linux commands
- **Solution**: `.venv\Scripts\python.exe` or `wsl python3`

### Issue: Docker commands fail on Windows
- **Cause**: Docker Desktop runs in WSL2
- **Solution**: ALWAYS prefix with `wsl`: `wsl docker-compose up -d`

### Issue: Path separator confusion
- **Windows**: Use backslashes `\` or raw strings
- **Mac/Linux**: Use forward slashes `/`
- **Solution**: Let Claude detect platform and use correct separators

### Issue: .env file encoding problems
- **Windows**: Often saves as UTF-16 or with BOM
- **Solution**: Save as UTF-8 without BOM in VS Code/Notepad++

### Issue: Port already in use
- **Windows**: `cmd.exe /c "netstat -ano | findstr :8000"` then `taskkill /PID <pid> /F`
- **Mac/Linux**: `lsof -i :8000` then `kill -9 <pid>`

### Issue: venv activation doesn't persist
- **All platforms**: Just use direct paths: `.venv\Scripts\python.exe` (Windows) or `.venv/bin/python` (Unix)

## Platform-Specific Quick Reference

### Windows 11 (Docker Desktop Required)
```bash
# All operations through Docker - no Python installation needed
docker-compose up -d                # Start services
docker ps                           # Check status
docker-compose logs -f app          # View logs
docker exec -it secondbrain-postgres psql -U secondbrain

# Running tests and tools
docker exec -it secondbrain-app python -m pytest tests/unit/ -v
docker exec -it secondbrain-app ruff check .
docker exec -it secondbrain-app black .

# Port management (if needed)
netstat -ano | findstr :8000
taskkill /PID <pid> /F
```

### macOS / Linux
```bash
# All operations through Docker
docker-compose up -d
docker ps
docker exec -it secondbrain-app python -m pytest tests/unit/ -v
lsof -i :8000                      # macOS
ss -tlnp | grep 8000               # Linux
```

### Why WSL2 on Windows?
- **10x faster** Docker operations than Docker Desktop alone
- **Native Linux tooling** (grep, awk, sed, find)
- **Consistent behavior** with CI/CD pipelines
- **Better PostgreSQL** integration with pgvector

## Project Architecture

### Core Services
- **FastAPI Backend** (port 8000) - Main application server
- **PostgreSQL + pgvector** (port 5432) - Vector database for embeddings
- **LM Studio** (port 1234) - Local text generation (LLaVA 1.6 Mistral 7B)
- **CLIP Service** (port 8002) - Image embeddings and similarity
- **LLaVA Service** (port 8003) - Vision understanding and OCR

### Project Structure
```
/app                 - Main application code
  /routes           - API endpoints (v2 API, WebSocket, Google Drive)
  /services         - Business logic (memory, Google Drive processing)
  /storage          - Database backends (PostgreSQL, mock)
  /models           - Pydantic models and schemas
/frontend           - SvelteKit frontend application
/services/gpu       - GPU-accelerated vision services
/tests              - Comprehensive test suite
  /unit            - Fast unit tests
  /integration     - Integration tests
/static             - Static files and legacy UIs
/scripts            - Development and CI/CD scripts
/docs               - Documentation and guides
```

## Environment Configuration

### Essential Setup
1. Copy `.env.example` to `.env`
2. Key variables:
   - `DATABASE_URL` - PostgreSQL connection (defaults to SQLite for dev)
      - `OPENAI_API_KEY` - Optional, for enhanced features
   - `ENVIRONMENT=development` - Environment mode

### Development Modes
- **Full Stack**: `docker-compose up -d` (PostgreSQL + pgvector + app)
- **GPU Services**: `docker-compose -f docker-compose.gpu.yml up -d` (includes vision models)

## Testing Strategy
The project uses a tiered testing approach:
- **Smoke Tests** (<60s): `make test-smoke` - Critical path validation
- **Fast Tests** (<5min): `make test-fast` - Core functionality
- **Comprehensive** (<15min): `make test-comprehensive` - Full validation
- **Performance** (<20min): `make test-performance` - Benchmarks

## Key Features
- **Multimodal Search**: Text and image semantic search
- **Google Drive Integration**: OAuth 2.0, automatic sync
- **Knowledge Graph**: Automatic relationship discovery and visualization
- **100% Local Option**: Run entirely on local models without API keys
- **WebSocket Support**: Real-time updates and streaming

## Code Quality Standards
- **Formatter**: Black (line length 100)
- **Linter**: Ruff with extensive rule set
- **Type Checker**: MyPy in strict mode
- **Test Coverage**: Minimum 80% required
- Python 3.11+ required

## Common Tasks
- View logs: `make logs` or `docker-compose logs -f app`
- Database shell: `make db-shell` or connect to PostgreSQL on port 5432
- Run specific test: `docker exec -it secondbrain-app python -m pytest tests/unit/test_memory_service.py -v`
- Check health: `curl http://localhost:8000/health`
- View API docs: http://localhost:8000/docs

## Important Notes
- Docker-only development - no local Python needed
- All commands run through Docker containers
- Frontend development: `docker exec -it secondbrain-frontend npm run dev`
- All linting/formatting should pass before committing

## Claude Assistant Guidelines

### Smart Platform Handling
Claude automatically detects your platform from the environment and adjusts commands accordingly:

#### Windows 11 (win32)
- **WSL2 First**: Prefers `wsl` for Docker, PostgreSQL, and Unix tools
- **Native Python**: Uses `.venv\Scripts\python.exe` for better Windows integration  
- **Hybrid Approach**: Leverages WSL2's Linux performance while maintaining Windows tooling

#### macOS M4 (darwin) / Arch Linux (linux)
- **Native Commands**: Direct execution without translation layers
- **ARM Awareness**: Considers M4 architecture for macOS

Commands in this file are platform-agnostic - Claude will adapt them using the optimal approach for your system

### Session Behavior
1. **Docker first**: All operations use Docker containers
2. **Smart command execution**: Claude uses docker exec for running commands
3. **Port awareness**: Always uses port 8000 (Docker standard)

### Development Standards
- Read existing code before making changes to match conventions
- Prefer editing over creating new files
- Run tests after significant changes
- Only commit when explicitly asked
- Don't create documentation unless requested

## Useful File Locations
- API endpoints: `app/routes/v2/`
- Memory logic: `app/services/memory_service.py`
- Database models: `app/models/memory.py`
- Mock storage: `app/storage/mock_storage.py`
- PostgreSQL storage: `app/storage/postgres_unified.py`
- Test fixtures: `tests/conftest.py`
- Environment config: `app/config.py` and `app/core/env_manager.py`