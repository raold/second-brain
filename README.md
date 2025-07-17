# Second Brain v2.0.0 - AI Memory System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-green.svg)](https://fastapi.tiangolo.com/)

**Second Brain v2.0.0** is a **completely refactored** AI memory system with **90% code reduction** and simplified architecture. Store, search, and retrieve memories using PostgreSQL with pgvector for semantic search.

## 🚀 **What's New in v2.0.0**

### **📊 Major Improvements**
- **90% Code Reduction**: From 1,596 lines to 165 lines in main application
- **Single Database**: PostgreSQL with pgvector (removed Qdrant)
- **Minimal Dependencies**: 5 core packages (down from 50+)
- **Direct Database Access**: No ORM overhead
- **Environment-Only Config**: Simple .env configuration

### **🎯 Key Features**
- **Semantic Search**: PostgreSQL pgvector for fast vector similarity
- **OpenAI Integration**: `text-embedding-3-small` model
- **REST API**: Clean FastAPI with 6 endpoints
- **Mock Database**: Cost-free testing without API calls
- **Token Authentication**: Simple API key security
- **JSONB Metadata**: Flexible metadata storage

## 📁 **Project Structure**

```
second-brain/
├── app/                          # Core application
│   ├── app.py                   # Main FastAPI application (165 lines)
│   ├── database.py              # PostgreSQL + pgvector client (227 lines)
│   ├── database_mock.py         # Mock database for testing
│   └── __init__.py              # Package initialization
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md          # System architecture
│   ├── DEPLOYMENT.md            # Deployment guide
│   ├── USAGE.md                 # Usage examples
│   └── TESTING.md               # Testing guide
├── archive/                     # Archived v1.x files
│   └── v1.x/                    # Complete v1.x system archive
├── .env.example                 # Environment configuration template
├── .gitignore                   # Git ignore rules
├── CHANGELOG.md                 # Version history
├── docker-compose.yml           # Docker configuration
├── Dockerfile                   # Container image
├── Makefile                     # Development commands
├── pytest.ini                  # Test configuration
├── README.md                    # This file
├── requirements-minimal.txt     # Core dependencies (5 packages)
├── ruff.toml                    # Code formatting
├── setup_db.py                  # Database initialization
├── test_db_setup.py             # Database setup tests
├── test_mock_database.py        # Mock database tests
└── test_refactored.py           # Main test suite
```

## 🚀 **Quick Start**

### **1. Prerequisites**
- Python 3.10+
- PostgreSQL 15+ with pgvector extension
- OpenAI API key

### **2. Installation**
```bash
# Clone repository
git clone https://github.com/raold/second-brain.git
cd second-brain

# Install dependencies
pip install -r requirements-minimal.txt

# Setup environment
cp .env.example .env
# Edit .env with your configuration
```

### **3. Database Setup**
```bash
# Install pgvector extension in PostgreSQL
psql -d your_database -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Initialize database tables
python setup_db.py
```

### **4. Configuration**
Edit `.env` file:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/second_brain

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# Authentication
API_TOKENS=your_secure_api_token_here

# Optional
HOST=0.0.0.0
PORT=8000
```

### **5. Run Application**
```bash
# Start the server
python -m app.app

# Or with uvicorn
uvicorn app.app:app --reload

# Server runs at http://localhost:8000
```

## 📡 **API Endpoints**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/memories` | Store a memory |
| `GET` | `/memories` | List all memories (paginated) |
| `GET` | `/memories/{id}` | Get specific memory |
| `DELETE` | `/memories/{id}` | Delete memory |
| `POST` | `/memories/search` | Semantic search |

### **Example Usage**
```bash
# Store a memory
curl -X POST "http://localhost:8000/memories?api_key=your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "PostgreSQL pgvector provides excellent semantic search",
    "metadata": {"category": "database", "importance": "high"}
  }'

# Search memories
curl -X POST "http://localhost:8000/memories/search?api_key=your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "database search",
    "limit": 5
  }'
```

## 🧪 **Testing**

### **Quick Test**
```bash
# Test with mock database (no OpenAI API required)
python test_mock_database.py

# Run full test suite
python -m pytest test_refactored.py -v

# Run with coverage
python -m pytest test_refactored.py --cov=app --cov-report=html
```

### **Mock Database**
The mock database enables cost-free testing:
```python
from app.database_mock import MockDatabase

mock_db = MockDatabase()
memory_id = await mock_db.store_memory("Test content", {"type": "test"})
results = await mock_db.search_memories("test query")
```

## 🐳 **Docker Deployment**

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build manually
docker build -t second-brain .
docker run -p 8000:8000 --env-file .env second-brain
```

## 🔧 **Development**

### **Dependencies**
```bash
# Core dependencies (5 packages)
pip install -r requirements-minimal.txt

# Development tools
pip install pytest pytest-cov ruff pre-commit
```

### **Code Quality**
```bash
# Format code
ruff format .

# Lint code
ruff check .

# Run tests
make test

# Coverage report
make coverage
```

## 📊 **Performance Comparison**

| Metric | v1.x | v2.0.0 | Improvement |
|--------|------|--------|-------------|
| **Lines of Code** | 1,596 | 165 | **90% reduction** |
| **Dependencies** | 50+ | 5 | **90% reduction** |
| **Database Systems** | 2 (PostgreSQL + Qdrant) | 1 (PostgreSQL) | **Simplified** |
| **Memory Usage** | High | Low | **Optimized** |
| **Startup Time** | Slow | Fast | **Improved** |

## 🗑️ **Removed in v2.0.0**

- ❌ **Qdrant** vector database → PostgreSQL pgvector
- ❌ **Complex caching** → Direct database access
- ❌ **ORM** → Pure SQL queries
- ❌ **Extensive monitoring** → Basic logging
- ❌ **Plugin architecture** → Core functionality focus
- ❌ **WebSocket streaming** → REST API only
- ❌ **Background tasks** → Synchronous operations
- ❌ **Complex configuration** → Environment variables only

## 🔄 **Migration from v1.x**

### **Database Migration**
```sql
-- Add pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column (if upgrading)
ALTER TABLE memories ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- Create vector index
CREATE INDEX IF NOT EXISTS memories_embedding_idx 
ON memories USING ivfflat (embedding vector_cosine_ops);
```

### **Configuration Migration**
- Replace complex config files with `.env` variables
- Update database connection strings
- Set OpenAI API key and auth tokens

## 📚 **Documentation**

- **[Architecture Guide](docs/ARCHITECTURE.md)** - System design and components
- **[Usage Guide](docs/USAGE.md)** - API usage and examples
- **[Testing Guide](docs/TESTING.md)** - Testing strategies and mock database
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production deployment
- **[Changelog](CHANGELOG.md)** - Version history and breaking changes

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

```bash
# Development setup
pip install -r requirements-minimal.txt
python test_mock_database.py  # Quick test
python -m pytest test_refactored.py -v  # Full test suite
```

## 📜 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 **Acknowledgments**

- **OpenAI** for embedding models and API
- **PostgreSQL** and **pgvector** for robust vector storage
- **FastAPI** for modern Python web framework
- **Community** for feedback and contributions

## 🔗 **Links**

- **GitHub Repository**: https://github.com/raold/second-brain
- **Documentation**: https://github.com/raold/second-brain/tree/main/docs
- **Issues**: https://github.com/raold/second-brain/issues
- **Discussions**: https://github.com/raold/second-brain/discussions

---

**Second Brain v2.0.0** - *Simplified, Fast, and Maintainable AI Memory System*

> **Note**: v1.x files are archived in `archive/v1.x/` for reference. The complete v1.x system with all its complexity is preserved but no longer maintained.

### 🎯 **Ready to Get Started?**

1. **Clone the repo** → `git clone https://github.com/raold/second-brain.git`
2. **Install dependencies** → `pip install -r requirements-minimal.txt`
3. **Configure environment** → Edit `.env` file
4. **Setup database** → `python setup_db.py`
5. **Run application** → `python -m app.app`
6. **Test functionality** → `python test_mock_database.py`

**Happy memory management!** 🧠✨
