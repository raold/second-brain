"""
Enhanced Memory Service with PostgreSQL + pgvector
Provides unified memory management with vector search, full-text search, and relationships
"""

import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.core.degradation import DegradationLevel, get_degradation_manager
from app.storage.postgres_unified import PostgresUnifiedBackend
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class MemoryServicePostgres:
    """
    Production memory service using PostgreSQL with pgvector
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        enable_embeddings: bool = True,
        embedding_batch_size: int = 10,
        embedding_model: str = "text-embedding-ada-002",
    ):
        """
        Initialize memory service with PostgreSQL backend

        Args:
            connection_string: PostgreSQL connection string
            enable_embeddings: Whether to generate embeddings for new memories
            embedding_batch_size: Batch size for embedding generation
            embedding_model: Local embedding model to use (Nomic/CLIP)
        """
        self.backend = PostgresUnifiedBackend(connection_string)
        self.degradation_manager = get_degradation_manager()
        self.enable_embeddings = enable_embeddings
        self.embedding_batch_size = embedding_batch_size
        self.embedding_model = embedding_model

        # Local embedding client (lazy loaded)
        self._local_client = None
        self._embedding_queue = []

        logger.info("Memory service initialized with PostgreSQL backend")

    async def initialize(self):
        """Initialize the backend connection"""
        await self.backend.initialize()
        logger.info("PostgreSQL backend initialized")

    async def close(self):
        """Close backend connections"""
        # Process any pending embeddings
        if self._embedding_queue:
            await self._process_embedding_queue()

        await self.backend.close()
        logger.info("Memory service closed")

    # ==================== Memory CRUD Operations ====================

    async def create_memory(
        self,
        content: str,
        memory_type: str = "generic",
        importance_score: float = 0.5,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
        generate_embedding: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a new memory with optional embedding generation

        Args:
            content: Memory content
            memory_type: Type of memory
            importance_score: Importance (0-1)
            tags: List of tags
            metadata: Additional metadata
            generate_embedding: Whether to generate embedding

        Returns:
            Created memory dictionary
        """
        # Check degradation level
        if self.degradation_manager.current_level >= DegradationLevel.READONLY:
            logger.warning("System in read-only mode, cannot create memory")
            return None

        # Create memory object
        memory = {
            "id": str(uuid.uuid4()),
            "content": content,
            "memory_type": memory_type,
            "importance_score": importance_score,
            "tags": tags or [],
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Generate embedding if enabled
        embedding = None
        if generate_embedding and self.enable_embeddings:
            if self.degradation_manager.is_feature_available("ai_features"):
                embedding = await self._generate_embedding(content)
                if embedding:
                    memory["embedding_model"] = self.embedding_model

        # Store in PostgreSQL
        try:
            created_memory = await self.backend.create_memory(memory, embedding)
            logger.info(f"Created memory {created_memory['id'][:8]}...")

            # Auto-detect duplicates if we have embeddings
            if embedding and self.degradation_manager.is_feature_available("deduplication"):
                await self._check_for_duplicates(created_memory["id"], embedding)

            return created_memory

        except Exception as e:
            logger.error(f"Failed to create memory: {e}")
            if self.degradation_manager.current_level < DegradationLevel.NO_PERSISTENCE:
                # Try to degrade gracefully
                # Report failure to degradation manager
                pass  # degradation_manager.report_failure not implemented yet
            raise

    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a memory by ID"""
        try:
            return await self.backend.get_memory(memory_id)
        except Exception as e:
            logger.error(f"Failed to get memory {memory_id}: {e}")
            return None

    async def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        importance_score: Optional[float] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        regenerate_embedding: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Update a memory with optional embedding regeneration"""

        # Check degradation level
        if self.degradation_manager.current_level >= DegradationLevel.READONLY:
            logger.warning("System in read-only mode, cannot update memory")
            return None

        updates = {}
        if content is not None:
            updates["content"] = content
        if importance_score is not None:
            updates["importance_score"] = importance_score
        if tags is not None:
            updates["tags"] = tags
        if metadata is not None:
            updates["metadata"] = metadata

        # Generate new embedding if content changed
        new_embedding = None
        if regenerate_embedding or (content and self.enable_embeddings):
            if self.degradation_manager.is_feature_available("ai_features"):
                new_embedding = await self._generate_embedding(content or "")

        try:
            return await self.backend.update_memory(memory_id, updates, new_embedding)
        except Exception as e:
            logger.error(f"Failed to update memory {memory_id}: {e}")
            return None

    async def delete_memory(self, memory_id: str, soft: bool = True) -> bool:
        """Delete a memory (soft delete by default)"""

        # Check degradation level
        if self.degradation_manager.current_level >= DegradationLevel.READONLY:
            logger.warning("System in read-only mode, cannot delete memory")
            return False

        try:
            return await self.backend.delete_memory(memory_id, soft)
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False

    async def list_memories(
        self,
        limit: int = 20,
        offset: int = 0,
        memory_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_importance: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """List memories with filtering"""
        try:
            return await self.backend.list_memories(
                limit=limit,
                offset=offset,
                memory_type=memory_type,
                tags=tags,
                min_importance=min_importance,
            )
        except Exception as e:
            logger.error(f"Failed to list memories: {e}")
            return []

    # ==================== Search Operations ====================

    async def search_memories(
        self,
        query: str,
        limit: int = 10,
        search_type: str = "hybrid",
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search memories using various strategies

        Args:
            query: Search query
            limit: Maximum results
            search_type: 'vector', 'text', or 'hybrid'
            min_score: Minimum score threshold
            filters: Additional filters (tags, type, etc.)

        Returns:
            List of matching memories with scores
        """
        # Check if vector search is available
        if search_type in [
            "vector",
            "hybrid",
        ] and not self.degradation_manager.is_feature_available("semantic_search"):
            logger.warning("Semantic search unavailable, falling back to text search")
            search_type = "text"

        try:
            # Generate embedding for vector/hybrid search
            embedding = None
            if search_type in ["vector", "hybrid"] and self.enable_embeddings:
                embedding = await self._generate_embedding(query)

            # Perform search based on type
            if search_type == "vector" and embedding:
                results = await self.backend.vector_search(
                    embedding=embedding, limit=limit, min_similarity=min_score
                )
            elif search_type == "text":
                results = await self.backend.text_search(query=query, limit=limit)
            else:  # hybrid
                results = await self.backend.hybrid_search(
                    query=query,
                    embedding=embedding,
                    limit=limit,
                    vector_weight=0.5,  # Default weight
                    min_score=min_score,
                )

            # Record search for learning
            if results and self.degradation_manager.is_feature_available("analytics"):
                selected_ids = [r["id"] for r in results[:3]]  # Top 3 as "selected"
                await self.backend.record_search(
                    query=query,
                    embedding=embedding,
                    results_count=len(results),
                    selected_ids=selected_ids,
                    search_type=search_type,
                    metadata=filters,
                )

            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            # Fallback to simple search
            return await self._fallback_search(query, limit)

    async def semantic_search(
        self, query: str, limit: int = 10, min_similarity: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Pure semantic search using vector similarity"""
        return await self.search_memories(
            query=query, limit=limit, search_type="vector", min_score=min_similarity
        )

    async def keyword_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Pure keyword search using full-text search"""
        return await self.search_memories(query=query, limit=limit, search_type="text")

    # ==================== Relationship Operations ====================

    async def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        strength: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a relationship between memories"""
        try:
            return await self.backend.create_relationship(
                source_id=source_id,
                target_id=target_id,
                relationship_type=relationship_type,
                strength=strength,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            raise

    async def get_related_memories(
        self,
        memory_id: str,
        relationship_type: Optional[str] = None,
        min_strength: float = 0.0,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get memories related to a given memory"""
        try:
            related = await self.backend.get_related_memories(
                memory_id=memory_id, relationship_type=relationship_type, min_strength=min_strength
            )
            return related[:limit]
        except Exception as e:
            logger.error(f"Failed to get related memories: {e}")
            return []

    async def build_knowledge_graph(
        self, center_memory_id: str, depth: int = 2, min_strength: float = 0.5
    ) -> Dict[str, Any]:
        """Build a knowledge graph around a memory"""
        graph = {"nodes": [], "edges": [], "center": center_memory_id}

        visited = set()
        queue = [(center_memory_id, 0)]

        while queue:
            memory_id, current_depth = queue.pop(0)

            if memory_id in visited or current_depth > depth:
                continue

            visited.add(memory_id)

            # Get memory details
            memory = await self.get_memory(memory_id)
            if memory:
                graph["nodes"].append(
                    {
                        "id": memory_id,
                        "content": memory["content"][:100],  # Truncate for graph
                        "type": memory["memory_type"],
                        "depth": current_depth,
                    }
                )

                # Get related memories
                related = await self.get_related_memories(
                    memory_id=memory_id, min_strength=min_strength
                )

                for rel_memory in related:
                    graph["edges"].append(
                        {
                            "source": memory_id,
                            "target": rel_memory["id"],
                            "type": rel_memory["relationship_type"],
                            "strength": rel_memory["relationship_strength"],
                        }
                    )

                    if current_depth < depth:
                        queue.append((rel_memory["id"], current_depth + 1))

        return graph

    # ==================== Consolidation Operations ====================

    async def consolidate_memories(
        self,
        source_ids: List[str],
        consolidation_type: str = "merge",
        summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Consolidate multiple memories into one"""

        if len(source_ids) < 2:
            raise ValueError("At least 2 memories required for consolidation")

        # Get source memories
        source_memories = []
        for memory_id in source_ids:
            memory = await self.get_memory(memory_id)
            if memory:
                source_memories.append(memory)

        if len(source_memories) < 2:
            raise ValueError("Could not find enough valid memories")

        # Generate consolidated content
        if summary:
            consolidated_content = summary
        else:
            # Auto-generate summary
            consolidated_content = await self._generate_consolidation_summary(source_memories)

        # Create consolidated memory
        metadata = {
            "consolidation_type": consolidation_type,
            "source_count": len(source_ids),
            "source_ids": source_ids,
        }

        try:
            return await self.backend.consolidate_memories(
                source_ids=source_ids,
                consolidated_content=consolidated_content,
                consolidation_type=consolidation_type,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Failed to consolidate memories: {e}")
            raise

    async def find_duplicate_memories(
        self, similarity_threshold: float = 0.95
    ) -> List[Tuple[str, str, float]]:
        """Find potential duplicate memories"""
        try:
            return await self.backend.find_duplicates(similarity_threshold)
        except Exception as e:
            logger.error(f"Failed to find duplicates: {e}")
            return []

    async def auto_consolidate_duplicates(
        self, similarity_threshold: float = 0.95, dry_run: bool = True
    ) -> Dict[str, Any]:
        """Automatically consolidate duplicate memories"""

        duplicates = await self.find_duplicate_memories(similarity_threshold)

        results = {"found": len(duplicates), "consolidated": 0, "errors": 0, "dry_run": dry_run}

        if not dry_run:
            for memory1_id, memory2_id, similarity in duplicates:
                try:
                    await self.consolidate_memories(
                        source_ids=[memory1_id, memory2_id], consolidation_type="merge"
                    )
                    results["consolidated"] += 1
                except Exception as e:
                    logger.error(f"Failed to consolidate {memory1_id} and {memory2_id}: {e}")
                    results["errors"] += 1

        return results

    # ==================== Analytics Operations ====================

    async def get_statistics(self) -> Dict[str, Any]:
        """Get memory service statistics"""
        try:
            stats = await self.backend.get_statistics()
            stats["degradation_level"] = self.degradation_manager.current_level.name
            stats["embeddings_enabled"] = self.enable_embeddings
            stats["embedding_model"] = self.embedding_model
            return stats
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {"error": str(e)}

    async def get_memory_insights(self) -> Dict[str, Any]:
        """Get insights about memory patterns"""
        stats = await self.get_statistics()

        insights = {
            "total_memories": stats.get("total_memories", 0),
            "memory_types": stats.get("unique_types", 0),
            "avg_importance": stats.get("avg_importance", 0),
            "most_accessed": stats.get("max_access_count", 0),
            "storage_size": stats.get("table_size", "unknown"),
            "embeddings_coverage": 0,
        }

        if stats.get("total_memories", 0) > 0:
            insights["embeddings_coverage"] = (
                stats.get("memories_with_embeddings", 0) / stats["total_memories"] * 100
            )

        return insights

    # ==================== Embedding Operations ====================

    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using local models"""

        if not self.enable_embeddings:
            return None

        # Check for API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set, skipping embedding generation")
            return None

        # Initialize local client if needed
        if not self._local_client:
            try:
                from app.utils.local_embedding_client import get_local_client
                self._local_client = get_local_client()
            except ImportError:
                logger.error("Local embedding client not available")
                return None

        try:
            # Add to queue for batching
            self._embedding_queue.append(text)

            # Process queue if it reaches batch size
            if len(self._embedding_queue) >= self.embedding_batch_size:
                return await self._process_embedding_queue()

            # For single embedding, process immediately
            embedding = await self._local_client.get_embedding(text)
            if embedding:
                return embedding

            return response.data[0].embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    async def _process_embedding_queue(self) -> Optional[List[float]]:
        """Process queued texts for embedding generation"""

        if not self._embedding_queue:
            return None

        try:
            # Batch generate embeddings
            # Generate embeddings for all texts in queue
            embeddings = []
            for txt in self._embedding_queue:
                emb = await self._local_client.get_embedding(txt)
                if emb:
                    embeddings.append(emb)

            embeddings = [item.embedding for item in response.data]

            # Clear queue and return last embedding
            self._embedding_queue.clear()
            return embeddings[-1] if embeddings else None

        except Exception as e:
            logger.error(f"Failed to process embedding queue: {e}")
            self._embedding_queue.clear()
            return None

    async def generate_embeddings_for_all(
        self, batch_size: int = 20, max_memories: int = 1000
    ) -> Dict[str, Any]:
        """Generate embeddings for all memories without them"""

        results = {"processed": 0, "success": 0, "errors": 0, "skipped": 0}

        # Get memories without embeddings
        memories = await self.backend.list_memories(limit=max_memories)

        for memory in memories:
            if memory.get("has_embedding"):
                results["skipped"] += 1
                continue

            results["processed"] += 1

            # Generate embedding
            embedding = await self._generate_embedding(memory["content"])

            if embedding:
                # Update memory with embedding
                await self.backend.update_memory(memory["id"], {}, new_embedding=embedding)
                results["success"] += 1
            else:
                results["errors"] += 1

            # Log progress
            if results["processed"] % 10 == 0:
                logger.info(f"Processed {results['processed']} memories")

        return results

    # ==================== Helper Methods ====================

    async def _check_for_duplicates(self, memory_id: str, embedding: List[float]):
        """Check if a new memory is duplicate of existing ones"""

        # Search for similar memories
        similar = await self.backend.vector_search(
            embedding=embedding, limit=5, min_similarity=0.95
        )

        # Filter out self
        similar = [m for m in similar if m["id"] != memory_id]

        if similar:
            logger.warning(
                f"Found {len(similar)} potential duplicates for memory {memory_id[:8]}..."
            )

            # Create relationships to mark as similar
            for sim_memory in similar:
                await self.backend.create_relationship(
                    source_id=memory_id,
                    target_id=sim_memory["id"],
                    relationship_type="similar",
                    strength=sim_memory["similarity"],
                )

    async def _generate_consolidation_summary(self, memories: List[Dict[str, Any]]) -> str:
        """Generate a summary for consolidating memories"""

        # Simple concatenation for now
        # TODO: Use LLM to generate intelligent summary
        contents = [m["content"] for m in memories]
        summary = f"Consolidated from {len(memories)} memories:\n\n"
        summary += "\n---\n".join(contents[:3])  # First 3 memories

        if len(memories) > 3:
            summary += f"\n---\n... and {len(memories) - 3} more memories"

        return summary

    async def _fallback_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Simple fallback search when advanced search fails"""

        try:
            # Get all memories and do simple string matching
            memories = await self.backend.list_memories(limit=100)

            query_lower = query.lower()
            results = []

            for memory in memories:
                if query_lower in memory.get("content", "").lower():
                    results.append(memory)
                    if len(results) >= limit:
                        break

            return results

        except Exception as e:
            logger.error(f"Fallback search also failed: {e}")
            return []
