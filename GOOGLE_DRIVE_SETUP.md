# Google Drive Integration Setup Guide

## Current Status
The Google Drive integration code is **complete** but needs OAuth credentials to function.

## Setup Steps

### 1. Get Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Navigate to "APIs & Services" > "Credentials"
4. Click "Create Credentials" > "OAuth client ID"
5. Choose "Web application"
6. Add authorized redirect URI: `http://localhost:8001/api/v1/gdrive/callback`
7. Copy the Client ID and Client Secret

### 2. Configure Environment Variables

Add to your `.env` file:
```env
# Google Drive OAuth Settings
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8001/api/v1/gdrive/callback
```

### 3. Start the Application

```bash
# Start with Google Drive support
cd "C:\Users\dro\second-brain"
python -m uvicorn app.main:app --port 8001 --reload
```

### 4. Connect Google Drive

1. Open: http://localhost:8001/static/gdrive-ui.html
2. Click "Connect Google Drive"
3. Authorize the application
4. You'll be redirected back with access

### 5. Test Integration

```bash
# Test the integration
python scripts/test_gdrive_production.py
```

## Features Available

Once connected, you can:
- List all Google Drive files
- Sync documents to local memory system
- Process images with CLIP/LLaVA (v5.0.0)
- Generate embeddings for semantic search
- OCR text from images and PDFs

## Integration with v5.0.0 Multimodal Features

The new GPU-accelerated services can process Google Drive content:

### Text Documents
- Generate embeddings with CLIP (768-dim) or LLaVA (4096-dim)
- Store in PostgreSQL with full-text search

### Images
- Extract visual features with CLIP
- Deep analysis with LLaVA
- OCR text extraction
- Generate searchable descriptions

### PDFs
- Extract text content
- Process embedded images
- Generate page-by-page embeddings

## API Endpoints

- `GET /api/v1/gdrive/status` - Connection status
- `POST /api/v1/gdrive/connect` - Start OAuth
- `GET /api/v1/gdrive/files` - List files
- `POST /api/v1/gdrive/sync/file/{file_id}` - Sync single file
- `POST /api/v1/gdrive/sync/batch` - Sync multiple files

## Troubleshooting

### "Google OAuth not configured"
- Ensure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set in .env
- Restart the application after adding credentials

### "Connection refused" 
- Check that Redis is running: `redis-cli ping`
- Ensure PostgreSQL is accessible

### "Invalid redirect URI"
- Verify the redirect URI in Google Cloud Console matches exactly:
  `http://localhost:8001/api/v1/gdrive/callback`

## Next Steps

1. Set up OAuth credentials (5 minutes)
2. Test file listing and sync
3. Integrate with GPU embedding services
4. Deploy to production with HTTPS redirect URI