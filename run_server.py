#!/usr/bin/env python
"""Start the Second Brain FastAPI server"""

import uvicorn
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("Starting Second Brain server on http://localhost:8000")
    print("Ingestion interface available at http://localhost:8000/ingestion")
    print("API docs available at http://localhost:8000/docs")
    
    uvicorn.run(
        "app.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )