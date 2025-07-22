"""
Background worker implementations for automated memory management.

These workers handle:
- Memory consolidation and deduplication
- Log and data cleanup
- Importance score updates
- Memory aging calculations
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.database import get_db
from app.services.memory_merger import MemoryMergerService, MergeStrategy
from app.services.deduplication_orchestrator import DeduplicationOrchestrator
from app.algorithms.memory_aging_algorithms import MemoryAgingAlgorithms
from app.importance_engine import ImportanceEngine

logger = logging.getLogger(__name__)


class ConsolidationWorker:
    """
    Background worker for memory consolidation and deduplication.
    
    Features:
    - Automatic duplicate detection and merging
    - Configurable merge strategies
    - Performance monitoring
    - Progress tracking
    """
    
    def __init__(self, batch_size: int = 100, similarity_threshold: float = 0.95):
        self.batch_size = batch_size
        self.similarity_threshold = similarity_threshold
        self.merger_service = MemoryMergerService()
        self.dedup_orchestrator = DeduplicationOrchestrator()
        
    async def run_consolidation(self, db: Any, **kwargs) -> Dict[str, Any]:
        """
        Main consolidation task that runs periodically.
        
        Args:
            db: Database connection
            **kwargs: Additional parameters from scheduler
            
        Returns:
            Dict with consolidation results
        """
        start_time = datetime.now()
        logger.info("Starting memory consolidation task...")
        
        try:
            # Run deduplication scan
            scan_config = {
                "similarity_threshold": self.similarity_threshold,
                "batch_size": self.batch_size,
                "detection_methods": ["semantic", "fuzzy"],
                "merge_strategy": MergeStrategy.SMART_MERGE.value
            }
            
            # Execute deduplication
            results = await self.dedup_orchestrator.process_deduplication(
                db=db,
                config=scan_config,
                dry_run=False  # Actually perform merges
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Consolidation completed: {results['merged_count']} memories merged")
            
            return {
                "status": "completed",
                "start_time": start_time.isoformat(),
                "execution_time": execution_time,
                "memories_scanned": results.get("total_scanned", 0),
                "duplicates_found": results.get("duplicates_found", 0),
                "memories_merged": results.get("merged_count", 0),
                "errors": results.get("errors", [])
            }
            
        except Exception as e:
            logger.error(f"Consolidation task failed: {e}")
            raise


class CleanupWorker:
    """
    Background worker for cleanup operations.
    
    Handles:
    - Log cleanup (access logs, operation logs)
    - Orphaned data removal
    - Temporary file cleanup
    - Old backup removal
    """
    
    def __init__(self, retention_days: int = 90):
        self.retention_days = retention_days
        
    async def run_cleanup(self, db: Any, **kwargs) -> Dict[str, Any]:
        """
        Main cleanup task that runs periodically.
        
        Args:
            db: Database connection
            **kwargs: Additional parameters from scheduler
            
        Returns:
            Dict with cleanup results
        """
        start_time = datetime.now()
        logger.info("Starting cleanup task...")
        
        cleaned_items = {
            "access_logs": 0,
            "operation_logs": 0,
            "orphaned_embeddings": 0,
            "temporary_files": 0
        }
        
        try:
            # Clean old access logs
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            
            # Access logs cleanup
            query = """
                DELETE FROM access_logs 
                WHERE accessed_at < $1
                RETURNING id
            """
            result = await db.fetch(query, cutoff_date)
            cleaned_items["access_logs"] = len(result)
            
            # Operation logs cleanup
            query = """
                DELETE FROM bulk_operation_logs
                WHERE completed_at < $1 AND status IN ('completed', 'failed')
                RETURNING id
            """
            result = await db.fetch(query, cutoff_date)
            cleaned_items["operation_logs"] = len(result)
            
            # Clean orphaned embeddings (memories that no longer exist)
            query = """
                DELETE FROM memory_embeddings
                WHERE memory_id NOT IN (SELECT id FROM memories)
                RETURNING memory_id
            """
            result = await db.fetch(query)
            cleaned_items["orphaned_embeddings"] = len(result)
            
            # Clean old importance recalculation logs
            query = """
                DELETE FROM importance_recalculation_logs
                WHERE recalculated_at < $1
                RETURNING id
            """
            result = await db.fetch(query, cutoff_date)
            cleaned_items["importance_logs"] = len(result)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            total_cleaned = sum(cleaned_items.values())
            logger.info(f"Cleanup completed: {total_cleaned} items removed")
            
            return {
                "status": "completed",
                "start_time": start_time.isoformat(),
                "execution_time": execution_time,
                "retention_days": self.retention_days,
                "cleaned_items": cleaned_items,
                "total_cleaned": total_cleaned
            }
            
        except Exception as e:
            logger.error(f"Cleanup task failed: {e}")
            raise


class ImportanceUpdateWorker:
    """
    Background worker for updating memory importance scores.
    
    Features:
    - Recalculates importance based on access patterns
    - Applies decay for unused memories
    - Updates consolidation scores
    """
    
    def __init__(self, batch_size: int = 500):
        self.batch_size = batch_size
        self.importance_engine = ImportanceEngine()
        
    async def run_importance_update(self, db: Any, **kwargs) -> Dict[str, Any]:
        """
        Main importance update task.
        
        Args:
            db: Database connection
            **kwargs: Additional parameters from scheduler
            
        Returns:
            Dict with update results
        """
        start_time = datetime.now()
        logger.info("Starting importance update task...")
        
        try:
            # Get memories that need importance updates
            # Focus on memories that haven't been updated recently
            query = """
                SELECT id, importance_score, created_at, 
                       last_accessed, access_count, content_length
                FROM memories
                WHERE importance_last_updated < $1
                   OR importance_last_updated IS NULL
                ORDER BY importance_last_updated ASC NULLS FIRST
                LIMIT $2
            """
            
            update_cutoff = datetime.now() - timedelta(days=7)
            memories = await db.fetch(query, update_cutoff, self.batch_size)
            
            updated_count = 0
            total_change = 0.0
            
            for memory in memories:
                # Calculate new importance
                old_score = memory['importance_score']
                
                # Use the importance engine's calculation
                factors = {
                    'base_importance': old_score,
                    'access_count': memory['access_count'] or 0,
                    'days_since_creation': (datetime.now() - memory['created_at']).days,
                    'days_since_access': (
                        (datetime.now() - memory['last_accessed']).days 
                        if memory['last_accessed'] else 365
                    ),
                    'content_length': memory['content_length'] or 0
                }
                
                new_score = await self.importance_engine.calculate_importance(
                    db, memory['id'], factors
                )
                
                # Update if changed significantly
                if abs(new_score - old_score) > 0.1:
                    update_query = """
                        UPDATE memories
                        SET importance_score = $1,
                            importance_last_updated = $2
                        WHERE id = $3
                    """
                    await db.execute(update_query, new_score, datetime.now(), memory['id'])
                    
                    updated_count += 1
                    total_change += abs(new_score - old_score)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Importance update completed: {updated_count} memories updated")
            
            return {
                "status": "completed",
                "start_time": start_time.isoformat(),
                "execution_time": execution_time,
                "memories_processed": len(memories),
                "memories_updated": updated_count,
                "average_change": total_change / updated_count if updated_count > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Importance update task failed: {e}")
            raise


class MemoryAgingWorker:
    """
    Background worker for memory aging calculations.
    
    Features:
    - Applies cognitive aging models
    - Updates memory strength scores
    - Identifies memories for archival
    - Calculates optimal review times
    """
    
    def __init__(self, batch_size: int = 200):
        self.batch_size = batch_size
        self.aging_algorithms = MemoryAgingAlgorithms()
        
    async def run_aging_update(self, db: Any, **kwargs) -> Dict[str, Any]:
        """
        Main memory aging task.
        
        Args:
            db: Database connection
            **kwargs: Additional parameters from scheduler
            
        Returns:
            Dict with aging results
        """
        start_time = datetime.now()
        logger.info("Starting memory aging task...")
        
        try:
            # Get memories for aging calculation
            query = """
                SELECT m.id, m.created_at, m.last_accessed, m.access_count,
                       m.importance_score, m.content, ma.memory_type,
                       ma.initial_strength, ma.current_strength,
                       ma.last_review, ma.review_count
                FROM memories m
                LEFT JOIN memory_aging ma ON m.id = ma.memory_id
                WHERE ma.last_calculated < $1 
                   OR ma.last_calculated IS NULL
                ORDER BY ma.last_calculated ASC NULLS FIRST
                LIMIT $2
            """
            
            aging_cutoff = datetime.now() - timedelta(days=1)
            memories = await db.fetch(query, aging_cutoff, self.batch_size)
            
            results = {
                "processed": 0,
                "strength_updates": 0,
                "archival_candidates": 0,
                "review_scheduled": 0
            }
            
            for memory in memories:
                # Calculate aging metrics
                memory_data = {
                    "id": memory['id'],
                    "created_at": memory['created_at'],
                    "last_accessed": memory['last_accessed'],
                    "access_count": memory['access_count'] or 0,
                    "importance_score": memory['importance_score'],
                    "initial_strength": memory['initial_strength'] or 1.0,
                    "current_strength": memory['current_strength'] or 1.0,
                    "review_count": memory['review_count'] or 0
                }
                
                # Apply aging algorithm
                aging_result = self.aging_algorithms.calculate_memory_strength(
                    memory_data,
                    algorithm="adaptive"  # Uses best algorithm for memory type
                )
                
                # Update or insert aging data
                if memory['memory_type']:
                    # Update existing
                    update_query = """
                        UPDATE memory_aging
                        SET current_strength = $1,
                            consolidation_score = $2,
                            predicted_decay_rate = $3,
                            next_review_date = $4,
                            strength_category = $5,
                            last_calculated = $6
                        WHERE memory_id = $7
                    """
                    await db.execute(
                        update_query,
                        aging_result['current_strength'],
                        aging_result['consolidation_score'],
                        aging_result['decay_rate'],
                        aging_result['next_review'],
                        aging_result['strength_category'],
                        datetime.now(),
                        memory['id']
                    )
                else:
                    # Insert new
                    insert_query = """
                        INSERT INTO memory_aging (
                            memory_id, memory_type, initial_strength,
                            current_strength, consolidation_score,
                            predicted_decay_rate, next_review_date,
                            strength_category, last_calculated
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """
                    await db.execute(
                        insert_query,
                        memory['id'],
                        self._determine_memory_type(memory),
                        aging_result['initial_strength'],
                        aging_result['current_strength'],
                        aging_result['consolidation_score'],
                        aging_result['decay_rate'],
                        aging_result['next_review'],
                        aging_result['strength_category'],
                        datetime.now()
                    )
                
                results["processed"] += 1
                
                # Track special cases
                if aging_result['current_strength'] < 0.3:
                    results["archival_candidates"] += 1
                
                if aging_result['next_review']:
                    results["review_scheduled"] += 1
                
                if abs(aging_result['current_strength'] - (memory['current_strength'] or 1.0)) > 0.1:
                    results["strength_updates"] += 1
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Memory aging completed: {results['processed']} memories processed")
            
            return {
                "status": "completed",
                "start_time": start_time.isoformat(),
                "execution_time": execution_time,
                **results
            }
            
        except Exception as e:
            logger.error(f"Memory aging task failed: {e}")
            raise
    
    def _determine_memory_type(self, memory: Dict[str, Any]) -> str:
        """Determine memory type based on content and metadata"""
        content = memory.get('content', '').lower()
        
        # Simple heuristic for memory type
        if any(word in content for word in ['remember', 'event', 'happened', 'did']):
            return "episodic"
        elif any(word in content for word in ['how to', 'procedure', 'steps', 'method']):
            return "procedural"
        else:
            return "semantic"


# Singleton instances for global access
consolidation_worker = ConsolidationWorker()
cleanup_worker = CleanupWorker()
importance_worker = ImportanceUpdateWorker()
aging_worker = MemoryAgingWorker()