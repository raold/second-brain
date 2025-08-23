<div align="center">
<img src="logo.png" alt="Second Brain Logo" width="400">

# 🧠 Second Brain v5

### 100% Local AI-Powered Knowledge Management System

[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue.svg)](https://www.postgresql.org/)
[![pgvector](https://img.shields.io/badge/pgvector-0.8.0-blue.svg)](https://github.com/pgvector/pgvector)

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
- Stream files using Google Drive API - no storage required
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
- **Docker Desktop** (required) - [Download](https://www.docker.com/products/docker-desktop/)
- 16GB+ RAM recommended
- 20GB+ free disk space

### 1. Clone Repository
```bash
git clone https://github.com/raold/second-brain.git
cd second-brain
```

### 2. Platform Setup (One-time)
```bash
# Copy environment file
cp .env.example .env

# Auto-configure for your platform
./setup-platform.sh     # Mac/Linux
# OR
setup-platform.bat      # Windows (coming soon)
```

### 3. Start Everything
```bash
# Quick start with platform-specific script:
./start-dev.sh          # Mac/Linux  
./start-dev.bat         # Windows

# OR manually with Docker:
docker-compose up -d
```

### 3. Access the Application
- **Main App**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Photo Pipeline**: http://localhost:8000/static/photo-pipeline.html
- **Database Admin**: http://localhost:8080

### Optional: Local AI Models
For GPU-accelerated vision features:
```bash
# Start GPU services with Docker
docker-compose -f docker-compose.gpu.yml up -d
```

## 📊 **Architecture**

```mermaid
graph TB
    subgraph "Local Services"
        LM[LM Studio<br/>:1234]
        CLIP[CLIP Service<br/>:8002]
        LLAVA[LLaVA Service<br/>:8003]
    end
    
    subgraph "Core"
        API[FastAPI<br/>:8000]
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
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/api/v1/gdrive/callback
```

## ⚙️ Models
| Component | Default | Source | Approx Size |
|-----------|---------|--------|-------------|
| Text/Vision (LLaVA) | llava-1.6-mistral-7b Q6_K | LM Studio | ~5–7 GB |
| Text Embeddings | nomic-embed-text | Hugging Face | ~300 MB |
| CLIP | ViT-L/14 | Hugging Face | ~1 GB |

## 📈 **Performance**

Tested on RTX 4090:

| Operation | Performance | Conditions |
|-----------|-------------|-----------|
| Text Embedding | ~100ms/doc | batch=16 |
| Image Embedding | ~300ms/image | 4090, fp16 |
| Vision Analysis | 2–5s/image | 1024px |
| Vector Search | <50ms | top_k=10 |
| Hybrid Search | <100ms | rerank enabled |
| Doc Processing | 200 docs/min | avg 1 KB chunks |

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

## 🧪 API Examples

Create a memory:
```bash
curl -X POST http://localhost:8000/api/v1/memories \
  -H "Content-Type: application/json" \
  -d '{"type":"text","content":"Graph neural nets paper notes","tags":["gnn","research"]}'
```

Semantic search:
```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query":"recent notes about vision transformers","limit":5}'
```

Image similarity:
```bash
curl -X POST http://localhost:8000/api/v1/search/image \
  -F file=@example.jpg
```

## 🎯 **Use Cases**

- **Personal Knowledge Base**: Store and search all your notes, documents, and ideas
- **Research Assistant**: Analyze papers, extract insights, build connections
- **Document Management**: OCR, categorization, and intelligent search
- **Learning System**: Track learning progress, discover patterns
- **Creative Projects**: Manage inspiration, references, and iterations
- **Code Documentation**: Understand codebases with multimodal analysis

## 📚 **Documentation**

- [API Documentation](http://localhost:8000/docs)
- [Architecture Guide](docs/ARCHITECTURE.md)
- [Setup Guide](docs/SETUP.md)
- [Contributing](CONTRIBUTING.md)

## 🤝 **Contributing**

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.


## 🙏 **Acknowledgments**

- **LM Studio** - Excellent local LLM inference
- **Hugging Face** - Model repository and tools
- **PostgreSQL & pgvector** - Robust vector database
- **FastAPI** - Modern Python web framework
- The open-source AI community

## 🔮 **Roadmap**

- [ ] Apple Silicon optimization
- [ ] Ollama integration
- [ ] Web UI improvements
- [ ] Mobile apps
- [ ] Voice input/output
- [ ] Self-supervised learning
- [ ] Automated model optimization
- [ ] Multi-user support
- [ ] Federated learning

---

<div align="center">

**Built with ❤️ for privacy and self-sovereignty**

No cloud. No tracking. No API keys. Just you and your second brain.

[Report Bug](https://github.com/raold/second-brain/issues) · [Request Feature](https://github.com/raold/second-brain/issues)

</div>
