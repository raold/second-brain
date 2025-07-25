"""
Tag-related use cases.

Contains business logic for tag operations.
"""

from uuid import UUID, uuid4

from src.application.dto.tag_dto import CreateTagDTO, TagDTO, TagListDTO, UpdateTagDTO
from src.application.exceptions import ConflictError, NotFoundError
from src.application.use_cases.base import UseCase
from src.domain.models.tag import Tag, TagId
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class CreateTagUseCase(UseCase[CreateTagDTO, TagDTO]):
    """Use case for creating a new tag."""
    
    async def execute(self, request: CreateTagDTO) -> TagDTO:
        """Create a new tag."""
        # Get user from context (would come from auth in real app)
        user_id = UUID("00000000-0000-0000-0000-000000000001")  # Placeholder
        
        async with self.deps.begin_transaction() as session:
            tag_repo = await self.deps.get_tag_repository()
            
            # Check if tag name already exists for user
            existing = await tag_repo.get_by_name(user_id, request.name)
            if existing:
                raise ConflictError(
                    f"Tag '{request.name}' already exists",
                    "Tag",
                    request.name,
                )
            
            # Create tag
            tag = Tag(
                id=TagId(uuid4()),
                name=request.name.lower(),
                user_id=user_id,
                parent_id=TagId(request.parent_id) if request.parent_id else None,
                color=request.color,
                icon=request.icon,
                description=request.description,
            )
            
            # Save tag
            saved_tag = await tag_repo.save(tag)
            
            await session.commit()
            
        return TagDTO.from_domain(saved_tag)


class GetTagUseCase(UseCase[UUID, TagDTO]):
    """Use case for retrieving a tag."""
    
    async def execute(self, tag_id: UUID) -> TagDTO:
        """Get a tag by ID."""
        async with self.deps.begin_transaction() as session:
            tag_repo = await self.deps.get_tag_repository()
            
            tag = await tag_repo.get(TagId(tag_id))
            if not tag:
                raise NotFoundError("Tag", str(tag_id))
            
        return TagDTO.from_domain(tag)


class UpdateTagUseCase(UseCase[tuple[UUID, UpdateTagDTO], TagDTO]):
    """Use case for updating a tag."""
    
    async def execute(self, request: tuple[UUID, UpdateTagDTO]) -> TagDTO:
        """Update a tag."""
        tag_id, update_dto = request
        
        async with self.deps.begin_transaction() as session:
            tag_repo = await self.deps.get_tag_repository()
            
            # Get existing tag
            tag = await tag_repo.get(TagId(tag_id))
            if not tag:
                raise NotFoundError("Tag", str(tag_id))
            
            # Check name uniqueness if updating
            if update_dto.name and update_dto.name != tag.name:
                existing = await tag_repo.get_by_name(tag.user_id, update_dto.name)
                if existing:
                    raise ConflictError(
                        f"Tag '{update_dto.name}' already exists",
                        "Tag",
                        update_dto.name,
                    )
            
            # Update fields
            if update_dto.name is not None:
                tag.name = update_dto.name.lower()
            if update_dto.parent_id is not None:
                tag.parent_id = TagId(update_dto.parent_id) if update_dto.parent_id else None
            if update_dto.color is not None:
                tag.color = update_dto.color
            if update_dto.icon is not None:
                tag.icon = update_dto.icon
            if update_dto.description is not None:
                tag.description = update_dto.description
            
            # Save updated tag
            updated_tag = await tag_repo.save(tag)
            
            await session.commit()
            
        return TagDTO.from_domain(updated_tag)


class DeleteTagUseCase(UseCase[UUID, bool]):
    """Use case for deleting a tag."""
    
    async def execute(self, tag_id: UUID) -> bool:
        """Delete a tag."""
        async with self.deps.begin_transaction() as session:
            tag_repo = await self.deps.get_tag_repository()
            
            # Check if tag exists
            tag = await tag_repo.get(TagId(tag_id))
            if not tag:
                raise NotFoundError("Tag", str(tag_id))
            
            # Delete tag
            deleted = await tag_repo.delete(TagId(tag_id))
            
            await session.commit()
            
        return deleted


class GetUserTagsUseCase(UseCase[UUID, TagListDTO]):
    """Use case for getting all tags for a user."""
    
    async def execute(self, user_id: UUID) -> TagListDTO:
        """Get all tags for a user."""
        async with self.deps.begin_transaction() as session:
            tag_repo = await self.deps.get_tag_repository()
            
            # Get tags
            tags = await tag_repo.get_by_user(user_id, limit=1000)
            
        return TagListDTO(
            tags=[TagDTO.from_domain(tag) for tag in tags],
            total=len(tags),
            page=1,
            page_size=1000,
        )