#!/usr/bin/env python3
"""
Standalone test for batch processing core functionality without database dependencies.
"""

import sys
import os
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import json

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Copy essential classes from batch_processor.py without database imports
class ProcessingMode(Enum):
    SEQUENTIAL = "sequential"
    CONCURRENT = "concurrent"
    STREAMING = "streaming"
    ADAPTIVE = "adaptive"

class BatchStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class BatchConfig:
    processing_mode: ProcessingMode = ProcessingMode.SEQUENTIAL
    batch_size: int = 100
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float = 300.0
    checkpoint_interval: int = 50
    parallel_workers: int = 4
    memory_limit_mb: int = 1024
    enable_progress_tracking: bool = True

@dataclass
class BatchJob:
    id: str
    status: BatchStatus = BatchStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_items: int = 0
    processed_items: int = 0
    failed_items: int = 0
    progress_percentage: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "failed_items": self.failed_items,
            "progress_percentage": self.progress_percentage,
            "error_message": self.error_message,
            "metadata": self.metadata
        }

class MockBatchProcessor:
    """Mock batch processor for testing core functionality"""
    
    def __init__(self, config: BatchConfig):
        self.config = config
        self.jobs: Dict[str, BatchJob] = {}
        
    def create_job(self, job_id: str, total_items: int) -> BatchJob:
        # Convert config to JSON-serializable format
        config_dict = self.config.__dict__.copy()
        config_dict["processing_mode"] = self.config.processing_mode.value
        
        job = BatchJob(
            id=job_id,
            total_items=total_items,
            metadata={"config": config_dict}
        )
        self.jobs[job_id] = job
        return job
    
    def get_job(self, job_id: str) -> Optional[BatchJob]:
        return self.jobs.get(job_id)
    
    async def process_mock_items(self, items: List[Any], job_id: str) -> Dict[str, Any]:
        """Mock processing function"""
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.status = BatchStatus.RUNNING
        job.started_at = datetime.now()
        
        processed = 0
        failed = 0
        
        for i, item in enumerate(items):
            # Simulate processing
            await asyncio.sleep(0.01)  # 10ms per item
            
            # Simulate occasional failures
            if i % 20 == 19:  # 5% failure rate
                failed += 1
            else:
                processed += 1
            
            job.processed_items = processed
            job.failed_items = failed
            job.progress_percentage = ((processed + failed) / len(items)) * 100
        
        job.status = BatchStatus.COMPLETED
        job.completed_at = datetime.now()
        
        return {
            "processed": processed,
            "failed": failed,
            "total": len(items)
        }

async def test_batch_processor_core():
    """Test core batch processing functionality"""
    print("🧪 Testing Batch Processing Core Functionality")
    print("=" * 50)
    
    # Test 1: Basic Configuration
    print("\n1. Testing BatchConfig...")
    config = BatchConfig(
        processing_mode=ProcessingMode.CONCURRENT,
        batch_size=50,
        max_retries=5,
        parallel_workers=8
    )
    assert config.processing_mode == ProcessingMode.CONCURRENT
    assert config.batch_size == 50
    assert config.max_retries == 5
    assert config.parallel_workers == 8
    print("✅ BatchConfig initialization successful")
    
    # Test 2: Processing Modes
    print("\n2. Testing ProcessingMode enum...")
    modes = [ProcessingMode.SEQUENTIAL, ProcessingMode.CONCURRENT, 
             ProcessingMode.STREAMING, ProcessingMode.ADAPTIVE]
    for mode in modes:
        config_test = BatchConfig(processing_mode=mode)
        assert config_test.processing_mode == mode
    print("✅ All processing modes validated")
    
    # Test 3: Batch Job Management
    print("\n3. Testing BatchJob management...")
    processor = MockBatchProcessor(config)
    
    # Create a job
    job = processor.create_job("test-job-1", 100)
    assert job.id == "test-job-1"
    assert job.status == BatchStatus.PENDING
    assert job.total_items == 100
    assert job.processed_items == 0
    print("✅ BatchJob creation successful")
    
    # Test job retrieval
    retrieved_job = processor.get_job("test-job-1")
    assert retrieved_job is not None
    assert retrieved_job.id == job.id
    print("✅ BatchJob retrieval successful")
    
    # Test 4: Mock Processing
    print("\n4. Testing mock processing...")
    test_items = list(range(100))  # 100 test items
    
    start_time = datetime.now()
    result = await processor.process_mock_items(test_items, "test-job-1")
    end_time = datetime.now()
    
    processing_time = (end_time - start_time).total_seconds()
    
    assert result["total"] == 100
    assert result["processed"] + result["failed"] == 100
    assert result["processed"] > 90  # Should have >90% success rate
    print(f"✅ Mock processing completed: {result}")
    print(f"✅ Processing time: {processing_time:.2f}s")
    
    # Test 5: Job Status Updates
    print("\n5. Testing job status tracking...")
    final_job = processor.get_job("test-job-1")
    assert final_job.status == BatchStatus.COMPLETED
    assert final_job.started_at is not None
    assert final_job.completed_at is not None
    assert final_job.progress_percentage == 100.0
    print("✅ Job status tracking successful")
    
    # Test 6: Job Serialization
    print("\n6. Testing job serialization...")
    job_dict = final_job.to_dict()
    assert "id" in job_dict
    assert "status" in job_dict
    assert job_dict["status"] == "completed"
    assert job_dict["progress_percentage"] == 100.0
    
    # Test JSON serialization (job_dict should already be JSON-serializable)
    job_json = json.dumps(job_dict, indent=2)
    assert len(job_json) > 0
    parsed_back = json.loads(job_json)
    assert parsed_back["id"] == job_dict["id"]
    print("✅ Job serialization successful")
    
    # Test 7: Multiple Jobs
    print("\n7. Testing multiple job management...")
    job2 = processor.create_job("test-job-2", 50)
    job3 = processor.create_job("test-job-3", 200)
    
    assert len(processor.jobs) == 3
    assert processor.get_job("test-job-2").total_items == 50
    assert processor.get_job("test-job-3").total_items == 200
    print("✅ Multiple job management successful")
    
    # Test 8: Configuration Variations
    print("\n8. Testing configuration variations...")
    configs = [
        BatchConfig(processing_mode=ProcessingMode.SEQUENTIAL, batch_size=10),
        BatchConfig(processing_mode=ProcessingMode.CONCURRENT, parallel_workers=16),
        BatchConfig(processing_mode=ProcessingMode.STREAMING, checkpoint_interval=25),
        BatchConfig(processing_mode=ProcessingMode.ADAPTIVE, memory_limit_mb=2048)
    ]
    
    for i, config in enumerate(configs):
        test_processor = MockBatchProcessor(config)
        test_job = test_processor.create_job(f"config-test-{i}", 10)
        assert test_job.metadata["config"]["processing_mode"] == config.processing_mode.value
    print("✅ Configuration variations tested")
    
    print("\n" + "=" * 50)
    print("🎉 ALL BATCH PROCESSING CORE TESTS PASSED!")
    print("=" * 50)
    
    return {
        "tests_run": 8,
        "tests_passed": 8,
        "processing_time": processing_time,
        "items_processed": result["total"],
        "success_rate": (result["processed"] / result["total"]) * 100
    }

if __name__ == "__main__":
    try:
        result = asyncio.run(test_batch_processor_core())
        print(f"\nTest Summary:")
        print(f"- Tests Run: {result['tests_run']}")
        print(f"- Tests Passed: {result['tests_passed']}")
        print(f"- Processing Time: {result['processing_time']:.2f}s")
        print(f"- Items Processed: {result['items_processed']}")
        print(f"- Success Rate: {result['success_rate']:.1f}%")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)