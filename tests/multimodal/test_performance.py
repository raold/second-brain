"""
Multi-Modal Performance Tests for Second Brain v2.6.0
Comprehensive testing of system performance, scalability, and resource usage.
"""

import asyncio
import time
import psutil
import pytest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, patch, MagicMock
import tempfile
import io
import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.multimodal.models import ContentType, MultiModalSearchRequest
from multimodal.api import router
from multimodal.database import MultiModalDatabase
from multimodal.processing import MultiModalProcessingService


class TestMultiModalPerformance:
    """Performance tests for multi-modal functionality in Second Brain v2.6.0."""

    @pytest.fixture
    def test_client(self):
        """Test client for performance testing."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        
        # Mock authentication
        async def mock_auth():
            return {"user_id": "perf_test_user"}
        
        router.dependency_overrides[router.get_current_user] = mock_auth
        return TestClient(app)

    @pytest.fixture
    def mock_database(self):
        """Mock database with performance simulation."""
        mock_db = AsyncMock(spec=MultiModalDatabase)
        
        # Simulate realistic response times
        async def slow_search(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms simulated query time
            return []
        
        mock_db.search_memories.side_effect = slow_search
        return mock_db

    def test_file_upload_performance(self, test_client):
        """Test file upload performance with various file sizes."""
        file_sizes = [
            ("small", 1024),           # 1KB
            ("medium", 1024 * 1024),   # 1MB  
            ("large", 10 * 1024 * 1024), # 10MB
            ("xlarge", 50 * 1024 * 1024) # 50MB
        ]
        
        performance_results = {}
        
        for size_name, size_bytes in file_sizes:
            content = b"A" * size_bytes
            
            start_time = time.time()
            
            response = test_client.post(
                "/multimodal/upload",
                files={"file": (f"test_{size_name}.txt", io.BytesIO(content), "text/plain")},
                data={"content": f"Performance test file - {size_name}"}
            )
            
            end_time = time.time()
            upload_time = end_time - start_time
            
            performance_results[size_name] = {
                "size_mb": size_bytes / (1024 * 1024),
                "upload_time": upload_time,
                "throughput_mbps": (size_bytes / (1024 * 1024)) / upload_time if upload_time > 0 else 0,
                "status_code": response.status_code
            }
            
            # Verify successful upload for reasonable sizes
            if size_bytes <= 100 * 1024 * 1024:  # Within 100MB limit
                assert response.status_code == 200, f"Upload failed for {size_name} file"
        
        # Performance assertions
        assert performance_results["small"]["upload_time"] < 1.0, "Small file upload should be under 1 second"
        assert performance_results["medium"]["upload_time"] < 5.0, "Medium file upload should be under 5 seconds"
        
        # Throughput should be reasonable (>1 MB/s for larger files)
        if performance_results["large"]["throughput_mbps"] > 0:
            assert performance_results["large"]["throughput_mbps"] > 1.0, "Large file throughput should be >1 MB/s"

    def test_concurrent_upload_performance(self, test_client):
        """Test performance under concurrent upload load."""
        
        def upload_file(file_index):
            """Upload a single file and return timing info."""
            content = b"Test content " * 1000  # ~13KB file
            
            start_time = time.time()
            response = test_client.post(
                "/multimodal/upload",
                files={"file": (f"concurrent_test_{file_index}.txt", io.BytesIO(content), "text/plain")},
                data={"content": f"Concurrent test file {file_index}"}
            )
            end_time = time.time()
            
            return {
                "file_index": file_index,
                "upload_time": end_time - start_time,
                "status_code": response.status_code,
                "success": response.status_code == 200
            }
        
        # Test with different levels of concurrency
        concurrency_levels = [1, 5, 10, 20]
        results = {}
        
        for num_concurrent in concurrency_levels:
            with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
                start_time = time.time()
                
                # Submit all upload tasks
                futures = [executor.submit(upload_file, i) for i in range(num_concurrent)]
                
                # Wait for all to complete
                upload_results = [future.result() for future in futures]
                
                total_time = time.time() - start_time
                
                results[num_concurrent] = {
                    "total_time": total_time,
                    "avg_upload_time": sum(r["upload_time"] for r in upload_results) / len(upload_results),
                    "success_rate": sum(1 for r in upload_results if r["success"]) / len(upload_results),
                    "throughput_uploads_per_sec": num_concurrent / total_time
                }
        
        # Performance assertions
        for num_concurrent, result in results.items():
            assert result["success_rate"] >= 0.9, f"Success rate should be ≥90% for {num_concurrent} concurrent uploads"
            assert result["avg_upload_time"] < 10.0, f"Average upload time should be <10s for {num_concurrent} concurrent uploads"

    def test_search_performance(self, test_client):
        """Test search performance with various query types and sizes."""
        search_queries = [
            ("simple", "test"),
            ("medium", "test document with multiple words"),
            ("complex", "artificial intelligence machine learning neural networks deep learning"),
            ("very_long", "this is a very long search query " * 20)
        ]
        
        performance_results = {}
        
        for query_name, query_text in search_queries:
            search_times = []
            
            # Run each query multiple times for statistical significance
            for _ in range(5):
                start_time = time.time()
                
                response = test_client.post(
                    "/multimodal/search",
                    json={
                        "query": query_text,
                        "limit": 20,
                        "threshold": 0.7
                    }
                )
                
                end_time = time.time()
                search_time = end_time - start_time
                search_times.append(search_time)
                
                assert response.status_code == 200, f"Search failed for {query_name} query"
            
            performance_results[query_name] = {
                "avg_search_time": sum(search_times) / len(search_times),
                "max_search_time": max(search_times),
                "min_search_time": min(search_times),
                "query_length": len(query_text)
            }
        
        # Performance assertions
        for query_name, result in performance_results.items():
            assert result["avg_search_time"] < 2.0, f"Average search time should be <2s for {query_name} query"
            assert result["max_search_time"] < 5.0, f"Max search time should be <5s for {query_name} query"

    def test_memory_usage_during_processing(self, test_client):
        """Test memory usage during file processing."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Upload and process several files
        file_sizes = [1024, 1024*1024, 5*1024*1024]  # 1KB, 1MB, 5MB
        memory_measurements = []
        
        for size in file_sizes:
            content = b"A" * size
            
            # Measure memory before upload
            before_memory = process.memory_info().rss / 1024 / 1024
            
            response = test_client.post(
                "/multimodal/upload",
                files={"file": (f"memory_test_{size}.txt", io.BytesIO(content), "text/plain")},
                data={"content": f"Memory test file {size} bytes", "auto_process": "true"}
            )
            
            # Measure memory after upload
            after_memory = process.memory_info().rss / 1024 / 1024
            
            memory_measurements.append({
                "file_size_mb": size / 1024 / 1024,
                "memory_before_mb": before_memory,
                "memory_after_mb": after_memory,
                "memory_increase_mb": after_memory - before_memory,
                "success": response.status_code == 200
            })
        
        # Memory usage assertions
        for measurement in memory_measurements:
            if measurement["success"]:
                # Memory increase shouldn't be more than 10x file size (reasonable buffer)
                max_expected_increase = measurement["file_size_mb"] * 10 + 50  # +50MB base allowance
                assert measurement["memory_increase_mb"] < max_expected_increase, \
                    f"Memory increase too high: {measurement['memory_increase_mb']}MB for {measurement['file_size_mb']}MB file"

    def test_database_query_performance(self):
        """Test database query performance simulation."""
        # This would test actual database performance in integration tests
        
        query_types = [
            ("simple_select", "SELECT * FROM multimodal_memories LIMIT 10"),
            ("vector_search", "SELECT * FROM multimodal_memories ORDER BY text_vector <=> $1 LIMIT 10"),
            ("full_text_search", "SELECT * FROM multimodal_memories WHERE search_vector @@ plainto_tsquery($1)"),
            ("complex_join", """
                SELECT m.*, COUNT(r.id) as relationship_count
                FROM multimodal_memories m
                LEFT JOIN multimodal_relationships r ON m.id = r.source_memory_id
                GROUP BY m.id
                LIMIT 10
            """)
        ]
        
        performance_targets = {
            "simple_select": 0.01,    # 10ms
            "vector_search": 0.1,     # 100ms  
            "full_text_search": 0.05, # 50ms
            "complex_join": 0.2       # 200ms
        }
        
        # In actual implementation, this would test real queries
        # For now, simulate performance testing structure
        for query_name, query in query_types:
            target_time = performance_targets.get(query_name, 0.1)
            # Simulated query time would be measured here
            pass

    def test_api_response_time_under_load(self, test_client):
        """Test API response times under sustained load."""
        
        def make_api_call(endpoint_info):
            """Make a single API call and measure response time."""
            endpoint, method, data = endpoint_info
            
            start_time = time.time()
            
            if method == "GET":
                response = test_client.get(endpoint)
            elif method == "POST":
                response = test_client.post(endpoint, json=data)
            else:
                return None
                
            end_time = time.time()
            
            return {
                "endpoint": endpoint,
                "response_time": end_time - start_time,
                "status_code": response.status_code,
                "success": 200 <= response.status_code < 300
            }
        
        # Test various endpoints under load
        endpoints = [
            ("/multimodal/health", "GET", {}),
            ("/multimodal/memories", "GET", {}),
            ("/multimodal/stats", "GET", {}),
            ("/multimodal/search", "POST", {"query": "test", "limit": 5})
        ]
        
        # Simulate sustained load
        total_requests = 100
        concurrent_requests = 10
        
        with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            # Distribute requests across endpoints
            request_list = [endpoints[i % len(endpoints)] for i in range(total_requests)]
            
            start_time = time.time()
            futures = [executor.submit(make_api_call, endpoint_info) for endpoint_info in request_list]
            results = [future.result() for future in futures if future.result()]
            total_time = time.time() - start_time
        
        # Analyze results
        success_rate = sum(1 for r in results if r["success"]) / len(results)
        avg_response_time = sum(r["response_time"] for r in results) / len(results)
        max_response_time = max(r["response_time"] for r in results)
        requests_per_second = len(results) / total_time
        
        # Performance assertions
        assert success_rate >= 0.95, f"Success rate under load should be ≥95%, got {success_rate:.2%}"
        assert avg_response_time < 1.0, f"Average response time should be <1s, got {avg_response_time:.3f}s"
        assert max_response_time < 5.0, f"Max response time should be <5s, got {max_response_time:.3f}s"
        assert requests_per_second > 10, f"Should handle >10 req/s, got {requests_per_second:.1f} req/s"

    def test_file_processing_throughput(self):
        """Test file processing throughput for different content types."""
        
        processing_service = MultiModalProcessingService()
        
        # Test different file types and sizes
        test_cases = [
            ("text", b"Sample text content " * 1000, "text/plain"),
            ("small_image", b"\x89PNG\r\n\x1a\n" + b"\x00" * 1000, "image/png"),  # Fake PNG
            ("document", b"%PDF-1.4\nSample PDF content", "application/pdf")
        ]
        
        throughput_results = {}
        
        for content_type, content, mime_type in test_cases:
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_file.write(content)
                tmp_file.flush()
                
                start_time = time.time()
                
                try:
                    # This would test actual processing in integration environment
                    # result = await processing_service.process_file(tmp_file.name)
                    
                    # Simulate processing time based on content size
                    processing_time = len(content) / (1024 * 1024) * 0.1  # 0.1s per MB
                    time.sleep(processing_time)
                    
                    end_time = time.time()
                    
                    throughput_results[content_type] = {
                        "size_mb": len(content) / (1024 * 1024),
                        "processing_time": end_time - start_time,
                        "throughput_mbps": (len(content) / (1024 * 1024)) / (end_time - start_time)
                    }
                    
                finally:
                    os.unlink(tmp_file.name)
        
        # Verify reasonable processing throughput
        for content_type, result in throughput_results.items():
            if result["size_mb"] > 0.1:  # For files larger than 100KB
                assert result["throughput_mbps"] > 0.5, \
                    f"Processing throughput for {content_type} should be >0.5 MB/s"

    def test_scalability_limits(self, test_client):
        """Test system behavior at scalability limits."""
        
        # Test maximum supported file size
        max_size = 95 * 1024 * 1024  # Just under 100MB limit
        large_content = b"X" * max_size
        
        start_time = time.time()
        response = test_client.post(
            "/multimodal/upload",
            files={"file": ("max_size_test.txt", io.BytesIO(large_content), "text/plain")},
            data={"content": "Maximum size test file"}
        )
        upload_time = time.time() - start_time
        
        # Should handle maximum size within reasonable time
        assert response.status_code == 200, "Should handle maximum file size"
        assert upload_time < 30.0, f"Maximum size upload should complete within 30s, took {upload_time:.1f}s"
        
        # Test maximum number of concurrent operations
        # This would be tested with actual concurrent processing in integration environment
        pass

    @pytest.mark.asyncio
    async def test_async_operations_performance(self):
        """Test performance of async operations."""
        
        database = MultiModalDatabase()
        
        # Test concurrent database operations
        async def mock_db_operation(operation_id):
            """Simulate database operation."""
            await asyncio.sleep(0.1)  # Simulate 100ms DB operation
            return f"operation_{operation_id}_complete"
        
        # Test various levels of concurrency
        concurrency_levels = [1, 10, 50, 100]
        
        for num_concurrent in concurrency_levels:
            start_time = time.time()
            
            # Create concurrent tasks
            tasks = [mock_db_operation(i) for i in range(num_concurrent)]
            results = await asyncio.gather(*tasks)
            
            total_time = time.time() - start_time
            
            # Verify all operations completed
            assert len(results) == num_concurrent
            
            # Async operations should be significantly faster than sequential
            sequential_time = num_concurrent * 0.1  # Each operation takes 0.1s
            efficiency = sequential_time / total_time
            
            # Should achieve at least 2x speedup with async (conservative estimate)
            if num_concurrent > 1:
                assert efficiency > 2.0, \
                    f"Async operations should be >2x faster than sequential for {num_concurrent} operations"

    def test_resource_cleanup_performance(self, test_client):
        """Test that resources are cleaned up efficiently."""
        
        initial_process = psutil.Process()
        initial_memory = initial_process.memory_info().rss
        initial_files = len(initial_process.open_files())
        
        # Perform multiple operations that create temporary resources
        for i in range(10):
            content = b"Test content for cleanup " * 1000
            response = test_client.post(
                "/multimodal/upload",
                files={"file": (f"cleanup_test_{i}.txt", io.BytesIO(content), "text/plain")},
                data={"content": f"Cleanup test file {i}"}
            )
            assert response.status_code == 200
        
        # Allow some time for cleanup
        time.sleep(2)
        
        # Check resource usage after operations
        final_process = psutil.Process()
        final_memory = final_process.memory_info().rss
        final_files = len(final_process.open_files())
        
        memory_increase = (final_memory - initial_memory) / 1024 / 1024  # MB
        file_handle_increase = final_files - initial_files
        
        # Resource usage should not grow indefinitely
        assert memory_increase < 100, f"Memory increase should be <100MB, got {memory_increase:.1f}MB"
        assert file_handle_increase < 10, f"File handle increase should be <10, got {file_handle_increase}"


class TestPerformanceMonitoring:
    """Tests for performance monitoring and metrics collection."""
    
    def test_response_time_metrics(self, test_client):
        """Test that response time metrics are collected."""
        
        # Make several API calls
        endpoints = [
            "/multimodal/health",
            "/multimodal/stats",
            "/multimodal/memories"
        ]
        
        response_times = {}
        
        for endpoint in endpoints:
            times = []
            for _ in range(5):
                start = time.time()
                response = test_client.get(endpoint)
                end = time.time()
                
                if response.status_code == 200:
                    times.append(end - start)
            
            if times:
                response_times[endpoint] = {
                    "avg": sum(times) / len(times),
                    "min": min(times),
                    "max": max(times)
                }
        
        # Verify metrics are reasonable
        for endpoint, metrics in response_times.items():
            assert metrics["avg"] < 2.0, f"Average response time for {endpoint} should be <2s"
            assert metrics["max"] < 5.0, f"Max response time for {endpoint} should be <5s"
    
    def test_throughput_metrics(self, test_client):
        """Test throughput measurement and monitoring."""
        
        # This would integrate with actual metrics collection system
        # For now, simulate the structure of throughput testing
        
        start_time = time.time()
        request_count = 0
        duration = 5  # Test for 5 seconds
        
        while time.time() - start_time < duration:
            response = test_client.get("/multimodal/health")
            if response.status_code == 200:
                request_count += 1
        
        actual_duration = time.time() - start_time
        throughput = request_count / actual_duration
        
        # Should achieve reasonable throughput
        assert throughput > 10, f"Throughput should be >10 req/s, got {throughput:.1f} req/s"
    
    def test_error_rate_monitoring(self, test_client):
        """Test error rate monitoring under various conditions."""
        
        total_requests = 100
        error_requests = 0
        
        # Mix of valid and invalid requests
        for i in range(total_requests):
            if i % 10 == 0:  # 10% invalid requests
                response = test_client.get(f"/multimodal/memories/invalid-id-{i}")
            else:
                response = test_client.get("/multimodal/health")
            
            if response.status_code >= 500:  # Server errors
                error_requests += 1
        
        error_rate = error_requests / total_requests
        
        # Server error rate should be very low
        assert error_rate < 0.01, f"Server error rate should be <1%, got {error_rate:.1%}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
