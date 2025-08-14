"""
Google Drive Sync Worker

Background worker that processes Drive sync tasks from the queue.
Handles file streaming, processing, and memory creation.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from app.services.task_queue import TaskQueue, TaskType, TaskStatus
from app.services.gdrive.streaming_service import GoogleDriveStreamingService
from app.services.gdrive.file_processor import DriveFileProcessor
from app.services.memory_service import MemoryService
from app.services.service_factory import get_memory_service
from app.utils.logging_config import get_logger
from app.services.gdrive.auth_service import GoogleAuthService
from app.core.dependencies import get_google_auth_service_dep

logger = get_logger(__name__)


class GoogleDriveSyncWorker:
    """
    Worker that processes Google Drive sync tasks from the queue.
    
    Responsibilities:
    - Pull tasks from the queue
    - Stream files from Google Drive
    - Process content and create memories
    - Handle webhooks and change notifications
    - Manage task lifecycle (complete/retry/fail)
    """
    
    def __init__(
        self,
        task_queue: TaskQueue,
        streaming_service: GoogleDriveStreamingService,
        memory_service: MemoryService,
        auth_service: GoogleAuthService
    ):
        """
        Initialize the sync worker.
        
        Args:
            task_queue: Task queue for getting jobs
            streaming_service: Service for streaming Drive files
            memory_service: Service for creating memories
            auth_service: Service for Google authentication
        """
        self.task_queue = task_queue
        self.streaming_service = streaming_service
        self.memory_service = memory_service
        self.auth_service = auth_service
        self.file_processor = DriveFileProcessor(memory_service)
        self.running = False
        
    async def start(self, max_workers: int = 3):
        """
        Start the worker pool.
        
        Args:
            max_workers: Maximum number of concurrent workers
        """
        self.running = True
        logger.info(f"Starting Drive sync worker pool with {max_workers} workers")
        
        # Create worker tasks
        workers = []
        for i in range(max_workers):
            worker = asyncio.create_task(self._worker_loop(worker_id=i))
            workers.append(worker)
        
        # Wait for all workers
        try:
            await asyncio.gather(*workers)
        except Exception as e:
            logger.error(f"Worker pool error: {e}")
        finally:
            self.running = False
    
    async def stop(self):
        """Stop the worker pool"""
        self.running = False
        logger.info("Stopping Drive sync worker pool")
    
    async def _worker_loop(self, worker_id: int):
        """
        Main worker loop that processes tasks.
        
        Args:
            worker_id: Worker identifier for logging
        """
        logger.info(f"Worker {worker_id} started")
        
        while self.running:
            try:
                # Get next task from queue
                task = await self.task_queue.dequeue()
                
                if not task:
                    # No tasks available, wait a bit
                    await asyncio.sleep(1)
                    continue
                
                logger.info(f"Worker {worker_id} processing task", extra={
                    "task_id": task["id"],
                    "task_type": task["type"]
                })
                
                # Process based on task type
                task_type = TaskType(task["type"])
                
                if task_type == TaskType.DRIVE_FILE_SYNC:
                    await self._process_file_sync(task)
                elif task_type == TaskType.DRIVE_FOLDER_SYNC:
                    await self._process_folder_sync(task)
                elif task_type == TaskType.DRIVE_WEBHOOK:
                    await self._process_webhook(task)
                else:
                    logger.warning(f"Unknown task type: {task_type}")
                    await self.task_queue.fail(task["id"], f"Unknown task type: {task_type}")
                
            except Exception as e:
                logger.exception(f"Worker {worker_id} error: {e}")
                if task:
                    await self.task_queue.fail(task["id"], str(e))
        
        logger.info(f"Worker {worker_id} stopped")
    
    async def _process_file_sync(self, task: Dict[str, Any]):
        """
        Process a file sync task.
        
        Args:
            task: Task data containing file_id, user_id, etc.
        """
        task_id = task["id"]
        payload = task["payload"]
        user_id = task.get("user_id")
        
        file_id = payload.get("file_id")
        processing_options = payload.get("processing_options", {})
        
        try:
            # Get user credentials
            credentials = await self.auth_service.get_user_credentials(user_id)
            if not credentials:
                raise Exception(f"No credentials found for user {user_id}")
            
            # Initialize streaming service with credentials
            await self.streaming_service.initialize(credentials)
            
            # Get file metadata
            file_metadata = await self.streaming_service.get_file_metadata(file_id)
            
            logger.info(f"Processing file: {file_metadata.get('name')}", extra={
                "file_id": file_id,
                "mime_type": file_metadata.get("mimeType"),
                "size": file_metadata.get("size")
            })
            
            # Check if file was already processed (using MD5)
            md5_checksum = file_metadata.get("md5Checksum")
            if md5_checksum:
                existing = await self.memory_service._find_memory_by_checksum(md5_checksum)
                if existing:
                    logger.info(f"File already processed, skipping", extra={
                        "file_id": file_id,
                        "md5_checksum": md5_checksum,
                        "existing_memory_id": existing
                    })
                    await self.task_queue.complete(task_id, {
                        "status": "skipped",
                        "reason": "already_processed",
                        "memory_id": existing
                    })
                    return
            
            # Stream the file
            stream = self.streaming_service.stream_file(file_id)
            
            # Prepare metadata for memory creation
            memory_metadata = {
                "source": "google_drive",
                "file_id": file_id,
                "file_name": file_metadata.get("name"),
                "mime_type": file_metadata.get("mimeType"),
                "size": file_metadata.get("size"),
                "modified_time": file_metadata.get("modifiedTime"),
                "parents": file_metadata.get("parents", []),
                "web_view_link": file_metadata.get("webViewLink"),
                "md5_checksum": md5_checksum,
                "user_id": user_id,
                "synced_at": datetime.utcnow().isoformat()
            }
            
            # Determine if we should chunk the content
            file_size = file_metadata.get("size", 0)
            if isinstance(file_size, str):
                file_size = int(file_size)
            
            if file_size > 10000:  # Files larger than 10KB get chunked
                # Create multiple memories from chunks
                memory_ids = await self.memory_service.create_memories_from_chunks(
                    stream=stream,
                    metadata=memory_metadata,
                    chunk_size=processing_options.get("chunk_size", 1000)
                )
                
                result = {
                    "status": "success",
                    "memories_created": len(memory_ids),
                    "memory_ids": memory_ids
                }
            else:
                # Create single memory
                memory_id = await self.memory_service.create_memory_from_stream(
                    stream=stream,
                    metadata=memory_metadata
                )
                
                result = {
                    "status": "success",
                    "memories_created": 1,
                    "memory_ids": [memory_id]
                }
            
            # Mark task as completed
            await self.task_queue.complete(task_id, result)
            
            logger.info(f"File sync completed", extra={
                "task_id": task_id,
                "file_id": file_id,
                "memories_created": result["memories_created"]
            })
            
        except Exception as e:
            logger.error(f"File sync failed: {e}", extra={
                "task_id": task_id,
                "file_id": file_id,
                "error": str(e)
            })
            await self.task_queue.fail(task_id, str(e))
    
    async def _process_folder_sync(self, task: Dict[str, Any]):
        """
        Process a folder sync task.
        
        Args:
            task: Task data containing folder_id, recursive flag, etc.
        """
        task_id = task["id"]
        payload = task["payload"]
        user_id = task.get("user_id")
        
        folder_id = payload.get("folder_id")
        recursive = payload.get("recursive", False)
        file_types = payload.get("file_types")
        processing_options = payload.get("processing_options", {})
        
        try:
            # Get user credentials
            credentials = await self.auth_service.get_user_credentials(user_id)
            if not credentials:
                raise Exception(f"No credentials found for user {user_id}")
            
            # Initialize streaming service
            await self.streaming_service.initialize(credentials)
            
            logger.info(f"Processing folder", extra={
                "folder_id": folder_id,
                "recursive": recursive,
                "file_types": file_types
            })
            
            # Process all files in the folder
            results = []
            async for file_result in self.streaming_service.process_folder(
                folder_id=folder_id,
                recursive=recursive,
                file_types=file_types
            ):
                if file_result.get("status") == "success":
                    # Create memory from the file content
                    content = file_result.get("content")
                    if content:
                        # Create a stream from the content
                        async def content_stream():
                            yield content
                        
                        memory_metadata = {
                            "source": "google_drive",
                            "file_id": file_result.get("file_id"),
                            "file_name": file_result.get("file_name"),
                            "mime_type": file_result.get("mime_type"),
                            "folder_id": folder_id,
                            "user_id": user_id
                        }
                        
                        memory_id = await self.memory_service.create_memory_from_stream(
                            stream=content_stream(),
                            metadata=memory_metadata
                        )
                        
                        results.append({
                            "file_name": file_result.get("file_name"),
                            "memory_id": memory_id,
                            "status": "success"
                        })
                else:
                    results.append({
                        "file_name": file_result.get("file_name"),
                        "status": "error",
                        "error": file_result.get("error")
                    })
            
            # Calculate summary
            success_count = sum(1 for r in results if r["status"] == "success")
            error_count = sum(1 for r in results if r["status"] == "error")
            
            result = {
                "status": "success",
                "files_processed": len(results),
                "success_count": success_count,
                "error_count": error_count,
                "results": results
            }
            
            await self.task_queue.complete(task_id, result)
            
            logger.info(f"Folder sync completed", extra={
                "task_id": task_id,
                "folder_id": folder_id,
                "files_processed": len(results),
                "success_count": success_count,
                "error_count": error_count
            })
            
        except Exception as e:
            logger.error(f"Folder sync failed: {e}", extra={
                "task_id": task_id,
                "folder_id": folder_id,
                "error": str(e)
            })
            await self.task_queue.fail(task_id, str(e))
    
    async def _process_webhook(self, task: Dict[str, Any]):
        """
        Process a webhook notification task.
        
        Args:
            task: Task data containing webhook payload
        """
        task_id = task["id"]
        payload = task["payload"]
        user_id = task.get("user_id")
        
        resource_id = payload.get("resource_id")
        resource_state = payload.get("resource_state")
        changes = payload.get("changes", [])
        
        try:
            logger.info(f"Processing webhook", extra={
                "resource_id": resource_id,
                "resource_state": resource_state,
                "changes": changes
            })
            
            # Handle different types of changes
            if resource_state == "sync":
                # Initial sync notification, no action needed
                result = {"status": "sync_acknowledged"}
                
            elif "content_modified" in changes:
                # File content was modified, re-sync the file
                file_sync_task = {
                    "file_id": resource_id,
                    "processing_options": {
                        "force_update": True
                    }
                }
                
                # Enqueue a file sync task
                new_task_id = await self.task_queue.enqueue(
                    task_type=TaskType.DRIVE_FILE_SYNC,
                    payload=file_sync_task,
                    user_id=user_id
                )
                
                result = {
                    "status": "file_sync_queued",
                    "sync_task_id": new_task_id
                }
                
            elif "moved" in changes:
                # File was moved, update metadata
                # This would update the parent folder relationships
                result = {"status": "metadata_update_needed"}
                
            else:
                result = {"status": "no_action_needed"}
            
            await self.task_queue.complete(task_id, result)
            
            logger.info(f"Webhook processed", extra={
                "task_id": task_id,
                "result": result
            })
            
        except Exception as e:
            logger.error(f"Webhook processing failed: {e}", extra={
                "task_id": task_id,
                "error": str(e)
            })
            await self.task_queue.fail(task_id, str(e))