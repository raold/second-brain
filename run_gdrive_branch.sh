#!/bin/bash

# Google Drive Feature Branch Startup Script
# This script ensures the Google Drive feature runs on your Mac

echo "============================================================"
echo "🚀 Second Brain - Google Drive Feature Branch"
echo "============================================================"

# Change to script directory
cd "$(dirname "$0")"

# Check Python version
echo -e "\n📍 Checking environment..."
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
echo "   Python version: $PYTHON_VERSION"

# Check if on correct branch
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null)
if [ "$CURRENT_BRANCH" != "feature/gdrive" ]; then
    echo "⚠️  Warning: Not on feature/gdrive branch (current: $CURRENT_BRANCH)"
fi

# Try to install minimal dependencies
echo -e "\n📦 Checking dependencies..."
if [ -d "venv" ]; then
    source venv/bin/activate 2>/dev/null || true
fi

# Check if FastAPI is installed
if python3 -c "import fastapi" 2>/dev/null; then
    echo "   ✅ FastAPI installed"
    
    # Try to run the full app
    echo -e "\n🔧 Attempting to start full application..."
    echo "   URL will be: http://localhost:8001"
    echo "   Google Drive UI: http://localhost:8001/static/gdrive-ui.html"
    echo -e "\n💡 Press Ctrl+C to stop the server"
    echo "============================================================"
    
    # Set environment variables for mock mode
    export USE_MOCK_DATABASE=true
    export OPENAI_API_KEY="sk-mock-key-for-testing"
    export DATABASE_URL="sqlite+aiosqlite:///./test.db"
    
    # Try to start with uvicorn
    if command -v uvicorn &> /dev/null; then
        uvicorn app.app:app --reload --host 0.0.0.0 --port 8001
    else
        python3 -m uvicorn app.app:app --reload --host 0.0.0.0 --port 8001
    fi
else
    echo "   ⚠️  FastAPI not installed"
    echo -e "\n📌 Starting demo server instead..."
    echo "   This will show the Google Drive UI in demo mode"
    echo "============================================================"
    
    # Run the demo server
    python3 start_gdrive_demo.py
fi