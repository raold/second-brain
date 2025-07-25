"""
Concrete tag repository implementation using SQLAlchemy.

Implements the TagRepository interface with PostgreSQL.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.models.tag import Tag, TagId
from src.domain.repositories.tag_repository import TagRepository
from src.infrastructure.database.models import TagModel, memory_tags
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class SQLTagRepository(TagRepository):
    """SQL implementation of tag repository."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
    
    async def get(self, tag_id: TagId) -> Optional[Tag]:
        """Get a tag by ID."""
        result = await self.session.get(
            TagModel,
            tag_id.value,
            options=[
                selectinload(TagModel.children),
                selectinload(TagModel.parent),
            ]
        )
        
        if not result:
            return None
        
        return self._to_domain(result)
    
    async def get_by_name(self, user_id: UUID, name: str) -> Optional[Tag]:
        """Get a tag by name for a user."""
        result = await self.session.execute(
            self.session.query(TagModel).filter(
                and_(
                    TagModel.user_id == user_id,
                    TagModel.name == name.lower(),
                )
            ).options(
                selectinload(TagModel.children),
                selectinload(TagModel.parent),
            )
        )
        
        tag = result.scalar_one_or_none()
        if not tag:
            return None
        
        return self._to_domain(tag)
    
    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        parent_id: Optional[TagId] = None,
    ) -> list[Tag]:
        """Get tags for a user."""
        query = self.session.query(TagModel).filter(
            TagModel.user_id == user_id
        )
        
        if parent_id:
            query = query.filter(TagModel.parent_id == parent_id.value)
        else:
            query = query.filter(TagModel.parent_id.is_(None))
        
        query = query.order_by(TagModel.name).offset(skip).limit(limit)
        
        results = await self.session.execute(
            query.options(
                selectinload(TagModel.children),
                selectinload(TagModel.parent),
            )
        )
        
        return [self._to_domain(row) for row in results.scalars()]
    
    async def save(self, tag: Tag) -> Tag:
        """Save a tag (create or update)."""
        # Check if tag exists
        existing = await self.session.get(TagModel, tag.id.value)
        
        if existing:
            # Update existing
            existing.name = tag.name.lower()
            existing.parent_id = tag.parent_id.value if tag.parent_id else None
            existing.color = tag.color
            existing.icon = tag.icon
            existing.description = tag.description
            existing.usage_count = tag.usage_count
            existing.updated_at = datetime.utcnow()
            existing.last_used_at = tag.last_used_at
            
            db_tag = existing
        else:
            # Create new
            db_tag = TagModel(
                id=tag.id.value,
                name=tag.name.lower(),
                user_id=tag.user_id,
                parent_id=tag.parent_id.value if tag.parent_id else None,
                color=tag.color,
                icon=tag.icon,
                description=tag.description,
                usage_count=tag.usage_count,
                created_at=tag.created_at,
                updated_at=tag.updated_at,
                last_used_at=tag.last_used_at,
            )
            self.session.add(db_tag)
        
        await self.session.flush()
        return tag
    
    async def delete(self, tag_id: TagId) -> bool:
        """Delete a tag."""
        result = await self.session.get(TagModel, tag_id.value)
        if not result:
            return False
        
        await self.session.delete(result)
        await self.session.flush()
        return True
    
    async def search(
        self,
        user_id: UUID,
        query: str,
        limit: int = 50,
    ) -> list[Tag]:
        """Search tags by name or description."""
        search_query = f"%{query}%"
        
        results = await self.session.execute(
            self.session.query(TagModel).filter(
                and_(
                    TagModel.user_id == user_id,
                    or_(
                        TagModel.name.ilike(search_query),
                        TagModel.description.ilike(search_query),
                    ),
                )
            ).order_by(TagModel.usage_count.desc()).limit(limit).options(
                selectinload(TagModel.children),
                selectinload(TagModel.parent),
            )
        )
        
        return [self._to_domain(row) for row in results.scalars()]
    
    async def get_popular(
        self,
        user_id: UUID,
        limit: int = 20,
    ) -> list[Tag]:
        """Get most popular tags by usage count."""
        results = await self.session.execute(
            self.session.query(TagModel).filter(
                TagModel.user_id == user_id
            ).order_by(TagModel.usage_count.desc()).limit(limit).options(
                selectinload(TagModel.children),
                selectinload(TagModel.parent),
            )
        )
        
        return [self._to_domain(row) for row in results.scalars()]
    
    async def get_children(self, tag_id: TagId) -> list[Tag]:
        """Get child tags of a parent tag."""
        results = await self.session.execute(
            self.session.query(TagModel).filter(
                TagModel.parent_id == tag_id.value
            ).order_by(TagModel.name).options(
                selectinload(TagModel.children),
                selectinload(TagModel.parent),
            )
        )
        
        return [self._to_domain(row) for row in results.scalars()]
    
    async def get_hierarchy(self, user_id: UUID) -> dict[Optional[TagId], list[Tag]]:
        """Get complete tag hierarchy for a user."""
        results = await self.session.execute(
            self.session.query(TagModel).filter(
                TagModel.user_id == user_id
            ).order_by(TagModel.name).options(
                selectinload(TagModel.children),
                selectinload(TagModel.parent),
            )
        )
        
        hierarchy = {}
        for tag in results.scalars():
            parent_id = TagId(tag.parent_id) if tag.parent_id else None
            if parent_id not in hierarchy:
                hierarchy[parent_id] = []
            hierarchy[parent_id].append(self._to_domain(tag))
        
        return hierarchy
    
    async def merge_tags(
        self,
        source_tag_id: TagId,
        target_tag_id: TagId,
    ) -> bool:
        """Merge one tag into another."""
        try:
            # Update all memories with source tag to use target tag
            stmt = memory_tags.update().where(
                memory_tags.c.tag_id == source_tag_id.value
            ).values(tag_id=target_tag_id.value)
            
            await self.session.execute(stmt)
            
            # Update child tags to point to target
            await self.session.execute(
                self.session.query(TagModel).filter(
                    TagModel.parent_id == source_tag_id.value
                ).update({TagModel.parent_id: target_tag_id.value})
            )
            
            # Delete source tag
            await self.delete(source_tag_id)
            
            # Update target tag usage count
            target = await self.session.get(TagModel, target_tag_id.value)
            if target:
                result = await self.session.execute(
                    func.count(memory_tags.c.memory_id).filter(
                        memory_tags.c.tag_id == target_tag_id.value
                    )
                )
                target.usage_count = result.scalar() or 0
            
            await self.session.flush()
            return True
            
        except Exception as e:
            logger.error(f"Failed to merge tags: {e}")
            return False
    
    def _to_domain(self, db_tag: TagModel) -> Tag:
        """Convert database model to domain model."""
        return Tag(
            id=TagId(db_tag.id),
            name=db_tag.name,
            user_id=db_tag.user_id,
            parent_id=TagId(db_tag.parent_id) if db_tag.parent_id else None,
            color=db_tag.color,
            icon=db_tag.icon,
            description=db_tag.description,
            usage_count=db_tag.usage_count,
            created_at=db_tag.created_at,
            updated_at=db_tag.updated_at,
            last_used_at=db_tag.last_used_at,
        )