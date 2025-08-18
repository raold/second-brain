# COMPLETE PHOTO PIPELINE STARTUP GUIDE
## ETCHED IN STONE - DO NOT DEVIATE

# 🚀 AUTOMATIC STARTUP

Run this ONE command:
```
START_PHOTO_PIPELINE.bat
```

This will:
1. Check Google Drive is mounted
2. Start Docker if needed
3. Verify Second Brain v5.0.0
4. Check LLaVA is running  
5. Start CLIP service if needed
6. Open the dashboard

# 🔧 MANUAL STARTUP (if automatic fails)

## Step 1: Google Drive
```
# Check if mounted
dir G:\

# If not, start Google Drive Desktop app
```

## Step 2: Docker
```
# Start Docker Desktop (if not running)
"C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Start containers
docker-compose up -d

# Verify
docker ps
```

## Step 3: LLaVA (LM Studio)
```
# Start LM Studio
# Load model: llava-v1.6-mistral-7b
# Ensure server running on port 1234
```

## Step 4: CLIP Service (REQUIRED!)
```
cd services\gpu\clip
python clip_api.py

# Should see:
# INFO:     Uvicorn running on http://0.0.0.0:8002
```

## Step 5: Verify Everything
```
curl http://localhost:8000/           # → {"version":"5.0.0"...}
curl http://127.0.0.1:1234/          # → LLaVA response
curl http://localhost:8002/          # → CLIP service info
dir G:\My Drive\Takeout\*.zip        # → Your photo archives
```

## Step 6: Open Dashboard
```
http://localhost:8000/api/photo-pipeline/
```

# 🎯 RUNNING THE PROCESSOR

## Option A: Through Dashboard (if Docker mount works)
1. Click START button
2. Watch progress in real-time

## Option B: Direct Execution (RECOMMENDED)
```
python app/services/photo_processor.py

# Select:
# 1 - Test with first zip
# 2 - Process all zips
```

# ⚠️ COMMON ISSUES & FIXES

## "CLIP service not available"
```
cd services\gpu\clip
python clip_api.py
```

## "Cannot find G:/My Drive/Takeout"
```
# Start Google Drive Desktop
# Wait for sync to complete
```

## "Docker not running"
```
# Start Docker Desktop
# Wait for whale icon in system tray
```

## "LLaVA not responding"
```
# Open LM Studio
# Server → Start Server
# Port should be 1234
```

## Dashboard shows "0 files"
```
# Docker can't see G: drive
# Use Option B: Direct Execution instead
```

# 🔴 CRITICAL SERVICES

ALL of these MUST be running:

| Service | Port | Test Command | Required? |
|---------|------|--------------|-----------|
| PostgreSQL | 5432 | `docker ps \| findstr postgres` | YES |
| Second Brain | 8000 | `curl http://localhost:8000/` | YES |
| LLaVA | 1234 | `curl http://127.0.0.1:1234/` | YES |
| CLIP | 8002 | `curl http://localhost:8002/` | YES |
| Google Drive | - | `dir G:\` | YES |

# 📊 EXPECTED OUTPUT

When everything is working:
```
📂 Found 32 zip files to process
🔄 Processing takeout-20250816T143016Z-1-001.zip...
  📸 Processing: IMG_0098.JPG
  ✅ Stored in database with embedding
  🧠 LLaVA: "A person standing in front of colorful mural..."
✅ Completed: 156 images processed
```

# 🛑 DO NOT CHANGE

1. Port 8000 → Second Brain API
2. Port 8002 → CLIP embeddings  
3. Port 1234 → LLaVA vision
4. Port 5432 → PostgreSQL
5. Path: G:/My Drive/Takeout/

# 💾 THIS IS THE WAY

This configuration processed 75+ photos successfully.
Do not deviate. Do not "improve". Just follow.