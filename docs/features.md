# 🚀 Features

## Core Capabilities

### 📸 Photo Processing Pipeline
- **Google Takeout Support**: Process entire photo archives from Google Photos exports
- **HEIC Conversion**: Automatic conversion of iPhone HEIC images
- **Batch Processing**: Handle thousands of photos efficiently with progress tracking
- **Duplicate Detection**: Skip already processed images automatically

### 🧠 AI-Powered Analysis
- **CLIP Embeddings**: 768-dimensional vectors for semantic image search
- **LLaVA Descriptions**: Automatic image captioning and content understanding
- **100% Local Option**: Run entirely on local models without cloud dependencies
- **Optional Cloud AI**: Enhance with OpenAI/Anthropic when needed

### 🔍 Multimodal Search
- **Text Search**: Full-text search across all memories
- **Image Similarity**: Find visually similar photos using CLIP
- **Semantic Search**: Query by meaning, not just keywords
- **Hybrid Search**: Combine multiple search strategies

### 💾 Storage & Database
- **PostgreSQL + pgvector**: Production-grade vector database
- **Unified Storage**: Single database for vectors, metadata, and content
- **Efficient Compression**: 60% storage reduction with smart compression
- **Mock Mode**: In-memory storage for development

### 📊 Real-time Monitoring
- **Live Dashboard**: WebSocket-powered real-time metrics
- **Processing Status**: Track photo pipeline progress
- **Performance Metrics**: CPU, memory, and GPU utilization
- **System Health**: Service availability monitoring

### 🔌 Integrations

#### Google Drive
- **OAuth 2.0**: Secure authentication flow
- **Automatic Sync**: Keep memories synchronized
- **Document Processing**: Extract text from PDFs and documents
- **Folder Navigation**: Browse and process specific folders

#### LM Studio
- **LLaVA Integration**: Vision-language model for image understanding
- **Local Inference**: Run models on your own hardware
- **Custom Models**: Support for various model architectures

## Architecture Highlights

### Services & Ports
| Service | Port | Purpose |
|---------|------|---------|
| FastAPI | 8000/8001 | Main API server |
| PostgreSQL | 5432 | Vector database |
| CLIP | 8002 | Image embeddings |
| LLaVA | 1234 | Vision understanding |
| Adminer | 8080 | Database UI |

### Performance
- **Sub-100ms Search**: Optimized vector similarity search
- **42 photos/minute**: Average processing rate
- **5.8GB/hour**: Typical throughput for photo archives
- **768-dim vectors**: State-of-the-art CLIP embeddings

### Development Features
- **Hot Reload**: Automatic server restart on code changes
- **Mock Services**: Development without external dependencies
- **Comprehensive Tests**: 165+ unit and integration tests
- **Docker Support**: One-command deployment

## Supported File Types

### Images
- JPEG/JPG
- PNG
- GIF
- HEIC/HEIF (with conversion)
- WebP
- BMP

### Documents
- PDF
- TXT
- Markdown
- JSON
- CSV

### Archives
- Google Takeout ZIP files
- Standard ZIP archives

## API Capabilities

### RESTful Endpoints
- `POST /api/v2/memories` - Create memories
- `GET /api/v2/memories/search` - Search memories
- `GET /api/v2/statistics` - System statistics
- `GET /api/v2/metrics` - Performance metrics

### WebSocket Support
- `/api/photo-pipeline/ws` - Real-time processing updates
- `/api/v2/ws` - General WebSocket connection

### Batch Operations
- Bulk memory creation
- Batch embedding generation
- Archive processing

## Security Features
- Environment-based configuration
- API key authentication (optional)
- CORS configuration
- SQL injection prevention
- Input validation with Pydantic

## Platform Support
- **Windows 11**: Native and WSL2 support
- **macOS**: Intel and Apple Silicon
- **Linux**: Ubuntu, Debian, Arch
- **Docker**: Cross-platform containers

## Coming Soon
- Knowledge graph visualization
- Audio transcription with Whisper
- Advanced memory relationships
- Mobile app support
- Browser extension