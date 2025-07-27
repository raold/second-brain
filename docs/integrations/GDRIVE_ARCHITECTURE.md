# Google Drive Streaming Architecture

## Executive Summary
Enterprise-grade streaming architecture for Google Drive integration, designed to process 15TB+ of user data without local storage. Based on Google AI's native recommendations and Second Brain's Clean Architecture principles.

---

## 🏗️ Core Architecture Principles

### Streaming-First Design
- **No Local Storage**: Files are streamed directly from Google Drive API
- **Chunked Processing**: Large files processed in 2MB chunks
- **Memory Bounded**: Constant memory usage regardless of file size
- **Real-time**: Webhook-driven change detection

### Google-Native Optimization
- **Direct API Integration**: Stream from `files.get` with `alt=media`
- **Google AI Services**: Leverage Document AI, Vertex AI, Natural Language API
- **Cloud Run Workers**: Serverless processing for scalability
- **OAuth 2.0**: Secure, enterprise-grade authentication

---

## 📊 System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User's        │    │   Second Brain   │    │   Google        │
│   Browser       │    │   Dashboard      │    │   Services      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │ 1. Click "Connect"    │                       │
         ├──────────────────────►│                       │
         │                       │ 2. OAuth Request      │
         │                       ├──────────────────────►│
         │                       │                       │
         │ 3. OAuth Redirect     │                       │
         │◄──────────────────────┼───────────────────────┤
         │                       │                       │
         │ 4. Authorization      │                       │
         ├──────────────────────►│                       │
         │                       │ 5. Token Exchange     │
         │                       ├──────────────────────►│
         │                       │                       │
         │ 6. Drive Integration  │ 7. File Streaming     │
         │      Complete         │◄──────────────────────┤
         │◄──────────────────────┤                       │
                                 │                       │
                          ┌──────▼──────┐         ┌──────▼──────┐
                          │   Redis     │         │   Cloud     │
                          │   Queue     │         │   Workers   │
                          └─────────────┘         └─────────────┘
```

---

## 🔄 Data Flow Architecture

### 1. Authentication Flow
```python
# OAuth 2.0 Authorization Code Flow
class GoogleAuthService:
    async def initiate_oauth(self, user_id: str) -> str:
        """Generate OAuth URL for user authorization"""
        
    async def handle_callback(self, code: str, user_id: str) -> Credentials:
        """Exchange authorization code for tokens"""
        
    async def refresh_access_token(self, user_id: str) -> Credentials:
        """Refresh expired access token using refresh token"""
```

### 2. Streaming Pipeline
```python
# File Streaming Service
class DriveStreamingService:
    async def stream_file(self, file_id: str, user_creds: Credentials) -> AsyncIterator[bytes]:
        """Stream file content in chunks without local storage"""
        
        request = self.drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request, chunksize=2*1024*1024)  # 2MB
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if fh.tell() > 0:
                fh.seek(0)
                yield fh.read()
                fh.seek(0)
                fh.truncate()
```

### 3. Real-time Updates
```python
# Webhook Handler
class DriveWebhookService:
    async def handle_change_notification(self, notification: dict):
        """Process Drive change webhook"""
        
        # Queue background job for file processing
        await self.queue_service.enqueue_job({
            'user_id': notification['user_id'],
            'file_id': notification['file_id'],
            'change_type': notification['change_type']
        })
```

---

## 🛠️ Service Layer Design

### Core Services Structure
```
app/services/gdrive/
├── __init__.py
├── auth_service.py          # OAuth & credential management
├── streaming_service.py     # File streaming & processing
├── webhook_service.py       # Real-time change handling
├── metadata_service.py      # Drive metadata integration
├── ai_service.py           # Google AI services integration
├── queue_service.py        # Background job management
└── cache_service.py        # Redis caching layer
```

### Service Dependencies
```python
# Dependency Injection Pattern
from app.services.service_factory import (
    get_gdrive_auth_service,
    get_gdrive_streaming_service,
    get_gdrive_webhook_service
)

# Usage in routes
@router.post("/gdrive/connect")
async def connect_drive(user_id: str):
    auth_service = get_gdrive_auth_service()
    return await auth_service.initiate_oauth(user_id)
```

---

## 🔐 Security Architecture

### Token Management
```python
class SecureTokenStorage:
    """Encrypted storage for Google credentials"""
    
    def encrypt_refresh_token(self, token: str) -> str:
        """Encrypt refresh token using Fernet"""
        key = self._get_encryption_key()
        fernet = Fernet(key)
        return fernet.encrypt(token.encode()).decode()
    
    def decrypt_refresh_token(self, encrypted_token: str) -> str:
        """Decrypt refresh token"""
        key = self._get_encryption_key()
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_token.encode()).decode()
```

### Permission Scopes
- **Drive Readonly**: `https://www.googleapis.com/auth/drive.readonly`
- **User Info**: `openid email profile`
- **No Write Access**: Zero risk of data modification

### Audit Logging
```python
class DriveAuditLogger:
    """Log all Drive API interactions for security"""
    
    async def log_file_access(self, user_id: str, file_id: str, action: str):
        """Log file access for audit trail"""
        
    async def log_auth_event(self, user_id: str, event: str):
        """Log authentication events"""
```

---

## 📡 API Integration Points

### Google Drive API
```python
# Primary API interactions
class DriveAPIClient:
    def __init__(self, credentials: Credentials):
        self.service = build('drive', 'v3', credentials=credentials)
    
    async def get_file_metadata(self, file_id: str) -> dict:
        """Get file metadata without content"""
        return self.service.files().get(fileId=file_id).execute()
    
    async def stream_file_content(self, file_id: str) -> AsyncIterator[bytes]:
        """Stream file binary content"""
        # Implementation using MediaIoBaseDownload
        
    async def export_workspace_file(self, file_id: str, mime_type: str) -> AsyncIterator[bytes]:
        """Export Google Workspace files (Docs, Sheets, etc.)"""
        # Use files().export() for Google native files
```

### Google AI Services
```python
# Document AI Integration
class DocumentAIClient:
    async def process_document(self, file_stream: AsyncIterator[bytes]) -> dict:
        """Extract text and structure from documents"""
        
# Vertex AI Integration  
class VertexAIClient:
    async def generate_embeddings(self, text: str) -> List[float]:
        """Generate semantic embeddings"""
        
    async def extract_entities(self, text: str) -> List[dict]:
        """Extract named entities and relationships"""
```

---

## 🔄 Background Processing

### Job Queue Architecture
```python
# Redis-based job queue
class DriveJobQueue:
    async def enqueue_file_processing(self, job_data: dict) -> str:
        """Add file processing job to queue"""
        
    async def process_jobs(self):
        """Worker process for handling queued jobs"""
        while True:
            job = await self.dequeue_job()
            if job:
                await self.process_file_job(job)
```

### Worker Deployment
```yaml
# Cloud Run worker configuration
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: gdrive-worker
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "0"
        autoscaling.knative.dev/maxScale: "100"
    spec:
      containers:
      - image: gcr.io/project/gdrive-worker
        env:
        - name: REDIS_URL
          value: "redis://redis:6379"
        - name: POSTGRES_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
```

---

## 📊 Data Models

### Database Schema
```sql
-- Google Drive integration tables
CREATE TABLE user_google_credentials (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    encrypted_refresh_token TEXT NOT NULL,
    access_token_hash VARCHAR(255), -- For cache validation
    drive_permissions JSONB,
    quota_info JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE gdrive_files (
    file_id VARCHAR(255) PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    mime_type VARCHAR(255),
    size_bytes BIGINT,
    md5_checksum VARCHAR(255),
    modified_time TIMESTAMP,
    processed_at TIMESTAMP,
    memory_id UUID REFERENCES memories(id),
    parent_folders TEXT[], -- Array of folder IDs
    metadata JSONB,
    processing_status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Webhook subscriptions
CREATE TABLE gdrive_webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    resource_id VARCHAR(255) NOT NULL,
    resource_uri TEXT NOT NULL,
    expiration TIMESTAMP NOT NULL,
    token VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Processing jobs tracking
CREATE TABLE gdrive_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    file_id VARCHAR(255) NOT NULL,
    job_type VARCHAR(50) NOT NULL, -- 'initial_sync', 'update', 'delete'
    status VARCHAR(50) DEFAULT 'queued', -- 'queued', 'processing', 'completed', 'failed'
    priority INTEGER DEFAULT 5,
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_gdrive_files_user_id ON gdrive_files(user_id);
CREATE INDEX idx_gdrive_files_modified_time ON gdrive_files(modified_time);
CREATE INDEX idx_gdrive_files_processing_status ON gdrive_files(processing_status);
CREATE INDEX idx_gdrive_jobs_status ON gdrive_jobs(status);
CREATE INDEX idx_gdrive_jobs_user_file ON gdrive_jobs(user_id, file_id);
```

### Pydantic Models
```python
# API models
class DriveConnectionRequest(BaseModel):
    user_id: str
    selected_folders: Optional[List[str]] = None

class DriveFileMetadata(BaseModel):
    file_id: str
    name: str
    mime_type: str
    size_bytes: Optional[int]
    modified_time: datetime
    md5_checksum: Optional[str]
    parent_folders: List[str]
    processing_status: str

class DriveJobStatus(BaseModel):
    job_id: str
    file_id: str
    status: str
    progress_percent: Optional[int]
    error_message: Optional[str]
    estimated_completion: Optional[datetime]
```

---

## 🚀 Performance Optimizations

### Caching Strategy
```python
class DriveCacheService:
    """Redis-based caching for Drive operations"""
    
    async def cache_file_metadata(self, file_id: str, metadata: dict, ttl: int = 300):
        """Cache file metadata for 5 minutes"""
        
    async def cache_access_token(self, user_id: str, token: str, expires_in: int):
        """Cache access token until expiry"""
        
    async def get_cached_file_hash(self, file_id: str) -> Optional[str]:
        """Get cached MD5 hash to detect changes"""
```

### Rate Limiting
```python
class DriveRateLimiter:
    """Implement exponential backoff for API calls"""
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(HttpError)
    )
    async def make_api_call(self, api_call: Callable):
        """Execute API call with retry logic"""
```

### Batch Operations
```python
class DriveBatchService:
    """Batch multiple API requests for efficiency"""
    
    async def batch_get_metadata(self, file_ids: List[str]) -> List[dict]:
        """Batch metadata requests for multiple files"""
        
        batch = BatchHttpRequest()
        for file_id in file_ids:
            batch.add(
                self.drive_service.files().get(fileId=file_id),
                callback=self._metadata_callback
            )
        
        batch.execute()
        return self.batch_results
```

---

## 🔍 Monitoring & Observability

### Key Metrics
```python
# Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge

# API metrics
drive_api_calls = Counter('drive_api_calls_total', 'Total Drive API calls', ['endpoint', 'status'])
drive_api_latency = Histogram('drive_api_duration_seconds', 'Drive API call duration')

# Processing metrics
files_processed = Counter('gdrive_files_processed_total', 'Files processed', ['file_type', 'status'])
processing_duration = Histogram('gdrive_processing_duration_seconds', 'File processing duration')

# Queue metrics
queue_depth = Gauge('gdrive_queue_depth', 'Number of jobs in queue')
active_workers = Gauge('gdrive_active_workers', 'Number of active worker instances')
```

### Health Checks
```python
class DriveHealthChecker:
    """Monitor system health and integration status"""
    
    async def check_api_connectivity(self) -> bool:
        """Verify Google Drive API is accessible"""
        
    async def check_worker_health(self) -> dict:
        """Check background worker status"""
        
    async def check_webhook_status(self) -> dict:
        """Verify webhook subscriptions are active"""
```

---

## 🧪 Testing Strategy

### Integration Tests
```python
class TestDriveIntegration:
    """Test Drive API integration with mock responses"""
    
    @pytest.mark.integration
    async def test_file_streaming(self):
        """Test file streaming without storage"""
        
    @pytest.mark.integration  
    async def test_webhook_processing(self):
        """Test webhook change notifications"""
```

### Load Testing
```python
class DriveLoa 
dTest:
    """Simulate high-volume Drive processing"""
    
    async def test_concurrent_file_processing(self):
        """Test processing 1000+ files concurrently"""
        
    async def test_large_file_streaming(self):
        """Test streaming GB-sized files"""
```

This architecture ensures scalable, secure, and efficient Google Drive integration while maintaining Second Brain's enterprise standards and leveraging Google's native AI capabilities.