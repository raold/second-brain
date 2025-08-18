#!/bin/bash
# Second Brain - Unix Development Starter (Mac/Linux)

echo "========================================="
echo "Second Brain Development Environment"
echo "========================================="
echo ""

# Detect platform
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="Linux"
else
    PLATFORM="Unix"
fi

echo "Platform: $PLATFORM"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi

# Run platform setup if needed
if [ ! -f "docker-compose.override.yml" ]; then
    echo "First time setup detected. Configuring for $PLATFORM..."
    ./setup-platform.sh
    echo ""
fi

# Start Docker services
echo "[1/3] Starting Docker services..."
docker-compose up -d

if [ $? -ne 0 ]; then
    echo "❌ Failed to start Docker services"
    exit 1
fi

echo ""
echo "[2/3] Waiting for services to be ready..."
sleep 5

# Start CLIP in background
echo ""
echo "[3/3] Starting GPU services..."
echo "Starting CLIP service in background..."
cd services/gpu/clip && nohup python clip_api.py > clip.log 2>&1 &
CLIP_PID=$!
cd - > /dev/null
echo "CLIP service started (PID: $CLIP_PID)"

# Show status
echo ""
echo "========================================="
echo "Services Status:"
echo "========================================="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "second"

echo ""
echo "========================================="
echo "All services started successfully!"
echo "========================================="
echo ""
echo "Web Interfaces:"
echo "  • Main App:        http://localhost:8000"
echo "  • API Docs:        http://localhost:8000/docs"
echo "  • Photo Pipeline:  http://localhost:8000/static/photo-pipeline.html"
echo "  • Database Admin:  http://localhost:8080"
echo "  • LM Studio:       http://localhost:1234"
echo ""
echo "GPU Services:"
echo "  • CLIP (8002):     Running (PID: $CLIP_PID)"
echo "  • LM Studio:       Start manually if needed"
echo ""
echo "To stop all services:"
echo "  • Docker: docker-compose down"
echo "  • CLIP:   kill $CLIP_PID"
echo "========================================="