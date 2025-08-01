"""
Performance and Load Testing Scenarios
Tests system performance under various load conditions
"""

import asyncio
import statistics
import time

import pytest

pytestmark = pytest.mark.performance

from httpx import AsyncClient


class TestLoadScenarios:
    """Test system performance under load"""

    @pytest.mark.asyncio
    async def test_concurrent_memory_storage(self, client: AsyncClient, api_key: str):
        """Test concurrent memory storage operations"""

        async def store_memory(session_id: int):
            payload = {
                "content": f"Concurrent memory test {session_id} - testing system under load",
                "importance_score": 0.5 + (session_id % 5) * 0.1
            }

            start_time = time.time()
            response = await client.post(
                "/memories/semantic",
                json=payload,
                params={"api_key": api_key}
            )
            end_time = time.time()

            return {
                "session_id": session_id,
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "success": response.status_code == 200
            }

        # Test with increasing concurrency levels
        concurrency_levels = [5, 10, 20]

        for concurrency in concurrency_levels:
            print(f"\nTesting concurrency level: {concurrency}")

            # Execute concurrent operations
            tasks = [store_memory(i) for i in range(concurrency)]
            start_time = time.time()
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start_time

            # Analyze results
            successful_requests = sum(1 for r in results if r["success"])
            response_times = [r["response_time"] for r in results if r["success"]]

            # Performance assertions
            success_rate = successful_requests / concurrency
            assert success_rate >= 0.8, f"Success rate {success_rate} too low for concurrency {concurrency}"

            if response_times:
                avg_response_time = statistics.mean(response_times)
                max_response_time = max(response_times)

                print(f"  Success rate: {success_rate:.2%}")
                print(f"  Average response time: {avg_response_time:.3f}s")
                print(f"  Max response time: {max_response_time:.3f}s")
                print(f"  Total time: {total_time:.3f}s")
                print(f"  Throughput: {successful_requests/total_time:.2f} req/s")

                # Performance thresholds
                assert avg_response_time < 5.0, f"Average response time too high: {avg_response_time}s"
                assert max_response_time < 10.0, f"Max response time too high: {max_response_time}s"

    @pytest.mark.asyncio
    async def test_concurrent_search_operations(self, client: AsyncClient, api_key: str):
        """Test concurrent search operations performance"""

        # First, seed some memories for searching
        seed_memories = [
            "Python programming language concepts and syntax",
            "Machine learning algorithms and applications",
            "Database design patterns and optimization",
            "Web development frameworks and tools",
            "Software architecture principles and patterns"
        ]

        for content in seed_memories:
            await client.post(
                "/memories/semantic",
                json={"content": content, "importance_score": 0.7},
                params={"api_key": api_key}
            )

        async def search_memory(query_id: int):
            queries = [
                "python programming",
                "machine learning",
                "database design",
                "web development",
                "software architecture"
            ]

            payload = {
                "query": queries[query_id % len(queries)],
                "limit": 5
            }

            start_time = time.time()
            response = await client.post(
                "/memories/search",
                json=payload,
                params={"api_key": api_key}
            )
            end_time = time.time()

            return {
                "query_id": query_id,
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "results_count": len(response.json()) if response.status_code == 200 else 0,
                "success": response.status_code == 200
            }

        # Test concurrent searches
        concurrent_searches = 15
        tasks = [search_memory(i) for i in range(concurrent_searches)]

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Analyze search performance
        successful_searches = sum(1 for r in results if r["success"])
        response_times = [r["response_time"] for r in results if r["success"]]

        success_rate = successful_searches / concurrent_searches
        assert success_rate >= 0.9, f"Search success rate too low: {success_rate}"

        if response_times:
            avg_response_time = statistics.mean(response_times)
            print("\nSearch Performance:")
            print(f"  Success rate: {success_rate:.2%}")
            print(f"  Average response time: {avg_response_time:.3f}s")
            print(f"  Throughput: {successful_searches/total_time:.2f} searches/s")

            # Search should be fast
            assert avg_response_time < 3.0, f"Search too slow: {avg_response_time}s"

    @pytest.mark.asyncio
    async def test_memory_retrieval_performance(self, client: AsyncClient, api_key: str):
        """Test memory retrieval performance under load"""

        # Store memories to retrieve
        memory_ids = []
        for i in range(20):
            payload = {
                "content": f"Performance test memory {i} with some content to retrieve",
                "importance_score": 0.6
            }

            response = await client.post(
                "/memories/semantic",
                json=payload,
                params={"api_key": api_key}
            )

            if response.status_code == 200:
                memory_ids.append(response.json()["id"])

        if not memory_ids:
            pytest.skip("Could not create test memories for retrieval test")

        async def retrieve_memory(memory_id: str):
            start_time = time.time()
            response = await client.get(
                f"/memories/{memory_id}",
                params={"api_key": api_key}
            )
            end_time = time.time()

            return {
                "memory_id": memory_id,
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "success": response.status_code == 200
            }

        # Test concurrent retrieval
        tasks = [retrieve_memory(mid) for mid in memory_ids[:10]]  # Test subset
        results = await asyncio.gather(*tasks)

        successful_retrievals = sum(1 for r in results if r["success"])
        response_times = [r["response_time"] for r in results if r["success"]]

        success_rate = successful_retrievals / len(tasks)
        assert success_rate >= 0.95, f"Retrieval success rate too low: {success_rate}"

        if response_times:
            avg_response_time = statistics.mean(response_times)
            print("\nRetrieval Performance:")
            print(f"  Success rate: {success_rate:.2%}")
            print(f"  Average response time: {avg_response_time:.3f}s")

            # Individual memory retrieval should be very fast
            assert avg_response_time < 1.0, f"Retrieval too slow: {avg_response_time}s"

    @pytest.mark.asyncio
    async def test_mixed_workload_performance(self, client: AsyncClient, api_key: str):
        """Test performance with mixed read/write workload"""

        async def mixed_operation(op_id: int):
            """Perform mixed operations: store, search, retrieve"""
            operations = []

            # Store operation
            if op_id % 3 == 0:
                payload = {
                    "content": f"Mixed workload test memory {op_id}",
                    "importance_score": 0.5
                }

                start_time = time.time()
                response = await client.post(
                    "/memories/semantic",
                    json=payload,
                    params={"api_key": api_key}
                )
                end_time = time.time()

                operations.append({
                    "type": "store",
                    "success": response.status_code == 200,
                    "response_time": end_time - start_time
                })

            # Search operation
            elif op_id % 3 == 1:
                payload = {
                    "query": f"test memory {op_id}",
                    "limit": 5
                }

                start_time = time.time()
                response = await client.post(
                    "/memories/search",
                    json=payload,
                    params={"api_key": api_key}
                )
                end_time = time.time()

                operations.append({
                    "type": "search",
                    "success": response.status_code == 200,
                    "response_time": end_time - start_time
                })

            # Health check (simulating monitoring)
            else:
                start_time = time.time()
                response = await client.get(
                    "/health",
                    params={"api_key": api_key}
                )
                end_time = time.time()

                operations.append({
                    "type": "health",
                    "success": response.status_code == 200,
                    "response_time": end_time - start_time
                })

            return operations

        # Run mixed workload
        tasks = [mixed_operation(i) for i in range(30)]
        all_results = await asyncio.gather(*tasks)

        # Flatten results
        operations = [op for result_list in all_results for op in result_list]

        # Analyze by operation type
        by_type = {}
        for op in operations:
            op_type = op["type"]
            if op_type not in by_type:
                by_type[op_type] = []
            by_type[op_type].append(op)

        print("\nMixed Workload Performance:")
        for op_type, ops in by_type.items():
            successful = sum(1 for op in ops if op["success"])
            response_times = [op["response_time"] for op in ops if op["success"]]

            success_rate = successful / len(ops) if ops else 0
            avg_time = statistics.mean(response_times) if response_times else 0

            print(f"  {op_type}: {success_rate:.2%} success, {avg_time:.3f}s avg")

            assert success_rate >= 0.8, f"{op_type} success rate too low: {success_rate}"

    @pytest.mark.asyncio
    async def test_sustained_load_performance(self, client: AsyncClient, api_key: str):
        """Test system performance under sustained load"""

        async def sustained_operation(duration_seconds: int = 10):
            """Run operations for a sustained period"""
            start_time = time.time()
            operations = []
            op_count = 0

            while time.time() - start_time < duration_seconds:
                op_count += 1

                # Alternate between different operations
                if op_count % 4 == 0:
                    # Store memory
                    payload = {
                        "content": f"Sustained load test {op_count}",
                        "importance_score": 0.5
                    }

                    op_start = time.time()
                    response = await client.post(
                        "/memories/semantic",
                        json=payload,
                        params={"api_key": api_key}
                    )
                    op_end = time.time()

                    operations.append({
                        "type": "store",
                        "success": response.status_code == 200,
                        "response_time": op_end - op_start,
                        "timestamp": op_start
                    })

                elif op_count % 4 == 1:
                    # Search
                    payload = {"query": f"test {op_count}", "limit": 3}

                    op_start = time.time()
                    response = await client.post(
                        "/memories/search",
                        json=payload,
                        params={"api_key": api_key}
                    )
                    op_end = time.time()

                    operations.append({
                        "type": "search",
                        "success": response.status_code == 200,
                        "response_time": op_end - op_start,
                        "timestamp": op_start
                    })

                else:
                    # Health check
                    op_start = time.time()
                    response = await client.get("/health", params={"api_key": api_key})
                    op_end = time.time()

                    operations.append({
                        "type": "health",
                        "success": response.status_code == 200,
                        "response_time": op_end - op_start,
                        "timestamp": op_start
                    })

                # Small delay to avoid overwhelming
                await asyncio.sleep(0.01)

            return operations

        # Run sustained load test (shorter duration for tests)
        operations = await sustained_operation(duration_seconds=5)

        if not operations:
            pytest.skip("No operations completed in sustained load test")

        # Analyze sustained performance
        successful_ops = [op for op in operations if op["success"]]
        success_rate = len(successful_ops) / len(operations)

        response_times = [op["response_time"] for op in successful_ops]
        avg_response_time = statistics.mean(response_times) if response_times else 0

        # Calculate throughput
        total_duration = operations[-1]["timestamp"] - operations[0]["timestamp"]
        throughput = len(successful_ops) / total_duration if total_duration > 0 else 0

        print("\nSustained Load Performance:")
        print(f"  Total operations: {len(operations)}")
        print(f"  Success rate: {success_rate:.2%}")
        print(f"  Average response time: {avg_response_time:.3f}s")
        print(f"  Throughput: {throughput:.2f} ops/sec")

        # Performance requirements
        assert success_rate >= 0.85, f"Sustained load success rate too low: {success_rate}"
        assert avg_response_time < 2.0, f"Sustained load response time too high: {avg_response_time}s"

    @pytest.mark.asyncio
    async def test_memory_pagination_performance(self, client: AsyncClient, api_key: str):
        """Test pagination performance with large datasets"""

        # Store a reasonable number of memories for pagination testing
        total_memories = 50
        batch_size = 10

        print(f"Creating {total_memories} memories for pagination test...")
        for batch in range(0, total_memories, batch_size):
            batch_tasks = []
            for i in range(batch, min(batch + batch_size, total_memories)):
                payload = {
                    "content": f"Pagination test memory {i} with unique content for testing",
                    "importance_score": 0.5 + (i % 10) * 0.05
                }

                task = client.post(
                    "/memories/semantic",
                    json=payload,
                    params={"api_key": api_key}
                )
                batch_tasks.append(task)

            # Execute batch
            await asyncio.gather(*batch_tasks)

            # Small delay between batches
            await asyncio.sleep(0.1)

        # Test pagination performance
        page_sizes = [10, 20, 50]

        for page_size in page_sizes:
            page_times = []

            # Test first few pages
            for page in range(3):
                offset = page * page_size

                start_time = time.time()
                response = await client.get(
                    "/memories",
                    params={
                        "api_key": api_key,
                        "limit": page_size,
                        "offset": offset
                    }
                )
                end_time = time.time()

                if response.status_code == 200:
                    page_times.append(end_time - start_time)
                    data = response.json()
                    assert len(data) <= page_size

            if page_times:
                avg_page_time = statistics.mean(page_times)
                print(f"  Page size {page_size}: {avg_page_time:.3f}s avg")

                # Pagination should be fast
                assert avg_page_time < 1.0, f"Pagination too slow for page size {page_size}: {avg_page_time}s"

    @pytest.mark.asyncio
    async def test_api_endpoint_response_times(self, client: AsyncClient, api_key: str):
        """Test response times for all major API endpoints"""

        # Store a test memory for endpoints that need it
        store_response = await client.post(
            "/memories/semantic",
            json={"content": "API response time test memory", "importance_score": 0.7},
            params={"api_key": api_key}
        )

        memory_id = None
        if store_response.status_code == 200:
            memory_id = store_response.json()["id"]

        # Test endpoints with response time requirements
        endpoints_to_test = [
            ("/health", "GET", None, 0.5),  # Health should be very fast
            ("/memories", "GET", None, 1.0),  # List memories
            ("/status", "GET", None, 2.0),  # Status might be slower
        ]

        # Add memory-specific endpoints if we have a memory
        if memory_id:
            endpoints_to_test.extend([
                (f"/memories/{memory_id}", "GET", None, 1.0),  # Get specific memory
                ("/memories/search", "POST", {"query": "test", "limit": 5}, 2.0),  # Search
            ])

        results = {}

        for endpoint, method, payload, max_time in endpoints_to_test:
            times = []

            # Test each endpoint multiple times
            for _ in range(5):
                start_time = time.time()

                if method == "GET":
                    response = await client.get(endpoint, params={"api_key": api_key})
                elif method == "POST":
                    response = await client.post(endpoint, json=payload, params={"api_key": api_key})

                end_time = time.time()

                if response.status_code == 200:
                    times.append(end_time - start_time)

            if times:
                avg_time = statistics.mean(times)
                results[f"{method} {endpoint}"] = avg_time

                print(f"{method} {endpoint}: {avg_time:.3f}s avg")
                assert avg_time < max_time, f"Endpoint {endpoint} too slow: {avg_time}s > {max_time}s"

        return results

    @pytest.mark.asyncio
    async def test_error_rate_under_load(self, client: AsyncClient, api_key: str):
        """Test error rates under various load conditions"""

        async def stress_operation(error_inducing: bool = False):
            """Operation that might induce errors"""

            if error_inducing:
                # Intentionally cause some errors
                payloads = [
                    {"content": "", "importance_score": 0.5},  # Empty content
                    {"content": "test", "importance_score": 2.0},  # Invalid score
                    {"invalid": "payload"},  # Wrong structure
                ]
                payload = payloads[int(time.time()) % len(payloads)]
            else:
                payload = {
                    "content": f"Load test memory {time.time()}",
                    "importance_score": 0.6
                }

            response = await client.post(
                "/memories/semantic",
                json=payload,
                params={"api_key": api_key}
            )

            return {
                "status_code": response.status_code,
                "error_inducing": error_inducing,
                "success": response.status_code == 200
            }

        # Mix of normal and error-inducing operations
        tasks = []
        for i in range(20):
            # 20% error-inducing operations
            error_inducing = i % 5 == 0
            tasks.append(stress_operation(error_inducing))

        results = await asyncio.gather(*tasks)

        # Analyze error rates
        normal_ops = [r for r in results if not r["error_inducing"]]
        error_ops = [r for r in results if r["error_inducing"]]

        normal_success_rate = sum(1 for r in normal_ops if r["success"]) / len(normal_ops) if normal_ops else 1
        error_success_rate = sum(1 for r in error_ops if r["success"]) / len(error_ops) if error_ops else 0

        print("\nError Rate Analysis:")
        print(f"  Normal operations success rate: {normal_success_rate:.2%}")
        print(f"  Error-inducing operations success rate: {error_success_rate:.2%}")

        # Normal operations should have high success rate
        assert normal_success_rate >= 0.9, f"Normal operations success rate too low: {normal_success_rate}"

        # Error-inducing operations should mostly fail (be handled properly)
        assert error_success_rate <= 0.2, f"Error handling not working properly: {error_success_rate}"

    @pytest.mark.asyncio
    async def test_resource_usage_monitoring(self, client: AsyncClient, api_key: str):
        """Test resource usage during load operations"""

        async def monitor_resources():
            """Monitor system resources during test"""
            try:
                import psutil

                # Get initial resource usage
                initial_memory = psutil.virtual_memory().percent
                initial_cpu = psutil.cpu_percent()

                return {
                    "memory_percent": initial_memory,
                    "cpu_percent": initial_cpu,
                    "available": True
                }
            except ImportError:
                return {"available": False}

        # Monitor resources before load
        initial_resources = await monitor_resources()

        # Apply load
        tasks = []
        for i in range(15):
            payload = {
                "content": f"Resource monitoring test {i} with substantial content to process",
                "importance_score": 0.6
            }
            tasks.append(client.post("/memories/semantic", json=payload, params={"api_key": api_key}))

        # Execute load
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        # Monitor resources after load
        final_resources = await monitor_resources()

        # Analyze results
        successful_ops = sum(1 for r in results if r.status_code == 200)
        success_rate = successful_ops / len(tasks)
        throughput = successful_ops / (end_time - start_time)

        print("\nResource Usage Test:")
        print(f"  Operations: {len(tasks)}")
        print(f"  Success rate: {success_rate:.2%}")
        print(f"  Throughput: {throughput:.2f} ops/sec")

        if initial_resources["available"] and final_resources["available"]:
            memory_increase = final_resources["memory_percent"] - initial_resources["memory_percent"]
            print(f"  Memory usage change: {memory_increase:+.1f}%")

            # Memory usage shouldn't increase dramatically
            assert memory_increase < 10, f"Memory usage increased too much: {memory_increase}%"

        # Performance should remain good
        assert success_rate >= 0.8, f"Success rate under load too low: {success_rate}"
