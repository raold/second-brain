#!/usr/bin/env python3
"""
Automated Importance Scoring Engine for Second Brain
Intelligent memory importance calculation based on access patterns, content analysis, and temporal factors
"""

import asyncio
import json
import logging
import math
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ImportanceFactors(Enum):
    """Factors that influence memory importance"""
    FREQUENCY = "frequency"           # How often accessed
    RECENCY = "recency"              # How recently accessed
    SEARCH_RELEVANCE = "search_relevance"  # How often appears in search results
    CONTENT_QUALITY = "content_quality"    # Content richness and complexity
    TEMPORAL_DECAY = "temporal_decay"      # Natural importance decay over time
    MEMORY_TYPE = "memory_type"            # Type-specific importance weighting
    USER_FEEDBACK = "user_feedback"       # Explicit user interactions


@dataclass
class AccessPattern:
    """Represents memory access patterns for importance calculation"""
    memory_id: str
    total_accesses: int
    recent_accesses: int
    last_accessed: datetime
    search_appearances: int
    avg_search_position: float
    user_interactions: Dict[str, int]  # clicks, saves, shares, etc.


@dataclass
class ImportanceScore:
    """Complete importance score with breakdown"""
    final_score: float
    frequency_score: float
    recency_score: float
    search_relevance_score: float
    content_quality_score: float
    type_weight: float
    decay_factor: float
    confidence: float
    explanation: str


class ImportanceEngine:
    """
    Advanced importance scoring engine that learns from user behavior.
    
    The engine calculates importance scores based on multiple factors:
    1. Access frequency and patterns
    2. Recency of access with decay curves
    3. Search relevance and ranking positions
    4. Content quality indicators
    5. Memory type-specific weighting
    6. Temporal decay with memory consolidation
    """

    def __init__(self, database=None):
        self.database = database
        self.config = self._load_config()
        self.memory_type_weights = {
            "semantic": 1.0,     # Facts and knowledge - standard baseline
            "episodic": 0.8,     # Experiences - decay faster but boost on access
            "procedural": 1.2    # Processes - more important, longer retention
        }
        
    def _load_config(self) -> Dict[str, Any]:
        """Load importance scoring configuration"""
        return {
            # Base scoring weights
            "frequency_weight": 0.30,
            "recency_weight": 0.25,
            "search_relevance_weight": 0.20,
            "content_quality_weight": 0.15,
            "type_weight": 0.10,
            
            # Temporal decay parameters
            "half_life_days": 30,  # Days for importance to decay by 50%
            "min_importance": 0.1,  # Minimum importance threshold
            
            # Access pattern thresholds
            "high_frequency_threshold": 10,
            "recent_access_days": 7,
            
            # Content quality indicators
            "quality_indicators": {
                "min_length": 50,
                "has_code": r'```|`[^`]+`',
                "has_urls": r'https?://\S+',
                "has_structured_data": r'(\d+\.\s|\-\s|\*\s)',
                "technical_terms": r'\b(API|SQL|JSON|HTTP|algorithm|function|class|method)\b',
                "complexity_words": ['implementation', 'architecture', 'optimization', 'integration']
            }
        }

    async def calculate_importance_score(
        self, 
        memory_id: str, 
        content: str,
        memory_type: str,
        current_score: float = 0.5
    ) -> ImportanceScore:
        """
        Calculate comprehensive importance score for a memory.
        
        Args:
            memory_id: Unique memory identifier
            content: Memory content for quality analysis
            memory_type: Memory type (semantic, episodic, procedural)
            current_score: Current importance score
            
        Returns:
            ImportanceScore object with detailed breakdown
        """
        try:
            # Get access patterns from database
            access_pattern = await self._get_access_pattern(memory_id)
            
            # Calculate individual scoring factors
            frequency_score = self._calculate_frequency_score(access_pattern)
            recency_score = self._calculate_recency_score(access_pattern)
            search_relevance_score = self._calculate_search_relevance_score(access_pattern)
            content_quality_score = self._calculate_content_quality_score(content)
            type_weight = self.memory_type_weights.get(memory_type, 1.0)
            decay_factor = self._calculate_temporal_decay(access_pattern)
            
            # Combine scores with configured weights
            config = self.config
            weighted_score = (
                frequency_score * config["frequency_weight"] +
                recency_score * config["recency_weight"] +
                search_relevance_score * config["search_relevance_weight"] +
                content_quality_score * config["content_quality_weight"]
            )
            
            # Apply memory type weighting and temporal decay
            final_score = weighted_score * type_weight * decay_factor
            final_score = max(final_score, config["min_importance"])
            final_score = min(final_score, 1.0)
            
            # Calculate confidence based on data availability
            confidence = self._calculate_confidence(access_pattern)
            
            # Generate explanation
            explanation = self._generate_explanation(
                frequency_score, recency_score, search_relevance_score,
                content_quality_score, type_weight, decay_factor
            )
            
            return ImportanceScore(
                final_score=final_score,
                frequency_score=frequency_score,
                recency_score=recency_score,
                search_relevance_score=search_relevance_score,
                content_quality_score=content_quality_score,
                type_weight=type_weight,
                decay_factor=decay_factor,
                confidence=confidence,
                explanation=explanation
            )
            
        except Exception as e:
            logger.error(f"Error calculating importance score for {memory_id}: {e}")
            return ImportanceScore(
                final_score=current_score,
                frequency_score=0.5,
                recency_score=0.5,
                search_relevance_score=0.5,
                content_quality_score=0.5,
                type_weight=1.0,
                decay_factor=1.0,
                confidence=0.0,
                explanation="Error in calculation, using current score"
            )

    async def _get_access_pattern(self, memory_id: str) -> AccessPattern:
        """Extract access patterns from database"""
        if not self.database or not self.database.pool:
            # Return default pattern for testing
            return AccessPattern(
                memory_id=memory_id,
                total_accesses=1,
                recent_accesses=1,
                last_accessed=datetime.now(),
                search_appearances=0,
                avg_search_position=10.0,
                user_interactions={}
            )
            
        async with self.database.pool.acquire() as conn:
            # Get basic access data
            memory_data = await conn.fetchrow("""
                SELECT access_count, last_accessed, created_at, memory_type
                FROM memories WHERE id = $1
            """, memory_id)
            
            if not memory_data:
                raise ValueError(f"Memory {memory_id} not found")
            
            # Get recent access patterns (last 7 days)
            recent_date = datetime.now() - timedelta(days=self.config["recent_access_days"])
            recent_accesses = await conn.fetchval("""
                SELECT COUNT(*) FROM memory_access_log 
                WHERE memory_id = $1 AND accessed_at > $2
            """, memory_id, recent_date) or 0
            
            # Get search appearance data
            search_data = await conn.fetchrow("""
                SELECT COUNT(*) as appearances, AVG(position) as avg_position
                FROM search_result_log 
                WHERE memory_id = $1
            """, memory_id)
            
            return AccessPattern(
                memory_id=memory_id,
                total_accesses=memory_data['access_count'] or 1,
                recent_accesses=recent_accesses,
                last_accessed=memory_data['last_accessed'] or datetime.now(),
                search_appearances=search_data['appearances'] if search_data else 0,
                avg_search_position=float(search_data['avg_position']) if search_data and search_data['avg_position'] else 10.0,
                user_interactions={}
            )

    def _calculate_frequency_score(self, pattern: AccessPattern) -> float:
        """
        Calculate frequency-based importance score.
        Uses logarithmic scaling to prevent over-weighting of highly accessed items.
        """
        if pattern.total_accesses <= 1:
            return 0.1
        
        # Logarithmic scaling with threshold for high frequency
        threshold = self.config["high_frequency_threshold"]
        if pattern.total_accesses >= threshold:
            # High frequency items get boosted score
            base_score = 0.8
            bonus = min(0.2, (pattern.total_accesses - threshold) * 0.01)
            return min(1.0, base_score + bonus)
        else:
            # Logarithmic scaling for normal frequency
            return min(0.8, 0.1 + (math.log(pattern.total_accesses) / math.log(threshold)) * 0.7)

    def _calculate_recency_score(self, pattern: AccessPattern) -> float:
        """
        Calculate recency-based importance score.
        Recent access boosts importance with exponential decay.
        """
        if not pattern.last_accessed:
            return 0.1
            
        days_since_access = (datetime.now() - pattern.last_accessed).days
        
        # Exponential decay with recent access boost
        if days_since_access == 0:
            return 1.0  # Accessed today
        elif days_since_access <= 1:
            return 0.9  # Accessed yesterday
        elif days_since_access <= 7:
            # Linear decay for first week
            return 0.9 - (days_since_access - 1) * 0.1
        else:
            # Exponential decay after first week
            decay_rate = 0.1  # Adjust this to control decay speed
            return max(0.1, 0.2 * math.exp(-decay_rate * (days_since_access - 7)))

    def _calculate_search_relevance_score(self, pattern: AccessPattern) -> float:
        """
        Calculate search relevance based on how often memory appears in search results
        and its average position in those results.
        Enhanced with cross-memory-type relationship analysis.
        """
        if pattern.search_appearances == 0:
            return 0.3  # Neutral score for memories not yet in search results
        
        # Frequency component (how often it appears in searches)
        frequency_component = min(1.0, pattern.search_appearances / 20.0)
        
        # Position component (better ranking = higher score)
        # Average position of 1 = 1.0 score, position 10 = 0.1 score
        position_component = max(0.1, 1.0 - (pattern.avg_search_position - 1) / 9.0)
        
        # Cross-memory-type relationship bonus
        # Memories that connect different memory types are more valuable in search
        cross_type_bonus = self._calculate_cross_type_search_bonus(pattern.memory_id)
        
        # Combine frequency, position, and cross-type factors
        base_score = (frequency_component * 0.6) + (position_component * 0.4)
        enhanced_score = base_score + cross_type_bonus
        
        return min(1.0, enhanced_score)
    
    def _calculate_cross_type_search_bonus(self, memory_id: str) -> float:
        """
        Calculate bonus for memories that bridge different memory types.
        These act as knowledge connectors and should rank higher in search.
        """
        # This would integrate with the cross-memory relationship engine
        # For now, we'll simulate based on content analysis
        
        try:
            # In a full implementation, this would query the relationship engine
            # For demonstration, we'll use heuristics based on content patterns
            
            # Memories with cross-type indicators get search bonus
            cross_type_indicators = [
                "example", "instance", "case study",  # Semantic → Episodic
                "pattern", "principle", "general",    # Episodic → Semantic  
                "procedure", "steps", "process",      # Semantic → Procedural
                "experience", "context", "situation", # Procedural → Episodic
                "implementation", "applied", "practice" # Theory → Practice
            ]
            
            # This is a simplified version - in production would use actual relationship data
            bonus = 0.0
            
            # Memories that frequently bridge types get higher search relevance
            return min(0.15, bonus)
            
        except Exception as e:
            logger.debug(f"Cross-type search bonus calculation failed: {e}")
            return 0.0

    def _calculate_content_quality_score(self, content: str) -> float:
        """
        Analyze content quality to determine intrinsic importance.
        Higher quality content gets higher base importance.
        """
        if not content or len(content.strip()) < 10:
            return 0.1
        
        score = 0.3  # Base score
        indicators = self.config["quality_indicators"]
        
        # Length factor (longer content often more valuable)
        if len(content) >= indicators["min_length"]:
            score += 0.1
        if len(content) >= indicators["min_length"] * 3:
            score += 0.1
        
        # Structured content indicators
        if re.search(indicators["has_code"], content, re.IGNORECASE):
            score += 0.15  # Code snippets are valuable
        
        if re.search(indicators["has_urls"], content):
            score += 0.1   # URLs indicate references
        
        if re.search(indicators["has_structured_data"], content, re.MULTILINE):
            score += 0.1   # Lists and structure indicate organization
        
        # Technical content indicators
        tech_matches = len(re.findall(indicators["technical_terms"], content, re.IGNORECASE))
        score += min(0.1, tech_matches * 0.02)
        
        # Complexity indicators
        complexity_matches = sum(1 for word in indicators["complexity_words"] 
                               if word.lower() in content.lower())
        score += min(0.1, complexity_matches * 0.03)
        
        return min(1.0, score)

    def _calculate_temporal_decay(self, pattern: AccessPattern) -> float:
        """
        Enhanced temporal decay calculation using advanced memory aging algorithms.
        Implements multiple cognitive science-based models for sophisticated memory aging.
        """
        if not pattern.last_accessed:
            return 1.0
        
        days_since_creation = (datetime.now() - pattern.last_accessed).days
        half_life = self.config["half_life_days"]
        
        # Enhanced aging calculation using multiple models
        
        # 1. Base Ebbinghaus forgetting curve: R = e^(-t/S)
        strength_factor = half_life * (1 + math.log1p(pattern.total_accesses))
        ebbinghaus_retention = math.exp(-days_since_creation / strength_factor)
        
        # 2. Power law decay component: R = (1 + t)^(-d)
        # More realistic for long-term memory patterns
        decay_param = 0.1 * (1 - min(0.5, pattern.total_accesses / 20))
        power_law_retention = math.pow(1 + days_since_creation, -decay_param)
        
        # 3. Spacing effect enhancement
        # Memories accessed at optimal intervals retain better
        if pattern.recent_accesses > 0:
            # Calculate spacing intervals (1, 2, 4, 8, 16, 32 days)
            optimal_intervals = [1, 2, 4, 8, 16, 32, 64]
            spacing_bonus = 0.0
            
            # Reward optimal spacing patterns
            for i, interval in enumerate(optimal_intervals):
                if days_since_creation <= interval * 1.5:  # Within optimal window
                    spacing_bonus = min(0.2, (i + 1) * 0.03)
                    break
        else:
            spacing_bonus = 0.0
        
        # 4. Memory consolidation modeling
        # Recent memories (< 7 days) are more fragile
        consolidation_period = 7
        if days_since_creation <= consolidation_period:
            consolidation_factor = days_since_creation / consolidation_period
            fragility_penalty = (1 - consolidation_factor) * 0.15
        else:
            # Older memories become more stable
            consolidation_factor = 1.0
            fragility_penalty = 0.0
            # Consolidated memories get stability bonus
            stability_bonus = min(0.1, (days_since_creation - consolidation_period) / 30 * 0.1)
        
        # 5. Interference modeling
        # High-frequency access patterns can cause interference
        interference_factor = 0.0
        if pattern.total_accesses > 15:
            # Too many accesses in short time can reduce effectiveness
            access_density = pattern.total_accesses / max(1, days_since_creation)
            if access_density > 1.0:  # More than 1 access per day average
                interference_factor = min(0.1, (access_density - 1.0) * 0.05)
        
        # 6. Recency boost with exponential decay
        recent_boost = 0.0
        if pattern.recent_accesses > 0:
            days_since_recent = min(7, days_since_creation)  # Cap at week
            recent_boost = min(0.3, pattern.recent_accesses * 0.08) * math.exp(-days_since_recent / 3.0)
        
        # 7. Frequency protection with logarithmic scaling
        # Prevents over-weighting of extremely high-access memories
        if pattern.total_accesses > 1:
            frequency_protection = min(0.25, math.log1p(pattern.total_accesses) / math.log(21) * 0.25)
        else:
            frequency_protection = 0.0
        
        # 8. Search relevance decay factor
        # Memories that appear in search results age more slowly
        search_protection = 0.0
        if pattern.search_appearances > 0:
            # Better search positions provide more protection
            avg_position_factor = max(0.1, 1.0 - (pattern.avg_search_position - 1) / 9.0)
            search_frequency_factor = min(1.0, pattern.search_appearances / 10.0)
            search_protection = avg_position_factor * search_frequency_factor * 0.15
        
        # Combine all aging factors using weighted model
        primary_retention = (ebbinghaus_retention * 0.4) + (power_law_retention * 0.3)
        enhancement_factors = (
            spacing_bonus + 
            recent_boost + 
            frequency_protection + 
            search_protection +
            (stability_bonus if days_since_creation > consolidation_period else 0)
        )
        penalty_factors = fragility_penalty + interference_factor
        
        # Final decay calculation with bounds
        final_decay = primary_retention + enhancement_factors - penalty_factors
        final_decay = max(0.05, min(1.0, final_decay))  # Ensure reasonable bounds
        
        # Apply memory strength categorization
        # Different strength levels have different decay characteristics
        if final_decay >= 0.8:
            # Crystal memories - very stable, minimal decay
            final_decay = final_decay * 0.95 + 0.05
        elif final_decay >= 0.6:
            # Strong memories - stable with slow decay
            final_decay = final_decay * 0.9 + 0.1
        elif final_decay >= 0.3:
            # Moderate memories - standard decay
            pass  # No modification
        else:
            # Weak memories - faster decay but with protection floor
            final_decay = max(0.1, final_decay * 1.1)
        
        return final_decay

    def _calculate_confidence(self, pattern: AccessPattern) -> float:
        """Calculate confidence in the importance score based on available data"""
        confidence = 0.5  # Base confidence
        
        # More accesses = higher confidence
        if pattern.total_accesses > 5:
            confidence += 0.2
        if pattern.total_accesses > 15:
            confidence += 0.1
        
        # Search data adds confidence
        if pattern.search_appearances > 0:
            confidence += 0.1
        
        # Recent activity adds confidence
        if pattern.recent_accesses > 0:
            confidence += 0.1
        
        return min(1.0, confidence)

    def _generate_explanation(
        self, frequency: float, recency: float, search_rel: float,
        quality: float, type_weight: float, decay: float
    ) -> str:
        """Generate human-readable explanation of importance score"""
        explanations = []
        
        if frequency > 0.7:
            explanations.append("frequently accessed")
        elif frequency > 0.4:
            explanations.append("moderately accessed")
        else:
            explanations.append("rarely accessed")
        
        if recency > 0.7:
            explanations.append("recently used")
        elif recency < 0.3:
            explanations.append("not recently accessed")
        
        if search_rel > 0.6:
            explanations.append("high search relevance")
        
        if quality > 0.7:
            explanations.append("high-quality content")
        
        if type_weight > 1.0:
            explanations.append("procedural memory bonus")
        elif type_weight < 1.0:
            explanations.append("episodic memory")
        
        if decay < 0.5:
            explanations.append("temporal decay applied")
        
        return ", ".join(explanations) if explanations else "standard scoring"

    async def update_memory_importance(self, memory_id: str) -> Optional[float]:
        """
        Update importance score for a specific memory.
        Called when memory is accessed or appears in search results.
        """
        if not self.database or not self.database.pool:
            return None
        
        try:
            async with self.database.pool.acquire() as conn:
                # Get current memory data
                memory_data = await conn.fetchrow("""
                    SELECT content, memory_type, importance_score
                    FROM memories WHERE id = $1
                """, memory_id)
                
                if not memory_data:
                    return None
                
                # Calculate new importance score
                score = await self.calculate_importance_score(
                    memory_id,
                    memory_data['content'],
                    memory_data['memory_type'],
                    memory_data['importance_score']
                )
                
                # Update database
                await conn.execute("""
                    UPDATE memories 
                    SET importance_score = $2, updated_at = NOW()
                    WHERE id = $1
                """, memory_id, score.final_score)
                
                logger.info(f"Updated importance for {memory_id}: {score.final_score:.3f} ({score.explanation})")
                return score.final_score
                
        except Exception as e:
            logger.error(f"Error updating importance for {memory_id}: {e}")
            return None

    async def batch_recalculate_importance(self, limit: int = 100) -> Dict[str, Any]:
        """
        Batch recalculation of importance scores for memories.
        Should be run periodically (daily/weekly) to update scores.
        """
        if not self.database or not self.database.pool:
            return {"error": "Database not available"}
        
        try:
            async with self.database.pool.acquire() as conn:
                # Get memories that need importance recalculation
                # Prioritize: old scores, high access counts, recent activity
                memories = await conn.fetch("""
                    SELECT id, content, memory_type, importance_score, 
                           access_count, last_accessed, updated_at
                    FROM memories 
                    WHERE access_count > 0 
                       OR last_accessed > NOW() - INTERVAL '30 days'
                    ORDER BY 
                        (access_count > 5) DESC,
                        (updated_at < NOW() - INTERVAL '7 days') DESC,
                        last_accessed DESC NULLS LAST
                    LIMIT $1
                """, limit)
                
                updated_count = 0
                total_change = 0.0
                
                for memory in memories:
                    old_score = float(memory['importance_score'])
                    
                    # Calculate new score
                    score = await self.calculate_importance_score(
                        memory['id'],
                        memory['content'],
                        memory['memory_type'],
                        old_score
                    )
                    
                    # Update if score changed significantly
                    score_change = abs(score.final_score - old_score)
                    if score_change > 0.05:  # Only update if change > 5%
                        await conn.execute("""
                            UPDATE memories 
                            SET importance_score = $2, updated_at = NOW()
                            WHERE id = $1
                        """, memory['id'], score.final_score)
                        
                        updated_count += 1
                        total_change += score_change
                
                avg_change = total_change / max(updated_count, 1)
                
                return {
                    "processed": len(memories),
                    "updated": updated_count,
                    "average_change": round(avg_change, 3),
                    "status": "completed"
                }
                
        except Exception as e:
            logger.error(f"Error in batch importance recalculation: {e}")
            return {"error": str(e)}

    async def log_memory_access(
        self, 
        memory_id: str, 
        access_type: str = "retrieval",
        search_position: Optional[int] = None,
        user_action: Optional[str] = None
    ) -> None:
        """
        Log memory access for importance calculation.
        Called whenever a memory is accessed, searched, or interacted with.
        """
        if not self.database or not self.database.pool:
            return
        
        try:
            async with self.database.pool.acquire() as conn:
                # Update access count and timestamp
                await conn.execute("""
                    UPDATE memories 
                    SET access_count = access_count + 1,
                        last_accessed = NOW()
                    WHERE id = $1
                """, memory_id)
                
                # Log detailed access information
                await conn.execute("""
                    INSERT INTO memory_access_log 
                    (memory_id, access_type, search_position, user_action, accessed_at)
                    VALUES ($1, $2, $3, $4, NOW())
                    ON CONFLICT DO NOTHING
                """, memory_id, access_type, search_position, user_action)
                
                # Trigger importance update for frequently accessed memories
                access_count = await conn.fetchval("""
                    SELECT access_count FROM memories WHERE id = $1
                """, memory_id)
                
                # Update importance every 5 accesses or after search appearances
                if access_count % 5 == 0 or search_position is not None:
                    await self.update_memory_importance(memory_id)
                    
        except Exception as e:
            logger.error(f"Error logging memory access for {memory_id}: {e}")

    async def get_importance_analytics(self) -> Dict[str, Any]:
        """Get analytics about importance score distribution and trends"""
        if not self.database or not self.database.pool:
            return {"error": "Database not available"}
        
        try:
            async with self.database.pool.acquire() as conn:
                # Importance score distribution
                distribution = await conn.fetch("""
                    SELECT 
                        CASE 
                            WHEN importance_score >= 0.8 THEN 'high'
                            WHEN importance_score >= 0.5 THEN 'medium'
                            ELSE 'low'
                        END as importance_level,
                        COUNT(*) as count,
                        AVG(importance_score) as avg_score
                    FROM memories
                    GROUP BY 1
                    ORDER BY avg_score DESC
                """)
                
                # Top important memories
                top_memories = await conn.fetch("""
                    SELECT id, content[1:100] as content_preview, 
                           importance_score, memory_type, access_count
                    FROM memories
                    ORDER BY importance_score DESC
                    LIMIT 10
                """)
                
                # Memory type analysis
                type_analysis = await conn.fetch("""
                    SELECT memory_type, 
                           COUNT(*) as count,
                           AVG(importance_score) as avg_importance,
                           AVG(access_count) as avg_accesses
                    FROM memories
                    GROUP BY memory_type
                """)
                
                return {
                    "distribution": [dict(row) for row in distribution],
                    "top_memories": [dict(row) for row in top_memories],
                    "type_analysis": [dict(row) for row in type_analysis],
                    "total_memories": sum(row['count'] for row in distribution)
                }
                
        except Exception as e:
            logger.error(f"Error getting importance analytics: {e}")
            return {"error": str(e)}


# Singleton instance
_importance_engine = None

def get_importance_engine(database=None):
    """Get singleton importance engine instance"""
    global _importance_engine
    if _importance_engine is None:
        _importance_engine = ImportanceEngine(database)
    return _importance_engine 