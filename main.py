"""
Main entry point for Second Brain API.

This is the primary application entry point. Run with:
    uvicorn main:app --reload
    
Or directly:
    python main.py
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import the FastAPI app
from app.app import app

# Development configuration
if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment variables
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("DEBUG", "false").lower() == "true"
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    
    print(f"Starting Second Brain API v3.0.0")
    print(f"Host: {host}:{port}")
    print(f"Auto-reload: {reload}")
    print(f"Log level: {log_level}")
    print(f"API docs: http://localhost:{port}/docs")
    print()
    
    # Run the application
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )