"""
Main application entry point using factory pattern
"""

import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.factory import create_app

# Determine environment
environment = os.getenv("ENVIRONMENT", "development")

# Create app using factory
app = create_app(environment)

# Mount static files (HTML interfaces)
static_dir = Path(__file__).parent.parent  # Go up to project root
if (static_dir / "interface.html").exists():
    # Serve individual HTML files
    @app.get("/interface.html")
    async def serve_interface():
        return FileResponse(static_dir / "interface.html")
    
    @app.get("/interface_production.html")
    async def serve_interface_production():
        return FileResponse(static_dir / "interface_production.html")
    
    # Also serve docs folder for GitHub Pages locally
    if (static_dir / "docs").exists():
        app.mount("/docs-static", StaticFiles(directory=str(static_dir / "docs")), name="docs")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=environment == "development",
    )
