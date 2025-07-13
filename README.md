# LLM Output Processor

> Ingest and search semantically indexed memory using OpenAI embeddings and Qdrant vector database.

---

## 📦 Project Structure

```
llm_output_processor/
├── app/                 # Core FastAPI application
│   ├── main.py          # App entry point
│   ├── router.py        # API routes (/ingest, /search, /health)
│   ├── qdrant_client.py # Qdrant upsert/search logic
│   ├── auth.py          # Token verification
│   └── utils/
│       ├── logger.py    # Loguru logger config
│       └── openai_client.py # OpenAI embeddings client
├── docker-compose.yml   # Docker Compose orchestration
├── Dockerfile           # App container definition
├── requirements.txt     # Python dependencies
├── logs/                # Processor logs (ensure this exists)
├── qdrant_data/         # Qdrant persistent storage
├── data/                # General data storage (optional)
└── README.md            # Project overview
```

---

## 🚀 Setup

### 1. Prerequisites
- Docker + Docker Compose
- OpenAI API key

### 2. Clone & Configure
Create a `.env` file (for local dev):
```
OPENAI_API_KEY=your_openai_key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

Alternatively, set these in **docker-compose.yml** under `environment`.

### 3. Build & Run
```bash
docker compose up --build -d
```

Qdrant UI: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)  
API Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## ✅ API Endpoints

- `POST /ingest`: Ingest a note for semantic indexing.
- `GET /search?q=query`: Semantic search.
- `GET /health`: Health check.

### Example Ingest
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{ "id": "check-1", "type": "note", "data": {"note": "test embedding"} }'
```

---

## 🧩 Components

- **Qdrant**: High-performance vector database for storage & search.
- **OpenAI Embeddings**: `text-embedding-3-small` model for vectorization.
- **FastAPI**: API layer for ingestion, search, and health check.
- **Loguru**: Structured logging to `logs/processor.log`.

---

## 🛠️ Development

Rebuild after code changes:
```bash
docker compose build
docker compose up -d
```

Logs:
```bash
tail -f logs/processor.log
```

---

## ✅ Roadmap
- Dynamic collection versioning
- Batch ingestion
- Health endpoints with dimension checks
- Voice command integration

---

## 🔒 Security
Ensure API tokens are rotated and stored securely via Docker secrets or environment variables.

---

## ✅ License
MIT or internal/private — adjust as necessary.
