# Local Testing Guide - Second Brain v3.1.0

## 🚀 Quick Start

Since we've removed the CI/CD pipeline, here's how to test locally:

### Docker Testing (Recommended)
```bash
# Run all tests in Docker
make test

# Run specific test types
make test-unit
make test-integration
make test-performance
```

### Local Python Testing
```bash
# Activate virtual environment
source .venv/bin/activate  # Unix/macOS
# or
.venv\Scripts\activate  # Windows

# Run all tests
python scripts/test_runner.py --all

# Run specific test categories
python scripts/test_runner.py --unit
python scripts/test_runner.py --integration
python scripts/test_runner.py --validation
```

## 🧪 Test Categories

1. **Unit Tests** - Fast, isolated component tests
   ```bash
   pytest tests/unit -v
   ```

2. **Integration Tests** - Service interaction tests
   ```bash
   pytest tests/integration -v
   ```

3. **Performance Tests** - Load and stress tests
   ```bash
   pytest tests/performance -v
   ```

## 🛠️ Before Committing

Run these checks locally:

```bash
# 1. Format code
black app tests

# 2. Lint code
ruff check app tests

# 3. Type checking
mypy app

# 4. Run tests
pytest tests/unit -v
```

## 🐳 Docker Environment

```bash
# Start full environment
docker-compose up -d

# Run tests in container
docker-compose exec app pytest

# View logs
docker-compose logs -f app
```

## 💡 Tips

- Use `pytest -x` to stop on first failure
- Use `pytest -k "test_name"` to run specific tests
- Use `pytest --lf` to run only last failed tests
- Add `-s` to see print statements during tests

## 🔧 Troubleshooting

If tests fail:
1. Check Docker is running: `docker ps`
2. Check database: `docker-compose ps db`
3. Reset environment: `docker-compose down -v && docker-compose up -d`
4. Check logs: `docker-compose logs app`

## 📝 Writing Tests

```python
# Example test structure
def test_my_feature():
    # Arrange
    data = {"key": "value"}
    
    # Act
    result = my_function(data)
    
    # Assert
    assert result["status"] == "success"
```

Remember: No CI/CD means we rely on local testing discipline. Test before pushing!