"""
Unit tests for Google Drive integration
"""

import io
import pickle
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ingestion.google_drive_client import DriveFile, GoogleDriveClient


class TestDriveFile:
    """Test DriveFile dataclass"""

    def test_drive_file_creation(self):
        """Test creating DriveFile instance"""
        file = DriveFile(
            id="file123",
            name="document.pdf",
            mime_type="application/pdf",
            size=1024,
            created_time=datetime.utcnow(),
            modified_time=datetime.utcnow(),
            parents=["folder123"],
            web_view_link="https://drive.google.com/file/123",
            is_folder=False
        )

        assert file.id == "file123"
        assert file.name == "document.pdf"
        assert file.mime_type == "application/pdf"
        assert file.size == 1024
        assert file.parents == ["folder123"]
        assert file.is_folder is False

    def test_drive_file_minimal(self):
        """Test DriveFile with minimal fields"""
        file = DriveFile(
            id="file456",
            name="folder",
            mime_type="application/vnd.google-apps.folder",
            is_folder=True
        )

        assert file.id == "file456"
        assert file.name == "folder"
        assert file.is_folder is True
        assert file.size is None
        assert file.created_time is None


class TestGoogleDriveClient:
    """Test GoogleDriveClient"""

    @pytest.fixture
    def client(self, tmp_path):
        """Create GoogleDriveClient instance"""
        return GoogleDriveClient(credentials_path=tmp_path / "test_creds.pickle")

    def test_client_initialization(self, client):
        """Test client initialization"""
        assert client.creds is None
        assert client.service is None
        assert client.credentials_path.parent.exists()

    @patch.dict('os.environ', {'GOOGLE_CLIENT_ID': 'test_id', 'GOOGLE_CLIENT_SECRET': 'test_secret'})
    def test_get_auth_url(self, client):
        """Test getting OAuth authorization URL"""
        with patch('app.ingestion.google_drive_client.Flow') as MockFlow:
            mock_flow = MagicMock()
            mock_flow.authorization_url.return_value = ("https://auth.url", "state")
            MockFlow.from_client_config.return_value = mock_flow

            auth_url = client.get_auth_url()

            assert auth_url == "https://auth.url"
            MockFlow.from_client_config.assert_called_once()
            mock_flow.authorization_url.assert_called_once()

    def test_get_auth_url_no_client_id(self, client):
        """Test getting auth URL without client ID"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="Google Client ID not configured"):
                client.get_auth_url()

    @pytest.mark.asyncio
    async def test_authenticate_with_existing_creds(self, client, tmp_path):
        """Test authentication with existing credentials"""
        # Create mock credentials
        mock_creds = MagicMock()
        mock_creds.valid = True

        # Save credentials
        with open(client.credentials_path, 'wb') as f:
            pickle.dump(mock_creds, f)

        with patch('app.ingestion.google_drive_client.build') as MockBuild:
            mock_service = MagicMock()
            MockBuild.return_value = mock_service

            result = await client.authenticate()

            assert result is True
            assert client.creds == mock_creds
            assert client.service == mock_service

    @pytest.mark.asyncio
    async def test_authenticate_with_expired_creds(self, client, tmp_path):
        """Test authentication with expired credentials"""
        # Create expired credentials
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh_token"

        # Save credentials
        with open(client.credentials_path, 'wb') as f:
            pickle.dump(mock_creds, f)

        with patch('app.ingestion.google_drive_client.Request') as MockRequest, \
             patch('app.ingestion.google_drive_client.build') as MockBuild:

            mock_service = MagicMock()
            MockBuild.return_value = mock_service

            result = await client.authenticate()

            assert result is True
            mock_creds.refresh.assert_called_once_with(MockRequest())

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'GOOGLE_CLIENT_ID': 'test_id', 'GOOGLE_CLIENT_SECRET': 'test_secret'})
    async def test_authenticate_with_auth_code(self, client):
        """Test authentication with authorization code"""
        auth_code = "test_auth_code"

        with patch('app.ingestion.google_drive_client.Flow') as MockFlow, \
             patch('app.ingestion.google_drive_client.build') as MockBuild:

            mock_flow = MagicMock()
            mock_creds = MagicMock()
            mock_creds.valid = True
            mock_flow.credentials = mock_creds
            MockFlow.from_client_config.return_value = mock_flow

            mock_service = MagicMock()
            MockBuild.return_value = mock_service

            result = await client.authenticate(auth_code)

            assert result is True
            assert client.creds == mock_creds
            mock_flow.fetch_token.assert_called_once_with(code=auth_code)

    def test_is_authenticated(self, client):
        """Test authentication check"""
        assert client.is_authenticated() is False

        client.creds = MagicMock()
        client.creds.valid = True
        assert client.is_authenticated() is True

        client.creds.valid = False
        assert client.is_authenticated() is False

    @pytest.mark.asyncio
    async def test_list_files(self, client):
        """Test listing files from Google Drive"""
        client.service = MagicMock()

        # Mock API response
        mock_response = {
            'files': [
                {
                    'id': 'file1',
                    'name': 'document.pdf',
                    'mimeType': 'application/pdf',
                    'size': '1024',
                    'createdTime': '2024-01-24T10:00:00.000Z',
                    'modifiedTime': '2024-01-24T11:00:00.000Z',
                    'parents': ['folder1'],
                    'webViewLink': 'https://drive.google.com/file/1'
                },
                {
                    'id': 'folder1',
                    'name': 'My Folder',
                    'mimeType': 'application/vnd.google-apps.folder',
                    'createdTime': '2024-01-20T10:00:00.000Z',
                    'modifiedTime': '2024-01-20T10:00:00.000Z'
                }
            ],
            'nextPageToken': 'next_token_123'
        }

        client.service.files().list.return_value.execute.return_value = mock_response

        result = await client.list_files(folder_id="root", page_size=50)

        assert len(result['files']) == 2
        assert result['next_page_token'] == 'next_token_123'

        # Check first file
        file1 = result['files'][0]
        assert file1.id == 'file1'
        assert file1.name == 'document.pdf'
        assert file1.mime_type == 'application/pdf'
        assert file1.size == 1024
        assert file1.is_folder is False

        # Check folder
        folder = result['files'][1]
        assert folder.id == 'folder1'
        assert folder.name == 'My Folder'
        assert folder.is_folder is True

    @pytest.mark.asyncio
    async def test_list_files_not_authenticated(self, client):
        """Test listing files without authentication"""
        with pytest.raises(ValueError, match="Not authenticated"):
            await client.list_files()

    @pytest.mark.asyncio
    async def test_download_file(self, client):
        """Test downloading a file"""
        client.service = MagicMock()

        # Mock file metadata
        client.service.files().get.return_value.execute.return_value = {
            'mimeType': 'application/pdf'
        }

        # Mock file download
        mock_request = MagicMock()
        client.service.files().get_media.return_value = mock_request

        # Mock MediaIoBaseDownload
        with patch('app.ingestion.google_drive_client.MediaIoBaseDownload') as MockDownloader:
            mock_downloader = MagicMock()
            mock_downloader.next_chunk.side_effect = [
                (MagicMock(progress=lambda: 0.5), False),
                (MagicMock(progress=lambda: 1.0), True)
            ]
            MockDownloader.return_value = mock_downloader

            content = await client.download_file("file123", "document.pdf")

            assert isinstance(content, bytes)
            client.service.files().get_media.assert_called_once_with(fileId="file123")

    @pytest.mark.asyncio
    async def test_download_google_doc(self, client):
        """Test downloading Google Docs file with export"""
        client.service = MagicMock()

        # Mock file metadata - Google Docs
        client.service.files().get.return_value.execute.return_value = {
            'mimeType': 'application/vnd.google-apps.document'
        }

        # Mock file export
        mock_request = MagicMock()
        client.service.files().export_media.return_value = mock_request

        with patch('app.ingestion.google_drive_client.MediaIoBaseDownload') as MockDownloader:
            mock_downloader = MagicMock()
            mock_downloader.next_chunk.return_value = (None, True)
            MockDownloader.return_value = mock_downloader

            content = await client.download_file("doc123", "My Document")

            # Should export as DOCX
            client.service.files().export_media.assert_called_once_with(
                fileId="doc123",
                mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )

    @pytest.mark.asyncio
    async def test_get_file_info(self, client):
        """Test getting file information"""
        client.service = MagicMock()

        mock_file_data = {
            'id': 'file123',
            'name': 'test.pdf',
            'mimeType': 'application/pdf',
            'size': '2048',
            'createdTime': '2024-01-24T10:00:00.000Z',
            'modifiedTime': '2024-01-24T12:00:00.000Z',
            'parents': ['parent123'],
            'webViewLink': 'https://drive.google.com/file/123'
        }

        client.service.files().get.return_value.execute.return_value = mock_file_data

        file_info = await client.get_file_info("file123")

        assert file_info.id == 'file123'
        assert file_info.name == 'test.pdf'
        assert file_info.size == 2048
        assert file_info.web_view_link == 'https://drive.google.com/file/123'

    @pytest.mark.asyncio
    async def test_search_files(self, client):
        """Test searching files"""
        client.service = MagicMock()

        mock_response = {
            'files': [
                {
                    'id': 'file1',
                    'name': 'machine learning.pdf',
                    'mimeType': 'application/pdf',
                    'size': '1024',
                    'createdTime': '2024-01-24T10:00:00.000Z',
                    'modifiedTime': '2024-01-24T11:00:00.000Z',
                    'webViewLink': 'https://drive.google.com/file/1'
                }
            ]
        }

        client.service.files().list.return_value.execute.return_value = mock_response

        results = await client.search_files("machine learning", page_size=10)

        assert len(results) == 1
        assert results[0].name == 'machine learning.pdf'

        # Check search query was built correctly
        call_args = client.service.files().list.call_args
        assert "fullText contains 'machine learning'" in call_args[1]['q']

    @pytest.mark.asyncio
    async def test_monitor_folder(self, client):
        """Test folder monitoring"""
        client.service = MagicMock()

        # Mock callback
        callback = AsyncMock()

        # Mock list_files responses
        responses = [
            # First check - 2 files
            {
                'files': [
                    DriveFile(
                        id='file1',
                        name='doc1.pdf',
                        mime_type='application/pdf',
                        modified_time=datetime(2024, 1, 24, 10, 0)
                    ),
                    DriveFile(
                        id='file2',
                        name='doc2.docx',
                        mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        modified_time=datetime(2024, 1, 24, 11, 0)
                    )
                ],
                'next_page_token': None
            },
            # Second check - file2 modified, file3 added
            {
                'files': [
                    DriveFile(
                        id='file1',
                        name='doc1.pdf',
                        mime_type='application/pdf',
                        modified_time=datetime(2024, 1, 24, 10, 0)
                    ),
                    DriveFile(
                        id='file2',
                        name='doc2.docx',
                        mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        modified_time=datetime(2024, 1, 24, 12, 0)  # Modified
                    ),
                    DriveFile(
                        id='file3',
                        name='doc3.txt',
                        mime_type='text/plain',
                        modified_time=datetime(2024, 1, 24, 13, 0)  # New
                    )
                ],
                'next_page_token': None
            }
        ]

        # Setup to run only 2 iterations
        call_count = 0
        async def mock_list_files(*args, **kwargs):
            nonlocal call_count
            result = responses[min(call_count, 1)]
            call_count += 1
            if call_count > 1:
                # Stop monitoring after 2 checks
                raise KeyboardInterrupt()
            return result

        client.list_files = mock_list_files

        with patch('asyncio.sleep'):
            try:
                await client.monitor_folder(
                    folder_id="folder123",
                    callback=callback,
                    check_interval=1
                )
            except KeyboardInterrupt:
                pass

        # Check callback was called with new/modified files
        assert callback.call_count == 1
        new_files = callback.call_args[0][0]
        assert len(new_files) == 2  # file2 (modified) and file3 (new)
        assert any(f.id == 'file2' for f in new_files)
        assert any(f.id == 'file3' for f in new_files)

    def test_get_export_filename(self, client):
        """Test getting export filename for Google Docs"""
        # Regular file - no change
        file = DriveFile(
            id="file1",
            name="document.pdf",
            mime_type="application/pdf"
        )
        assert client.get_export_filename(file) == "document.pdf"

        # Google Docs - add .docx
        file = DriveFile(
            id="doc1",
            name="My Document",
            mime_type="application/vnd.google-apps.document"
        )
        assert client.get_export_filename(file) == "My Document.docx"

        # Google Sheets - add .xlsx
        file = DriveFile(
            id="sheet1",
            name="My Spreadsheet",
            mime_type="application/vnd.google-apps.spreadsheet"
        )
        assert client.get_export_filename(file) == "My Spreadsheet.xlsx"

        # Google Slides - add .pdf
        file = DriveFile(
            id="pres1",
            name="My Presentation",
            mime_type="application/vnd.google-apps.presentation"
        )
        assert client.get_export_filename(file) == "My Presentation.pdf"

    @pytest.mark.asyncio
    async def test_ingest_file_streaming(self, client):
        """Test that file ingestion uses streaming"""
        client.service = MagicMock()

        # Mock file metadata
        client.service.files().get.return_value.execute.return_value = {
            'mimeType': 'application/pdf'
        }

        # Mock file download to return a file-like object
        mock_file_stream = io.BytesIO(b"test content")
        with patch('app.ingestion.google_drive_client.MediaIoBaseDownload') as MockDownloader:
            mock_downloader = MagicMock()
            mock_downloader.next_chunk.return_value = (None, True)
            MockDownloader.return_value = mock_downloader
            
            # Mock the download_file to return a stream
            async def mock_download_file(*args, **kwargs):
                return mock_file_stream
            
            client.download_file = mock_download_file

            # Mock the ingestion engine
            with patch('app.routes.google_drive_routes.IngestionEngine') as MockIngestionEngine:
                mock_ingestion_engine = AsyncMock()
                mock_ingestion_engine.ingest_file.return_value = MagicMock(success=True, memories_created=1)
                MockIngestionEngine.return_value = mock_ingestion_engine

                # Call the ingestion route
                from app.routes.google_drive_routes import process_drive_ingestion
                await process_drive_ingestion(
                    client=client,
                    file_ids=["file123"],
                    user_id="user123",
                    tags=[],
                    metadata={},
                    db=MagicMock()
                )

                # Assert that ingest_file was called with a file-like object
                mock_ingestion_engine.ingest_file.assert_called_once()
                call_args = mock_ingestion_engine.ingest_file.call_args
                assert call_args[1]['file'] == mock_file_stream
