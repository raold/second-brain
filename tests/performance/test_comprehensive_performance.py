"""
Performance tests for V2 API, StructuredDataExtractor, and WebSocket functionality
Tests performance under load, memory usage, and response times
"""

import asyncio
import gc
import json
import psutil
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.services.structured_data_extractor import StructuredDataExtractor
from app.services.synthesis.websocket_service import get_websocket_service


class PerformanceMonitor:
    """Utility class for monitoring performance metrics"""
    
    def __init__(self):
        self.start_time = None
        self.start_memory = None
        self.start_cpu = None
        
    def start(self):
        """Start performance monitoring"""
        self.start_time = time.time()
        self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.start_cpu = psutil.cpu_percent()
        
    def stop(self):
        """Stop performance monitoring and return metrics"""
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        end_cpu = psutil.cpu_percent()
        
        return {
            "duration_seconds": end_time - self.start_time,
            "memory_delta_mb": end_memory - self.start_memory,
            "cpu_usage_percent": end_cpu,
            "peak_memory_mb": end_memory
        }


@pytest.mark.performance
class TestV2APIPerformance:
    """Performance tests for V2 API endpoints"""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_response_time(self, client: AsyncClient, api_key: str):
        """Test metrics endpoint response time under normal load"""
        monitor = PerformanceMonitor()
        
        # Warm up
        await client.get("/api/v2/metrics", params={"api_key": api_key})
        
        # Measure performance
        monitor.start()
        
        # Make 10 sequential requests
        response_times = []
        for _ in range(10):
            start = time.time()
            response = await client.get("/api/v2/metrics", params={"api_key": api_key})
            end = time.time()
            
            assert response.status_code == 200
            response_times.append(end - start)
        
        metrics = monitor.stop()
        
        # Performance assertions
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        assert avg_response_time < 1.0  # Average under 1 second
        assert max_response_time < 2.0  # Max under 2 seconds
        assert metrics["duration_seconds"] < 15.0  # Total time under 15 seconds
        
        print(f"Metrics endpoint - Avg: {avg_response_time:.3f}s, Max: {max_response_time:.3f}s")

    @pytest.mark.asyncio
    async def test_detailed_metrics_performance(self, client: AsyncClient, api_key: str):
        """Test detailed metrics endpoint performance"""
        monitor = PerformanceMonitor()
        monitor.start()
        
        response_times = []
        for _ in range(5):  # Fewer requests due to complexity
            start = time.time()
            response = await client.get("/api/v2/metrics/detailed", params={"api_key": api_key})
            end = time.time()
            
            assert response.status_code == 200
            response_times.append(end - start)
        
        metrics = monitor.stop()
        
        # Performance assertions for detailed metrics
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        assert avg_response_time < 3.0  # Average under 3 seconds (more complex)
        assert max_response_time < 5.0  # Max under 5 seconds
        assert metrics["memory_delta_mb"] < 50  # Memory usage under 50MB
        
        print(f"Detailed metrics - Avg: {avg_response_time:.3f}s, Max: {max_response_time:.3f}s")

    @pytest.mark.asyncio
    async def test_concurrent_api_requests(self, client: AsyncClient, api_key: str):
        """Test API performance under concurrent load"""
        monitor = PerformanceMonitor()
        
        async def make_request(request_id):
            start_time = time.time()
            response = await client.get("/api/v2/metrics", params={"api_key": api_key})
            end_time = time.time()
            
            return {
                "request_id": request_id,
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "success": response.status_code == 200
            }
        
        # Test with 20 concurrent requests
        monitor.start()
        tasks = [make_request(i) for i in range(20)]
        results = await asyncio.gather(*tasks)
        metrics = monitor.stop()
        
        # Analyze results
        successful_requests = [r for r in results if r["success"]]
        response_times = [r["response_time"] for r in successful_requests]
        
        # Performance assertions
        success_rate = len(successful_requests) / len(results)
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)] if response_times else 0
        
        assert success_rate >= 0.95  # 95% success rate
        assert avg_response_time < 2.0  # Average under 2 seconds
        assert p95_response_time < 3.0  # 95th percentile under 3 seconds
        assert metrics["duration_seconds"] < 10.0  # Total time under 10 seconds
        
        print(f"Concurrent requests - Success rate: {success_rate:.2%}, Avg: {avg_response_time:.3f}s, P95: {p95_response_time:.3f}s")

    @pytest.mark.asyncio
    async def test_memory_ingestion_performance(self, client: AsyncClient, api_key: str):
        """Test memory ingestion performance with various content sizes"""
        monitor = PerformanceMonitor()
        
        # Test with different content sizes
        content_sizes = [
            ("small", "Small content" * 10),  # ~130 chars
            ("medium", "Medium content " * 100),  # ~1,600 chars
            ("large", "Large content " * 1000),  # ~16,000 chars
            ("xlarge", "Extra large content " * 5000)  # ~100,000 chars
        ]
        
        results = {}
        
        for size_name, content in content_sizes:
            monitor.start()
            
            response = await client.post(
                "/api/v2/memories/ingest",
                params={
                    "content": content,
                    "memory_type": "performance_test",
                    "tags": ["test", size_name],
                    "api_key": api_key
                }
            )
            
            metrics = monitor.stop()
            
            results[size_name] = {
                "success": response.status_code == 200,
                "content_length": len(content),
                "response_time": metrics["duration_seconds"],
                "memory_delta": metrics["memory_delta_mb"]
            }
            
            # Performance assertions based on content size
            if size_name == "small":
                assert metrics["duration_seconds"] < 1.0
            elif size_name == "medium":
                assert metrics["duration_seconds"] < 2.0
            elif size_name == "large":
                assert metrics["duration_seconds"] < 5.0
            else:  # xlarge
                assert metrics["duration_seconds"] < 10.0
            
            assert metrics["memory_delta_mb"] < 100  # Memory usage should be reasonable
        
        # Verify performance scales reasonably with content size
        small_time = results["small"]["response_time"]
        large_time = results["large"]["response_time"]
        
        # Large content shouldn't take more than 10x longer than small content
        assert large_time / small_time < 10
        
        print("Memory ingestion performance:")
        for size_name, result in results.items():
            print(f"  {size_name}: {result['response_time']:.3f}s, {result['content_length']} chars")

    @pytest.mark.asyncio
    async def test_api_throughput(self, client: AsyncClient, api_key: str):
        """Test API throughput - requests per second"""
        duration_seconds = 10
        
        start_time = time.time()
        request_count = 0
        errors = 0
        
        while time.time() - start_time < duration_seconds:
            try:
                response = await client.get("/api/v2/health", params={"api_key": api_key})
                if response.status_code == 200:
                    request_count += 1
                else:
                    errors += 1
            except Exception:
                errors += 1
            
            # Small delay to prevent overwhelming the system
            await asyncio.sleep(0.01)
        
        actual_duration = time.time() - start_time
        throughput = request_count / actual_duration
        error_rate = errors / (request_count + errors) if (request_count + errors) > 0 else 0
        
        # Performance assertions
        assert throughput > 10  # At least 10 requests per second
        assert error_rate < 0.05  # Less than 5% error rate
        
        print(f"API throughput: {throughput:.1f} RPS, Error rate: {error_rate:.2%}")


@pytest.mark.performance
class TestStructuredDataExtractorPerformance:
    """Performance tests for StructuredDataExtractor"""

    def setup_method(self):
        """Set up test fixtures"""
        self.extractor = StructuredDataExtractor(use_ai=False)

    def test_extraction_performance_by_content_size(self):
        """Test extraction performance with different content sizes"""
        monitor = PerformanceMonitor()
        
        # Create content of different sizes
        base_content = """
        Name: Performance Test
        Status: Running
        
        Tasks:
        - Task 1
        - Task 2
        - Task 3
        
        | Metric | Value |
        |--------|-------|
        | Speed  | Fast  |
        | Memory | Low   |
        
        ```python
        def test():
            return True
        ```
        """
        
        content_multipliers = [1, 10, 50, 100, 500]  # Scale content
        results = {}
        
        for multiplier in content_multipliers:
            content = base_content * multiplier
            content_size = len(content)
            
            monitor.start()
            result = self.extractor.extract_structured_data(content)
            metrics = monitor.stop()
            
            results[multiplier] = {
                "content_size": content_size,
                "duration": metrics["duration_seconds"],
                "memory_delta": metrics["memory_delta_mb"],
                "extracted_elements": (
                    len(result.key_value_pairs) +
                    len(result.lists) +
                    len(result.tables) +
                    len(result.code_snippets)
                )
            }
            
            # Performance assertions
            if multiplier <= 10:
                assert metrics["duration_seconds"] < 1.0
            elif multiplier <= 100:
                assert metrics["duration_seconds"] < 5.0
            else:  # multiplier > 100
                assert metrics["duration_seconds"] < 15.0
            
            assert metrics["memory_delta_mb"] < 50  # Keep memory usage reasonable
        
        # Analyze scaling behavior
        print("Extraction performance by content size:")
        for mult, result in results.items():
            size_kb = result["content_size"] / 1024
            print(f"  {mult}x ({size_kb:.1f}KB): {result['duration']:.3f}s, {result['extracted_elements']} elements")

    def test_extraction_performance_by_complexity(self):
        """Test extraction performance with different content complexity"""
        monitor = PerformanceMonitor()
        
        test_cases = {
            "simple": """
            Name: Simple Document
            Value: 42
            """,
            
            "medium": """
            # Medium Complexity Document
            
            Author: John Doe
            Date: 2024-01-15
            Version: 1.0
            
            ## Content
            - Item 1
            - Item 2
            - Item 3
            
            | Col1 | Col2 |
            |------|------|
            | A    | 1    |
            | B    | 2    |
            """,
            
            "complex": """
            # Complex Technical Document
            
            **Project**: Advanced Data Processing System
            **Version**: 2.1.0
            **Author**: Jane Smith <jane@example.com>
            **Date**: 2024-01-15
            **Status**: In Development
            **Budget**: $150,000
            **Timeline**: 6 months
            
            ## Architecture Overview
            
            The system consists of multiple components:
            
            1. Data Ingestion Layer
               - Handles CSV, JSON, XML formats
               - Real-time streaming support
               - Batch processing capabilities
            
            2. Processing Engine
               - Machine learning algorithms
               - Statistical analysis
               - Data transformation pipelines
            
            ## Technical Specifications
            
            | Component | Technology | Performance |
            |-----------|------------|-------------|
            | Database | PostgreSQL | 10K TPS |
            | Cache | Redis | 100K OPS |
            | API | FastAPI | 1K RPS |
            | Frontend | React | <2s load |
            
            ## Implementation Details
            
            ```python
            import asyncio
            import pandas as pd
            from typing import List, Dict, Any
            
            class DataProcessor:
                def __init__(self, config: Dict[str, Any]):
                    self.config = config
                    self.pipeline = self._build_pipeline()
                
                async def process_batch(self, data: List[Dict]) -> List[Dict]:
                    results = []
                    for item in data:
                        processed = await self._process_item(item)
                        if processed:
                            results.append(processed)
                    return results
                
                def _build_pipeline(self):
                    return [
                        self._validate_data,
                        self._transform_data,
                        self._enrich_data,
                        self._store_data
                    ]
            
            class AnalyticsEngine:
                def calculate_metrics(self, dataset):
                    return {
                        'mean': dataset.mean(),
                        'std': dataset.std(),
                        'correlation': dataset.corr()
                    }
            ```
            
            ## Contact Information
            
            - Technical Lead: tech.lead@company.com
            - Project Manager: pm@company.com  
            - Documentation: https://docs.company.com/project
            - Repository: https://github.com/company/data-processor
            
            ## Milestones
            
            Phase 1 (Jan-Feb 2024):
            - [x] Requirements gathering
            - [x] Architecture design
            - [ ] Database schema design
            - [ ] API specification
            
            Phase 2 (Mar-Apr 2024):
            - [ ] Core engine development
            - [ ] API implementation
            - [ ] Frontend development
            - [ ] Integration testing
            """
        }
        
        results = {}
        
        for complexity, content in test_cases.items():
            monitor.start()
            result = self.extractor.extract_structured_data(content)
            metrics = monitor.stop()
            
            results[complexity] = {
                "content_length": len(content),
                "duration": metrics["duration_seconds"],
                "memory_delta": metrics["memory_delta_mb"],
                "key_value_pairs": len(result.key_value_pairs),
                "lists": len(result.lists),
                "tables": len(result.tables),
                "code_snippets": len(result.code_snippets),
                "entities": len(result.entities)
            }
            
            # Performance assertions based on complexity
            if complexity == "simple":
                assert metrics["duration_seconds"] < 0.1
            elif complexity == "medium":
                assert metrics["duration_seconds"] < 0.5
            else:  # complex
                assert metrics["duration_seconds"] < 2.0
        
        # Verify complex documents extract more structured data
        assert results["complex"]["key_value_pairs"] > results["simple"]["key_value_pairs"]
        assert results["complex"]["lists"] > results["simple"]["lists"]
        
        print("Extraction performance by complexity:")
        for complexity, result in results.items():
            total_elements = (result["key_value_pairs"] + result["lists"] + 
                            result["tables"] + result["code_snippets"])
            print(f"  {complexity}: {result['duration']:.3f}s, {total_elements} elements")

    def test_concurrent_extraction_performance(self):
        """Test extraction performance under concurrent load"""
        monitor = PerformanceMonitor()
        
        content = """
        # Test Document for Concurrent Processing
        
        Field1: Value1
        Field2: Value2
        Field3: Value3
        
        List of items:
        - Item A
        - Item B
        - Item C
        
        | Name | Count |
        |------|-------|
        | Test | 100   |
        | Demo | 200   |
        """
        
        def extract_data(content_id):
            start_time = time.time()
            result = self.extractor.extract_structured_data(content)
            duration = time.time() - start_time
            
            return {
                "content_id": content_id,
                "duration": duration,
                "success": len(result.key_value_pairs) > 0
            }
        
        # Test with thread pool (simulating concurrent requests)
        monitor.start()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(extract_data, i) for i in range(50)]
            results = [future.result() for future in futures]
        
        metrics = monitor.stop()
        
        # Analyze results
        successful_extractions = [r for r in results if r["success"]]
        durations = [r["duration"] for r in successful_extractions]
        
        success_rate = len(successful_extractions) / len(results)
        avg_duration = sum(durations) / len(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        
        # Performance assertions
        assert success_rate >= 0.95  # 95% success rate
        assert avg_duration < 1.0  # Average under 1 second
        assert max_duration < 3.0  # Max under 3 seconds
        assert metrics["duration_seconds"] < 30.0  # Total time reasonable
        
        print(f"Concurrent extraction - Success: {success_rate:.2%}, Avg: {avg_duration:.3f}s, Max: {max_duration:.3f}s")

    def test_memory_usage_stability(self):
        """Test that memory usage remains stable during repeated extractions"""
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        content = """
        Document for memory stability test
        
        Data: Large dataset processing
        Memory: Efficient algorithms
        
        Features:
        - Low memory footprint
        - Fast processing
        - Stable performance
        
        | Metric | Before | After |
        |--------|--------|-------|
        | Memory | 100MB  | 105MB |
        | Speed  | 1.0s   | 0.9s  |
        """
        
        # Perform many extractions
        for i in range(100):
            result = self.extractor.extract_structured_data(content)
            assert len(result.key_value_pairs) > 0  # Ensure extraction works
            
            # Force garbage collection periodically
            if i % 10 == 0:
                gc.collect()
        
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be minimal (less than 20MB for 100 extractions)
        assert memory_increase < 20, f"Memory increased by {memory_increase:.1f}MB"
        
        print(f"Memory stability test - Increase: {memory_increase:.1f}MB over 100 extractions")


@pytest.mark.performance
class TestWebSocketPerformance:
    """Performance tests for WebSocket functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.websocket_service = get_websocket_service()

    @pytest.mark.asyncio
    async def test_connection_establishment_performance(self):
        """Test WebSocket connection establishment performance"""
        monitor = PerformanceMonitor()
        monitor.start()
        
        # Establish many connections quickly
        connections = []
        for i in range(100):
            mock_ws = AsyncMock()
            await self.websocket_service.connection_manager.connect(
                mock_ws, f"perf-conn-{i}", f"user-{i}"
            )
            connections.append(mock_ws)
        
        metrics = monitor.stop()
        
        # Performance assertions
        assert metrics["duration_seconds"] < 5.0  # Should establish 100 connections in under 5s
        assert metrics["memory_delta_mb"] < 30  # Memory usage should be reasonable
        
        # Verify all connections are tracked
        ws_metrics = self.websocket_service.get_metrics()
        assert ws_metrics["active_connections"] == 100
        assert ws_metrics["users_connected"] == 100
        
        print(f"Connection establishment - {len(connections)} connections in {metrics['duration_seconds']:.3f}s")

    @pytest.mark.asyncio
    async def test_broadcast_performance(self):
        """Test broadcast performance with many connections"""
        # Set up many connections
        connections = []
        for i in range(50):
            mock_ws = AsyncMock()
            await self.websocket_service.connection_manager.connect(
                mock_ws, f"broadcast-conn-{i}", f"user-{i}"
            )
            connections.append(mock_ws)
        
        monitor = PerformanceMonitor()
        monitor.start()
        
        # Perform multiple broadcasts
        for i in range(10):
            await self.websocket_service.event_broadcaster.broadcast_event(
                "performance.test",
                {"message": f"Broadcast {i}", "timestamp": datetime.utcnow().isoformat()}
            )
        
        metrics = monitor.stop()
        
        # Performance assertions
        assert metrics["duration_seconds"] < 2.0  # 10 broadcasts to 50 connections in under 2s
        
        # Verify all connections received all messages
        for mock_ws in connections:
            assert mock_ws.send_text.call_count == 10
        
        print(f"Broadcast performance - 10 broadcasts to 50 connections in {metrics['duration_seconds']:.3f}s")

    @pytest.mark.asyncio
    async def test_connection_cleanup_performance(self):
        """Test connection cleanup performance"""
        # Set up connections
        connection_ids = []
        for i in range(100):
            mock_ws = AsyncMock()
            conn_id = f"cleanup-conn-{i}"
            await self.websocket_service.connection_manager.connect(
                mock_ws, conn_id, f"user-{i}"
            )
            connection_ids.append(conn_id)
        
        monitor = PerformanceMonitor()
        monitor.start()
        
        # Disconnect all connections
        for conn_id in connection_ids:
            self.websocket_service.connection_manager.disconnect(conn_id)
        
        metrics = monitor.stop()
        
        # Performance assertions
        assert metrics["duration_seconds"] < 1.0  # Cleanup 100 connections in under 1s
        
        # Verify all connections are cleaned up
        ws_metrics = self.websocket_service.get_metrics()
        assert ws_metrics["active_connections"] == 0
        assert ws_metrics["users_connected"] == 0
        
        print(f"Connection cleanup - 100 connections in {metrics['duration_seconds']:.3f}s")

    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(self):
        """Test concurrent WebSocket operations performance"""
        monitor = PerformanceMonitor()
        monitor.start()
        
        async def establish_and_broadcast():
            # Establish connection
            mock_ws = AsyncMock()
            conn_id = f"concurrent-{int(time.time() * 1000000) % 1000000}"
            await self.websocket_service.connection_manager.connect(
                mock_ws, conn_id, f"user-{conn_id}"
            )
            
            # Send notification
            await self.websocket_service.send_notification(
                f"user-{conn_id}",
                {"type": "test", "message": "concurrent test"}
            )
            
            # Cleanup
            self.websocket_service.connection_manager.disconnect(conn_id)
            
            return True
        
        # Run 50 concurrent operations
        tasks = [establish_and_broadcast() for _ in range(50)]
        results = await asyncio.gather(*tasks)
        
        metrics = monitor.stop()
        
        # Performance assertions
        assert all(results)  # All operations should succeed
        assert metrics["duration_seconds"] < 5.0  # All operations in under 5s
        
        print(f"Concurrent operations - 50 operations in {metrics['duration_seconds']:.3f}s")

    @pytest.mark.asyncio
    async def test_websocket_memory_efficiency(self):
        """Test WebSocket memory efficiency under load"""
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # Cycle through many connections to test memory cleanup
        for cycle in range(10):
            # Establish connections
            connections = []
            for i in range(20):
                mock_ws = AsyncMock()
                conn_id = f"memory-test-{cycle}-{i}"
                await self.websocket_service.connection_manager.connect(
                    mock_ws, conn_id, f"user-{conn_id}"
                )
                connections.append((mock_ws, conn_id))
            
            # Broadcast to all connections
            await self.websocket_service.event_broadcaster.broadcast_event(
                "memory.test",
                {"cycle": cycle, "connections": len(connections)}
            )
            
            # Disconnect all connections
            for _, conn_id in connections:
                self.websocket_service.connection_manager.disconnect(conn_id)
            
            # Force garbage collection
            gc.collect()
        
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be minimal
        assert memory_increase < 15, f"Memory increased by {memory_increase:.1f}MB"
        
        # Verify no connections remain
        ws_metrics = self.websocket_service.get_metrics()
        assert ws_metrics["active_connections"] == 0
        
        print(f"WebSocket memory efficiency - {memory_increase:.1f}MB increase over 200 connection cycles")


@pytest.mark.performance
class TestCrossComponentPerformance:
    """Performance tests across multiple components"""

    @pytest.mark.asyncio
    async def test_end_to_end_performance(self, client: AsyncClient, api_key: str):
        """Test end-to-end performance across API, extraction, and WebSocket"""
        monitor = PerformanceMonitor()
        
        # Set up WebSocket connections
        websocket_service = get_websocket_service()
        ws_connections = []
        for i in range(10):
            mock_ws = AsyncMock()
            await websocket_service.connection_manager.connect(
                mock_ws, f"e2e-conn-{i}", f"user-{i}"
            )
            ws_connections.append(mock_ws)
        
        # Prepare structured content for extraction
        structured_content = """
        Performance Test Document
        
        Test ID: E2E-001
        Timestamp: 2024-01-15T10:30:00Z
        Users: 10
        Load: High
        
        Test Results:
        - API Response: < 1s
        - Extraction: < 0.5s  
        - WebSocket: < 0.1s
        
        | Component | Target | Actual |
        |-----------|--------|--------|
        | API | 1s | 0.8s |
        | Extraction | 0.5s | 0.3s |
        | WebSocket | 0.1s | 0.05s |
        """
        
        monitor.start()
        
        # Simulate end-to-end workflow
        tasks = []
        for i in range(20):  # 20 concurrent end-to-end operations
            async def e2e_operation(op_id):
                # 1. Ingest memory via API
                response = await client.post(
                    "/api/v2/memories/ingest",
                    params={
                        "content": structured_content,
                        "memory_type": "performance_test",
                        "tags": ["e2e", f"test-{op_id}"],
                        "api_key": api_key
                    }
                )
                
                # 2. Extract structured data (simulated)
                extractor = StructuredDataExtractor(use_ai=False)
                extracted = extractor.extract_structured_data(structured_content)
                
                # 3. Broadcast via WebSocket (simulated)
                await websocket_service.event_broadcaster.broadcast_event(
                    "e2e.test",
                    {"operation_id": op_id, "extracted_elements": len(extracted.key_value_pairs)}
                )
                
                return {
                    "operation_id": op_id,
                    "api_success": response.status_code == 200,
                    "extraction_success": len(extracted.key_value_pairs) > 0
                }
            
            tasks.append(e2e_operation(i))
        
        results = await asyncio.gather(*tasks)
        metrics = monitor.stop()
        
        # Analyze results
        successful_ops = [r for r in results if r["api_success"] and r["extraction_success"]]
        success_rate = len(successful_ops) / len(results)
        
        # Performance assertions
        assert success_rate >= 0.95  # 95% success rate
        assert metrics["duration_seconds"] < 30.0  # 20 operations in under 30s
        assert metrics["memory_delta_mb"] < 100  # Memory usage under 100MB
        
        # Verify WebSocket broadcasts worked
        for mock_ws in ws_connections:
            assert mock_ws.send_text.call_count == 20  # Each received all broadcasts
        
        print(f"End-to-end performance - {len(results)} operations in {metrics['duration_seconds']:.3f}s, {success_rate:.2%} success")

    def test_system_resource_utilization(self):
        """Test overall system resource utilization during load"""
        initial_cpu = psutil.cpu_percent(interval=1)
        initial_memory = psutil.virtual_memory().percent
        
        # Simulate mixed workload
        extractor = StructuredDataExtractor(use_ai=False)
        websocket_service = get_websocket_service()
        
        content = "Test content\nField: Value\n- Item 1\n- Item 2" * 100
        
        monitor = PerformanceMonitor()
        monitor.start()
        
        # Mixed operations
        for i in range(50):
            # Data extraction
            result = extractor.extract_structured_data(content)
            
            # Simulated WebSocket activity
            if i % 10 == 0:
                asyncio.run(websocket_service.event_broadcaster.broadcast_event(
                    "system.test",
                    {"iteration": i, "extracted": len(result.key_value_pairs)}
                ))
        
        metrics = monitor.stop()
        
        final_cpu = psutil.cpu_percent(interval=1)
        final_memory = psutil.virtual_memory().percent
        
        # Resource utilization should be reasonable
        cpu_increase = final_cpu - initial_cpu
        memory_increase = final_memory - initial_memory
        
        assert cpu_increase < 50  # CPU increase under 50%
        assert memory_increase < 10  # Memory increase under 10%
        assert metrics["duration_seconds"] < 10.0  # Complete in reasonable time
        
        print(f"Resource utilization - CPU: +{cpu_increase:.1f}%, Memory: +{memory_increase:.1f}%, Duration: {metrics['duration_seconds']:.3f}s")