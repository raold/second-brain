# Cross-Platform Development Guide

## 🎯 Overview
Second Brain works seamlessly on Windows, macOS, and Linux. The setup automatically detects your platform and configures networking accordingly.

## 🚀 Quick Start (All Platforms)

```bash
# 1. Clone the repo
git clone https://github.com/raold/second-brain.git
cd second-brain

# 2. Run platform setup (one-time)
./setup-platform.sh      # Unix (Mac/Linux)
./start-dev.bat          # Windows

# 3. Start everything
./start-dev.sh           # Unix (Mac/Linux)  
./start-dev.bat          # Windows
```

## 🖥️ Platform-Specific Networking

### Windows
- **Host → Container**: `localhost:PORT`
- **Container → Host**: `host.docker.internal:PORT`
- **Networking**: Works out of the box with Docker Desktop

### macOS  
- **Host → Container**: `localhost:PORT`
- **Container → Host**: `host.docker.internal:PORT`
- **Networking**: Native support for host.docker.internal

### Linux
- **Host → Container**: `localhost:PORT`
- **Container → Host**: `172.17.0.1:PORT` (Docker bridge IP)
- **Alternative**: `host.docker.internal:PORT` (newer Docker versions)
- **Note**: Script auto-detects the Docker bridge IP

## 📁 File Structure

```
second-brain/
├── docker-compose.yml                    # Base configuration (don't modify)
├── docker-compose.override.yml           # Platform-specific (auto-generated, git-ignored)
├── docker-compose.override.yml.example   # Template with all platform configs
├── setup-platform.sh                     # Auto-configures for your platform
├── start-dev.sh                          # Unix startup script
├── start-dev.bat                         # Windows startup script
└── PORTS.md                             # Complete port reference
```

## 🔧 Manual Configuration

If auto-setup doesn't work, create `docker-compose.override.yml`:

### For Windows/Mac:
```yaml
services:
  app:
    environment:
      - CLIP_SERVICE_URL=http://host.docker.internal:8002
      - LLAVA_SERVICE_URL=http://host.docker.internal:8003
      - LM_STUDIO_URL=http://host.docker.internal:1234
```

### For Linux:
```yaml
services:
  app:
    environment:
      - CLIP_SERVICE_URL=http://172.17.0.1:8002
      - LLAVA_SERVICE_URL=http://172.17.0.1:8003
      - LM_STUDIO_URL=http://172.17.0.1:1234
```

## 🐛 Troubleshooting

### Linux: Find Docker Bridge IP
```bash
# Method 1: Docker network inspect
docker network inspect bridge | grep Gateway

# Method 2: ip command
ip -4 addr show docker0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}'

# Method 3: Usually it's
172.17.0.1
```

### All Platforms: Test Connectivity
```bash
# From host to container
curl http://localhost:8000/health

# From container to host (Windows/Mac)
docker exec secondbrain-app curl http://host.docker.internal:8002

# From container to host (Linux)
docker exec secondbrain-app curl http://172.17.0.1:8002
```

## 🎮 GPU Services

### CLIP Service (All Platforms)
```bash
cd services/gpu/clip
python clip_api.py
# Runs on port 8002
```

### Prerequisites by Platform:

**Windows:**
- NVIDIA GPU with CUDA support
- Python 3.10+ with PyTorch CUDA

**Mac (Apple Silicon):**
- PyTorch with MPS (Metal Performance Shaders) support
- Will use CPU if MPS unavailable

**Linux:**
- NVIDIA GPU with CUDA support
- NVIDIA drivers and CUDA toolkit

## 📝 Notes

1. **docker-compose.override.yml** is git-ignored because it's platform-specific
2. The setup script creates this file automatically
3. Docker Compose automatically merges override.yml with docker-compose.yml
4. No need to modify the main docker-compose.yml

## 🔄 Switching Platforms

If you move between machines:
```bash
# Re-run setup to reconfigure
./setup-platform.sh

# This will detect your new platform and update accordingly
```