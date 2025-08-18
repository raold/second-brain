#!/bin/bash
# Docker management script for Mac/Linux
# Use start-dev.sh for initial setup and startup

case "$1" in
  start)
    echo "🚀 Starting Second Brain services..."
    docker-compose up -d
    echo "✅ Services running at http://localhost:8000"
    ;;
  stop)
    echo "🛑 Stopping services..."
    docker-compose down
    ;;
  restart)
    echo "🔄 Restarting app..."
    docker-compose restart app
    ;;
  logs)
    docker-compose logs -f app
    ;;
  test)
    echo "🧪 Running tests..."
    docker exec -it secondbrain-app python -m pytest tests/unit/ -v
    ;;
  shell)
    echo "📟 Opening shell in app container..."
    docker exec -it secondbrain-app /bin/bash
    ;;
  db)
    echo "🗄️ Connecting to database..."
    docker exec -it secondbrain-postgres psql -U secondbrain
    ;;
  format)
    echo "🎨 Formatting code..."
    docker exec -it secondbrain-app black .
    docker exec -it secondbrain-app isort .
    ;;
  lint)
    echo "🔍 Linting code..."
    docker exec -it secondbrain-app ruff check .
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|logs|test|shell|db|format|lint}"
    exit 1
    ;;
esac