# CI/CD Guide

## Quick Setup

### GitHub Actions
```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - run: |
          pip install -r requirements.txt
          pytest tests/
```

### Local Testing
```bash
# Run before pushing
python scripts/check_secrets.py  # Security scan
pytest tests/                    # Run tests
flake8 app/                     # Lint code
```

### Docker Deployment
```bash
# Build and run
docker-compose up -d postgres
docker build -t second-brain:v4.2.3 .
docker run -p 8000:8000 second-brain:v4.2.3
```

### Environment Variables
Copy `.env.example` to `.env` and set:
- `OPENAI_API_KEY` - Required for embeddings
- `DATABASE_URL` - PostgreSQL connection
- `ENVIRONMENT` - dev/staging/production

That's it. Keep it simple.