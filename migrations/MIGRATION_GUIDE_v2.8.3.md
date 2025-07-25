# Migration Guide - Second Brain v2.8.3

## Overview

Second Brain v2.8.3 introduces file ingestion capabilities without requiring any database schema changes. This guide will help you upgrade from v2.8.2 to v2.8.3.

## Prerequisites

- Second Brain v2.8.2 or later
- Python 3.8+
- PostgreSQL with pgvector extension
- (Optional) Tesseract OCR for image processing
- (Optional) Google Cloud Console account for Drive integration

## Migration Steps

### 1. Update Dependencies

Install the new required packages:

```bash
# Update to v2.8.3
git pull origin main
git checkout v2.8.3

# Install new dependencies
pip install -r requirements.txt
```

### 2. Install System Dependencies (Optional)

For full OCR support, install Tesseract:

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows
# Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
```

### 3. Configure Environment Variables

Add these optional environment variables to your `.env` file:

```bash
# File processing settings
MAX_FILE_SIZE_MB=100  # Maximum file size for uploads
TEMP_DIR=/tmp/secondbrain/ingestion  # Temporary directory for file processing

# Google Drive OAuth (optional)
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
```

### 4. Google Drive Setup (Optional)

If you want to use Google Drive integration:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Drive API
4. Create OAuth 2.0 credentials:
   - Application type: Desktop app
   - Download credentials
   - Add client ID and secret to `.env`

### 5. Create Required Directories

```bash
# Create temp directory for file processing
mkdir -p /tmp/secondbrain/ingestion

# Create credentials directory for Google Drive
mkdir -p credentials
```

### 6. Test the Installation

Verify that the new endpoints are available:

```bash
# Check supported file types
curl http://localhost:8000/api/v1/ingest/supported-types

# Check ingestion dashboard
open http://localhost:8000/ingestion
```

## New Features Available

### File Upload
- Single file: `POST /api/v1/ingest/upload`
- Batch upload: `POST /api/v1/ingest/upload/batch`
- Job monitoring: `GET /api/v1/ingest/status/{job_id}`

### Google Drive
- Authentication: `GET /api/v1/google-drive/auth/url`
- File browsing: `GET /api/v1/google-drive/files`
- File ingestion: `POST /api/v1/google-drive/ingest`

### Supported File Types
- Documents: PDF, DOCX, TXT, Markdown, HTML
- Images: JPEG, PNG (with OCR)
- Spreadsheets: XLSX, CSV

## Rollback Instructions

If you need to rollback to v2.8.2:

```bash
# Checkout previous version
git checkout v2.8.2

# Reinstall dependencies
pip install -r requirements.txt

# No database rollback needed
```

## Troubleshooting

### Import Errors
If you see import errors for file processing libraries:
```bash
pip install --upgrade PyPDF2 pdfplumber python-docx beautifulsoup4
```

### OCR Not Working
- Ensure Tesseract is installed: `tesseract --version`
- Install language packs if needed: `sudo apt-get install tesseract-ocr-[lang]`

### Google Drive Authentication Failed
- Verify CLIENT_ID and CLIENT_SECRET are set correctly
- Ensure redirect URI is set to `urn:ietf:wg:oauth:2.0:oob`
- Check that Drive API is enabled in Google Cloud Console

### Large File Upload Failures
- Increase `MAX_FILE_SIZE_MB` in environment variables
- Ensure sufficient disk space in `TEMP_DIR`
- Check server timeout settings

## Performance Considerations

- Large files are processed asynchronously
- Files are chunked for efficient memory usage
- Consider increasing server resources for heavy ingestion workloads
- OCR processing can be CPU-intensive

## Security Notes

- Google Drive credentials are stored per-user
- File uploads are validated for type and size
- Temporary files are cleaned up after processing
- Consider implementing virus scanning for production

## Next Steps

1. Test file upload with a small PDF
2. Configure Google Drive if needed
3. Access the ingestion dashboard at `/ingestion`
4. Monitor job progress through the API

For more information, see the [API Documentation](../docs/API_SPECIFICATION_v2.8.3.md).