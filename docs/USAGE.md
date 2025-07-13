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
    "timestamp": "2025-07-13T00:00:00Z"
  }
}
```

### Search
`GET /search?q=<query>`
- Requires `Authorization: Bearer <token>`
- Returns semantically similar entries.

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

## Logs
Available under `logs/processor.log`.
