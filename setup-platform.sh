#!/bin/bash
# Second Brain - Cross-Platform Setup Script
# Automatically configures for Windows, Mac, or Linux

set -e

echo "========================================="
echo "Second Brain - Platform Configuration"
echo "========================================="
echo ""

# Detect platform
detect_platform() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "mac"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OS" == "Windows_NT" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

PLATFORM=$(detect_platform)
echo "Detected platform: $PLATFORM"
echo ""

# Create docker-compose.override.yml based on platform
create_override_file() {
    case $PLATFORM in
        windows)
            cat > docker-compose.override.yml << 'EOF'
# Auto-generated for Windows
services:
  app:
    environment:
      - CLIP_SERVICE_URL=http://host.docker.internal:8002
      - LLAVA_SERVICE_URL=http://host.docker.internal:8003
      - LM_STUDIO_URL=http://host.docker.internal:1234
      - DATABASE_URL=postgresql://secondbrain:changeme@postgres:5432/secondbrain
      - ENVIRONMENT=development
      - LOG_LEVEL=INFO
    extra_hosts:
      - "host.docker.internal:host-gateway"
EOF
            echo "✅ Created docker-compose.override.yml for Windows"
            ;;
            
        mac)
            cat > docker-compose.override.yml << 'EOF'
# Auto-generated for macOS
services:
  app:
    environment:
      - CLIP_SERVICE_URL=http://host.docker.internal:8002
      - LLAVA_SERVICE_URL=http://host.docker.internal:8003
      - LM_STUDIO_URL=http://host.docker.internal:1234
      - DATABASE_URL=postgresql://secondbrain:changeme@postgres:5432/secondbrain
      - ENVIRONMENT=development
      - LOG_LEVEL=INFO
EOF
            echo "✅ Created docker-compose.override.yml for macOS"
            ;;
            
        linux)
            # Get Docker bridge IP
            DOCKER_HOST_IP=$(ip -4 addr show docker0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || echo "172.17.0.1")
            
            cat > docker-compose.override.yml << EOF
# Auto-generated for Linux
services:
  app:
    environment:
      - CLIP_SERVICE_URL=http://${DOCKER_HOST_IP}:8002
      - LLAVA_SERVICE_URL=http://${DOCKER_HOST_IP}:8003
      - LM_STUDIO_URL=http://${DOCKER_HOST_IP}:1234
      - DATABASE_URL=postgresql://secondbrain:changeme@postgres:5432/secondbrain
      - ENVIRONMENT=development
      - LOG_LEVEL=INFO
    extra_hosts:
      - "host.docker.internal:host-gateway"
EOF
            echo "✅ Created docker-compose.override.yml for Linux (Docker host: $DOCKER_HOST_IP)"
            ;;
            
        *)
            echo "⚠️ Unknown platform. Please configure manually."
            exit 1
            ;;
    esac
}

# Check if override file exists
if [ -f "docker-compose.override.yml" ]; then
    echo "⚠️ docker-compose.override.yml already exists!"
    read -p "Overwrite? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing file."
        exit 0
    fi
fi

# Create the override file
create_override_file

echo ""
echo "========================================="
echo "Configuration complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Start Docker services: docker-compose up -d"
echo "2. Start GPU services:"
echo "   - CLIP: cd services/gpu/clip && python clip_api.py"
echo "   - LLaVA: cd services/gpu/llava && python llava_api.py"
echo "3. Access the app at: http://localhost:8000"
echo ""