# LLM Output Processor - Usage Guide

## API Endpoints

### Health Check
`GET /health`
- Returns: `{ "status": "ok" }`

### Ingest
`POST /ingest`
- Requires `Authorization: Bearer <token>`
- Payload Example:
```json
{
  "id": "example-id",
  "type": "note",
  "context": "example",
  "priority": "normal",
  "ttl": "1d",
  "data": {
    "note": "Some text to embed"
  },
  "metadata": {
    "source": "manual",
    "timestamp": "2025-07-13T00:00:00Z",
    "intent": "note",
    "model_version": "gpt-4o"
  }
}
```

### WebSocket Streaming
`GET /ws/generate`
- Real-time LLM output streaming (JSON or text chunks)
- Requires `Authorization: Bearer <token>`

### Memories Search
`POST /memories/search`
- SQL query for memories/metadata (Postgres)

### Summarize Memories
`POST /memories/summarize`
- Summarize memories via LLM

### Feedback
`POST /feedback`
- Submit feedback (upvote, correct, ignore)

### Plugins
`POST /plugin/{name}`
- Trigger plugin actions (reminder, webhook, file search, etc)

## Electron/Mobile/PWA Usage
- See README for setup and usage of Electron and mobile/PWA clients.
- Voice input, real-time streaming, TTS, and advanced UI/UX supported.

## Running the App

```bash
make build
make up
make logs
```

## Testing

```bash
make test
```
- See [Testing Guide](./TESTING.md) for details on our mocking approach for OpenAI and Qdrant in integration tests.

## Logs
Available under `logs/processor.log`.
