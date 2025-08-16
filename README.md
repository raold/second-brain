<div align="center">
<img src="logo.png" alt="Second Brain Logo" width="400">

# 🧠 Second Brain v5.0

### 100% Local AI-Powered Knowledge Management System

[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue.svg)](https://www.postgresql.org/)
[![pgvector](https://img.shields.io/badge/pgvector-0.8.0-blue.svg)](https://github.com/pgvector/pgvector)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

</div>

> **🚀 v5.0: NO API KEYS REQUIRED!** Run entirely on local models with CLIP, LLaVA, and LM Studio. Complete privacy, zero monthly costs, unlimited usage.

## 🎯 **What is Second Brain?**

Second Brain is your personal AI-powered knowledge management system that runs **100% locally** on your machine. Store, search, and synthesize all your documents, images, and ideas using state-of-the-art AI models - without sending a single byte to the cloud.

## ✨ **Key Features**

### 🧠 **Fully Local AI Stack**
- **LM Studio** (port 1234): Text generation with LLaVA 1.6 Mistral 7B
- **CLIP Service** (port 8002): Image embeddings and similarity search
- **LLaVA Service** (port 8003): Advanced vision understanding and OCR
- **Nomic Embeddings**: Fast text embeddings (768 dimensions)

### 🔍 **Multimodal Search**
- Search by text, image, or both simultaneously
- Semantic understanding of documents and images
- Sub-100ms query performance
- Hybrid search combining vectors and full-text

### 📁 **Google Drive Integration**
- OAuth 2.0 authentication
- Automatic document synchronization
- Process Google Docs, Sheets, PDFs, and images
- Maintain folder structure and metadata

### 🔗 **Knowledge Graph**
- Automatic relationship discovery
- Interactive visualization
- Topic clustering and analysis
- Memory consolidation and deduplication

### 🔐 **Complete Privacy**
- **No API keys** - ever
- **No cloud dependencies**
- **No tracking or telemetry**
- **Works fully offline**
- **Your data stays yours**

## 🚀 **Quick Start**

### Prerequisites
- Python 3.11+
- PostgreSQL 16+ with pgvector
- NVIDIA GPU with CUDA (for optimal performance)
- 16GB+ RAM recommended
- 20GB+ free disk space

### 1. Clone and Setup
```bash
git clone https://github.com/raold/second-brain.git
cd second-brain
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env - no API keys needed!
```

### 3. Start PostgreSQL
```bash
docker-compose up -d postgres
```

### 4. Install and Configure LM Studio
1. Download [LM Studio](https://lmstudio.ai/)
2. Load these models:
   - `llava-1.6-mistral-7b` Q6_K (6.57GB)
   - `text-embedding-nomic-embed-text-v1.5` (137MB)
3. Start server on port 1234

### 5. Start GPU Services
```bash
# Terminal 1: CLIP Service
python services/gpu/clip/clip_api.py

# Terminal 2: LLaVA Service  
python services/gpu/llava/llava_api.py
```

### 6. Run Main Application
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Visit http://localhost:8001/docs for the API documentation.

## 📊 **Architecture**

```mermaid
graph TB
    subgraph "Local Services"
        LM[LM Studio<br/>:1234]
        CLIP[CLIP Service<br/>:8002]
        LLAVA[LLaVA Service<br/>:8003]
    end
    
    subgraph "Core"
        API[FastAPI<br/>:8001]
        PG[(PostgreSQL<br/>+ pgvector<br/>:5432)]
    end
    
    subgraph "Data Sources"
        GD[Google Drive]
        LOCAL[Local Files]
    end
    
    API --> LM
    API --> CLIP
    API --> LLAVA
    API --> PG
    GD --> API
    LOCAL --> API
```

## 🔧 **Configuration**

### Essential Environment Variables
```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/secondbrain

# Local Model Services (no API keys!)
LM_STUDIO_URL=http://127.0.0.1:1234/v1
CLIP_SERVICE_URL=http://127.0.0.1:8002
LLAVA_SERVICE_URL=http://127.0.0.1:8003

# Google Drive (optional)
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:8001/api/v1/gdrive/callback
```

## 📈 **Performance**

Tested on RTX 4090:

| Operation | Performance |
|-----------|------------|
| Text Embedding | ~100ms/document |
| Image Embedding | ~300ms/image |
| Vision Analysis | 2-5s/image |
| Vector Search | <50ms |
| Hybrid Search | <100ms |
| Document Processing | 200 docs/minute |

## 🔄 **API Endpoints**

### Core Memory Operations
- `POST /api/v1/memories` - Create memory
- `GET /api/v1/memories` - List memories
- `GET /api/v1/memories/{id}` - Get memory
- `PUT /api/v1/memories/{id}` - Update memory
- `DELETE /api/v1/memories/{id}` - Delete memory

### Search & Analysis
- `POST /api/v1/search` - Semantic search
- `POST /api/v1/search/hybrid` - Hybrid search
- `POST /api/v1/search/image` - Image similarity search
- `GET /api/v1/knowledge-graph` - Get knowledge graph

### Google Drive
- `GET /api/v1/gdrive/auth` - Initiate OAuth
- `GET /api/v1/gdrive/files` - List files
- `POST /api/v1/gdrive/sync` - Sync folder

### GPU Services
- `POST /clip/embed-text` - Text embeddings
- `POST /clip/embed-image` - Image embeddings
- `POST /llava/analyze` - Vision analysis
- `POST /llava/extract-text` - OCR

## 🎯 **Use Cases**

- **Personal Knowledge Base**: Store and search all your notes, documents, and ideas
- **Research Assistant**: Analyze papers, extract insights, build connections
- **Document Management**: OCR, categorization, and intelligent search
- **Learning System**: Track learning progress, discover patterns
- **Creative Projects**: Manage inspiration, references, and iterations
- **Code Documentation**: Understand codebases with multimodal analysis

## 🛠️ **Development**

### Running Tests
```bash
pytest tests/ -v
```

### Code Quality
```bash
# Format code
black app/ tests/

# Lint
ruff check app/

# Type checking
mypy app/
```

### Docker Development
```bash
docker-compose up --build
```

## 📚 **Documentation**

- [API Documentation](http://localhost:8001/docs)
- [Architecture Guide](docs/ARCHITECTURE.md)
- [Setup Guide](docs/SETUP.md)
- [Contributing](CONTRIBUTING.md)

## 🤝 **Contributing**

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 **License**

MIT License - see [LICENSE](LICENSE) file.

## 🙏 **Acknowledgments**

- **LM Studio** - Excellent local LLM inference
- **Hugging Face** - Model repository and tools
- **PostgreSQL & pgvector** - Robust vector database
- **FastAPI** - Modern Python web framework
- The open-source AI community

## 🔮 **Roadmap**

- [ ] Ollama integration
- [ ] Web UI improvements
- [ ] Mobile apps
- [ ] Voice input/output
- [ ] Automated model optimization
- [ ] Multi-user support
- [ ] Federated learning

---

<div align="center">

**Built with ❤️ for privacy and self-sovereignty**

No cloud. No tracking. No API keys. Just you and your second brain.

[Report Bug](https://github.com/raold/second-brain/issues) · [Request Feature](https://github.com/raold/second-brain/issues)

</div>