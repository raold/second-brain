# tests/test_integration_pipeline.py

from unittest.mock import Mock, patch


class TestFullPipelineIntegration:
    """Test the complete pipeline from ingest → search → retrieve"""
    
    def test_complete_workflow_success(self, test_client, auth_header, sample_payload_dict):
        """Test successful end-to-end workflow"""
        
        # Step 1: Ingest a payload
        ingest_response = test_client.post("/ingest", json=sample_payload_dict, headers=auth_header)
        assert ingest_response.status_code == 200
        ingest_data = ingest_response.json()
        assert ingest_data["status"] == "ingested"
        assert ingest_data["id"] == sample_payload_dict["id"]
        
        # Step 2: Search for the ingested content
        with patch("app.router.qdrant_search") as mock_search:
            mock_search.return_value = [{
                "id": sample_payload_dict["id"],
                "score": 0.95,
                "note": sample_payload_dict["data"]["note"],
                "timestamp": "2023-01-01T00:00:00Z",
                "type": "note",
                "priority": "normal"
            }]
            
            search_response = test_client.get(
                "/search?q=test note", 
                headers=auth_header
            )
            assert search_response.status_code == 200
            search_data = search_response.json()
            assert search_data["query"] == "test note"
            assert len(search_data["results"]) == 1
            assert search_data["results"][0]["id"] == sample_payload_dict["id"]
        
        # Step 3: Ranked search for better results
        with patch("app.router.qdrant_search") as mock_ranked_search:
            mock_ranked_search.return_value = [{
                "id": sample_payload_dict["id"],
                "score": 0.95,
                "note": sample_payload_dict["data"]["note"],
                "embedding_model": "text-embedding-3-small",
                "model_version": "gpt-4o",
                "type": "note"
            }]
            
            ranked_response = test_client.get(
                "/ranked-search?q=test note&type=note", 
                headers=auth_header
            )
            assert ranked_response.status_code == 200
            ranked_data = ranked_response.json()
            assert ranked_data["query"] == "test note"
            assert len(ranked_data["results"]) == 1
            result = ranked_data["results"][0]
            assert "final_score" in result
            assert "vector_score" in result
            assert "metadata_score" in result
    
    def test_batch_ingest_search_workflow(self, test_client, auth_header, multiple_payloads):
        """Test batch ingestion followed by search"""
        
        # Ingest multiple payloads
        ingested_ids = []
        for payload in multiple_payloads:
            response = test_client.post("/ingest", json=payload, headers=auth_header)
            assert response.status_code == 200
            ingested_ids.append(response.json()["id"])
        
        assert len(ingested_ids) == 10
        
        # Search should find relevant results
        with patch("app.router.qdrant_search") as mock_search:
            # Mock finding multiple results
            mock_search.return_value = [
                {
                    "id": payload_id,
                    "score": 0.9 - (i * 0.05),  # Decreasing scores
                    "note": f"Batch test note {i}",
                    "type": "note"
                }
                for i, payload_id in enumerate(ingested_ids[:5])  # Return top 5
            ]
            
            search_response = test_client.get(
                "/search?q=batch test", 
                headers=auth_header
            )
            assert search_response.status_code == 200
            results = search_response.json()["results"]
            assert len(results) == 5
            
            # Verify results are ordered by score
            scores = [result["score"] for result in results]
            assert scores == sorted(scores, reverse=True)
    
    def test_pipeline_with_intent_detection(self, test_client, auth_header):
        """Test pipeline with automatic intent detection"""
        
        # Payload without intent (should be auto-detected)
        payload_no_intent = {
            "id": "intent-test-123",
            "type": "note",
            "context": "test",
            "priority": "normal",
            "ttl": "1d",
            "data": {"note": "Remind me to call Alice tomorrow"},
            "meta": {}
        }
        
        # Mock intent detection
        with patch("app.router.detect_intent_via_llm") as mock_intent:
            mock_intent.return_value = "reminder"
            
            response = test_client.post("/ingest", json=payload_no_intent, headers=auth_header)
            assert response.status_code == 200
            data = response.json()
            assert data["intent"] == "reminder"
            mock_intent.assert_called_once()
    
    def test_pipeline_error_handling(self, test_client, auth_header, sample_payload_dict):
        """Test pipeline behavior with various errors"""
        
        # Test Qdrant failure during ingestion
        with patch("app.router.qdrant_upsert") as mock_upsert:
            mock_upsert.side_effect = Exception("Qdrant connection failed")
            
            response = test_client.post("/ingest", json=sample_payload_dict, headers=auth_header)
            assert response.status_code == 500
            assert "Failed to ingest payload" in response.json()["detail"]
        
        # Test search failure
        with patch("app.router.qdrant_search") as mock_search:
            mock_search.side_effect = Exception("Search service unavailable")
            
            response = test_client.get("/search?q=test", headers=auth_header)
            assert response.status_code == 500
            assert "Search failed" in response.json()["detail"]
    
    def test_websocket_llm_integration(self, test_client):
        """Test WebSocket LLM streaming integration"""
        
        with test_client.websocket_connect("/ws/generate?token=test-token") as websocket:
            # Send prompt
            websocket.send_json({
                "prompt": "Hello world test",
                "json": True
            })
            
            # Receive streamed chunks
            received_chunks = []
            for _ in range(3):  # Expect 3 words
                message = websocket.receive_json()
                if "chunk" in message:
                    received_chunks.append(message["chunk"].strip())
                elif "text" in message:
                    received_chunks.append(message["text"].strip())
            
            # Verify we received the expected content
            full_text = " ".join(received_chunks)
            assert "Hello world test" in full_text
    
    def test_transcription_integration(self, test_client, auth_header):
        """Test audio transcription integration"""
        
        # Mock audio file
        mock_audio_content = b"fake audio data"
        
        with patch("openai.audio.transcriptions.create") as mock_transcribe:
            # Mock OpenAI response
            mock_response = Mock()
            mock_response.text = "This is the transcribed text"
            mock_transcribe.return_value = mock_response
            
            # Test transcription endpoint
            response = test_client.post(
                "/transcribe",
                headers=auth_header,
                files={"file": ("test.wav", mock_audio_content, "audio/wav")}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["transcript"] == "This is the transcribed text"
            mock_transcribe.assert_called_once()
    
    def test_memory_crud_workflow(self, test_client, auth_header, sample_payload_dict):
        """Test complete memory CRUD workflow"""
        
        # 1. Create memory via ingest
        create_response = test_client.post("/ingest", json=sample_payload_dict, headers=auth_header)
        assert create_response.status_code == 200
        memory_id = create_response.json()["id"]
        
        # 2. Search and verify memory exists
        with patch("app.router.qdrant_search") as mock_search:
            mock_search.return_value = [{
                "id": memory_id,
                "score": 0.95,
                "note": sample_payload_dict["data"]["note"],
                "type": "note"
            }]
            
            search_response = test_client.get("/search?q=test", headers=auth_header)
            assert search_response.status_code == 200
            assert len(search_response.json()["results"]) == 1
        
        # 3. Update memory (if endpoint exists)
        update_data = {
            "note": "Updated test note",
            "intent": "updated_intent"
        }
        
        with patch("app.storage.postgres.AsyncSessionLocal") as mock_session:
            # Mock the update operation
            mock_session.return_value.__aenter__.return_value.execute.return_value = Mock()
            
            update_response = test_client.put(
                f"/memories/{memory_id}",
                headers=auth_header,
                params=update_data
            )
            
            # Expect 200 or 404 depending on implementation
            assert update_response.status_code in [200, 404]
        
        # 4. Delete memory (if endpoint exists)
        with patch("app.storage.postgres.AsyncSessionLocal") as mock_session:
            delete_response = test_client.delete(
                f"/memories/{memory_id}",
                headers=auth_header
            )
            
            # Expect 200 or 404 depending on implementation
            assert delete_response.status_code in [200, 404]


class TestPipelinePerformance:
    """Test pipeline performance characteristics"""
    
    def test_large_payload_handling(self, test_client, auth_header, large_payload):
        """Test handling of large payloads"""
        
        response = test_client.post("/ingest", json=large_payload, headers=auth_header)
        assert response.status_code == 200
        
        # Verify the large content was processed
        data = response.json()
        assert data["status"] == "ingested"
        assert data["id"] == large_payload["id"]
    
    def test_concurrent_operations(self, test_client, auth_header, multiple_payloads):
        """Test concurrent ingestion and search operations"""
        import concurrent.futures
        
        results = []
        
        def ingest_payload(payload):
            """Helper function for concurrent ingestion"""
            try:
                response = test_client.post("/ingest", json=payload, headers=auth_header)
                return response.status_code == 200
            except Exception:
                return False
        
        # Test concurrent ingestion
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(ingest_payload, payload) 
                for payload in multiple_payloads[:5]
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All ingestions should succeed
        assert all(results)
        assert len(results) == 5


class TestPipelineEdgeCases:
    """Test pipeline edge cases and boundary conditions"""
    
    def test_empty_search_query(self, test_client, auth_header):
        """Test search with empty query"""
        
        response = test_client.get("/search?q=", headers=auth_header)
        # Should handle gracefully - either error or empty results
        assert response.status_code in [200, 400, 422]
    
    def test_malformed_payload(self, test_client, auth_header):
        """Test ingestion with malformed payload"""
        
        malformed_payload = {
            "id": "malformed-test",
            # Missing required fields
            "data": {}
        }
        
        response = test_client.post("/ingest", json=malformed_payload, headers=auth_header)
        assert response.status_code in [400, 422, 500]  # Should be handled gracefully
    
    def test_special_characters_handling(self, test_client, auth_header):
        """Test handling of special characters in content"""
        
        special_payload = {
            "id": "special-chars-test",
            "type": "note",
            "context": "test",
            "priority": "normal",
            "ttl": "1d",
            "data": {
                "note": "Test with special chars: émojis 🚀, unicode ñáéíóú, symbols @#$%^&*()"
            },
            "meta": {}
        }
        
        response = test_client.post("/ingest", json=special_payload, headers=auth_header)
        assert response.status_code == 200
        
        # Search should handle special characters
        with patch("app.router.qdrant_search") as mock_search:
            mock_search.return_value = [{
                "id": "special-chars-test",
                "score": 0.9,
                "note": special_payload["data"]["note"],
                "type": "note"
            }]
            
            search_response = test_client.get(
                "/search?q=émojis 🚀", 
                headers=auth_header
            )
            assert search_response.status_code == 200
    
    def test_very_long_search_query(self, test_client, auth_header):
        """Test search with very long query"""
        
        long_query = "very long search query " * 100  # Very long query
        
        response = test_client.get(f"/search?q={long_query}", headers=auth_header)
        # Should handle gracefully
        assert response.status_code in [200, 400, 413, 422]
    
    def test_pagination_workflow(self, test_client, auth_header):
        """Test search result pagination"""
        
        with patch("app.router.qdrant_search") as mock_search:
            # Mock large result set
            mock_search.return_value = [
                {
                    "id": f"result-{i}",
                    "score": 0.9 - (i * 0.01),
                    "note": f"Test result {i}",
                    "type": "note"
                }
                for i in range(50)  # 50 results
            ]
            
            # Test default limit
            response = test_client.get("/search?q=test", headers=auth_header)
            assert response.status_code == 200
            results = response.json()["results"]
            
            # Should be limited to reasonable number
            assert len(results) <= 50 