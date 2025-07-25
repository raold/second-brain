# Second Brain API Specification v2.8.3

## Overview

Second Brain v2.8.3 introduces comprehensive file ingestion capabilities, including support for multiple document formats, image OCR, and Google Drive integration.

### New Features in v2.8.3

1. **Universal File Ingestion**
   - Support for PDF, DOCX, TXT, HTML, Markdown files
   - Image processing with OCR (JPG, PNG, GIF, BMP, TIFF)
   - Spreadsheet parsing (XLSX, XLS, CSV)
   - Unified ingestion engine with NLP pipeline integration

2. **Google Drive Integration**
   - OAuth 2.0 authentication
   - File browsing and search
   - Batch file ingestion
   - Folder monitoring for automatic sync

3. **Enhanced Processing Pipeline**
   - Automatic file type detection
   - Smart content chunking
   - Metadata preservation
   - Progress tracking for large files

## API Endpoints

### File Ingestion Endpoints

#### Upload Single File
```http
POST /api/v1/ingest/upload
Content-Type: multipart/form-data

Parameters:
- file: Binary file data (required)
- tags: Comma-separated tags (optional)
- metadata: JSON metadata (optional)

Response:
{
  "success": true,
  "job_id": "user123_1234567890.123",
  "message": "File 'document.pdf' queued for processing"
}
```

#### Upload Multiple Files
```http
POST /api/v1/ingest/upload/batch
Content-Type: multipart/form-data

Parameters:
- files: Multiple binary files (required)
- request: JSON object with tags and metadata

Response:
{
  "success": true,
  "job_id": "batch_user123_1234567890.123",
  "message": "Batch of 5 files queued for processing"
}
```

#### Check Ingestion Status
```http
GET /api/v1/ingest/status/{job_id}

Response:
{
  "job_id": "user123_1234567890.123",
  "status": "completed",
  "filename": "document.pdf",
  "file_type": "application/pdf",
  "created_at": "2024-01-24T10:00:00Z",
  "completed_at": "2024-01-24T10:00:30Z",
  "result": {
    "success": true,
    "memories_created": 5,
    "chunks_processed": 5,
    "processing_time": 30.5,
    "file_hash": "abc123..."
  }
}
```

#### List Ingestion Jobs
```http
GET /api/v1/ingest/jobs

Response:
[
  {
    "job_id": "user123_1234567890.123",
    "status": "completed",
    "filename": "document.pdf",
    "file_type": "application/pdf",
    "created_at": "2024-01-24T10:00:00Z",
    "completed_at": "2024-01-24T10:00:30Z"
  }
]
```

#### Get Supported File Types
```http
GET /api/v1/ingest/supported-types

Response:
{
  "supported_types": [
    {
      "category": "Documents",
      "types": [
        {"extension": ".pdf", "mime_type": "application/pdf"},
        {"extension": ".docx", "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
        {"extension": ".txt", "mime_type": "text/plain"},
        {"extension": ".md", "mime_type": "text/markdown"}
      ]
    },
    {
      "category": "Images",
      "types": [
        {"extension": ".jpg", "mime_type": "image/jpeg"},
        {"extension": ".png", "mime_type": "image/png"}
      ]
    }
  ],
  "max_file_size_mb": 100,
  "notes": [
    "Images are processed using OCR to extract text",
    "Large files may take longer to process"
  ]
}
```

### Google Drive Integration Endpoints

#### Get OAuth URL
```http
GET /api/v1/google-drive/auth/url

Response:
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?...",
  "instructions": [
    "1. Click the auth_url to authorize access to Google Drive",
    "2. Copy the authorization code from Google",
    "3. Call POST /api/v1/google-drive/auth/callback with the code"
  ]
}
```

#### Complete OAuth Authentication
```http
POST /api/v1/google-drive/auth/callback

Request:
{
  "auth_code": "4/0AX4XfWi..."
}

Response:
{
  "success": true,
  "message": "Successfully authenticated with Google Drive"
}
```

#### Check Authentication Status
```http
GET /api/v1/google-drive/auth/status

Response:
{
  "authenticated": true,
  "user_id": "user123"
}
```

#### List Google Drive Files
```http
GET /api/v1/google-drive/files?folder_id=xyz&page_size=50

Response:
{
  "files": [
    {
      "id": "1234567890",
      "name": "Research Paper.pdf",
      "mime_type": "application/pdf",
      "size": 1048576,
      "created_time": "2024-01-20T10:00:00Z",
      "modified_time": "2024-01-23T15:30:00Z",
      "web_view_link": "https://drive.google.com/file/d/1234567890/view",
      "is_folder": false,
      "is_supported": true
    }
  ],
  "next_page_token": "token123",
  "total": 25
}
```

#### Search Google Drive
```http
GET /api/v1/google-drive/search?query=machine%20learning&page_size=20

Response:
[
  {
    "id": "1234567890",
    "name": "ML Research.pdf",
    "mime_type": "application/pdf",
    "size": 2048576,
    "created_time": "2024-01-15T10:00:00Z",
    "modified_time": "2024-01-20T15:30:00Z",
    "web_view_link": "https://drive.google.com/file/d/1234567890/view",
    "is_folder": false,
    "is_supported": true
  }
]
```

#### Ingest Files from Google Drive
```http
POST /api/v1/google-drive/ingest

Request:
{
  "file_ids": ["file_id_1", "file_id_2"],
  "tags": ["research", "machine-learning"],
  "metadata": {
    "project": "AI Research",
    "importance": "high"
  }
}

Response:
{
  "success": true,
  "message": "Queued 2 files for ingestion",
  "file_count": 2
}
```

#### Monitor Google Drive Folder
```http
POST /api/v1/google-drive/monitor/folder

Request:
{
  "folder_id": "folder_123",
  "check_interval": 300,
  "auto_ingest": true,
  "tags": ["auto-sync", "research"]
}

Response:
{
  "success": true,
  "message": "Started monitoring folder folder_123",
  "check_interval": 300,
  "auto_ingest": true
}
```

## File Processing Details

### Supported File Types

#### Documents
- **PDF**: Text extraction with table and image detection
- **DOCX/DOC**: Full document parsing including tables and metadata
- **TXT**: Plain text files with encoding detection
- **Markdown**: Preserves formatting and extracts frontmatter
- **HTML**: Converts to clean text, extracts links and metadata

#### Images
- **JPEG/JPG**: OCR text extraction
- **PNG**: OCR with transparency support
- **GIF/BMP/TIFF**: Basic OCR support

#### Spreadsheets
- **XLSX/XLS**: Multi-sheet support with table preservation
- **CSV**: Intelligent parsing with delimiter detection

### Processing Pipeline

1. **File Upload**: Files are uploaded via multipart form data
2. **Validation**: File type, size, and security checks
3. **Content Extraction**: Format-specific parsers extract text and metadata
4. **NLP Processing**: Extracted content goes through:
   - Entity extraction
   - Relationship detection
   - Topic classification
   - Intent recognition
   - Embedding generation
5. **Memory Creation**: Content is chunked and stored as memories
6. **Indexing**: Memories are indexed for semantic search

### Metadata Extraction

Each file type extracts relevant metadata:

```json
{
  "file_metadata": {
    "filename": "document.pdf",
    "file_type": "application/pdf",
    "size": 1048576,
    "hash": "sha256:abc123...",
    "created_at": "2024-01-24T10:00:00Z"
  },
  "parsed_metadata": {
    "format": "pdf",
    "pages": 10,
    "has_images": true,
    "has_tables": true,
    "author": "John Doe",
    "title": "Research Paper"
  }
}
```

## Google Drive Integration Details

### Authentication Flow

1. **Get Auth URL**: Request OAuth authorization URL
2. **User Authorization**: User grants permissions in browser
3. **Exchange Code**: Submit authorization code to complete setup
4. **Token Storage**: Credentials stored securely per user

### Permissions Required

- `https://www.googleapis.com/auth/drive.readonly`: Read-only access to files

### Google Docs Export

Google Docs files are automatically exported to compatible formats:
- Google Docs → DOCX
- Google Sheets → XLSX
- Google Slides → PDF

### Folder Monitoring

The folder monitoring feature:
- Checks for new/modified files at specified intervals
- Optionally auto-ingests detected changes
- Preserves Google Drive metadata
- Supports recursive folder scanning

## Error Handling

### Common Error Responses

```json
{
  "error": {
    "code": 400,
    "message": "File too large: 105MB (max: 100MB)",
    "type": "ValidationError",
    "timestamp": "2024-01-24T10:00:00Z",
    "path": "/api/v1/ingest/upload",
    "method": "POST"
  }
}
```

### Error Codes

- **400**: Bad Request (invalid file type, size limit exceeded)
- **401**: Unauthorized (Google Drive not authenticated)
- **404**: Not Found (job or file not found)
- **413**: Payload Too Large (file exceeds size limit)
- **422**: Unprocessable Entity (unsupported file format)
- **429**: Rate Limit Exceeded
- **500**: Internal Server Error

## Best Practices

### File Upload
1. Check supported types before uploading
2. Use batch upload for multiple files
3. Monitor job status for large files
4. Add relevant tags for better organization

### Google Drive Integration
1. Authenticate once per user session
2. Use folder monitoring for automated workflows
3. Batch process files to reduce API calls
4. Handle token refresh for long-running operations

### Performance Optimization
1. Files are processed asynchronously
2. Large files are automatically chunked
3. Embeddings are cached for efficiency
4. Use pagination for listing operations

## Migration Notes

### Upgrading to v2.8.3

1. **New Dependencies**:
   ```bash
   pip install PyPDF2 pdfplumber python-docx beautifulsoup4 html2text
   pip install pytesseract pillow pandas openpyxl
   pip install google-auth google-auth-oauthlib google-api-python-client
   ```

2. **Environment Variables**:
   ```bash
   GOOGLE_CLIENT_ID=your_client_id
   GOOGLE_CLIENT_SECRET=your_client_secret
   ```

3. **Database Changes**: No schema changes required

### Backward Compatibility

All existing endpoints remain functional. The new ingestion features are additive and don't affect existing functionality.

## Example Usage

### Python Client Example

```python
import requests
import os

# Upload a file
with open('research.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/v1/ingest/upload',
        files={'file': f},
        data={
            'tags': 'research,ai,machine-learning',
            'metadata': '{"project": "AI Research", "year": 2024}'
        },
        headers={'Authorization': 'Bearer your_api_key'}
    )
    
job_id = response.json()['job_id']

# Check status
status = requests.get(
    f'http://localhost:8000/api/v1/ingest/status/{job_id}',
    headers={'Authorization': 'Bearer your_api_key'}
).json()

print(f"Status: {status['status']}")
print(f"Memories created: {status['result']['memories_created']}")
```

### Google Drive Example

```python
# Authenticate with Google Drive
auth_url = requests.get(
    'http://localhost:8000/api/v1/google-drive/auth/url',
    headers={'Authorization': 'Bearer your_api_key'}
).json()['auth_url']

print(f"Visit: {auth_url}")
auth_code = input("Enter authorization code: ")

# Complete authentication
requests.post(
    'http://localhost:8000/api/v1/google-drive/auth/callback',
    json={'auth_code': auth_code},
    headers={'Authorization': 'Bearer your_api_key'}
)

# List files
files = requests.get(
    'http://localhost:8000/api/v1/google-drive/files',
    headers={'Authorization': 'Bearer your_api_key'}
).json()['files']

# Ingest selected files
file_ids = [f['id'] for f in files[:5]]  # First 5 files
requests.post(
    'http://localhost:8000/api/v1/google-drive/ingest',
    json={
        'file_ids': file_ids,
        'tags': ['google-drive', 'import']
    },
    headers={'Authorization': 'Bearer your_api_key'}
)
```

## Roadmap

### Future Enhancements

1. **Additional Cloud Storage**:
   - Dropbox integration
   - OneDrive support
   - Box.com connectivity

2. **Advanced Processing**:
   - Video transcription
   - Audio file support
   - Code file analysis

3. **Enterprise Features**:
   - Bulk import tools
   - Scheduled ingestion
   - Webhook notifications

4. **AI Enhancements**:
   - Smart categorization
   - Duplicate detection
   - Content summarization

## Support

For issues or questions:
- GitHub Issues: [second-brain/issues](https://github.com/yourusername/second-brain/issues)
- Documentation: [Full API Docs](/docs)
- Email: support@secondbrain.ai