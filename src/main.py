"""
Main entry point for Second Brain API.

Run with: uvicorn src.main:app --reload
"""

import os

from src.api import create_app

# Create FastAPI application
app = create_app(
    title="Second Brain API",
    version="3.0.0",
    debug=os.getenv("DEBUG", "false").lower() == "true",
)

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("DEBUG", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )