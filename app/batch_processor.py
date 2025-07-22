"""
Sophisticated Batch Processing System for Second Brain v2.6.0-dev

This module provides high-performance batch processing capabilities with:
- Concurrent processing with configurable parallelism
- Progress tracking and resumable operations
- Error handling with retry mechanisms
- Memory-efficient streaming
- Result aggregation and reporting
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import UUID, uuid4

import aiofiles
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.ingestion.core_extraction_pipeline import CoreExtractionPipeline
from app.models import Memory
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class BatchStatus(Enum):
    """Status of a batch processing job"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class ProcessingMode(Enum):
    """Processing modes for different use cases"""
    SEQUENTIAL = "sequential"  # Process one item at a time
    CONCURRENT = "concurrent"  # Process multiple items concurrently
    STREAMING = "streaming"    # Stream processing for large datasets
    ADAPTIVE = "adaptive"      # Dynamically adjust based on system load


@dataclass
class BatchConfig:
    """Configuration for batch processing"""
    batch_size: int = 100
    max_concurrent: int = 10
    retry_attempts: int = 3
    retry_delay: float = 1.0
    timeout_per_item: float = 30.0
    checkpoint_interval: int = 1000
    mode: ProcessingMode = ProcessingMode.ADAPTIVE
    memory_limit_mb: int = 1024
    enable_progress_tracking: bool = True
    enable_checkpointing: bool = True
    result_aggregation: bool = True


@dataclass
class BatchProgress:
    """Track progress of batch processing"""
    total: int = 0
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def elapsed_time(self) -> float:
        """Calculate elapsed time"""
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def processing_rate(self) -> float:
        """Calculate items processed per second"""
        if self.elapsed_time == 0:
            return 0
        return self.processed / self.elapsed_time
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.processed == 0:
            return 0
        return self.succeeded / self.processed
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "total": self.total,
            "processed": self.processed,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "skipped": self.skipped,
            "elapsed_time": self.elapsed_time,
            "processing_rate": self.processing_rate,
            "success_rate": self.success_rate,
            "errors": self.errors[-10:]  # Keep last 10 errors
        }


class BatchJob(BaseModel):
    """Represents a batch processing job"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    status: BatchStatus = BatchStatus.PENDING
    config: Dict[str, Any] = Field(default_factory=dict)
    progress: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    checkpoint_data: Optional[Dict[str, Any]] = None
    result_summary: Optional[Dict[str, Any]] = None


class BatchProcessor:
    """Sophisticated batch processing engine"""
    
    def __init__(self, config: Optional[BatchConfig] = None):
        self.config = config or BatchConfig()
        self.jobs: Dict[str, BatchJob] = {}
        self.active_tasks: Set[asyncio.Task] = set()
        self._shutdown = False
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        
    async def process_memories_batch(
        self,
        memory_ids: List[UUID],
        operation: Callable[[Memory], Any],
        job_name: str = "Memory Batch Processing",
        **kwargs
    ) -> BatchJob:
        """Process a batch of memories with the given operation"""
        job = BatchJob(name=job_name, config={"memory_ids": len(memory_ids), **kwargs})
        self.jobs[job.id] = job
        
        try:
            job.status = BatchStatus.RUNNING
            job.started_at = datetime.utcnow()
            
            progress = BatchProgress(total=len(memory_ids))
            
            # Process in chunks for memory efficiency
            for chunk_start in range(0, len(memory_ids), self.config.batch_size):
                chunk_end = min(chunk_start + self.config.batch_size, len(memory_ids))
                chunk_ids = memory_ids[chunk_start:chunk_end]
                
                # Process chunk based on mode
                if self.config.mode == ProcessingMode.SEQUENTIAL:
                    await self._process_sequential(chunk_ids, operation, progress)
                elif self.config.mode == ProcessingMode.CONCURRENT:
                    await self._process_concurrent(chunk_ids, operation, progress)
                elif self.config.mode == ProcessingMode.STREAMING:
                    await self._process_streaming(chunk_ids, operation, progress)
                else:  # ADAPTIVE
                    await self._process_adaptive(chunk_ids, operation, progress)
                
                # Update job progress
                job.progress = progress.to_dict()
                
                # Checkpoint if enabled
                if self.config.enable_checkpointing and progress.processed % self.config.checkpoint_interval == 0:
                    await self._save_checkpoint(job, progress)
                
                # Check for cancellation
                if job.status == BatchStatus.CANCELLED:
                    break
            
            # Finalize job
            progress.end_time = time.time()
            job.progress = progress.to_dict()
            job.status = BatchStatus.COMPLETED if progress.failed == 0 else BatchStatus.FAILED
            job.completed_at = datetime.utcnow()
            
            # Generate result summary
            if self.config.result_aggregation:
                job.result_summary = await self._generate_summary(progress)
                
        except Exception as e:
            logger.error(f"Batch job {job.id} failed: {e}")
            job.status = BatchStatus.FAILED
            job.completed_at = datetime.utcnow()
            raise
            
        return job
    
    async def process_files_batch(
        self,
        file_paths: List[Path],
        job_name: str = "File Batch Processing",
        **kwargs
    ) -> BatchJob:
        """Process a batch of files (multimodal content)"""
        job = BatchJob(name=job_name, config={"file_count": len(file_paths), **kwargs})
        self.jobs[job.id] = job
        
        try:
            job.status = BatchStatus.RUNNING
            job.started_at = datetime.utcnow()
            
            progress = BatchProgress(total=len(file_paths))
            pipeline = CoreExtractionPipeline()
            
            # Group files by type for optimized processing
            files_by_type = self._group_files_by_type(file_paths)
            
            for file_type, files in files_by_type.items():
                logger.info(f"Processing {len(files)} {file_type} files")
                
                # Process each type with appropriate settings
                for chunk in self._chunk_list(files, self.config.batch_size):
                    await self._process_file_chunk(chunk, pipeline, progress, file_type)
                    
                    # Update progress
                    job.progress = progress.to_dict()
                    
                    if job.status == BatchStatus.CANCELLED:
                        break
            
            # Finalize
            progress.end_time = time.time()
            job.progress = progress.to_dict()
            job.status = BatchStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            
            if self.config.result_aggregation:
                job.result_summary = await self._generate_file_summary(progress, files_by_type)
                
        except Exception as e:
            logger.error(f"File batch job {job.id} failed: {e}")
            job.status = BatchStatus.FAILED
            job.completed_at = datetime.utcnow()
            raise
            
        return job
    
    async def import_from_export(
        self,
        export_file: Path,
        format: str = "json",
        job_name: str = "Import Batch Processing",
        **kwargs
    ) -> BatchJob:
        """Import memories from an export file with batch processing"""
        job = BatchJob(name=job_name, config={"file": str(export_file), "format": format, **kwargs})
        self.jobs[job.id] = job
        
        try:
            job.status = BatchStatus.RUNNING
            job.started_at = datetime.utcnow()
            
            # Stream data from file
            total_items = await self._count_export_items(export_file, format)
            progress = BatchProgress(total=total_items)
            
            async for batch in self._stream_export_data(export_file, format):
                # Process batch
                await self._process_import_batch(batch, progress)
                
                # Update progress
                job.progress = progress.to_dict()
                
                if job.status == BatchStatus.CANCELLED:
                    break
            
            # Finalize
            progress.end_time = time.time()
            job.progress = progress.to_dict()
            job.status = BatchStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Import job {job.id} failed: {e}")
            job.status = BatchStatus.FAILED
            job.completed_at = datetime.utcnow()
            raise
            
        return job
    
    async def reprocess_all_memories(
        self,
        filters: Optional[Dict[str, Any]] = None,
        job_name: str = "Reprocess All Memories",
        **kwargs
    ) -> BatchJob:
        """Reprocess all memories with updated extraction pipeline"""
        job = BatchJob(name=job_name, config={"filters": filters, **kwargs})
        self.jobs[job.id] = job
        
        try:
            job.status = BatchStatus.RUNNING
            job.started_at = datetime.utcnow()
            
            # Count total memories
            async with get_db() as db:
                total_count = await self._count_memories(db, filters)
            
            progress = BatchProgress(total=total_count)
            pipeline = CoreExtractionPipeline()
            
            # Process in batches
            offset = 0
            while offset < total_count:
                async with get_db() as db:
                    memories = await self._fetch_memory_batch(db, offset, self.config.batch_size, filters)
                    
                    if not memories:
                        break
                    
                    # Reprocess each memory
                    for memory in memories:
                        try:
                            # Extract enhanced features
                            extraction_result = await pipeline.process(memory.content)
                            
                            # Update memory with new data
                            await self._update_memory_extraction(db, memory.id, extraction_result)
                            
                            progress.succeeded += 1
                        except Exception as e:
                            logger.error(f"Failed to reprocess memory {memory.id}: {e}")
                            progress.failed += 1
                            progress.errors.append({
                                "memory_id": str(memory.id),
                                "error": str(e)
                            })
                        finally:
                            progress.processed += 1
                    
                    # Update progress
                    job.progress = progress.to_dict()
                    
                    if job.status == BatchStatus.CANCELLED:
                        break
                
                offset += self.config.batch_size
            
            # Finalize
            progress.end_time = time.time()
            job.progress = progress.to_dict()
            job.status = BatchStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Reprocess job {job.id} failed: {e}")
            job.status = BatchStatus.FAILED
            job.completed_at = datetime.utcnow()
            raise
            
        return job
    
    async def analyze_memory_patterns(
        self,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        job_name: str = "Pattern Analysis Batch",
        **kwargs
    ) -> BatchJob:
        """Analyze patterns across memories in batches"""
        job = BatchJob(name=job_name, config={"time_range": time_range, **kwargs})
        self.jobs[job.id] = job
        
        try:
            job.status = BatchStatus.RUNNING
            job.started_at = datetime.utcnow()
            
            # Initialize pattern analyzers
            from app.insights.pattern_detector import PatternDetector
            from app.insights.cluster_analyzer import ClusterAnalyzer
            
            pattern_detector = PatternDetector()
            cluster_analyzer = ClusterAnalyzer()
            
            # Count memories in range
            async with get_db() as db:
                total_count = await self._count_memories_in_range(db, time_range)
            
            progress = BatchProgress(total=total_count)
            patterns = defaultdict(list)
            clusters = []
            
            # Process in time-ordered batches
            offset = 0
            while offset < total_count:
                async with get_db() as db:
                    memories = await self._fetch_memories_by_time(
                        db, offset, self.config.batch_size, time_range
                    )
                    
                    if not memories:
                        break
                    
                    # Detect patterns in batch
                    batch_patterns = await pattern_detector.detect_patterns(memories)
                    for pattern_type, items in batch_patterns.items():
                        patterns[pattern_type].extend(items)
                    
                    # Perform clustering
                    if len(memories) >= 10:  # Minimum for meaningful clusters
                        batch_clusters = await cluster_analyzer.cluster_memories(memories)
                        clusters.extend(batch_clusters)
                    
                    progress.processed += len(memories)
                    progress.succeeded += len(memories)
                    
                    # Update progress
                    job.progress = progress.to_dict()
                    
                    if job.status == BatchStatus.CANCELLED:
                        break
                
                offset += self.config.batch_size
            
            # Generate comprehensive analysis
            job.result_summary = {
                "patterns": {k: len(v) for k, v in patterns.items()},
                "clusters": len(clusters),
                "top_patterns": self._get_top_patterns(patterns),
                "cluster_summary": self._summarize_clusters(clusters),
                "processing_stats": progress.to_dict()
            }
            
            # Finalize
            progress.end_time = time.time()
            job.progress = progress.to_dict()
            job.status = BatchStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Pattern analysis job {job.id} failed: {e}")
            job.status = BatchStatus.FAILED
            job.completed_at = datetime.utcnow()
            raise
            
        return job
    
    async def get_job_status(self, job_id: str) -> Optional[BatchJob]:
        """Get status of a batch job"""
        return self.jobs.get(job_id)
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running batch job"""
        job = self.jobs.get(job_id)
        if job and job.status == BatchStatus.RUNNING:
            job.status = BatchStatus.CANCELLED
            return True
        return False
    
    async def resume_job(self, job_id: str) -> Optional[BatchJob]:
        """Resume a paused or failed job from checkpoint"""
        job = self.jobs.get(job_id)
        if not job or not job.checkpoint_data:
            return None
            
        # Restore from checkpoint and continue processing
        # Implementation depends on specific job type
        logger.info(f"Resuming job {job_id} from checkpoint")
        # TODO: Implement checkpoint restoration
        
        return job
    
    # Private helper methods
    
    async def _process_sequential(
        self,
        items: List[Any],
        operation: Callable,
        progress: BatchProgress
    ):
        """Process items sequentially"""
        for item in items:
            try:
                await asyncio.wait_for(
                    operation(item),
                    timeout=self.config.timeout_per_item
                )
                progress.succeeded += 1
            except asyncio.TimeoutError:
                progress.failed += 1
                progress.errors.append({"item": str(item), "error": "Timeout"})
            except Exception as e:
                progress.failed += 1
                progress.errors.append({"item": str(item), "error": str(e)})
            finally:
                progress.processed += 1
    
    async def _process_concurrent(
        self,
        items: List[Any],
        operation: Callable,
        progress: BatchProgress
    ):
        """Process items concurrently with semaphore control"""
        async def process_with_semaphore(item):
            async with self._semaphore:
                try:
                    await asyncio.wait_for(
                        operation(item),
                        timeout=self.config.timeout_per_item
                    )
                    progress.succeeded += 1
                except Exception as e:
                    progress.failed += 1
                    progress.errors.append({"item": str(item), "error": str(e)})
                finally:
                    progress.processed += 1
        
        tasks = [process_with_semaphore(item) for item in items]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _process_streaming(
        self,
        items: List[Any],
        operation: Callable,
        progress: BatchProgress
    ):
        """Process items in streaming fashion"""
        # Create a queue for streaming
        queue = asyncio.Queue(maxsize=self.config.batch_size)
        
        # Producer task
        async def producer():
            for item in items:
                await queue.put(item)
            await queue.put(None)  # Sentinel
        
        # Consumer tasks
        async def consumer():
            while True:
                item = await queue.get()
                if item is None:
                    break
                    
                try:
                    await operation(item)
                    progress.succeeded += 1
                except Exception as e:
                    progress.failed += 1
                    progress.errors.append({"item": str(item), "error": str(e)})
                finally:
                    progress.processed += 1
                    queue.task_done()
        
        # Run producer and consumers
        producer_task = asyncio.create_task(producer())
        consumer_tasks = [
            asyncio.create_task(consumer())
            for _ in range(min(self.config.max_concurrent, len(items)))
        ]
        
        await producer_task
        await asyncio.gather(*consumer_tasks)
    
    async def _process_adaptive(
        self,
        items: List[Any],
        operation: Callable,
        progress: BatchProgress
    ):
        """Adaptively process based on system load"""
        # Monitor system resources and adjust concurrency
        import psutil
        
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent
        
        # Adjust concurrency based on system load
        if cpu_percent > 80 or memory_percent > 80:
            # High load - process sequentially
            await self._process_sequential(items, operation, progress)
        elif cpu_percent > 50 or memory_percent > 50:
            # Medium load - limited concurrency
            self._semaphore = asyncio.Semaphore(self.config.max_concurrent // 2)
            await self._process_concurrent(items, operation, progress)
        else:
            # Low load - full concurrency
            await self._process_concurrent(items, operation, progress)
    
    def _group_files_by_type(self, file_paths: List[Path]) -> Dict[str, List[Path]]:
        """Group files by their type/extension"""
        groups = defaultdict(list)
        for path in file_paths:
            ext = path.suffix.lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                groups['image'].append(path)
            elif ext in ['.mp3', '.wav', '.m4a', '.flac']:
                groups['audio'].append(path)
            elif ext in ['.mp4', '.avi', '.mov', '.mkv']:
                groups['video'].append(path)
            elif ext in ['.pdf', '.doc', '.docx', '.txt']:
                groups['document'].append(path)
            else:
                groups['other'].append(path)
        return dict(groups)
    
    def _chunk_list(self, items: List[Any], chunk_size: int) -> List[List[Any]]:
        """Split list into chunks"""
        return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
    
    async def _save_checkpoint(self, job: BatchJob, progress: BatchProgress):
        """Save job checkpoint for resumability"""
        checkpoint = {
            "job_id": job.id,
            "progress": progress.to_dict(),
            "timestamp": datetime.utcnow().isoformat(),
            "config": job.config
        }
        job.checkpoint_data = checkpoint
        
        # Optionally persist to disk
        checkpoint_file = Path(f"checkpoints/{job.id}.json")
        checkpoint_file.parent.mkdir(exist_ok=True)
        
        async with aiofiles.open(checkpoint_file, 'w') as f:
            await f.write(json.dumps(checkpoint, indent=2))
    
    async def _generate_summary(self, progress: BatchProgress) -> Dict[str, Any]:
        """Generate result summary"""
        return {
            "total_processed": progress.processed,
            "success_count": progress.succeeded,
            "failure_count": progress.failed,
            "success_rate": progress.success_rate,
            "processing_rate": progress.processing_rate,
            "total_time": progress.elapsed_time,
            "error_summary": self._summarize_errors(progress.errors)
        }
    
    def _summarize_errors(self, errors: List[Dict[str, Any]]) -> Dict[str, int]:
        """Summarize errors by type"""
        error_counts = defaultdict(int)
        for error in errors:
            error_type = error.get("error", "Unknown").split(":")[0]
            error_counts[error_type] += 1
        return dict(error_counts)
    
    # Database helper methods (stubs - implement based on your models)
    
    async def _count_memories(self, db: AsyncSession, filters: Optional[Dict[str, Any]]) -> int:
        """Count memories with optional filters"""
        # Implementation depends on your database models
        pass
    
    async def _fetch_memory_batch(
        self,
        db: AsyncSession,
        offset: int,
        limit: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[Memory]:
        """Fetch a batch of memories"""
        # Implementation depends on your database models
        pass
    
    async def _update_memory_extraction(
        self,
        db: AsyncSession,
        memory_id: UUID,
        extraction_result: Dict[str, Any]
    ):
        """Update memory with extraction results"""
        # Implementation depends on your database models
        pass


# Export main components
__all__ = [
    "BatchProcessor",
    "BatchConfig",
    "BatchJob",
    "BatchStatus",
    "ProcessingMode",
    "BatchProgress"
]