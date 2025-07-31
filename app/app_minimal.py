"""
Minimal Second Brain App - Just get it running
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.health_routes import router as health_router

# Create app
app = FastAPI(
    title="Second Brain API",
    description="Personal Knowledge Management System",
    version="3.0.0-minimal"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add only working routes
app.include_router(health_router, prefix="/api/v1")

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Second Brain API is running (minimal mode)"}

@app.get("/docs-status")
async def docs_status():
    return {"docs_available": True, "url": "/docs"}
