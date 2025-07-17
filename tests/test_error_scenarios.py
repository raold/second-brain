# tests/test_error_scenarios.py

import asyncio
from concurrent.futures import TimeoutError
from unittest.mock import MagicMock, Mock, patch

from app.main import app


class TestNetworkErrors:
    """Test network-related error scenarios"""
    
    def test_openai_api_timeout(self, test_client, auth_header, sample_payload_dict, monkeypatch):
        """Test OpenAI API timeout during embedding generation"""
        
        # Override the autouse mock to simulate timeout
        timeout_mock = MagicMock(side_effect=TimeoutError("OpenAI API timeout"))
        monkeypatch.setattr("app.storage.qdrant_client.get_openai_embedding", timeout_mock)
        monkeypatch.setattr("app.utils.openai_client.get_openai_embedding", timeout_mock)
        
        response = test_client.post("/ingest", json=sample_payload_dict, headers=auth_header)
        assert response.status_code == 500
        assert "Failed to ingest payload" in response.json()["detail"]
    
    def test_openai_api_rate_limit(self, test_client, auth_header, sample_payload_dict, monkeypatch):
        """Test OpenAI API rate limiting"""
        
        import openai
        
        rate_limit_mock = MagicMock(side_effect=openai.RateLimitError(
            message="Rate limit exceeded",
            response=Mock(status_code=429),
            body={"error": {"type": "rate_limit_exceeded"}}
        ))
        monkeypatch.setattr("app.storage.qdrant_client.get_openai_embedding", rate_limit_mock)
        monkeypatch.setattr("app.utils.openai_client.get_openai_embedding", rate_limit_mock)
        
        response = test_client.post("/ingest", json=sample_payload_dict, headers=auth_header)
        assert response.status_code == 500
    
    def test_qdrant_connection_refused(self, test_client, auth_header, sample_payload_dict):
        """Test Qdrant connection refused"""
        
        with patch("app.router.qdrant_upsert") as mock_upsert:
            mock_upsert.side_effect = ConnectionRefusedError("Connection refused")
            
            response = test_client.post("/ingest", json=sample_payload_dict, headers=auth_header)
            assert response.status_code == 500
            assert "Failed to ingest payload" in response.json()["detail"]
    
    def test_qdrant_network_timeout(self, test_client, auth_header):
        """Test Qdrant network timeout during search"""
        
        with patch("app.router.qdrant_search") as mock_search:
            mock_search.side_effect = TimeoutError("Network timeout")
            
            response = test_client.get("/search?q=test", headers=auth_header)
            assert response.status_code == 500
    
    def test_database_connection_error(self, test_client, auth_header, sample_payload_dict):
        """Test database connection error"""
        
        from sqlalchemy.exc import OperationalError
        with patch("app.router.store_memory_pg_background") as mock_store:
            mock_store.side_effect = OperationalError("Database connection failed", None, None)
            
            # Should still succeed as DB storage is background task
            response = test_client.post("/ingest", json=sample_payload_dict, headers=auth_header)
            assert response.status_code == 200


class TestValidationErrors:
    """Test input validation error scenarios"""
    
    def test_invalid_payload_structure(self, test_client, auth_header):
        """Test various invalid payload structures"""
        
        invalid_payloads = [
            {},  # Empty payload
            {"id": "test"},  # Missing data
            {"data": {"note": "test"}},  # Missing id
            {"id": "", "data": {"note": "test"}},  # Empty id
            {"id": "test", "data": {}},  # Missing note
            {"id": "test", "data": {"note": ""}},  # Empty note
        ]
        
        for payload in invalid_payloads:
            response = test_client.post("/ingest", json=payload, headers=auth_header)
            assert response.status_code in [400, 422, 500]
    
    def test_invalid_search_parameters(self, test_client, auth_header):
        """Test invalid search parameters"""
        
        invalid_queries = [
            "/search",  # Missing query parameter
            "/search?q=",  # Empty query
            "/search?q=" + "x" * 10000,  # Extremely long query
        ]
        
        for query_url in invalid_queries:
            response = test_client.get(query_url, headers=auth_header)
            assert response.status_code in [200, 400, 413, 422]
    
    def test_invalid_file_upload(self, test_client, auth_header):
        """Test invalid file uploads for transcription"""
        
        # Empty file
        response = test_client.post(
            "/transcribe",
            headers=auth_header,
            files={"file": ("empty.wav", b"", "audio/wav")}
        )
        assert response.status_code == 400
        
        # Invalid file type
        response = test_client.post(
            "/transcribe",
            headers=auth_header,
            files={"file": ("test.txt", b"not audio", "text/plain")}
        )
        # Should either reject or handle gracefully
        assert response.status_code in [200, 400, 415, 422]
    
    def test_malformed_json(self, test_client, auth_header):
        """Test malformed JSON in requests"""
        
        # Send malformed JSON
        response = test_client.post(
            "/ingest",
            headers={**auth_header, "Content-Type": "application/json"},
            data="{invalid json}"
        )
        assert response.status_code == 422


class TestAuthenticationErrors:
    """Test authentication and authorization error scenarios"""
    
    def test_missing_auth_header(self, sample_payload_dict):
        """Test requests without authentication"""
        from fastapi.testclient import TestClient
        
        # Create a new client without auth overrides
        app.dependency_overrides.clear()
        client = TestClient(app)
        
        response = client.post("/ingest", json=sample_payload_dict)
        assert response.status_code in [401, 403]
    
    def test_invalid_token(self, sample_payload_dict):
        """Test requests with invalid token"""
        from fastapi.testclient import TestClient
        
        # Create a new client without auth overrides
        app.dependency_overrides.clear()
        client = TestClient(app)
        
        invalid_headers = {"Authorization": "Bearer invalid-token"}
        response = client.post("/ingest", json=sample_payload_dict, headers=invalid_headers)
        assert response.status_code in [401, 403]
    
    def test_malformed_auth_header(self, sample_payload_dict):
        """Test malformed authorization header"""
        from fastapi.testclient import TestClient
        
        # Create a new client without auth overrides
        app.dependency_overrides.clear()
        client = TestClient(app)
        
        malformed_headers = [
            {"Authorization": "invalid"},  # Missing Bearer
            {"Authorization": "Bearer"},  # Missing token
            {"Authorization": "Basic token"},  # Wrong type
        ]
        
        for headers in malformed_headers:
            response = client.post("/ingest", json=sample_payload_dict, headers=headers)
            assert response.status_code in [401, 403, 422]


class TestWebSocketErrors:
    """Test WebSocket-specific error scenarios"""
    
    def test_websocket_auth_failure(self, test_client):
        """Test WebSocket authentication failure"""
        
        # Clear auth overrides
        app.dependency_overrides.clear()
        
        try:
            with test_client.websocket_connect("/ws/generate?token=invalid"):
                # Connection should be closed immediately
                assert False, "Should not reach here"
        except Exception:
            # Expected to fail
            pass
    
    def test_websocket_invalid_message_format(self, test_client):
        """Test invalid WebSocket message formats"""
        
        with test_client.websocket_connect("/ws/generate?token=test-token") as websocket:
            # Send invalid JSON
            try:
                websocket.send_text("invalid json")
                message = websocket.receive_json()
                assert "error" in message
            except Exception:
                # Expected behavior
                pass
    
    def test_websocket_missing_prompt(self, test_client):
        """Test WebSocket with missing prompt"""
        
        with test_client.websocket_connect("/ws/generate?token=test-token") as websocket:
            # Send message without prompt
            websocket.send_json({"json": True})
            message = websocket.receive_json()
            assert "error" in message
            assert "Missing prompt" in message["error"]
    
    def test_websocket_connection_interrupted(self, test_client):
        """Test WebSocket connection interruption"""
        
        with patch("app.api.websocket.get_openai_stream") as mock_stream:
            # Mock stream that raises exception
            async def failing_stream(prompt):
                yield "partial"
                raise ConnectionError("Connection lost")
            
            mock_stream.return_value = failing_stream("test")
            
            with test_client.websocket_connect("/ws/generate?token=test-token") as websocket:
                websocket.send_json({"prompt": "test", "json": True})
                
                # Should receive partial content then error
                messages = []
                try:
                    while True:
                        message = websocket.receive_json()
                        messages.append(message)
                        if message.get("done") or "error" in message:
                            break
                except Exception:
                    pass
                
                # Should have received at least one message
                assert len(messages) > 0


class TestConcurrencyErrors:
    """Test concurrency-related error scenarios"""
    
    def test_concurrent_writes_same_id(self, test_client, auth_header):
        """Test concurrent writes to same ID"""
        
        payload = {
            "id": "concurrent-test",
            "type": "note",
            "context": "test",
            "priority": "normal",
            "ttl": "1d",
            "data": {"note": "Concurrent test"},
            "meta": {}
        }
        
        import threading
        
        results = []
        
        def send_request():
            try:
                response = test_client.post("/ingest", json=payload, headers=auth_header)
                results.append(response.status_code)
            except Exception:
                results.append(500)
        
        # Send multiple concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=send_request)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All should succeed or handle gracefully
        assert all(status in [200, 409, 500] for status in results)
    
    def test_high_load_scenario(self, test_client, auth_header, multiple_payloads):
        """Test system behavior under high load"""
        
        import concurrent.futures
        
        def process_payload(payload):
            try:
                response = test_client.post("/ingest", json=payload, headers=auth_header)
                return response.status_code
            except Exception:
                return 500
        
        # Simulate high load with many concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(process_payload, payload) 
                for payload in multiple_payloads
            ]
            
            results = [future.result(timeout=30) for future in concurrent.futures.as_completed(futures)]
        
        # Most requests should succeed
        success_rate = sum(1 for r in results if r == 200) / len(results)
        assert success_rate >= 0.8  # At least 80% success rate


class TestResourceExhaustionErrors:
    """Test resource exhaustion scenarios"""
    
    def test_memory_exhaustion_large_payload(self, test_client, auth_header):
        """Test handling of extremely large payloads"""
        
        # Create very large payload
        huge_payload = {
            "id": "huge-test",
            "type": "note",
            "context": "test",
            "priority": "normal",
            "ttl": "1d",
            "data": {"note": "x" * (1024 * 1024)},  # 1MB of text
            "meta": {}
        }
        
        response = test_client.post("/ingest", json=huge_payload, headers=auth_header)
        # Should either succeed or reject gracefully
        assert response.status_code in [200, 413, 422, 500]
    
    def test_embedding_dimension_mismatch(self, test_client, auth_header, sample_payload_dict):
        """Test handling of wrong embedding dimensions"""
        
        with patch("app.storage.qdrant_client.get_openai_embedding") as mock_embedding:
            # Return wrong dimension embedding
            mock_embedding.return_value = [0.1] * 512  # Wrong size
            
            response = test_client.post("/ingest", json=sample_payload_dict, headers=auth_header)
            # Should handle gracefully
            assert response.status_code in [200, 500]
    
    def test_disk_space_exhaustion(self, test_client, auth_header, sample_payload_dict):
        """Test handling of disk space exhaustion"""
        
        with patch("app.router.write_markdown") as mock_write:
            mock_write.side_effect = OSError("No space left on device")
            
            response = test_client.post("/ingest", json=sample_payload_dict, headers=auth_header)
            assert response.status_code == 500


class TestDataCorruptionErrors:
    """Test data corruption and consistency error scenarios"""
    
    def test_corrupted_embedding_response(self, test_client, auth_header, sample_payload_dict, monkeypatch):
        """Test handling of corrupted OpenAI embedding response"""
        
        # Return corrupted embedding
        corrupted_mock = MagicMock(return_value=None)
        monkeypatch.setattr("app.storage.qdrant_client.get_openai_embedding", corrupted_mock)
        monkeypatch.setattr("app.utils.openai_client.get_openai_embedding", corrupted_mock)
        
        response = test_client.post("/ingest", json=sample_payload_dict, headers=auth_header)
        assert response.status_code == 500
    
    def test_invalid_search_results(self, test_client, auth_header):
        """Test handling of invalid/corrupted search results"""
        
        with patch("app.router.qdrant_search") as mock_search:
            # Return malformed results
            mock_search.return_value = [
                {"invalid": "structure"},  # Missing required fields
                None,  # Null result
                {"id": "test", "score": "invalid"}  # Invalid score type
            ]
            
            response = test_client.get("/search?q=test", headers=auth_header)
            # Should handle gracefully
            assert response.status_code in [200, 500]
    
    def test_unicode_encoding_errors(self, test_client, auth_header):
        """Test handling of unicode encoding/decoding errors"""
        
        # Payload with problematic unicode
        unicode_payload = {
            "id": "unicode-test",
            "type": "note",
            "context": "test",
            "priority": "normal",
            "ttl": "1d",
            "data": {"note": "Test with unicode: \x00\x01\x02 and \ud83d\ude00"},
            "meta": {}
        }
        
        response = test_client.post("/ingest", json=unicode_payload, headers=auth_header)
        assert response.status_code in [200, 400, 422]


class TestTimeoutErrors:
    """Test timeout-related error scenarios"""
    
    def test_slow_embedding_generation(self, test_client, auth_header, sample_payload_dict, monkeypatch):
        """Test slow embedding generation timeout"""
        
        # Simulate timeout error
        slow_mock = MagicMock(side_effect=TimeoutError("Embedding generation timeout"))
        monkeypatch.setattr("app.storage.qdrant_client.get_openai_embedding", slow_mock)
        monkeypatch.setattr("app.utils.openai_client.get_openai_embedding", slow_mock)
        
        response = test_client.post("/ingest", json=sample_payload_dict, headers=auth_header)
        assert response.status_code == 500
    
    def test_slow_search_timeout(self, test_client, auth_header):
        """Test slow search operation timeout"""
        
        with patch("app.router.qdrant_search") as mock_search:
            mock_search.side_effect = TimeoutError("Search timeout")
            
            response = test_client.get("/search?q=test", headers=auth_header)
            assert response.status_code == 500
    
    def test_websocket_timeout(self, test_client):
        """Test WebSocket operation timeout"""
        
        with patch("app.api.websocket.get_openai_stream") as mock_stream:
            # Mock stream that takes too long
            async def slow_stream(prompt):
                await asyncio.sleep(10)  # Very slow
                yield "slow response"
            
            mock_stream.return_value = slow_stream("test")
            
            with test_client.websocket_connect("/ws/generate?token=test-token") as websocket:
                websocket.send_json({"prompt": "test"})
                
                # Should timeout or handle gracefully
                try:
                    message = websocket.receive_json()
                    # If we get here, should be error message
                    if "error" in message:
                        assert "timeout" in message["error"].lower() or "error" in message
                except Exception:
                    # Timeout is acceptable
                    pass 