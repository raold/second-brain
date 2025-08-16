#!/bin/bash
# Start GPU services for second-brain

echo "🚀 Starting Second-Brain GPU Services..."

# Check for NVIDIA GPU
if ! command -v nvidia-smi &> /dev/null; then
    echo "❌ NVIDIA GPU not detected. Please ensure CUDA is installed."
    exit 1
fi

echo "✅ GPU detected:"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

# Create models directory if not exists
mkdir -p models

# Start services with Docker Compose
if command -v docker-compose &> /dev/null; then
    docker-compose -f docker-compose.gpu.yml up -d
else
    docker compose -f docker-compose.gpu.yml up -d
fi

echo ""
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo ""
echo "🔍 Checking service status:"

# Check Redis
if curl -s http://localhost:6379 > /dev/null 2>&1; then
    echo "✅ Redis: Running on port 6379"
else
    echo "⚠️  Redis: Not responding"
fi

# Check CLIP
if curl -s http://localhost:8002/clip/status > /dev/null 2>&1; then
    echo "✅ CLIP Service: Running on port 8002"
else
    echo "⚠️  CLIP Service: Starting up (may take a minute)..."
fi

# Check LLaVA
if curl -s http://localhost:8003/llava/status > /dev/null 2>&1; then
    echo "✅ LLaVA Service: Running on port 8003"
else
    echo "⚠️  LLaVA Service: Starting up (may take a few minutes)..."
fi

echo ""
echo "📊 GPU Services Dashboard:"
echo "  - CLIP API: http://localhost:8002/docs"
echo "  - LLaVA API: http://localhost:8003/docs"
echo ""
echo "💡 To view logs: docker-compose -f docker-compose.gpu.yml logs -f"
echo "💡 To stop services: docker-compose -f docker-compose.gpu.yml down"