# 🧠 Second Brain

[![Version](https://img.shields.io/badge/version-5.0.0-blue)](https://github.com/raold/second-brain)
[![License](https://img.shields.io/badge/license-AGPL--3.0-green)](https://www.gnu.org/licenses/agpl-3.0.html)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%2B-blue)](https://www.postgresql.org/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![100% Local](https://img.shields.io/badge/100%25-Local_AI-orange)](https://github.com/raold/second-brain)

## 🚀 What is Second Brain?

Second Brain v5.0 is a **100% local AI-powered** personal knowledge management system with multimodal search, Google Drive integration, and photo processing capabilities. NO API KEYS REQUIRED for core functionality - runs entirely on local models (CLIP, LLaVA, Whisper).

### 📊 Latest Achievements

- **64,000+ Photos Processed** - Google Takeout photo pipeline
- **100% Local AI** - No cloud dependencies for core features
- **Multimodal Search** - Text, image, and semantic search
- **Real-time Processing** - WebSocket support for live updates
- **768-dim CLIP Embeddings** - State-of-the-art image understanding

## ✨ Key Features

### 📸 Photo Pipeline
Process Google Takeout exports with automatic HEIC conversion, CLIP embeddings, and LLaVA descriptions.

### 🔍 Multimodal Search
Search by text, image similarity, or semantic meaning across all your memories.

### 🏠 100% Local Option
Run entirely on local models - CLIP for embeddings, LLaVA for vision, Whisper for audio.

### 🗄️ PostgreSQL + pgvector
Unified storage for vectors, metadata, and relationships with sub-100ms search.

### 📁 Google Drive Integration
OAuth 2.0 integration for automatic document and photo sync.

### 📊 Real-time Dashboard
WebSocket-powered live metrics, processing status, and performance monitoring.

## 💻 Quick Start

```bash
# Clone the repository
git clone https://github.com/raold/second-brain.git
cd second-brain

# Set up Python environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Start full stack with Docker (recommended)
docker-compose up -d

# Or run development server
python scripts/run_dev.py  # Port 8001, uses SQLite/mock

# For photo processing
python process_all_photos.py  # Process Google Takeout archives
```

## 📚 API Usage

### Create a Memory

```bash
curl -X POST http://localhost:8000/api/v2/memories \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Important meeting notes from today",
    "importance_score": 0.8,
    "tags": ["work", "meeting"]
  }'
```

### Search Memories

```bash
curl http://localhost:8000/api/v2/memories/search?query="meeting"
```

### Get Statistics

```bash
curl http://localhost:8000/api/v2/statistics
```

## 🏗️ Architecture

Second Brain v5.0 features a comprehensive AI stack:

### Core Services
- **PostgreSQL + pgvector** - Vector database (port 5432)
- **FastAPI** - Main API server (port 8000)
- **CLIP Service** - Image embeddings (port 8002)
- **LLaVA (LM Studio)** - Vision understanding (port 1234)

### Optional Enhancements
- **OpenAI/Anthropic** - Enhanced embeddings and generation
- **Whisper** - Audio transcription
- **Google Drive** - Cloud storage integration

## 📦 Project Structure

```
second-brain/
├── app/                    # Main application
│   ├── core/              # Infrastructure
│   ├── models/            # Data models
│   ├── routes/            # API endpoints
│   ├── services/          # Business logic
│   └── storage/           # Database backends
├── tests/                 # Test suites
├── docs/                  # Documentation
├── scripts/               # Utility scripts
├── docker/                # Docker configs
└── frontend/              # Web UI (SvelteKit)
```

## 🔗 Resources

- [📦 GitHub Repository](https://github.com/raold/second-brain)
- [🎨 Web Interface](interface.html)
- [📖 Full Documentation](https://github.com/raold/second-brain/blob/main/README.md)
- [🐛 Report Issues](https://github.com/raold/second-brain/issues)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](https://github.com/raold/second-brain/blob/main/CONTRIBUTING.md) for details.

## 📝 License

This project is licensed under the [GNU Affero General Public License v3.0 (AGPL-3.0)](https://www.gnu.org/licenses/agpl-3.0.html).

---

© 2024 Second Brain Project | Made with ❤️ by the Second Brain Team