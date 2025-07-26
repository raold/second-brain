# Multi-Modal Ingestion Guide

Second Brain now supports ingestion of various file types including documents, images, audio, and video files with automatic content extraction and transcription.

## Supported File Types

### Documents
- **PDF** (.pdf) - Text extraction, table detection, image detection
- **Word** (.docx, .doc) - Full formatting support
- **HTML** (.html, .htm) - Clean text extraction
- **Markdown** (.md) - Native support
- **Plain Text** (.txt) - Direct ingestion

### Spreadsheets
- **Excel** (.xlsx, .xls) - All sheets processed
- **CSV** (.csv) - Automatic delimiter detection
- **OpenDocument** (.ods) - Basic support

### Images
- **Common Formats** (.jpg, .jpeg, .png, .gif, .bmp, .tiff)
- **OCR Support** - Automatic text extraction from images
- **Multi-language OCR** - English, French, German, Spanish

### Audio
- **Formats** (.mp3, .wav, .m4a, .flac, .ogg)
- **Transcription** - Automatic speech-to-text
- **Timestamps** - Segment-level timing information

### Video
- **Formats** (.mp4, .avi, .mov, .mkv, .webm)
- **Audio Extraction** - Transcribes video audio track
- **Metadata** - Duration, resolution, FPS

### Subtitles
- **Formats** (.srt, .vtt, .sub)
- **Timeline Preservation** - Maintains timing information

## API Usage

### Single File Upload

```bash
curl -X POST "http://localhost:8000/api/v1/ingest/upload" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "file=@document.pdf" \
  -F "tags=work,important" \
  -F 'metadata={"project":"SecondBrain","priority":"high"}'
```

### Batch Upload

```bash
curl -X POST "http://localhost:8000/api/v1/ingest/batch" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "files=@file1.pdf" \
  -F "files=@file2.mp3" \
  -F "files=@image.jpg"
```

## Docker Configuration

### Standard Setup
Uses the regular Dockerfile with basic document support:
```bash
docker-compose up -d
```

### Multi-Modal Setup
For full audio/video support, use the multi-modal Dockerfile:
```bash
docker build -f Dockerfile.multimodal -t secondbrain:multimodal .
docker run -p 8000:8000 secondbrain:multimodal
```

## Installation

### Basic Document Support
```bash
pip install -r config/requirements.txt
```

### Full Multi-Modal Support
```bash
pip install -r config/requirements-multimodal.txt
```

### System Dependencies

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-eng ffmpeg
```

#### macOS
```bash
brew install tesseract ffmpeg
```

#### Windows
- Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
- Install FFmpeg: https://ffmpeg.org/download.html

## Configuration

### Environment Variables
```bash
# Temporary file storage (cross-platform)
TEMP_DIR=/app/temp

# Maximum upload size (bytes)
MAX_UPLOAD_SIZE=104857600  # 100MB

# Whisper model for audio transcription (tiny, base, small, medium, large)
WHISPER_MODEL=tiny

# OCR languages (comma-separated)
TESSERACT_LANGS=eng,fra,deu,spa
```

### Processing Options

#### OCR Configuration
```python
{
    "ocr": {
        "enabled": true,
        "languages": ["eng", "fra"],
        "enhance_image": true,
        "dpi": 300
    }
}
```

#### Audio Transcription
```python
{
    "audio": {
        "transcribe": true,
        "include_timestamps": true,
        "language": "auto",
        "model": "tiny"
    }
}
```

## Performance Considerations

### File Size Limits
- Default: 100MB per file
- Configurable via `MAX_UPLOAD_SIZE`

### Processing Time
- PDFs: ~1-5 seconds per page
- Images (OCR): ~2-10 seconds per image
- Audio: ~10-30% of audio duration
- Video: ~20-50% of video duration

### Resource Usage
- **Basic**: 2GB RAM, 2 CPU cores
- **Multi-Modal**: 4GB RAM, 4 CPU cores
- **With Whisper**: +2GB RAM for model

## Troubleshooting

### Common Issues

1. **OCR Not Working**
   - Ensure Tesseract is installed
   - Check `TESSDATA_PREFIX` environment variable
   - Verify language packs are installed

2. **Audio Transcription Failing**
   - Install ffmpeg system package
   - Check audio codec support
   - Verify Whisper model is downloaded

3. **Out of Memory**
   - Reduce batch size
   - Use smaller Whisper model
   - Process files sequentially

### Debug Mode
Enable detailed logging:
```python
LOG_LEVEL=debug
INGESTION_DEBUG=true
```

## Best Practices

1. **File Preparation**
   - Optimize PDFs before upload
   - Use standard video codecs
   - Compress large images

2. **Batch Processing**
   - Group similar file types
   - Limit batch size to 10-20 files
   - Monitor memory usage

3. **Error Handling**
   - Implement retry logic
   - Handle partial failures
   - Log failed files for reprocessing

## Advanced Features

### Custom Parsers
Create custom parsers by extending `FileParser`:

```python
from app.ingestion.engine import FileParser

class CustomParser(FileParser):
    SUPPORTED_TYPES = {'application/custom'}
    
    async def parse(self, file_path: Path) -> dict:
        # Custom parsing logic
        return {
            'content': extracted_text,
            'metadata': {...}
        }
```

### Pipeline Customization
Modify the extraction pipeline:

```python
pipeline = CoreExtractionPipeline()
pipeline.add_processor(CustomProcessor())
pipeline.add_validator(CustomValidator())
```

## API Reference

See [API Documentation](./API.md#ingestion) for detailed endpoint information.