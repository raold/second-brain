#!/usr/bin/env python3
"""
Simple test script to run the dashboard with mock data
"""

import os
import uvicorn

# Set environment variable to use mock database
os.environ["USE_MOCK_DATABASE"] = "true"

if __name__ == "__main__":
    print("🚀 Starting Project Pipeline Dashboard...")
    print("📍 Dashboard URL: http://127.0.0.1:8000/")
    print("📍 API Docs: http://127.0.0.1:8000/docs")
    print("\n✅ Using mock database for testing")
    
    # Run the application
    uvicorn.run(
        "app.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    ) 