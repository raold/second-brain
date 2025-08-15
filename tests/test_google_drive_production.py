"""
Comprehensive production test suite for Google Drive integration
Tests file size limits, content validation, duplicate detection, and multimodal support
"""

import io
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from app.services.google_drive_enhanced import MAX_FILE_SIZE, GoogleDriveEnhanced


class TestGoogleDriveEnhanced:
    """Test enhanced Google Drive service with production features"""

    @pytest.fixture
    def service(self):
        """Create GoogleDriveEnhanced instance"""
        with patch.dict(os.environ, {
            'GOOGLE_CLIENT_ID': 'test_client_id',
            'GOOGLE_CLIENT_SECRET': 'test_client_secret',
            'GOOGLE_REDIRECT_URI': 'http://localhost:8001/api/v1/gdrive/callback'
        }):
            return GoogleDriveEnhanced()

    @pytest.fixture
    def authenticated_service(self, service):
        """Create authenticated service instance"""
        service.tokens = {'access_token': 'test_token'}
        service.user_info = {'email': 'test@example.com', 'name': 'Test User'}
        return service

    def test_initialization(self, service):
        """Test service initialization"""
        assert service.client_id == 'test_client_id'
        assert service.client_secret == 'test_client_secret'
        assert service.tokens == {}
        assert service._ingested_files == set()

    def test_auth_url_generation(self, service):
        """Test OAuth URL generation"""
        auth_url = service.get_auth_url()

        assert 'https://accounts.google.com/o/oauth2/v2/auth' in auth_url
        assert 'client_id=test_client_id' in auth_url
        assert 'drive.readonly' in auth_url
        assert 'email' in auth_url
        assert 'profile' in auth_url

    @pytest.mark.asyncio
    async def test_token_exchange_success(self, service):
        """Test successful token exchange"""
        with patch('aiohttp.ClientSession') as MockSession:
            mock_session = AsyncMock()
            MockSession.return_value.__aenter__.return_value = mock_session

            # Mock token response
            mock_token_resp = AsyncMock()
            mock_token_resp.status = 200
            mock_token_resp.json = AsyncMock(return_value={
                'access_token': 'new_token',
                'refresh_token': 'refresh_token'
            })

            # Mock user info response
            mock_user_resp = AsyncMock()
            mock_user_resp.status = 200
            mock_user_resp.json = AsyncMock(return_value={
                'email': 'user@example.com',
                'name': 'Test User'
            })

            mock_session.post.return_value.__aenter__.return_value = mock_token_resp
            mock_session.get.return_value.__aenter__.return_value = mock_user_resp

            result = await service.exchange_code('auth_code')

            assert result['success'] is True
            assert result['email'] == 'user@example.com'
            assert service.tokens['access_token'] == 'new_token'

    @pytest.mark.asyncio
    async def test_list_files_with_ingested_marking(self, authenticated_service):
        """Test listing files marks already ingested ones"""
        authenticated_service._ingested_files.add('file1')

        with patch('aiohttp.ClientSession') as MockSession:
            mock_session = AsyncMock()
            MockSession.return_value.__aenter__.return_value = mock_session

            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value={
                'files': [
                    {'id': 'file1', 'name': 'doc1.pdf', 'mimeType': 'application/pdf'},
                    {'id': 'file2', 'name': 'doc2.txt', 'mimeType': 'text/plain'}
                ]
            })

            mock_session.get.return_value.__aenter__.return_value = mock_resp

            files = await authenticated_service.list_files()

            assert len(files) == 2
            assert files[0]['already_ingested'] is True
            assert files[1]['already_ingested'] is False

    def test_content_type_validation(self, service):
        """Test content type validation"""
        # Supported types
        assert service._validate_content_type('text/plain') == (True, 'text')
        assert service._validate_content_type('image/jpeg') == (True, 'image')
        assert service._validate_content_type('application/pdf') == (True, 'document')
        assert service._validate_content_type('application/vnd.google-apps.document') == (True, 'gdoc')

        # General text types
        assert service._validate_content_type('text/x-custom') == (True, 'text')

        # Unsupported types
        assert service._validate_content_type('video/mp4') == (False, 'unsupported')
        assert service._validate_content_type('audio/mp3') == (False, 'unsupported')

    @pytest.mark.asyncio
    async def test_duplicate_detection_memory(self, authenticated_service):
        """Test duplicate detection in memory cache"""
        authenticated_service._ingested_files.add('file123')

        is_duplicate = await authenticated_service.check_duplicate('file123')
        assert is_duplicate is True

        is_duplicate = await authenticated_service.check_duplicate('file456')
        assert is_duplicate is False

    @pytest.mark.asyncio
    async def test_duplicate_detection_database(self, authenticated_service):
        """Test duplicate detection via database check"""
        with patch.object(authenticated_service.memory_service, 'search_memories') as mock_search:
            # File exists in database
            mock_search.return_value = [{'id': 'memory123'}]

            is_duplicate = await authenticated_service.check_duplicate('file789')
            assert is_duplicate is True
            assert 'file789' in authenticated_service._ingested_files

            # File doesn't exist
            mock_search.return_value = []
            is_duplicate = await authenticated_service.check_duplicate('file999')
            assert is_duplicate is False

    @pytest.mark.asyncio
    async def test_file_size_validation(self, authenticated_service):
        """Test file size validation"""
        with patch('aiohttp.ClientSession') as MockSession:
            mock_session = AsyncMock()
            MockSession.return_value.__aenter__.return_value = mock_session

            # Mock metadata response with large file
            mock_metadata_resp = AsyncMock()
            mock_metadata_resp.status = 200
            mock_metadata_resp.json = AsyncMock(return_value={
                'id': 'file123',
                'name': 'huge_file.zip',
                'mimeType': 'application/zip',
                'size': str(MAX_FILE_SIZE + 1)  # Over limit
            })

            mock_session.get.return_value.__aenter__.return_value = mock_metadata_resp

            result = await authenticated_service.ingest_file('file123')

            assert result['status'] == 'skipped'
            assert result['reason'] == 'file_too_large'

    @pytest.mark.asyncio
    async def test_image_processing(self, authenticated_service):
        """Test image content processing"""
        # Create a test image
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()

        metadata = {'name': 'test_image.png'}

        content = await authenticated_service._process_image_content(img_bytes, metadata)

        assert 'Image: test_image.png' in content
        assert 'Format: PNG' in content
        assert 'Dimensions: 100x100' in content
        assert 'Mode: RGB' in content

    @pytest.mark.asyncio
    async def test_pdf_processing(self, authenticated_service):
        """Test PDF content processing"""
        # Create mock PDF bytes
        with patch('pypdf.PdfReader') as MockPdfReader:
            mock_reader = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "This is page content"
            mock_reader.pages = [mock_page]
            mock_reader.metadata = {'Title': 'Test PDF', 'Author': 'Test Author'}
            MockPdfReader.return_value = mock_reader

            metadata = {'name': 'test.pdf'}
            content = await authenticated_service._process_pdf_content(b'fake_pdf_bytes', metadata)

            assert 'PDF Document: test.pdf' in content
            assert 'Pages: 1' in content
            assert 'This is page content' in content
            assert 'Title: Test PDF' in content

    @pytest.mark.asyncio
    async def test_docx_processing(self, authenticated_service):
        """Test DOCX content processing"""
        with patch('docx.Document') as MockDocument:
            mock_doc = MagicMock()
            mock_paragraph = MagicMock()
            mock_paragraph.text = "This is a paragraph"
            mock_doc.paragraphs = [mock_paragraph]
            mock_doc.tables = []
            MockDocument.return_value = mock_doc

            metadata = {'name': 'test.docx'}
            content = await authenticated_service._process_docx_content(b'fake_docx_bytes', metadata)

            assert 'Word Document: test.docx' in content
            assert 'This is a paragraph' in content

    @pytest.mark.asyncio
    async def test_ingest_file_success(self, authenticated_service):
        """Test successful file ingestion"""
        with patch('aiohttp.ClientSession') as MockSession:
            mock_session = AsyncMock()
            MockSession.return_value.__aenter__.return_value = mock_session

            # Mock metadata response
            mock_metadata_resp = AsyncMock()
            mock_metadata_resp.status = 200
            mock_metadata_resp.json = AsyncMock(return_value={
                'id': 'file123',
                'name': 'document.txt',
                'mimeType': 'text/plain',
                'size': '1024',
                'modifiedTime': '2024-01-01T00:00:00Z',
                'webViewLink': 'https://drive.google.com/file/123'
            })

            # Mock content response
            mock_content_resp = AsyncMock()
            mock_content_resp.status = 200
            mock_content_resp.read = AsyncMock(return_value=b'File content here')

            mock_session.get.side_effect = [
                AsyncMock(__aenter__=AsyncMock(return_value=mock_metadata_resp)),
                AsyncMock(__aenter__=AsyncMock(return_value=mock_content_resp))
            ]

            # Mock memory service
            with patch.object(authenticated_service.memory_service, 'create_memory') as mock_create:
                mock_create.return_value = {'id': 'memory123', 'content': 'File content here'}

                result = await authenticated_service.ingest_file('file123')

                assert result['id'] == 'memory123'
                assert 'file123' in authenticated_service._ingested_files

                # Check memory was created with correct data
                mock_create.assert_called_once()
                call_args = mock_create.call_args
                assert call_args[1]['content'] == 'File content here'
                assert call_args[1]['metadata']['gdrive_id'] == 'file123'
                assert call_args[1]['metadata']['content_category'] == 'text'
                assert call_args[1]['importance_score'] == 0.7

    @pytest.mark.asyncio
    async def test_ingest_google_docs(self, authenticated_service):
        """Test Google Docs ingestion with export"""
        with patch('aiohttp.ClientSession') as MockSession:
            mock_session = AsyncMock()
            MockSession.return_value.__aenter__.return_value = mock_session

            # Mock metadata response for Google Doc
            mock_metadata_resp = AsyncMock()
            mock_metadata_resp.status = 200
            mock_metadata_resp.json = AsyncMock(return_value={
                'id': 'doc123',
                'name': 'My Document',
                'mimeType': 'application/vnd.google-apps.document',
                'modifiedTime': '2024-01-01T00:00:00Z',
                'webViewLink': 'https://docs.google.com/document/123'
            })

            # Mock export response
            mock_export_resp = AsyncMock()
            mock_export_resp.status = 200
            mock_export_resp.read = AsyncMock(return_value=b'Exported document content')

            mock_session.get.side_effect = [
                AsyncMock(__aenter__=AsyncMock(return_value=mock_metadata_resp)),
                AsyncMock(__aenter__=AsyncMock(return_value=mock_export_resp))
            ]

            with patch.object(authenticated_service.memory_service, 'create_memory') as mock_create:
                mock_create.return_value = {'id': 'memory456'}

                _ = await authenticated_service.ingest_file('doc123')

                # Check export URL was used
                export_call = mock_session.get.call_args_list[1]
                assert 'export' in str(export_call[0][0])
                assert export_call[1]['params'] == {'mimeType': 'text/plain'}

    @pytest.mark.asyncio
    async def test_ingest_skip_duplicate(self, authenticated_service):
        """Test skipping duplicate files"""
        authenticated_service._ingested_files.add('file123')

        result = await authenticated_service.ingest_file('file123')

        assert result['status'] == 'skipped'
        assert result['reason'] == 'duplicate'

    @pytest.mark.asyncio
    async def test_ingest_force_duplicate(self, authenticated_service):
        """Test force re-ingestion of duplicate"""
        authenticated_service._ingested_files.add('file123')

        with patch('aiohttp.ClientSession') as MockSession:
            mock_session = AsyncMock()
            MockSession.return_value.__aenter__.return_value = mock_session

            mock_metadata_resp = AsyncMock()
            mock_metadata_resp.status = 200
            mock_metadata_resp.json = AsyncMock(return_value={
                'id': 'file123',
                'name': 'document.txt',
                'mimeType': 'text/plain',
                'size': '1024'
            })

            mock_content_resp = AsyncMock()
            mock_content_resp.status = 200
            mock_content_resp.read = AsyncMock(return_value=b'Updated content')

            mock_session.get.side_effect = [
                AsyncMock(__aenter__=AsyncMock(return_value=mock_metadata_resp)),
                AsyncMock(__aenter__=AsyncMock(return_value=mock_content_resp))
            ]

            with patch.object(authenticated_service.memory_service, 'create_memory') as mock_create:
                mock_create.return_value = {'id': 'memory789'}

                result = await authenticated_service.ingest_file('file123', force=True)

                assert result['id'] == 'memory789'
                mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_ingest(self, authenticated_service):
        """Test batch file ingestion"""
        file_ids = ['file1', 'file2', 'file3']

        with patch.object(authenticated_service, 'ingest_file') as mock_ingest:
            mock_ingest.side_effect = [
                {'id': 'memory1'},  # Success
                {'status': 'skipped', 'reason': 'duplicate'},  # Skipped
                None  # Failed
            ]

            results = await authenticated_service.batch_ingest(file_ids)

            assert results['total'] == 3
            assert results['successful'] == 1
            assert results['skipped'] == 1
            assert results['failed'] == 1
            assert len(results['details']) == 3

    @pytest.mark.asyncio
    async def test_batch_ingest_with_progress(self, authenticated_service):
        """Test batch ingestion with progress callback"""
        file_ids = ['file1', 'file2']
        progress_updates = []

        async def progress_callback(update):
            progress_updates.append(update)

        with patch.object(authenticated_service, 'ingest_file') as mock_ingest:
            mock_ingest.return_value = {'id': 'memory1'}

            await authenticated_service.batch_ingest(file_ids, progress_callback)

            assert len(progress_updates) == 2
            assert progress_updates[0]['current'] == 1
            assert progress_updates[0]['total'] == 2
            assert progress_updates[0]['percentage'] == 50.0
            assert progress_updates[1]['percentage'] == 100.0

    @pytest.mark.asyncio
    async def test_image_thumbnail_generation(self, authenticated_service):
        """Test thumbnail generation for images"""
        # Create test image
        img = Image.new('RGB', (500, 500), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()

        with patch('aiohttp.ClientSession') as MockSession:
            mock_session = AsyncMock()
            MockSession.return_value.__aenter__.return_value = mock_session

            mock_metadata_resp = AsyncMock()
            mock_metadata_resp.status = 200
            mock_metadata_resp.json = AsyncMock(return_value={
                'id': 'img123',
                'name': 'photo.png',
                'mimeType': 'image/png',
                'size': str(len(img_bytes))
            })

            mock_content_resp = AsyncMock()
            mock_content_resp.status = 200
            mock_content_resp.read = AsyncMock(return_value=img_bytes)

            mock_session.get.side_effect = [
                AsyncMock(__aenter__=AsyncMock(return_value=mock_metadata_resp)),
                AsyncMock(__aenter__=AsyncMock(return_value=mock_content_resp))
            ]

            with patch.object(authenticated_service.memory_service, 'create_memory') as mock_create:
                mock_create.return_value = {'id': 'memory_img'}

                await authenticated_service.ingest_file('img123')

                # Check thumbnail was added to metadata
                call_args = mock_create.call_args
                metadata = call_args[1]['metadata']
                assert 'thumbnail' in metadata
                assert metadata['thumbnail'].startswith('data:image/png;base64,')

    def test_connection_status(self, service):
        """Test connection status reporting"""
        # Not connected
        status = service.get_connection_status()
        assert status['connected'] is False
        assert 'error' in status

        # Connected
        service.tokens = {'access_token': 'token'}
        service.user_info = {'email': 'user@example.com', 'name': 'User'}
        service._ingested_files = {'file1', 'file2'}

        status = service.get_connection_status()
        assert status['connected'] is True
        assert status['user_email'] == 'user@example.com'
        assert status['ingested_files_count'] == 2
        assert status['max_file_size_mb'] == 250.0
        assert len(status['supported_types']) > 0

    @pytest.mark.asyncio
    async def test_encoding_detection(self, authenticated_service):
        """Test character encoding detection for text files"""
        with patch('aiohttp.ClientSession') as MockSession:
            mock_session = AsyncMock()
            MockSession.return_value.__aenter__.return_value = mock_session

            mock_metadata_resp = AsyncMock()
            mock_metadata_resp.status = 200
            mock_metadata_resp.json = AsyncMock(return_value={
                'id': 'file123',
                'name': 'document.txt',
                'mimeType': 'text/plain',
                'size': '100'
            })

            # UTF-16 encoded content
            test_text = "Hello World with special chars: é, ñ, 中文"
            utf16_bytes = test_text.encode('utf-16')

            mock_content_resp = AsyncMock()
            mock_content_resp.status = 200
            mock_content_resp.read = AsyncMock(return_value=utf16_bytes)

            mock_session.get.side_effect = [
                AsyncMock(__aenter__=AsyncMock(return_value=mock_metadata_resp)),
                AsyncMock(__aenter__=AsyncMock(return_value=mock_content_resp))
            ]

            with patch('chardet.detect') as mock_detect:
                mock_detect.return_value = {'encoding': 'utf-16'}

                with patch.object(authenticated_service.memory_service, 'create_memory') as mock_create:
                    mock_create.return_value = {'id': 'memory123'}

                    _ = await authenticated_service.ingest_file('file123')

                    # Check content was properly decoded
                    call_args = mock_create.call_args
                    assert 'Hello World' in call_args[1]['content']

    @pytest.mark.asyncio
    async def test_error_handling(self, authenticated_service):
        """Test error handling during ingestion"""
        with patch('aiohttp.ClientSession') as MockSession:
            mock_session = AsyncMock()
            MockSession.return_value.__aenter__.return_value = mock_session

            # Simulate API error
            mock_error_resp = AsyncMock()
            mock_error_resp.status = 404

            mock_session.get.return_value.__aenter__.return_value = mock_error_resp

            result = await authenticated_service.ingest_file('nonexistent')

            assert result is None


@pytest.mark.integration
class TestGoogleDriveIntegration:
    """Integration tests with real Google Drive API (requires credentials)"""

    @pytest.mark.skipif(
        not os.getenv('GOOGLE_CLIENT_ID'),
        reason="Google Drive credentials not configured"
    )
    @pytest.mark.asyncio
    async def test_real_authentication(self):
        """Test real OAuth flow (interactive)"""
        service = GoogleDriveEnhanced()
        auth_url = service.get_auth_url()

        print(f"\nVisit this URL to authenticate: {auth_url}")
        # This would require manual interaction in real testing

    @pytest.mark.skipif(
        not os.getenv('GOOGLE_ACCESS_TOKEN'),
        reason="Google Drive access token not available"
    )
    @pytest.mark.asyncio
    async def test_real_file_listing(self):
        """Test listing real files from Google Drive"""
        service = GoogleDriveEnhanced()
        service.tokens = {'access_token': os.getenv('GOOGLE_ACCESS_TOKEN')}

        files = await service.list_files()

        assert isinstance(files, list)
        if files:
            assert 'id' in files[0]
            assert 'name' in files[0]
            assert 'mimeType' in files[0]

    @pytest.mark.skipif(
        not os.getenv('GOOGLE_ACCESS_TOKEN'),
        reason="Google Drive access token not available"
    )
    @pytest.mark.asyncio
    async def test_real_file_ingestion(self):
        """Test ingesting a real file from Google Drive"""
        service = GoogleDriveEnhanced()
        service.tokens = {'access_token': os.getenv('GOOGLE_ACCESS_TOKEN')}

        # List files first
        files = await service.list_files()

        if files:
            # Try to ingest the first text file found
            for file in files:
                if file['mimeType'].startswith('text/'):
                    result = await service.ingest_file(file['id'])

                    assert result is not None
                    if result.get('status') != 'skipped':
                        assert 'id' in result
                    break


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])

