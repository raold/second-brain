#!/bin/bash

echo "========================================="
echo "  SECOND BRAIN v4.2.0 - BACKEND STARTUP"
echo "========================================="
echo ""

# Kill any existing backend
echo "🔄 Stopping any existing backends..."
pkill -f uvicorn 2>/dev/null
sleep 2

# Check PostgreSQL connection
echo "🔍 Checking PostgreSQL connection..."
PGPASSWORD=changeme psql -h localhost -U secondbrain -d secondbrain -c "SELECT version();" > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "❌ PostgreSQL is not accessible!"
    echo ""
    echo "Please ensure PostgreSQL is running:"
    echo "1. Open PowerShell/CMD on Windows"
    echo "2. Run: cd C:\\tools\\second-brain"
    echo "3. Run: docker-compose up -d postgres"
    echo ""
    echo "Or install PostgreSQL locally with:"
    echo "sudo apt update && sudo apt install postgresql-16 postgresql-16-pgvector"
    exit 1
fi

echo "✅ PostgreSQL is accessible!"

# Initialize database schema
echo "📊 Initializing database schema..."
.venv/bin/python scripts/setup_postgres_pgvector.py

# Check OpenAI key
echo "🔑 Checking OpenAI API key..."
if [ -z "$OPENAI_API_KEY" ]; then
    source .env 2>/dev/null || true
fi

if [[ "$OPENAI_API_KEY" == *"sk-"* ]]; then
    echo "✅ OpenAI API key found"
else
    echo "⚠️  Warning: OpenAI API key may not be valid"
    echo "   Embeddings will not work without a valid key"
fi

# Start the REAL backend
echo ""
echo "🚀 Starting the REAL Second Brain backend..."
echo "========================================="
echo "  API: http://localhost:8000"
echo "  Docs: http://localhost:8000/docs"
echo "  Database: PostgreSQL with pgvector"
echo "  AI: OpenAI embeddings enabled"
echo "========================================="
echo ""

.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload