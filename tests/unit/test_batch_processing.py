"""
Comprehensive test suite for batch processing functionality
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.batch_processor import (
    BatchProcessor,
    BatchConfig,
    BatchJob,
    BatchStatus,
    ProcessingMode,
    BatchProgress
)


class TestBatchConfig:
    """Test BatchConfig configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = BatchConfig()
        assert config.batch_size == 100
        assert config.max_concurrent == 10
        assert config.retry_attempts == 3
        assert config.retry_delay == 1.0
        assert config.timeout_per_item == 30.0
        assert config.checkpoint_interval == 1000
        assert config.mode == ProcessingMode.ADAPTIVE
        assert config.memory_limit_mb == 1024
        assert config.enable_progress_tracking is True
        assert config.enable_checkpointing is True
        assert config.result_aggregation is True
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = BatchConfig(
            batch_size=500,
            max_concurrent=20,
            mode=ProcessingMode.CONCURRENT,
            enable_checkpointing=False
        )
        assert config.batch_size == 500
        assert config.max_concurrent == 20
        assert config.mode == ProcessingMode.CONCURRENT
        assert config.enable_checkpointing is False


class TestBatchProgress:
    """Test BatchProgress tracking"""
    
    def test_progress_initialization(self):
        """Test progress tracker initialization"""
        progress = BatchProgress(total=100)
        assert progress.total == 100
        assert progress.processed == 0
        assert progress.succeeded == 0
        assert progress.failed == 0
        assert progress.skipped == 0
        assert progress.start_time > 0
        assert progress.end_time is None
        assert progress.errors == []
    
    def test_elapsed_time(self):
        """Test elapsed time calculation"""
        progress = BatchProgress()
        progress.start_time = 100.0
        progress.end_time = 150.0
        assert progress.elapsed_time == 50.0
        
        # Test with no end time
        progress.end_time = None
        with patch('time.time', return_value=200.0):
            assert progress.elapsed_time == 100.0
    
    def test_processing_rate(self):
        """Test processing rate calculation"""
        progress = BatchProgress()
        progress.processed = 100
        progress.start_time = 0
        progress.end_time = 10
        assert progress.processing_rate == 10.0
        
        # Test with zero elapsed time
        progress.end_time = 0
        assert progress.processing_rate == 0
    
    def test_success_rate(self):
        """Test success rate calculation"""
        progress = BatchProgress()
        progress.processed = 100
        progress.succeeded = 75
        assert progress.success_rate == 0.75
        
        # Test with zero processed
        progress.processed = 0
        assert progress.success_rate == 0
    
    def test_to_dict(self):
        """Test dictionary conversion"""
        progress = BatchProgress(total=100)
        progress.processed = 50
        progress.succeeded = 45
        progress.failed = 5
        
        result = progress.to_dict()
        assert result["total"] == 100
        assert result["processed"] == 50
        assert result["succeeded"] == 45
        assert result["failed"] == 5
        assert "elapsed_time" in result
        assert "processing_rate" in result
        assert "success_rate" in result


class TestBatchJob:
    """Test BatchJob model"""
    
    def test_job_creation(self):
        """Test job creation with defaults"""
        job = BatchJob(name="Test Job")
        assert job.name == "Test Job"
        assert job.status == BatchStatus.PENDING
        assert len(job.id) > 0
        assert isinstance(job.created_at, datetime)
        assert job.started_at is None
        assert job.completed_at is None
    
    def test_job_with_config(self):
        """Test job with configuration"""
        config = {"batch_size": 200, "mode": "concurrent"}
        job = BatchJob(name="Test Job", config=config)
        assert job.config == config


class TestBatchProcessor:
    """Test BatchProcessor functionality"""
    
    @pytest.fixture
    def processor(self):
        """Create a batch processor instance"""
        config = BatchConfig(
            batch_size=10,
            max_concurrent=5,
            checkpoint_interval=20
        )
        return BatchProcessor(config)
    
    @pytest.fixture
    def mock_memories(self):
        """Create mock memory objects"""
        memories = []
        for i in range(25):
            memory = Mock()
            memory.id = uuid4()
            memory.content = f"Test content {i}"
            memory.metadata = {}
            memories.append(memory)
        return memories
    
    @pytest.mark.asyncio
    async def test_process_memories_batch_success(self, processor, mock_memories):
        """Test successful batch processing of memories"""
        memory_ids = [m.id for m in mock_memories]
        
        # Mock operation
        operation = AsyncMock()
        operation.return_value = None
        
        # Process batch
        job = await processor.process_memories_batch(
            memory_ids=memory_ids,
            operation=operation,
            job_name="Test Batch"
        )
        
        # Verify job completion
        assert job.status == BatchStatus.COMPLETED
        assert job.name == "Test Batch"
        assert job.started_at is not None
        assert job.completed_at is not None
        assert job.progress["total"] == 25
        assert job.progress["processed"] == 25
        assert job.progress["succeeded"] == 25
        assert job.progress["failed"] == 0
        
        # Verify operation was called for each memory
        assert operation.call_count == 25
    
    @pytest.mark.asyncio
    async def test_process_memories_batch_with_failures(self, processor, mock_memories):
        """Test batch processing with some failures"""
        memory_ids = [m.id for m in mock_memories[:10]]
        
        # Mock operation that fails for some items
        operation = AsyncMock()
        operation.side_effect = [None, None, Exception("Error"), None, None,
                                Exception("Error"), None, None, None, None]
        
        # Process batch
        job = await processor.process_memories_batch(
            memory_ids=memory_ids,
            operation=operation,
            job_name="Test Batch with Failures"
        )
        
        # Verify job completion with failures
        assert job.status == BatchStatus.FAILED
        assert job.progress["total"] == 10
        assert job.progress["processed"] == 10
        assert job.progress["succeeded"] == 8
        assert job.progress["failed"] == 2
        assert len(job.progress["errors"]) == 2
    
    @pytest.mark.asyncio
    async def test_process_files_batch(self, processor):
        """Test batch processing of files"""
        # Create mock file paths
        file_paths = [
            Path("test1.jpg"),
            Path("test2.png"),
            Path("test3.pdf"),
            Path("test4.mp3")
        ]
        
        # Mock pipeline
        with patch('app.batch_processor.CoreExtractionPipeline') as mock_pipeline:
            mock_pipeline.return_value.process = AsyncMock(return_value={})
            
            job = await processor.process_files_batch(
                file_paths=file_paths,
                job_name="File Batch Test"
            )
            
            assert job.status == BatchStatus.COMPLETED
            assert job.config["file_count"] == 4
    
    @pytest.mark.asyncio
    async def test_sequential_processing(self, processor):
        """Test sequential processing mode"""
        processor.config.mode = ProcessingMode.SEQUENTIAL
        
        items = list(range(5))
        results = []
        
        async def operation(item):
            results.append(item)
            await asyncio.sleep(0.01)
        
        progress = BatchProgress(total=5)
        await processor._process_sequential(items, operation, progress)
        
        # Verify sequential processing
        assert results == [0, 1, 2, 3, 4]
        assert progress.processed == 5
        assert progress.succeeded == 5
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, processor):
        """Test concurrent processing mode"""
        processor.config.mode = ProcessingMode.CONCURRENT
        processor.config.max_concurrent = 3
        
        items = list(range(10))
        processing_times = []
        
        async def operation(item):
            start = asyncio.get_event_loop().time()
            await asyncio.sleep(0.1)
            end = asyncio.get_event_loop().time()
            processing_times.append((item, start, end))
        
        progress = BatchProgress(total=10)
        
        start_time = asyncio.get_event_loop().time()
        await processor._process_concurrent(items, operation, progress)
        total_time = asyncio.get_event_loop().time() - start_time
        
        # Verify concurrent processing
        assert progress.processed == 10
        assert progress.succeeded == 10
        # Should take ~0.4s with max_concurrent=3, not 1.0s sequential
        assert total_time < 0.6
    
    @pytest.mark.asyncio
    async def test_streaming_processing(self, processor):
        """Test streaming processing mode"""
        processor.config.mode = ProcessingMode.STREAMING
        
        items = list(range(20))
        processed_items = []
        
        async def operation(item):
            processed_items.append(item)
            await asyncio.sleep(0.01)
        
        progress = BatchProgress(total=20)
        await processor._process_streaming(items, operation, progress)
        
        assert len(processed_items) == 20
        assert progress.processed == 20
        assert progress.succeeded == 20
    
    @pytest.mark.asyncio
    async def test_adaptive_processing(self, processor):
        """Test adaptive processing mode"""
        processor.config.mode = ProcessingMode.ADAPTIVE
        
        items = list(range(5))
        
        async def operation(item):
            await asyncio.sleep(0.01)
        
        progress = BatchProgress(total=5)
        
        # Mock system load
        with patch('psutil.cpu_percent', return_value=30.0):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value.percent = 40.0
                await processor._process_adaptive(items, operation, progress)
        
        assert progress.processed == 5
        assert progress.succeeded == 5
    
    @pytest.mark.asyncio
    async def test_checkpointing(self, processor, tmp_path):
        """Test checkpoint saving functionality"""
        processor.config.enable_checkpointing = True
        
        # Mock checkpoint directory
        with patch('pathlib.Path.mkdir'):
            with patch('aiofiles.open', create=True) as mock_open:
                mock_file = AsyncMock()
                mock_open.return_value.__aenter__.return_value = mock_file
                
                job = BatchJob(id="test-job", name="Test Job")
                progress = BatchProgress(total=100, processed=50)
                
                await processor._save_checkpoint(job, progress)
                
                # Verify checkpoint was saved
                assert job.checkpoint_data is not None
                assert job.checkpoint_data["job_id"] == "test-job"
                assert job.checkpoint_data["progress"]["processed"] == 50
                mock_file.write.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_job_cancellation(self, processor):
        """Test job cancellation"""
        # Create and start a job
        job = BatchJob(id="cancel-test", name="Cancel Test")
        job.status = BatchStatus.RUNNING
        processor.jobs[job.id] = job
        
        # Cancel the job
        success = await processor.cancel_job(job.id)
        assert success is True
        assert job.status == BatchStatus.CANCELLED
        
        # Try to cancel non-existent job
        success = await processor.cancel_job("non-existent")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_get_job_status(self, processor):
        """Test retrieving job status"""
        job = BatchJob(id="status-test", name="Status Test")
        processor.jobs[job.id] = job
        
        retrieved_job = await processor.get_job_status(job.id)
        assert retrieved_job is job
        
        # Test non-existent job
        result = await processor.get_job_status("non-existent")
        assert result is None
    
    def test_group_files_by_type(self, processor):
        """Test file grouping by type"""
        files = [
            Path("image1.jpg"),
            Path("image2.png"),
            Path("doc1.pdf"),
            Path("doc2.docx"),
            Path("audio1.mp3"),
            Path("video1.mp4"),
            Path("unknown.xyz")
        ]
        
        groups = processor._group_files_by_type(files)
        
        assert len(groups["image"]) == 2
        assert len(groups["document"]) == 2
        assert len(groups["audio"]) == 1
        assert len(groups["video"]) == 1
        assert len(groups["other"]) == 1
    
    def test_chunk_list(self, processor):
        """Test list chunking"""
        items = list(range(25))
        chunks = processor._chunk_list(items, 10)
        
        assert len(chunks) == 3
        assert len(chunks[0]) == 10
        assert len(chunks[1]) == 10
        assert len(chunks[2]) == 5
    
    def test_summarize_errors(self, processor):
        """Test error summarization"""
        errors = [
            {"error": "ConnectionError: timeout"},
            {"error": "ConnectionError: refused"},
            {"error": "ValueError: invalid input"},
            {"error": "ConnectionError: reset"}
        ]
        
        summary = processor._summarize_errors(errors)
        assert summary["ConnectionError"] == 3
        assert summary["ValueError"] == 1
    
    @pytest.mark.asyncio
    async def test_import_from_export(self, processor, tmp_path):
        """Test import from export file"""
        # Create mock export file
        export_file = tmp_path / "export.json"
        export_data = [
            {"content": "Memory 1", "tags": ["test"]},
            {"content": "Memory 2", "tags": ["test"]}
        ]
        export_file.write_text(json.dumps(export_data))
        
        with patch.object(processor, '_count_export_items', return_value=2):
            with patch.object(processor, '_stream_export_data') as mock_stream:
                # Mock streaming data
                async def stream_gen():
                    yield export_data
                
                mock_stream.return_value = stream_gen()
                
                with patch.object(processor, '_process_import_batch') as mock_process:
                    mock_process.return_value = None
                    
                    job = await processor.import_from_export(
                        export_file=export_file,
                        format="json",
                        job_name="Import Test"
                    )
                    
                    assert job.status == BatchStatus.COMPLETED
                    assert job.config["file"] == str(export_file)
                    assert job.config["format"] == "json"


class TestBatchProcessorEdgeCases:
    """Test edge cases and error scenarios"""
    
    @pytest.fixture
    def processor(self):
        """Create a batch processor instance"""
        return BatchProcessor()
    
    @pytest.mark.asyncio
    async def test_empty_batch(self, processor):
        """Test processing empty batch"""
        job = await processor.process_memories_batch(
            memory_ids=[],
            operation=AsyncMock(),
            job_name="Empty Batch"
        )
        
        assert job.status == BatchStatus.COMPLETED
        assert job.progress["total"] == 0
        assert job.progress["processed"] == 0
    
    @pytest.mark.asyncio
    async def test_operation_timeout(self, processor):
        """Test operation timeout handling"""
        processor.config.timeout_per_item = 0.1
        
        async def slow_operation(item):
            await asyncio.sleep(1.0)  # Longer than timeout
        
        progress = BatchProgress(total=1)
        await processor._process_sequential([1], slow_operation, progress)
        
        assert progress.processed == 1
        assert progress.failed == 1
        assert progress.succeeded == 0
        assert "Timeout" in progress.errors[0]["error"]
    
    @pytest.mark.asyncio
    async def test_exception_during_processing(self, processor):
        """Test exception handling during batch processing"""
        memory_ids = [uuid4() for _ in range(5)]
        
        async def failing_operation(item):
            raise RuntimeError("Processing failed")
        
        with pytest.raises(RuntimeError):
            await processor.process_memories_batch(
                memory_ids=memory_ids,
                operation=failing_operation,
                job_name="Failing Batch"
            )
    
    @pytest.mark.asyncio
    async def test_concurrent_job_management(self, processor):
        """Test managing multiple concurrent jobs"""
        # Create multiple jobs
        jobs = []
        for i in range(3):
            job = BatchJob(id=f"job-{i}", name=f"Job {i}")
            processor.jobs[job.id] = job
            jobs.append(job)
        
        # Verify all jobs are tracked
        assert len(processor.jobs) == 3
        
        # Cancel one job
        jobs[1].status = BatchStatus.RUNNING
        await processor.cancel_job(jobs[1].id)
        assert jobs[1].status == BatchStatus.CANCELLED
        
        # Others should be unaffected
        assert jobs[0].status == BatchStatus.PENDING
        assert jobs[2].status == BatchStatus.PENDING


class TestBatchProcessingIntegration:
    """Integration tests for batch processing"""
    
    @pytest.mark.asyncio
    async def test_full_memory_reprocessing_workflow(self):
        """Test complete memory reprocessing workflow"""
        processor = BatchProcessor()
        
        # Mock database and extraction pipeline
        with patch('app.batch_processor.get_db') as mock_get_db:
            with patch('app.batch_processor.CoreExtractionPipeline') as mock_pipeline:
                # Setup mocks
                mock_db = AsyncMock()
                mock_get_db.return_value.__aenter__.return_value = mock_db
                
                mock_pipeline.return_value.process = AsyncMock(
                    return_value={"entities": ["test"], "topics": ["test"]}
                )
                
                # Mock database methods
                processor._count_memories = AsyncMock(return_value=10)
                processor._fetch_memory_batch = AsyncMock()
                processor._update_memory_extraction = AsyncMock()
                
                # Create mock memories
                mock_memories = []
                for i in range(10):
                    memory = Mock()
                    memory.id = uuid4()
                    memory.content = f"Test content {i}"
                    mock_memories.append(memory)
                
                processor._fetch_memory_batch.return_value = mock_memories
                
                # Run reprocessing
                job = await processor.reprocess_all_memories(
                    filters={"tags": ["test"]},
                    job_name="Reprocess Test"
                )
                
                # Verify completion
                assert job.status == BatchStatus.COMPLETED
                assert job.progress["total"] == 10
                assert job.progress["succeeded"] == 10
    
    @pytest.mark.asyncio
    async def test_pattern_analysis_workflow(self):
        """Test pattern analysis batch workflow"""
        processor = BatchProcessor()
        
        with patch('app.batch_processor.get_db') as mock_get_db:
            with patch('app.insights.pattern_detector.PatternDetector') as mock_detector:
                with patch('app.insights.cluster_analyzer.ClusterAnalyzer') as mock_analyzer:
                    # Setup mocks
                    mock_db = AsyncMock()
                    mock_get_db.return_value.__aenter__.return_value = mock_db
                    
                    # Mock pattern detection
                    mock_detector.return_value.detect_patterns = AsyncMock(
                        return_value={
                            "temporal": ["pattern1", "pattern2"],
                            "semantic": ["pattern3"]
                        }
                    )
                    
                    # Mock clustering
                    mock_analyzer.return_value.cluster_memories = AsyncMock(
                        return_value=[{"cluster_id": 1, "size": 5}]
                    )
                    
                    # Mock database methods
                    processor._count_memories_in_range = AsyncMock(return_value=20)
                    processor._fetch_memories_by_time = AsyncMock(return_value=[Mock() for _ in range(20)])
                    
                    # Run analysis
                    job = await processor.analyze_memory_patterns(
                        job_name="Pattern Analysis Test"
                    )
                    
                    # Verify results
                    assert job.status == BatchStatus.COMPLETED
                    assert job.result_summary is not None
                    assert "patterns" in job.result_summary
                    assert "clusters" in job.result_summary


# Performance benchmarks
class TestBatchProcessingPerformance:
    """Performance tests for batch processing"""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_large_batch_performance(self):
        """Test performance with large batches"""
        processor = BatchProcessor(
            BatchConfig(
                batch_size=1000,
                max_concurrent=20,
                mode=ProcessingMode.CONCURRENT
            )
        )
        
        # Create large dataset
        memory_ids = [uuid4() for _ in range(10000)]
        
        async def fast_operation(item):
            # Simulate quick processing
            await asyncio.sleep(0.001)
        
        start_time = asyncio.get_event_loop().time()
        
        job = await processor.process_memories_batch(
            memory_ids=memory_ids,
            operation=fast_operation,
            job_name="Performance Test"
        )
        
        elapsed = asyncio.get_event_loop().time() - start_time
        
        # Should process 10k items in reasonable time
        assert elapsed < 30  # 30 seconds max
        assert job.progress["processing_rate"] > 100  # >100 items/second
        assert job.status == BatchStatus.COMPLETED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])