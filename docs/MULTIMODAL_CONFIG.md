# Multimodal Configuration Guide 🎨

> **Version**: v2.6.0-dev  
> **Last Updated**: July 21, 2025

## 📋 Overview

This guide covers all configuration options for the multimodal memory system in Second Brain v2.6.0.

## 🔧 Environment Variables

Add these to your `.env` file:

### Core Multimodal Settings
```bash
# Maximum upload size in bytes (default: 524288000 = 500MB)
MAX_UPLOAD_SIZE=524288000

# Storage path for uploaded files
MULTIMODAL_STORAGE_PATH=/data/multimodal

# Enable/disable specific processors
ENABLE_OCR=true
ENABLE_WHISPER=true
ENABLE_CLIP=true
ENABLE_SCENE_DETECTION=true

# Processing timeout in seconds
PROCESSING_TIMEOUT=300

# Maximum concurrent processing tasks
MAX_CONCURRENT_TASKS=5
```

### Content Type Limits
```bash
# Individual content type limits (in bytes)
MAX_IMAGE_SIZE=52428800      # 50MB
MAX_AUDIO_SIZE=209715200     # 200MB
MAX_VIDEO_SIZE=524288000     # 500MB
MAX_DOCUMENT_SIZE=104857600  # 100MB

# Allowed file extensions (comma-separated)
ALLOWED_IMAGE_TYPES=jpg,jpeg,png,gif,bmp,webp,svg
ALLOWED_AUDIO_TYPES=mp3,wav,ogg,m4a,flac,aac
ALLOWED_VIDEO_TYPES=mp4,avi,mov,mkv,webm,m4v
ALLOWED_DOCUMENT_TYPES=pdf,docx,xlsx,pptx,txt,md,csv
```

### Processing Configuration
```bash
# Image Processing
IMAGE_MAX_DIMENSION=4096
IMAGE_THUMBNAIL_SIZE=256
ENABLE_EXIF_EXTRACTION=true
ENABLE_OBJECT_DETECTION=false

# Audio Processing  
WHISPER_MODEL=base  # tiny, base, small, medium, large
AUDIO_SAMPLE_RATE=16000
ENABLE_SPEAKER_DIARIZATION=false

# Video Processing
VIDEO_FRAME_SAMPLE_RATE=1  # frames per second
VIDEO_MAX_FRAMES=100
VIDEO_THUMBNAIL_COUNT=5

# Document Processing
PDF_MAX_PAGES=500
ENABLE_TABLE_EXTRACTION=true
PRESERVE_FORMATTING=true
```

### Storage Configuration
```bash
# File storage settings
USE_S3_STORAGE=false
S3_BUCKET_NAME=
S3_REGION=
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=

# Local storage
LOCAL_STORAGE_CLEANUP=true
CLEANUP_AFTER_DAYS=30
ORPHAN_FILE_CLEANUP=true
```

### Security Settings
```bash
# File validation
ENABLE_VIRUS_SCAN=true
ENABLE_CONTENT_VALIDATION=true
BLOCK_EXECUTABLE_UPLOADS=true

# Rate limiting
MULTIMODAL_RATE_LIMIT=100  # requests per minute
UPLOAD_RATE_LIMIT=10       # uploads per minute

# Access control
REQUIRE_AUTH_FOR_DOWNLOADS=true
ENABLE_PUBLIC_SHARING=false
```

## 📂 Directory Structure

Create these directories:
```bash
second-brain/
├── data/
│   └── multimodal/
│       ├── uploads/      # Temporary upload directory
│       ├── processed/    # Processed files
│       ├── thumbnails/   # Generated thumbnails
│       └── cache/        # Processing cache
```

## 🚀 Docker Configuration

### docker-compose.yml additions:
```yaml
services:
  api:
    environment:
      - MAX_UPLOAD_SIZE=524288000
      - MULTIMODAL_STORAGE_PATH=/data/multimodal
      - ENABLE_OCR=true
      - ENABLE_WHISPER=true
    volumes:
      - ./data/multimodal:/data/multimodal
    
  # Optional: Add Redis for processing queue
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

## 🔍 Processing Pipeline Configuration

### Custom Processor Settings

Create `config/processors.json`:
```json
{
  "image": {
    "enabled": true,
    "timeout": 30,
    "processors": [
      {
        "name": "ocr",
        "enabled": true,
        "config": {
          "language": "eng",
          "confidence_threshold": 0.6
        }
      },
      {
        "name": "clip",
        "enabled": true,
        "config": {
          "model": "ViT-B/32"
        }
      }
    ]
  },
  "audio": {
    "enabled": true,
    "timeout": 180,
    "processors": [
      {
        "name": "whisper",
        "enabled": true,
        "config": {
          "model": "base",
          "language": "auto",
          "temperature": 0
        }
      }
    ]
  },
  "video": {
    "enabled": true,
    "timeout": 300,
    "processors": [
      {
        "name": "frame_extraction",
        "enabled": true,
        "config": {
          "sample_rate": 1,
          "max_frames": 100
        }
      },
      {
        "name": "scene_detection",
        "enabled": true,
        "config": {
          "threshold": 30.0
        }
      }
    ]
  },
  "document": {
    "enabled": true,
    "timeout": 60,
    "processors": [
      {
        "name": "text_extraction",
        "enabled": true,
        "config": {
          "preserve_formatting": true,
          "extract_images": false
        }
      }
    ]
  }
}
```

## 🛠️ Performance Tuning

### PostgreSQL Settings
```sql
-- Add to postgresql.conf for optimal performance
shared_buffers = 512MB
work_mem = 32MB
maintenance_work_mem = 128MB
max_parallel_workers = 8
max_parallel_workers_per_gather = 4
```

### Application Tuning
```python
# config/performance.py
PERFORMANCE_CONFIG = {
    "batch_size": {
        "embeddings": 32,
        "database": 100,
        "processing": 10
    },
    "cache": {
        "ttl": 3600,  # 1 hour
        "max_size": 1000
    },
    "connection_pool": {
        "min_size": 5,
        "max_size": 20,
        "timeout": 30
    }
}
```

## 📊 Monitoring Configuration

### Metrics Collection
```bash
# Enable metrics collection
ENABLE_METRICS=true
METRICS_PORT=9090

# Metrics to collect
TRACK_PROCESSING_TIME=true
TRACK_FILE_SIZES=true
TRACK_ERROR_RATES=true
TRACK_STORAGE_USAGE=true
```

### Logging Configuration
```python
# config/logging.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            'format': '%(asctime)s %(levelname)s [%(name)s] %(message)s'
        }
    },
    'handlers': {
        'multimodal': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/multimodal.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'detailed'
        }
    },
    'loggers': {
        'multimodal': {
            'handlers': ['multimodal'],
            'level': 'INFO'
        }
    }
}
```

## 🔒 Security Configuration

### File Type Validation
```python
# config/security.py
MIME_TYPE_WHITELIST = {
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/gif': ['.gif'],
    'audio/mpeg': ['.mp3'],
    'audio/wav': ['.wav'],
    'video/mp4': ['.mp4'],
    'application/pdf': ['.pdf']
}

MAGIC_BYTES = {
    'jpeg': b'\xff\xd8\xff',
    'png': b'\x89PNG\r\n\x1a\n',
    'gif': b'GIF87a',
    'pdf': b'%PDF'
}
```

## 🚨 Troubleshooting

### Common Issues

1. **OCR Not Working**:
   ```bash
   # Install Tesseract
   sudo apt-get install tesseract-ocr
   # Or on macOS
   brew install tesseract
   ```

2. **Whisper Out of Memory**:
   ```bash
   # Use smaller model
   WHISPER_MODEL=tiny
   ```

3. **Slow Processing**:
   ```bash
   # Increase workers
   MAX_CONCURRENT_TASKS=10
   # Reduce quality settings
   VIDEO_FRAME_SAMPLE_RATE=0.5
   ```

## 📚 Best Practices

1. **Storage Management**:
   - Enable cleanup for old files
   - Use S3 for production deployments
   - Monitor disk usage regularly

2. **Performance**:
   - Use appropriate model sizes
   - Enable caching for repeated operations
   - Batch process similar files

3. **Security**:
   - Always validate file types
   - Set appropriate size limits
   - Enable virus scanning in production

4. **Monitoring**:
   - Track processing times
   - Monitor error rates
   - Set up alerts for failures