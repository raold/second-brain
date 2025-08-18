# 🚀 Getting Started

## Prerequisites

### Required
- Python 3.11+
- Docker & Docker Compose
- 8GB+ RAM
- 20GB+ free disk space

### Optional (for enhanced features)
- NVIDIA GPU (for faster CLIP processing)
- LM Studio (for LLaVA vision model)
- Google account (for Drive integration)

## Quick Start (5 minutes)

### 1. Clone the Repository
```bash
git clone https://github.com/raold/second-brain.git
cd second-brain
```

### 2. Set Up Environment
```bash
# Copy environment template
cp .env.example .env

# Create Python virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Start Services

#### Option A: Full Stack (Recommended)
```bash
# Start all services with Docker
docker-compose up -d

# Verify services are running
docker ps

# Access the API
curl http://localhost:8000/
```

#### Option B: Development Mode
```bash
# Use mock database (no PostgreSQL needed)
python scripts/run_dev.py

# API will be available at http://localhost:8000
```

### 4. Verify Installation
```bash
# Check API health
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","version":"5.0.0"}
```

## Photo Processing Setup

### 1. Start CLIP Service
```bash
cd services/gpu/clip
python clip_api.py

# Should see: Uvicorn running on http://0.0.0.0:8002
```

### 2. Start LLaVA (Optional)
1. Open LM Studio
2. Download model: `llava-v1.6-mistral-7b`
3. Start server on port 1234

### 3. Process Google Takeout
```bash
# Place takeout zips in G:/My Drive/Takeout/
# Or configure TAKEOUT_PATH in .env

# Process all photos
python process_all_photos.py
```

## Web Interface

### Access Dashboards
- **Main UI**: http://localhost:8000/
- **API Docs**: http://localhost:8000/docs
- **Photo Pipeline**: http://localhost:8000/api/photo-pipeline/
- **Metrics**: http://localhost:8000/api/v2/metrics/dashboard
- **Database UI**: http://localhost:8080 (Adminer)

### Database Credentials (Adminer)
- System: PostgreSQL
- Server: postgres
- Username: secondbrain
- Password: changeme
- Database: secondbrain

## First Memory

### Create via API
```bash
curl -X POST http://localhost:8000/api/v2/memories \
  -H "Content-Type: application/json" \
  -d '{
    "content": "My first memory in Second Brain!",
    "importance_score": 0.8,
    "tags": ["test", "first"]
  }'
```

### Search Memories
```bash
curl "http://localhost:8000/api/v2/memories/search?query=first"
```

## Configuration

### Essential Environment Variables
```env
# Database
DATABASE_URL=postgresql://secondbrain:changeme@localhost/secondbrain
USE_MOCK_DATABASE=false

# Services
CLIP_SERVICE_URL=http://localhost:8002
LLAVA_SERVICE_URL=http://localhost:1234

# Paths
GDRIVE_MOUNT_PATH=G:/My Drive
TAKEOUT_PATH=G:/My Drive/Takeout

# Optional API Keys
OPENAI_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here
```

### Performance Tuning
```env
# Photo Processing
PHOTO_BATCH_SIZE=20
EMBEDDING_BATCH_SIZE=10
ENABLE_LLAVA_DESCRIPTIONS=true

# API Settings
API_PORT=8000
ENVIRONMENT=development
```

## Troubleshooting

### Common Issues

#### "CLIP service not available"
```bash
# Start CLIP service
cd services/gpu/clip
python clip_api.py
```

#### "Cannot connect to PostgreSQL"
```bash
# Start PostgreSQL
docker-compose up -d postgres

# Check if running
docker ps | grep postgres
```

#### "Google Drive not mounted"
- Windows: Ensure Google Drive Desktop is running
- Check path exists: `dir "G:\My Drive"`

#### Port conflicts
```bash
# Windows: Find process using port
netstat -ano | findstr :8000

# Kill process
taskkill /PID <pid> /F

# Mac/Linux:
lsof -i :8000
kill -9 <pid>
```

## Next Steps

1. 📸 [Process your photos](features.md#photo-processing-pipeline)
2. 🔍 [Set up search](features.md#multimodal-search)
3. 📊 [Monitor performance](features.md#real-time-monitoring)
4. 🔌 [Configure integrations](features.md#integrations)
5. 🚀 [Deploy to production](deployment.md)

## Getting Help

- 📖 [Full Documentation](https://github.com/raold/second-brain/blob/main/README.md)
- 🐛 [Report Issues](https://github.com/raold/second-brain/issues)
- 💬 [Discussions](https://github.com/raold/second-brain/discussions)
- 📧 [Contact Team](mailto:support@secondbrain.ai)