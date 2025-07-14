# Deployment Instructions for llm_output_processor

## Prerequisites
- Docker and Docker Compose installed
- An OpenAI API key

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/raold/second-brain.git
cd llm_output_processor_v1.0
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
```
Edit `.env` to set your OpenAI API key and other settings.

### 3. Build and Start the Services
```bash
docker compose up --build -d
```

### 4. Verify the API is Running
```bash
curl http://localhost:8000/health
```
Expected output:
```json
{"status": "ok"}
```

## Services

### llm_output_processor
- Hosts the FastAPI application.
- Exposes API on port 8000.

### Qdrant
- Runs on port 6333 for vector storage.

## Directory Structure
```
llm_output_processor_v1.0/
├── app/
├── logs/
├── qdrant_data/
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── Makefile
```

## Additional Commands
### Stop the stack
```bash
docker compose down
```

### Check logs
```bash
docker compose logs -f
```

### Enter the app container
```bash
docker exec -it llm_output_processor /bin/bash
```

## Notes
- Ensure ports 8000 (API) and 6333 (Qdrant) are open on your host.
- Use a `.env` file for secret keys and environment configuration.
