# Setup Guide

## Requirements
- Python 3.10+
- PostgreSQL 16 with pgvector
- Docker (optional)

## Quick Start

### 1. Clone & Install
```bash
git clone https://github.com/yourusername/second-brain.git
cd second-brain
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Database Setup
```bash
# Using Docker
docker-compose up -d postgres

# Or install PostgreSQL locally with pgvector extension
```

### 3. Configure
```bash
cp .env.example .env
# Edit .env with your settings:
# - OPENAI_API_KEY
# - DATABASE_URL
```

### 4. Initialize Database
```bash
python scripts/setup_postgres_pgvector.py
```

### 5. Run
```bash
uvicorn app.main:app --reload
# Visit http://localhost:8000/docs
```

## Environment Variables
See `.env.example` for all options.

## Testing
```bash
pytest tests/
```

## Troubleshooting
- **Database connection failed**: Check PostgreSQL is running
- **Import errors**: Ensure venv is activated
- **API key errors**: Set OPENAI_API_KEY in .env