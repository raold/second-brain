#!/usr/bin/env python
"""Simple backend starter with mock database fallback"""
import os
import sys
import uvicorn

# Force mock database for now since PostgreSQL isn't running
os.environ["USE_MOCK_DB"] = "true"
os.environ["ENVIRONMENT"] = "development"

# Ensure we have an API key
if not os.environ.get("OPENAI_API_KEY"):
    print("⚠️ Warning: OPENAI_API_KEY not set, some features will be disabled")

print("🚀 Starting Second Brain Backend v4.2.3")
print("📍 Using mock database (PostgreSQL not available)")
print("🌐 API will be available at http://localhost:8001")
print("📚 API Docs at http://localhost:8001/docs")

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )