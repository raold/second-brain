"""
Concrete user repository implementation using SQLAlchemy.

Implements the UserRepository interface with PostgreSQL.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.user import User, UserRole
from src.domain.repositories.user_repository import UserRepository
from src.infrastructure.database.models import UserModel
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class SQLUserRepository(UserRepository):
    """SQL implementation of user repository."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
    
    async def get(self, user_id: UUID) -> Optional[User]:
        """Get a user by ID."""
        result = await self.session.get(UserModel, user_id)
        
        if not result:
            return None
        
        return self._to_domain(result)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        result = await self.session.execute(
            self.session.query(UserModel).filter(
                UserModel.email == email.lower()
            )
        )
        
        user = result.scalar_one_or_none()
        if not user:
            return None
        
        return self._to_domain(user)
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get a user by username."""
        result = await self.session.execute(
            self.session.query(UserModel).filter(
                UserModel.username == username.lower()
            )
        )
        
        user = result.scalar_one_or_none()
        if not user:
            return None
        
        return self._to_domain(user)
    
    async def save(self, user: User) -> User:
        """Save a user (create or update)."""
        # Check if user exists
        existing = await self.session.get(UserModel, user.id)
        
        if existing:
            # Update existing
            existing.email = user.email
            existing.username = user.username
            existing.full_name = user.full_name
            existing.avatar_url = user.avatar_url
            existing.bio = user.bio
            existing.password_hash = user.password_hash
            existing.role = user.role.value
            existing.is_active = user.is_active
            existing.is_verified = user.is_verified
            existing.preferences = user.preferences
            existing.updated_at = datetime.utcnow()
            existing.memory_limit = user.memory_limit
            existing.storage_limit_mb = user.storage_limit_mb
            existing.api_rate_limit = user.api_rate_limit
            
            db_user = existing
        else:
            # Create new
            db_user = UserModel(
                id=user.id,
                email=user.email.lower(),
                username=user.username.lower(),
                full_name=user.full_name,
                avatar_url=user.avatar_url,
                bio=user.bio,
                password_hash=user.password_hash,
                role=user.role.value,
                is_active=user.is_active,
                is_verified=user.is_verified,
                preferences=user.preferences,
                created_at=user.created_at,
                updated_at=user.updated_at,
                last_login_at=user.last_login_at,
                memory_limit=user.memory_limit,
                storage_limit_mb=user.storage_limit_mb,
                api_rate_limit=user.api_rate_limit,
            )
            self.session.add(db_user)
        
        await self.session.flush()
        return user
    
    async def delete(self, user_id: UUID) -> bool:
        """Delete a user."""
        result = await self.session.get(UserModel, user_id)
        if not result:
            return False
        
        await self.session.delete(result)
        await self.session.flush()
        return True
    
    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
    ) -> list[User]:
        """List users with optional filters."""
        query = self.session.query(UserModel)
        
        if role:
            query = query.filter(UserModel.role == role.value)
        
        if is_active is not None:
            query = query.filter(UserModel.is_active == is_active)
        
        query = query.order_by(UserModel.created_at.desc())
        query = query.offset(skip).limit(limit)
        
        results = await self.session.execute(query)
        
        return [self._to_domain(row) for row in results.scalars()]
    
    async def search(
        self,
        query: str,
        limit: int = 50,
    ) -> list[User]:
        """Search users by name, email, or username."""
        search_query = f"%{query}%"
        
        results = await self.session.execute(
            self.session.query(UserModel).filter(
                (UserModel.email.ilike(search_query)) |
                (UserModel.username.ilike(search_query)) |
                (UserModel.full_name.ilike(search_query))
            ).limit(limit)
        )
        
        return [self._to_domain(row) for row in results.scalars()]
    
    async def update_last_login(self, user_id: UUID) -> None:
        """Update user's last login timestamp."""
        user = await self.session.get(UserModel, user_id)
        if user:
            user.last_login_at = datetime.utcnow()
            await self.session.flush()
    
    async def count(self, is_active: Optional[bool] = None) -> int:
        """Count users with optional filter."""
        query = func.count(UserModel.id)
        
        if is_active is not None:
            query = query.filter(UserModel.is_active == is_active)
        
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def exists_by_email(self, email: str) -> bool:
        """Check if a user with email exists."""
        result = await self.session.execute(
            func.count(UserModel.id).filter(
                UserModel.email == email.lower()
            )
        )
        return (result.scalar() or 0) > 0
    
    async def exists_by_username(self, username: str) -> bool:
        """Check if a user with username exists."""
        result = await self.session.execute(
            func.count(UserModel.id).filter(
                UserModel.username == username.lower()
            )
        )
        return (result.scalar() or 0) > 0
    
    def _to_domain(self, db_user: UserModel) -> User:
        """Convert database model to domain model."""
        return User(
            id=db_user.id,
            email=db_user.email,
            username=db_user.username,
            full_name=db_user.full_name,
            avatar_url=db_user.avatar_url,
            bio=db_user.bio,
            password_hash=db_user.password_hash,
            role=UserRole(db_user.role),
            is_active=db_user.is_active,
            is_verified=db_user.is_verified,
            preferences=db_user.preferences,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at,
            last_login_at=db_user.last_login_at,
            memory_limit=db_user.memory_limit,
            storage_limit_mb=db_user.storage_limit_mb,
            api_rate_limit=db_user.api_rate_limit,
        )