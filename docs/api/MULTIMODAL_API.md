# Multimodal API Documentation 🎨

> **Version**: v2.6.0-dev  
> **Base URL**: `http://localhost:8000/multimodal`  
> **Authentication**: Bearer token required for all endpoints

## 📸 Overview

The Multimodal API enables storage and retrieval of various media types in Second Brain, including:
- **Images** (JPEG, PNG, GIF, BMP, WEBP)
- **Audio** (MP3, WAV, OGG, M4A, FLAC)
- **Video** (MP4, AVI, MOV, MKV, WEBM)
- **Documents** (PDF, DOCX, XLSX, PPTX, TXT, MD)

All media is processed to extract searchable content and metadata, with vector embeddings generated for semantic search.

## 🔑 Authentication

All endpoints require a Bearer token in the Authorization header:
```bash
Authorization: Bearer your-api-token
```

## 📋 Endpoints

### 1. Upload File
**POST** `/multimodal/upload`

Upload and process a media file.

#### Request
- **Method**: `POST`
- **Content-Type**: `multipart/form-data`

#### Form Data Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| file | File | Yes | The media file to upload |
| importance | float | No | Importance score (0-10), default: 5.0 |
| tags | string | No | Comma-separated tags |
| metadata | JSON | No | Additional metadata as JSON string |
| process_async | boolean | No | Process in background, default: true |

#### Example Request
```bash
curl -X POST http://localhost:8000/multimodal/upload \
  -H "Authorization: Bearer demo-token" \
  -F "file=@document.pdf" \
  -F "importance=8.5" \
  -F "tags=research,ai,memory" \
  -F 'metadata={"project": "second-brain", "category": "documentation"}'
```

#### Response
```json
{
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "content_type": "document",
  "media_format": "pdf",
  "processing_task_id": "task-123",
  "message": "File uploaded successfully and processing started"
}
```

### 2. Get Multimodal Memory
**GET** `/multimodal/memories/{memory_id}`

Retrieve a multimodal memory with all metadata.

#### Path Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| memory_id | UUID | The memory ID |

#### Example Request
```bash
curl -X GET http://localhost:8000/multimodal/memories/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer demo-token"
```

#### Response
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "Extracted text from the document...",
  "content_type": "document",
  "media_format": "pdf",
  "importance": 8.5,
  "tags": ["research", "ai", "memory"],
  "created_at": "2025-07-21T10:00:00Z",
  "updated_at": "2025-07-21T10:01:00Z",
  "metadata": {
    "project": "second-brain",
    "category": "documentation"
  },
  "media_metadata": {
    "title": "AI Memory Systems Research",
    "author": "John Doe",
    "page_count": 42,
    "creation_date": "2025-07-20",
    "file_size": 2048576
  },
  "processing_status": "completed",
  "file_url": "/multimodal/files/550e8400-e29b-41d4-a716-446655440000.pdf"
}
```

### 3. Search Multimodal Memories
**POST** `/multimodal/search`

Search across all media types with filters.

#### Request Body
```json
{
  "query": "machine learning research",
  "content_types": ["document", "image"],
  "limit": 20,
  "offset": 0,
  "importance_min": 5.0,
  "tags": ["research", "ai"],
  "date_from": "2025-01-01",
  "date_to": "2025-12-31",
  "include_metadata": true
}
```

#### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| query | string | Yes | Search query text |
| content_types | array | No | Filter by content types |
| limit | integer | No | Results per page (default: 20, max: 100) |
| offset | integer | No | Pagination offset (default: 0) |
| importance_min | float | No | Minimum importance score |
| tags | array | No | Filter by tags |
| date_from | string | No | Start date (ISO format) |
| date_to | string | No | End date (ISO format) |
| include_metadata | boolean | No | Include media metadata (default: true) |

#### Response
```json
{
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "content": "Machine learning approaches to memory systems...",
      "content_type": "document",
      "media_format": "pdf",
      "similarity_score": 0.92,
      "importance": 8.5,
      "tags": ["research", "ai", "memory"],
      "created_at": "2025-07-21T10:00:00Z",
      "media_metadata": {
        "title": "AI Memory Systems Research",
        "page_count": 42
      }
    }
  ],
  "total": 15,
  "limit": 20,
  "offset": 0
}
```

### 4. Update Multimodal Memory
**PUT** `/multimodal/memories/{memory_id}`

Update metadata for a multimodal memory.

#### Request Body
```json
{
  "importance": 9.0,
  "tags": ["research", "ai", "memory", "important"],
  "metadata": {
    "project": "second-brain",
    "category": "documentation",
    "reviewed": true
  }
}
```

#### Response
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Memory updated successfully",
  "updated_fields": ["importance", "tags", "metadata"]
}
```

### 5. Delete Multimodal Memory
**DELETE** `/multimodal/memories/{memory_id}`

Delete a multimodal memory and its associated file.

#### Response
```json
{
  "message": "Memory and associated file deleted successfully",
  "memory_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 6. Get Processing Status
**GET** `/multimodal/processing/{task_id}`

Check the status of a file processing task.

#### Response
```json
{
  "task_id": "task-123",
  "status": "completed",
  "progress": 100,
  "result": {
    "memory_id": "550e8400-e29b-41d4-a716-446655440000",
    "extracted_text_length": 5420,
    "metadata_extracted": true,
    "embeddings_generated": true
  },
  "started_at": "2025-07-21T10:00:00Z",
  "completed_at": "2025-07-21T10:01:00Z"
}
```

### 7. Reprocess Media
**POST** `/multimodal/memories/{memory_id}/reprocess`

Reprocess a media file with updated settings.

#### Request Body
```json
{
  "extract_text": true,
  "generate_embeddings": true,
  "extract_metadata": true,
  "custom_processors": ["ocr_enhanced", "scene_detection"]
}
```

### 8. Get Statistics
**GET** `/multimodal/stats`

Get statistics about multimodal content.

#### Response
```json
{
  "total_memories": 1523,
  "by_content_type": {
    "text": 850,
    "image": 342,
    "audio": 156,
    "video": 89,
    "document": 86
  },
  "total_storage_bytes": 5368709120,
  "average_processing_time_ms": 2340,
  "recent_uploads": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "content_type": "document",
      "uploaded_at": "2025-07-21T10:00:00Z"
    }
  ]
}
```

## 🎨 Content Type Details

### Images
- **Supported Formats**: JPEG, PNG, GIF, BMP, WEBP
- **Processing**: OCR text extraction, CLIP embeddings, EXIF metadata
- **Metadata Extracted**: dimensions, color profile, camera settings, location

### Audio
- **Supported Formats**: MP3, WAV, OGG, M4A, FLAC
- **Processing**: Whisper transcription, audio fingerprinting
- **Metadata Extracted**: duration, bitrate, sample rate, channels

### Video
- **Supported Formats**: MP4, AVI, MOV, MKV, WEBM
- **Processing**: Frame extraction, scene detection, audio extraction
- **Metadata Extracted**: resolution, duration, codec, framerate

### Documents
- **Supported Formats**: PDF, DOCX, XLSX, PPTX, TXT, MD
- **Processing**: Full text extraction, structure preservation
- **Metadata Extracted**: title, author, page count, creation date

## ⚡ Performance Considerations

1. **File Size Limits**: 
   - Images: 50MB
   - Audio: 200MB
   - Video: 500MB
   - Documents: 100MB

2. **Processing Times**:
   - Images: 1-5 seconds
   - Audio: 5-30 seconds (depends on length)
   - Video: 10-60 seconds (depends on length)
   - Documents: 2-10 seconds

3. **Batch Processing**:
   - Use async processing for large files
   - Check status endpoint for progress
   - Maximum 10 concurrent uploads per token

## 🔒 Security

1. **File Validation**:
   - Magic byte verification
   - Extension validation
   - Content scanning for malicious code

2. **Access Control**:
   - Files are private to the token owner
   - No public file access without authentication

3. **Storage**:
   - Files stored with UUID names
   - Original filenames preserved in metadata
   - Automatic cleanup of orphaned files

## 📚 Examples

### Upload and Search Workflow
```python
import requests
import time

# Upload a document
files = {'file': open('research.pdf', 'rb')}
data = {
    'importance': 8.5,
    'tags': 'research,ai,memory'
}
response = requests.post(
    'http://localhost:8000/multimodal/upload',
    files=files,
    data=data,
    headers={'Authorization': 'Bearer demo-token'}
)
result = response.json()
task_id = result['processing_task_id']

# Wait for processing
while True:
    status = requests.get(
        f'http://localhost:8000/multimodal/processing/{task_id}',
        headers={'Authorization': 'Bearer demo-token'}
    ).json()
    
    if status['status'] == 'completed':
        break
    time.sleep(1)

# Search for content
search_data = {
    'query': 'neural networks',
    'content_types': ['document'],
    'importance_min': 7.0
}
results = requests.post(
    'http://localhost:8000/multimodal/search',
    json=search_data,
    headers={'Authorization': 'Bearer demo-token'}
).json()

print(f"Found {results['total']} results")
```

## 🚀 Best Practices

1. **Use Async Processing**: For files over 10MB
2. **Add Metadata**: Provide context with tags and custom metadata
3. **Monitor Processing**: Check status for large files
4. **Batch Operations**: Group related uploads
5. **Error Handling**: Implement retry logic for network issues