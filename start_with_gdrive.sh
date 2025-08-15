#!/bin/bash

# Second Brain v4.2.3 with Google Drive Integration
# Production-ready startup script

echo "=================================================="
echo "🧠 Second Brain v4.2.3 + Google Drive"
echo "=================================================="

# Change to script directory
cd "$(dirname "$0")"

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating template..."
    cat > .env << 'EOF'
# Google OAuth Configuration (REQUIRED for Google Drive)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8001/api/v1/gdrive/callback

# Database (use one of these)
DATABASE_URL=postgresql://user:password@localhost/secondbrain
USE_MOCK_DATABASE=true

# OpenAI (optional)
OPENAI_API_KEY=mock

# Application
APP_ENV=development
PORT=8001
EOF
    echo "✅ Created .env template"
    echo "📝 Please edit .env and add your Google OAuth credentials"
    echo "   See GOOGLE_OAUTH_SETUP.md for instructions"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check if Google credentials are configured
if [ -z "$GOOGLE_CLIENT_ID" ]; then
    echo "⚠️  Google OAuth not configured!"
    echo "   Please add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env"
    echo "   See GOOGLE_OAUTH_SETUP.md for instructions"
    echo ""
    echo "Do you want to continue without Google Drive? (y/n)"
    read -r response
    if [ "$response" != "y" ]; then
        exit 1
    fi
fi

# Check Python
echo "🔍 Checking environment..."
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python not found!"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
echo "   Python version: $PYTHON_VERSION"

# Check/create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    $PYTHON_CMD -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📦 Checking dependencies..."
pip install -q --upgrade pip

# Install core requirements
pip install -q fastapi uvicorn pydantic python-dotenv aiofiles psutil 2>/dev/null

# Install Google Drive requirements
pip install -q google-auth google-auth-oauthlib google-api-python-client 2>/dev/null

# Install database requirements
if [ "$USE_MOCK_DATABASE" != "true" ]; then
    pip install -q asyncpg psycopg2-binary pgvector 2>/dev/null
fi

# Check if PostgreSQL is needed and running
if [ "$USE_MOCK_DATABASE" != "true" ] && [ -n "$DATABASE_URL" ]; then
    echo "🐘 Checking PostgreSQL..."
    if ! pg_isready -q 2>/dev/null; then
        echo "⚠️  PostgreSQL not running. Starting in mock mode..."
        export USE_MOCK_DATABASE=true
    else
        echo "   PostgreSQL is running"
    fi
fi

# Start the application
echo ""
echo "=================================================="
echo "🚀 Starting Second Brain with Google Drive"
echo "=================================================="
echo ""
echo "📌 Access Points:"
echo "   • Main App: http://localhost:${PORT:-8001}"
echo "   • Google Drive UI: http://localhost:${PORT:-8001}/static/gdrive-ui.html"
echo "   • API Docs: http://localhost:${PORT:-8001}/docs"
echo ""

if [ -n "$GOOGLE_CLIENT_ID" ]; then
    echo "✅ Google Drive: Configured and ready"
else
    echo "⚠️  Google Drive: Not configured (see GOOGLE_OAUTH_SETUP.md)"
fi

if [ "$USE_MOCK_DATABASE" == "true" ]; then
    echo "💾 Database: Mock mode (in-memory)"
else
    echo "💾 Database: PostgreSQL"
fi

echo ""
echo "💡 Press Ctrl+C to stop"
echo "=================================================="
echo ""

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port ${PORT:-8001}