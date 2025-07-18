"""
Migration 002: Recalculate Memory Importance Scores

Recalculates importance scores for all existing memories using the new
importance engine with cognitive factors and temporal decay.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional

from app.memory_migrations import MemoryDataMigration
from app.migration_framework import MigrationMetadata, MigrationType
from app.bulk_memory_operations import BulkMemoryItem


class RecalculateMemoryImportance(MemoryDataMigration):
    """Migration to recalculate importance scores for all memories."""
    
    def _get_metadata(self) -> MigrationMetadata:
        return MigrationMetadata(
            id="002_recalculate_importance",
            name="Recalculate memory importance scores",
            description="Updates all memory importance scores using new cognitive importance engine",
            version="2.5.0",
            migration_type=MigrationType.MEMORY_DATA,
            author="importance_system",
            created_at=datetime(2024, 1, 16),
            dependencies=["001_add_user_preferences"],
            reversible=True,
            checksum="b2c3d4e5f6g7h8i9"
        )
    
    async def get_memories_to_migrate(self) -> List[Dict[str, Any]]:
        """Get all memories that need importance recalculation."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    id, 
                    content, 
                    metadata,
                    memory_type,
                    importance_score,
                    created_at,
                    last_accessed
                FROM memories
                WHERE 
                    importance_score IS NULL 
                    OR importance_score = 0.5  -- Default value needs recalculation
                    OR metadata->>'importance_calculated_at' IS NULL
                ORDER BY created_at DESC
                LIMIT 50000  -- Process in chunks
            """)
            return [dict(row) for row in rows]
    
    async def transform_memory(self, memory: Dict[str, Any]) -> Optional[BulkMemoryItem]:
        """Recalculate importance score using cognitive factors."""
        
        # Simulate importance calculation (would use real importance engine)
        content = memory['content']
        metadata = memory.get('metadata', {}) or {}
        created_at = memory.get('created_at')
        last_accessed = memory.get('last_accessed')
        
        # Calculate importance based on multiple factors
        importance_score = await self._calculate_importance(
            content, metadata, created_at, last_accessed
        )
        
        # Update metadata with calculation info
        metadata['importance_calculation'] = {
            'score': importance_score,
            'calculated_at': datetime.now().isoformat(),
            'factors': {
                'content_quality': self._analyze_content_quality(content),
                'temporal_relevance': self._calculate_temporal_relevance(created_at),
                'access_frequency': self._calculate_access_frequency(last_accessed),
                'content_uniqueness': self._analyze_uniqueness(content)
            },
            'migration': '002_recalculate_importance'
        }
        
        return BulkMemoryItem(
            memory_id=memory['id'],
            content=content,
            metadata=metadata,
            memory_type=memory.get('memory_type', 'semantic'),
            importance_score=importance_score
        )
    
    async def _calculate_importance(
        self, 
        content: str, 
        metadata: dict,
        created_at: datetime,
        last_accessed: Optional[datetime]
    ) -> float:
        """Calculate importance score using multiple cognitive factors."""
        
        # Factor 1: Content quality (40% weight)
        content_quality = self._analyze_content_quality(content)
        
        # Factor 2: Temporal relevance (25% weight) 
        temporal_relevance = self._calculate_temporal_relevance(created_at)
        
        # Factor 3: Access patterns (20% weight)
        access_score = self._calculate_access_frequency(last_accessed)
        
        # Factor 4: Content uniqueness (15% weight)
        uniqueness = self._analyze_uniqueness(content)
        
        # Weighted combination
        importance = (
            content_quality * 0.40 +
            temporal_relevance * 0.25 +
            access_score * 0.20 +
            uniqueness * 0.15
        )
        
        # Normalize to 0-1 range
        return max(0.0, min(1.0, importance))
    
    def _analyze_content_quality(self, content: str) -> float:
        """Analyze content quality based on length, structure, and complexity."""
        if not content:
            return 0.0
        
        base_score = 0.3  # Base quality score
        
        # Length factor (optimal around 100-500 chars)
        length = len(content)
        if 50 <= length <= 1000:
            length_bonus = min(0.3, (length - 50) / 950 * 0.3)
        else:
            length_bonus = 0.1
        
        # Structure indicators
        structure_score = 0.0
        structure_indicators = [
            ('•', 0.05),  # Bullet points
            ('\n', 0.03),  # Line breaks
            (':', 0.02),   # Colons (lists, definitions)
            ('?', 0.02),   # Questions
            ('!', 0.02),   # Exclamations
        ]
        
        for indicator, bonus in structure_indicators:
            if indicator in content:
                structure_score += bonus
        
        # Technical content indicators
        technical_score = 0.0
        technical_terms = ['function', 'class', 'method', 'API', 'database', 'algorithm']
        for term in technical_terms:
            if term.lower() in content.lower():
                technical_score += 0.02
        
        return min(1.0, base_score + length_bonus + structure_score + technical_score)
    
    def _calculate_temporal_relevance(self, created_at: datetime) -> float:
        """Calculate relevance based on age with exponential decay."""
        if not created_at:
            return 0.5
        
        days_old = (datetime.now() - created_at).days
        
        # Exponential decay with half-life of 30 days
        half_life = 30
        decay_factor = 0.5 ** (days_old / half_life)
        
        # Recent memories get bonus
        if days_old <= 7:
            return min(1.0, decay_factor + 0.2)
        
        return max(0.1, decay_factor)
    
    def _calculate_access_frequency(self, last_accessed: Optional[datetime]) -> float:
        """Calculate score based on access patterns."""
        if not last_accessed:
            return 0.3  # Never accessed
        
        days_since_access = (datetime.now() - last_accessed).days
        
        # Recent access gets high score
        if days_since_access <= 1:
            return 1.0
        elif days_since_access <= 7:
            return 0.8
        elif days_since_access <= 30:
            return 0.6
        else:
            return 0.3
    
    def _analyze_uniqueness(self, content: str) -> float:
        """Analyze content uniqueness (simplified version)."""
        if not content:
            return 0.0
        
        # Simple uniqueness indicators
        unique_score = 0.5  # Base score
        
        # Length uniqueness
        if len(content) > 200:
            unique_score += 0.2
        
        # Word variety (simplified)
        words = content.lower().split()
        if len(words) > 0:
            unique_words = len(set(words))
            variety_ratio = unique_words / len(words)
            unique_score += variety_ratio * 0.3
        
        return min(1.0, unique_score)
    
    async def get_original_memories(self) -> List[BulkMemoryItem]:
        """Get original memories for rollback (backup importance scores)."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, content, metadata, memory_type, importance_score
                FROM memories
                WHERE metadata->>'importance_calculation'->>'migration' = '002_recalculate_importance'
            """)
            
            original_memories = []
            for row in rows:
                # Restore original importance score (0.5 default)
                metadata = dict(row['metadata']) if row['metadata'] else {}
                if 'importance_calculation' in metadata:
                    del metadata['importance_calculation']
                
                original_memories.append(BulkMemoryItem(
                    memory_id=row['id'],
                    content=row['content'],
                    metadata=metadata,
                    memory_type=row['memory_type'],
                    importance_score=0.5  # Restore default
                ))
            
            return original_memories
    
    async def _validate_custom_preconditions(self) -> bool:
        """Validate that importance recalculation can proceed."""
        async with self.pool.acquire() as conn:
            # Check that memories table has importance_score column
            has_column = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'memories' 
                    AND column_name = 'importance_score'
                )
            """)
            
            if not has_column:
                return False
            
            # Check that there are memories to process
            memory_count = await conn.fetchval("SELECT COUNT(*) FROM memories")
            return memory_count > 0
    
    async def validate_postconditions(self) -> bool:
        """Validate that importance scores were updated correctly."""
        async with self.pool.acquire() as conn:
            # Check that no memories have null importance scores
            null_count = await conn.fetchval("""
                SELECT COUNT(*) FROM memories 
                WHERE importance_score IS NULL
            """)
            
            # Check that importance calculation metadata was added
            calculated_count = await conn.fetchval("""
                SELECT COUNT(*) FROM memories 
                WHERE metadata->>'importance_calculation'->>'migration' = '002_recalculate_importance'
            """)
            
            return null_count == 0 and calculated_count > 0 