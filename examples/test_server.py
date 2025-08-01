#!/usr/bin/env python3
"""
Minimal test server to verify Project Pipeline functionality
"""

import os

import uvicorn
from fastapi import FastAPI

# Create minimal FastAPI app
app = FastAPI(title="Project Pipeline Test", version="1.0.0")


@app.get("/")
async def root():
    return {"message": "🎯 Project Pipeline Test Server", "status": "working"}


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": "2025-07-17"}


@app.get("/test-dashboard")
async def test_dashboard():
    try:
        from app.dashboard import get_dashboard

        dashboard = get_dashboard()

        return {
            "status": "success",
            "dashboard_initialized": True,
            "milestones_count": len(dashboard.milestones),
            "message": "✅ Dashboard working!",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/test-session")
async def test_session():
    try:
        from app.session_manager import get_session_manager

        session_manager = get_session_manager()

        return {
            "status": "success",
            "session_initialized": True,
            "current_session": session_manager.current_session.session_id if session_manager.current_session else None,
            "message": "✅ Session management working!",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    print("🚀 Starting Project Pipeline Test Server...")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
