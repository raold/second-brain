#!/usr/bin/env python3
"""
Development server runner with SQLite fallback
"""

import os
import sys
import uvicorn

# Force SQLite for development
os.environ["DATABASE_URL"] = "sqlite:///data/memories.db"
os.environ["USE_SQLITE"] = "true"
os.environ["USE_MOCK_DATABASE"] = "true"
os.environ["ENABLE_EMBEDDINGS"] = "false"  # Disable embeddings for now

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )