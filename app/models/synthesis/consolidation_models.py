"""Consolidation models for memory deduplication and merging"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MergeStrategy(str, Enum):
    """Strategy for merging duplicate memories"""
    KEEP_NEWEST = "keep_newest"
    KEEP_OLDEST = "keep_oldest"
    KEEP_HIGHEST_IMPORTANCE = "keep_highest_importance"
    MERGE_CONTENT = "merge_content"
    MANUAL = "manual"


class DuplicateGroup(BaseModel):
    """Group of duplicate memories"""
    group_id: str = Field(default_factory=lambda: f"dup_{datetime.now().timestamp()}")
    memory_ids: List[str]
    similarity_score: float
    suggested_action: MergeStrategy = MergeStrategy.KEEP_HIGHEST_IMPORTANCE
    metadata: Dict[str, Any] = {}


class ConsolidationRequest(BaseModel):
    """Request for memory consolidation"""
    user_id: Optional[str] = None
    memory_ids: Optional[List[str]] = None
    strategy: MergeStrategy = MergeStrategy.KEEP_HIGHEST_IMPORTANCE
    similarity_threshold: float = 0.85
    auto_merge: bool = False
    dry_run: bool = False


class ConsolidationResult(BaseModel):
    """Result of memory consolidation"""
    consolidation_id: str = Field(default_factory=lambda: f"con_{datetime.now().timestamp()}")
    duplicates_found: int = 0
    memories_merged: int = 0
    memories_deleted: int = 0
    duplicate_groups: List[DuplicateGroup] = []
    strategy_used: MergeStrategy
    execution_time_ms: float = 0.0
    dry_run: bool = False
    created_at: datetime = Field(default_factory=datetime.now)