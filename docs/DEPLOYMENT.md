# Deployment Instructions for second-brain

## Prerequisites
- Docker and Docker Compose installed
- An OpenAI API key
- Postgres (included in docker-compose)

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/raold/second-brain.git
cd second-brain
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
This will start the FastAPI app, Qdrant, and Postgres services.

### 4. Verify the API is Running
```bash
curl http://localhost:8000/health
```
Expected output:
```json
{"status": "ok"}
```

## Services

### second_brain
- Hosts the FastAPI application.
- Exposes API on port 8000.

### Qdrant
- Runs on port 6333 for vector storage.

### Postgres
- Runs on port 5432 for memory persistence.

## Directory Structure
```
second-brain/
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
docker exec -it second_brain /bin/bash
```

## Additional Notes
- Electron and mobile/PWA clients can be run separately; see README for details.
- Ensure ports 8000 (API), 6333 (Qdrant), and 5432 (Postgres) are open on your host.
- Use a `.env` file for secret keys and environment configuration.
