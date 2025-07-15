[ 🎙️ Voice Input ]
       │
       ▼
[ Whisper ASR (local/cloud) ]
   → Converts speech to text
       │
       ▼
[ LLM Output Processor API ]
    POST /ingest
    - Token-based auth
    - Adds metadata (context, priority, etc.)
       │
       ▼
+------------------------------+
| Qdrant Vector Store          |
| + Markdown storage (.md)     |
| + Version history tracking   |
+------------------------------+
       │
       ▼
[ Observability ]
- Metrics (Prometheus / Grafana)
- Logs (structured / JSON)
- Errors (Sentry)
       │
       ▼
[ Retrieval via API ]
  /search
  /ranked-search
  /records
  /ws/generate (for live responses)
