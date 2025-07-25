# Second Brain Development Setup

This guide helps you set up the development environment on **any computer** (work, laptop, desktop).

## Quick Setup

### 1. Clone and Setup Environment

```bash
git clone <repository-url>
cd second-brain
python scripts/setup_dev_environment.py
```

### 2. Activate Environment

**Windows:**
```bash
.venv\Scripts\activate
```

**Linux/Mac:**
```bash
source .venv/bin/activate
```

### 3. Start Services

```bash
docker-compose up -d
```

### 4. Test Everything Works

```bash
python scripts/test_runner.py --validation
python scripts/test_runner.py --unit
```

## File Structure

```
second-brain/
├── docker-compose.yml                    # Main Docker services (PostgreSQL, Redis, Adminer)
├── scripts/
│   ├── setup_dev_environment.py          # Portable environment setup
│   └── test_runner.py                    # Comprehensive test runner
├── tests/
│   ├── validation/
│   │   └── validate_ci_ready.py          # Validate CI readiness
│   └── unit/                             # Unit tests
├── config/
│   └── requirements*.txt                 # Dependency files
└── .venv/                                # Virtual environment (auto-created, not in git)
```

## Services

After running `docker-compose up -d`:

- **PostgreSQL**: `localhost:5432` (user: `secondbrain`, password: `changeme`)  
- **Redis**: `localhost:6379`
- **Adminer**: `http://localhost:8080` (database management UI)

## Environment Variables

Copy `.env.development` to `.env` and update:
- `OPENAI_API_KEY`: Your OpenAI API key
- Other settings as needed

## Testing

```bash
# Test environment validation
python scripts/test_runner.py --validation

# Run unit tests
python scripts/test_runner.py --unit

# Run integration tests  
python scripts/test_runner.py --integration

# Run all tests
python scripts/test_runner.py --all

# Run tests with coverage
python scripts/test_runner.py --coverage

# Run linting
python scripts/test_runner.py --lint
```

## Troubleshooting

### Virtual Environment Issues
If you get path errors, delete `.venv` and run setup again:
```bash
rm -rf .venv
python scripts/setup_dev_environment.py
```

### Docker Issues
```bash
# Reset Docker services
docker-compose down -v
docker-compose up -d

# Check service status
docker-compose ps
```

### Import Errors
Run the validation script:
```bash
python scripts/test_runner.py --validation
```

## Platform Compatibility

This setup works on:
- ✅ Windows 10/11
- ✅ macOS (Intel/Apple Silicon)  
- ✅ Linux (Ubuntu, CentOS, etc.)
- ✅ WSL2

The setup script automatically detects your platform and creates the appropriate virtual environment.

## CI/CD Status

The CI pipeline will pass when you push to main because:
- ✅ All dependency conflicts resolved
- ✅ Pydantic version standardized (2.5.3)
- ✅ PostgreSQL image fixed (`pgvector/pgvector:pg16`)
- ✅ Dependencies installed in correct order

Run `python scripts/test_runner.py --validation` to confirm your local environment matches CI expectations.