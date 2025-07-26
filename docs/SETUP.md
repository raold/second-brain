# Second Brain Development Setup

**🐳 Docker-First Development with Bulletproof .venv Fallback**

This guide helps you set up the development environment on **any computer** with zero host dependencies.

## ⚡ Quick Setup (Recommended)

### 1. Clone and One-Command Setup

```bash
git clone <repository-url>
cd second-brain

# Single command setup (works everywhere)
make setup
```

### 2. Start Development

```bash
# Start development environment (Docker-first)
make dev

# Check everything is working
make status

# Run tests  
make test
```

### 3. Development Workflow

```bash
# Daily development
make dev           # Start environment
make shell         # Development shell
make dev-logs      # Show logs
make dev-stop      # Stop environment

# Testing
make test-unit     # Unit tests
make test-integration  # Integration tests
make test-validation   # Environment validation
```

## 🔧 Manual Setup (if needed)

### Docker-First Approach

```bash
# Start full development stack
docker-compose up --build

# Run tests in containers
docker-compose exec app python scripts/test_runner.py --all

# Open development shell
docker-compose exec app bash
```

### Bulletproof .venv Fallback

```bash
# Automated .venv creation with validation
python scripts/setup-bulletproof-venv.py

# Activate environment (Windows)
.venv\Scripts\activate
# OR activate-venv.bat

# Activate environment (Unix)
source .venv/bin/activate  
# OR ./activate-venv.sh

# Start application
python main.py
```

## 📁 Development Environment Files

```
second-brain/
├── Dockerfile                           # Multi-stage Docker build (dev/prod)
├── docker-compose.yml                   # Full development stack
├── Makefile                             # Cross-platform development commands
├── main.py                              # Application entry point

├── scripts/
│   ├── dev                              # Universal development script
│   ├── setup-bulletproof-venv.py       # Automated .venv creation
│   └── test_runner.py                   # Comprehensive testing

├── app/                                 # Main application
│   ├── services/                        # Business logic (moved from root)
│   ├── routes/                          # API endpoints  
│   ├── models/                          # Data models
│   └── ingestion/                       # File processing

├── config/
│   └── requirements*.txt               # Dependency management

├── .venv/                               # Virtual environment (auto-created)
├── activate-venv.bat                    # Windows activation (auto-created)  
└── activate-venv.sh                     # Unix activation (auto-created)
```

## 🐳 Docker Services

The development stack includes:

- **App**: `localhost:8000` (FastAPI application with hot reload)
- **PostgreSQL**: `localhost:5432` (user: `secondbrain`, password: `changeme`)  
- **Redis**: `localhost:6379` (caching and session storage)
- **Adminer**: `http://localhost:8080` (database management UI)

## 🧪 Testing

### Docker-First Testing (Recommended)
```bash
make test                    # All tests in containers
make test-unit              # Unit tests only  
make test-integration       # Integration tests only
make test-validation        # Environment validation
```

### Universal Testing Scripts
```bash
# Works with Docker or .venv automatically
python scripts/dev test --test-type all
python scripts/dev test --test-type unit  
python scripts/dev test --test-type integration
python scripts/dev test --test-type validation
```

### Direct .venv Testing (Fallback)
```bash
# Windows
.venv\Scripts\python.exe scripts/test_runner.py --validation

# Unix  
.venv/bin/python scripts/test_runner.py --validation
```

## 🛠️ Troubleshooting

### Environment Issues
```bash
# Check environment status  
make status

# Complete environment reset
make clean-all           # WARNING: Destroys all data
make setup               # Fresh setup
```

### Docker Issues
```bash
# Restart Docker services
make dev-stop
make dev

# Check Docker status
docker-compose ps
docker-compose logs app

# Rebuild from scratch  
make build
```

### .venv Issues  
```bash
# Recreate bulletproof .venv
python scripts/setup-bulletproof-venv.py --force

# Manual activation
activate-venv.bat        # Windows
./activate-venv.sh       # Unix
```

### Import/Path Errors
```bash
# Validate environment
make test-validation

# Check Python path
python scripts/dev status
```

## 🌍 Platform Compatibility

**✅ Zero-dependency setup works on:**
- Windows 10/11 (native and WSL2)
- macOS (Intel and Apple Silicon)  
- Linux (Ubuntu, CentOS, Debian, Arch, etc.)
- Any system with Docker or Python 3.11+

## 🚀 Architecture Benefits

This Docker-first approach provides:

- **🔒 Isolation**: No conflicts with system Python or packages
- **📦 Consistency**: Identical environment across all machines 
- **⚡ Speed**: One-command setup, automatic dependency resolution
- **🛡️ Reliability**: Bulletproof fallback ensures development never stops
- **🔄 Portability**: Move between machines seamlessly

## 💡 Pro Tips

```bash
# Always check status first
make status

# Use Docker shell for debugging
make shell

# Monitor logs during development  
make dev-logs

# Quick test before committing
make test-validation
```