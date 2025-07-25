"""
Memory-related use cases.

Contains business logic for memory operations.
"""

from uuid import UUID, uuid4

from src.application.dto.memory_dto import (
    CreateMemoryDTO,
    MemoryDTO,
    MemoryListDTO,
    UpdateMemoryDTO,
)
from src.application.exceptions import NotFoundError, ValidationError
from src.application.use_cases.base import UseCase
from src.domain.events.memory_events import MemoryCreated, MemoryDeleted, MemoryLinked, MemoryUpdated
from src.domain.models.memory import Memory, MemoryId
from src.infrastructure.logging import get_logger
from src.infrastructure.observability import trace, get_metrics_collector
from src.infrastructure.embeddings import EmbeddingClient

logger = get_logger(__name__)


class CreateMemoryUseCase(UseCase[CreateMemoryDTO, MemoryDTO]):
    """Use case for creating a new memory."""
    
    @trace("create_memory")
    async def execute(self, request: CreateMemoryDTO) -> MemoryDTO:
        """Create a new memory."""
        # Get user from context (would come from auth in real app)
        user_id = UUID("00000000-0000-0000-0000-000000000001")  # Placeholder
        
        metrics = get_metrics_collector()
        
        async with self.deps.begin_transaction() as session:
            # Generate embedding for the memory content
            embedding_client = EmbeddingClient()
            embedding_result = await embedding_client.generate_embedding(
                f"{request.title}\n\n{request.content}"
            )
            
            # Create memory domain object
            memory = Memory(
                id=MemoryId(uuid4()),
                user_id=user_id,
                title=request.title,
                content=request.content,
                memory_type=request.memory_type,
                importance_score=request.importance_score,
                confidence_score=request.confidence_score,
                source_url=request.source_url,
                metadata=request.metadata,
                embedding=embedding_result.embedding,
                embedding_model=embedding_result.model.value,
            )
            
            # Get repository
            memory_repo = await self.deps.get_memory_repository()
            
            # Save memory
            saved_memory = await memory_repo.save(memory)
            
            # Store event
            event_store = await self.deps.get_event_store()
            event = MemoryCreated(
                aggregate_id=memory.id.value,
                memory_type=memory.memory_type.value,
                title=memory.title,
            )
            await event_store.append(event)
            
            # Publish event to message queue
            event_publisher = await self.deps.get_event_publisher()
            if event_publisher:
                await event_publisher.publish(event)
            
            # Handle tags
            if request.tags:
                tag_repo = await self.deps.get_tag_repository()
                for tag_name in request.tags:
                    # Get or create tag
                    tag = await tag_repo.get_by_name(user_id, tag_name)
                    if tag:
                        # Add tag to memory (would need to implement this)
                        pass
            
            await session.commit()
            
            # Track metrics
            metrics.track_memory_operation("create", "success", 0)
            
        return MemoryDTO.from_domain(saved_memory)


class GetMemoryUseCase(UseCase[UUID, MemoryDTO]):
    """Use case for retrieving a memory."""
    
    async def execute(self, memory_id: UUID) -> MemoryDTO:
        """Get a memory by ID."""
        async with self.deps.begin_transaction() as session:
            memory_repo = await self.deps.get_memory_repository()
            
            memory = await memory_repo.get(MemoryId(memory_id))
            if not memory:
                raise NotFoundError("Memory", str(memory_id))
            
            # Update access time
            await memory_repo.update_access_time(memory.id)
            
            await session.commit()
            
        return MemoryDTO.from_domain(memory)


class UpdateMemoryUseCase(UseCase[tuple[UUID, UpdateMemoryDTO], MemoryDTO]):
    """Use case for updating a memory."""
    
    async def execute(self, request: tuple[UUID, UpdateMemoryDTO]) -> MemoryDTO:
        """Update a memory."""
        memory_id, update_dto = request
        
        async with self.deps.begin_transaction() as session:
            memory_repo = await self.deps.get_memory_repository()
            
            # Get existing memory
            memory = await memory_repo.get(MemoryId(memory_id))
            if not memory:
                raise NotFoundError("Memory", str(memory_id))
            
            # Update fields
            regenerate_embedding = False
            if update_dto.title is not None:
                memory.title = update_dto.title
                regenerate_embedding = True
            if update_dto.content is not None:
                memory.content = update_dto.content
                regenerate_embedding = True
            
            # Regenerate embedding if title or content changed
            if regenerate_embedding:
                embedding_client = EmbeddingClient()
                embedding_result = await embedding_client.generate_embedding(
                    f"{memory.title}\n\n{memory.content}"
                )
                memory.embedding = embedding_result.embedding
                memory.embedding_model = embedding_result.model.value
            if update_dto.memory_type is not None:
                memory.memory_type = update_dto.memory_type
            if update_dto.status is not None:
                memory.status = update_dto.status
            if update_dto.importance_score is not None:
                memory.importance_score = update_dto.importance_score
            if update_dto.confidence_score is not None:
                memory.confidence_score = update_dto.confidence_score
            if update_dto.source_url is not None:
                memory.source_url = update_dto.source_url
            if update_dto.metadata is not None:
                memory.metadata.update(update_dto.metadata)
            
            # Save updated memory
            updated_memory = await memory_repo.save(memory)
            
            # Publish event
            event_store = await self.deps.get_event_store()
            await event_store.append(
                MemoryUpdated(
                    aggregate_id=memory.id.value,
                    fields_updated=list(update_dto.__dict__.keys()),
                )
            )
            
            await session.commit()
            
        return MemoryDTO.from_domain(updated_memory)


class DeleteMemoryUseCase(UseCase[UUID, bool]):
    """Use case for deleting a memory."""
    
    async def execute(self, memory_id: UUID) -> bool:
        """Delete a memory."""
        async with self.deps.begin_transaction() as session:
            memory_repo = await self.deps.get_memory_repository()
            
            # Check if memory exists
            memory = await memory_repo.get(MemoryId(memory_id))
            if not memory:
                raise NotFoundError("Memory", str(memory_id))
            
            # Delete memory
            deleted = await memory_repo.delete(memory.id)
            
            # Publish event
            event_store = await self.deps.get_event_store()
            await event_store.append(
                MemoryDeleted(
                    aggregate_id=memory.id.value,
                )
            )
            
            await session.commit()
            
        return deleted


class SearchMemoriesUseCase(UseCase[tuple[UUID, str, int], MemoryListDTO]):
    """Use case for searching memories."""
    
    async def execute(self, request: tuple[UUID, str, int]) -> MemoryListDTO:
        """Search memories for a user."""
        user_id, query, limit = request
        
        async with self.deps.begin_transaction() as session:
            memory_repo = await self.deps.get_memory_repository()
            
            # Search memories
            memories = await memory_repo.search(user_id, query, limit)
            
            # Get total count
            total = await memory_repo.count_by_user(user_id)
            
        return MemoryListDTO(
            memories=[MemoryDTO.from_domain(m) for m in memories],
            total=total,
            page=1,
            page_size=limit,
        )


class FindSimilarMemoriesUseCase(UseCase[tuple[UUID, str, int, float], MemoryListDTO]):
    """Use case for finding similar memories using embeddings."""
    
    async def execute(self, request: tuple[UUID, str, int, float]) -> MemoryListDTO:
        """Find memories similar to the given text."""
        user_id, query_text, limit, threshold = request
        
        # Generate embedding for query text
        embedding_client = EmbeddingClient()
        embedding_result = await embedding_client.generate_embedding(query_text)
        
        async with self.deps.begin_transaction() as session:
            memory_repo = await self.deps.get_memory_repository()
            
            # Find similar memories using pgvector
            memories = await memory_repo.find_similar(
                user_id,
                embedding_result.embedding,
                limit,
                threshold,
            )
            
            # Get total count
            total = await memory_repo.count_by_user(user_id)
            
        return MemoryListDTO(
            memories=[MemoryDTO.from_domain(m) for m in memories],
            total=total,
            page=1,
            page_size=limit,
        )


class LinkMemoriesUseCase(UseCase[tuple[UUID, UUID, str], bool]):
    """Use case for linking two memories."""
    
    async def execute(self, request: tuple[UUID, UUID, str]) -> bool:
        """Link two memories together."""
        from_id, to_id, link_type = request
        
        if from_id == to_id:
            raise ValidationError("Cannot link a memory to itself")
        
        async with self.deps.begin_transaction() as session:
            memory_repo = await self.deps.get_memory_repository()
            
            # Verify both memories exist
            from_memory = await memory_repo.get(MemoryId(from_id))
            if not from_memory:
                raise NotFoundError("Memory", str(from_id))
            
            to_memory = await memory_repo.get(MemoryId(to_id))
            if not to_memory:
                raise NotFoundError("Memory", str(to_id))
            
            # Create link
            linked = await memory_repo.link_memories(
                MemoryId(from_id),
                MemoryId(to_id),
                link_type,
            )
            
            # Publish event
            event_store = await self.deps.get_event_store()
            await event_store.append(
                MemoryLinked(
                    aggregate_id=from_id,
                    to_memory_id=to_id,
                    link_type=link_type,
                )
            )
            
            await session.commit()
            
        return linked