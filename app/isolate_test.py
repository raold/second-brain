from fastapi import FastAPI
from fastapi.testclient import TestClient
from typing import Optional

app = FastAPI()

@app.get("/zzzzzzzzzz")
def zzzzzzzzzz_handler(type: Optional[str] = None, note: Optional[str] = None, limit: int = 20, offset: int = 0):
    return {"records": [{"id": "abc123", "note": "Test note", "type": "test", "timestamp": "2025-07-14T00:00:00Z"}], "total": 1} 