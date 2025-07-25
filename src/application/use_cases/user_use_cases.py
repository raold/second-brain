"""
User-related use cases.

Contains business logic for user operations.
"""

import bcrypt
from uuid import UUID, uuid4

from src.application.dto.user_dto import (
    CreateUserDTO,
    LoginDTO,
    TokenDTO,
    UpdateUserDTO,
    UserDTO,
)
from src.application.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from src.application.use_cases.base import UseCase
from src.domain.events.user_events import (
    UserDeleted,
    UserLoggedIn,
    UserRegistered,
    UserUpdated,
)
from src.domain.models.user import User
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class RegisterUserUseCase(UseCase[CreateUserDTO, UserDTO]):
    """Use case for registering a new user."""
    
    async def execute(self, request: CreateUserDTO) -> UserDTO:
        """Register a new user."""
        async with self.deps.begin_transaction() as session:
            user_repo = await self.deps.get_user_repository()
            
            # Check if email already exists
            if await user_repo.exists_by_email(request.email):
                raise ConflictError(
                    "Email already registered",
                    "User",
                    request.email,
                )
            
            # Check if username already exists
            if await user_repo.exists_by_username(request.username):
                raise ConflictError(
                    "Username already taken",
                    "User",
                    request.username,
                )
            
            # Hash password
            password_hash = bcrypt.hashpw(
                request.password.encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8')
            
            # Create user
            user = User(
                id=uuid4(),
                email=request.email.lower(),
                username=request.username.lower(),
                full_name=request.full_name,
                password_hash=password_hash,
                role=request.role,
            )
            
            # Save user
            saved_user = await user_repo.save(user)
            
            # Publish event
            event_store = await self.deps.get_event_store()
            await event_store.append(
                UserRegistered(
                    aggregate_id=user.id,
                    email=user.email,
                    username=user.username,
                    role=user.role.value,
                )
            )
            
            await session.commit()
            
        return UserDTO.from_domain(saved_user)


class LoginUserUseCase(UseCase[LoginDTO, TokenDTO]):
    """Use case for user login."""
    
    async def execute(self, request: LoginDTO) -> TokenDTO:
        """Authenticate user and return tokens."""
        async with self.deps.begin_transaction() as session:
            user_repo = await self.deps.get_user_repository()
            
            # Find user by email or username
            user = None
            if "@" in request.username_or_email:
                user = await user_repo.get_by_email(request.username_or_email)
            else:
                user = await user_repo.get_by_username(request.username_or_email)
            
            if not user:
                raise AuthenticationError("Invalid credentials")
            
            # Verify password
            if not bcrypt.checkpw(
                request.password.encode('utf-8'),
                user.password_hash.encode('utf-8')
            ):
                raise AuthenticationError("Invalid credentials")
            
            # Check if user is active
            if not user.is_active:
                raise AuthenticationError("Account is disabled")
            
            # Update last login
            await user_repo.update_last_login(user.id)
            
            # Publish event
            event_store = await self.deps.get_event_store()
            await event_store.append(
                UserLoggedIn(aggregate_id=user.id)
            )
            
            await session.commit()
            
        # Generate tokens (simplified - in production use JWT)
        return TokenDTO(
            access_token=f"access_{user.id}",
            refresh_token=f"refresh_{user.id}",
        )


class GetUserUseCase(UseCase[UUID, UserDTO]):
    """Use case for retrieving user information."""
    
    async def execute(self, user_id: UUID) -> UserDTO:
        """Get user by ID."""
        async with self.deps.begin_transaction() as session:
            user_repo = await self.deps.get_user_repository()
            
            user = await user_repo.get(user_id)
            if not user:
                raise NotFoundError("User", str(user_id))
            
        return UserDTO.from_domain(user)


class UpdateUserUseCase(UseCase[tuple[UUID, UpdateUserDTO], UserDTO]):
    """Use case for updating user information."""
    
    async def execute(self, request: tuple[UUID, UpdateUserDTO]) -> UserDTO:
        """Update user information."""
        user_id, update_dto = request
        
        async with self.deps.begin_transaction() as session:
            user_repo = await self.deps.get_user_repository()
            
            # Get existing user
            user = await user_repo.get(user_id)
            if not user:
                raise NotFoundError("User", str(user_id))
            
            # Check email uniqueness if updating
            if update_dto.email and update_dto.email != user.email:
                if await user_repo.exists_by_email(update_dto.email):
                    raise ConflictError(
                        "Email already registered",
                        "User",
                        update_dto.email,
                    )
            
            # Check username uniqueness if updating
            if update_dto.username and update_dto.username != user.username:
                if await user_repo.exists_by_username(update_dto.username):
                    raise ConflictError(
                        "Username already taken",
                        "User",
                        update_dto.username,
                    )
            
            # Update fields
            if update_dto.email is not None:
                user.email = update_dto.email.lower()
            if update_dto.username is not None:
                user.username = update_dto.username.lower()
            if update_dto.full_name is not None:
                user.full_name = update_dto.full_name
            if update_dto.avatar_url is not None:
                user.avatar_url = update_dto.avatar_url
            if update_dto.bio is not None:
                user.bio = update_dto.bio
            if update_dto.preferences is not None:
                user.preferences.update(update_dto.preferences)
            
            # Save updated user
            updated_user = await user_repo.save(user)
            
            # Publish event
            event_store = await self.deps.get_event_store()
            await event_store.append(
                UserUpdated(
                    aggregate_id=user.id,
                    fields_updated=list(update_dto.__dict__.keys()),
                )
            )
            
            await session.commit()
            
        return UserDTO.from_domain(updated_user)


class DeleteUserUseCase(UseCase[UUID, bool]):
    """Use case for deleting a user."""
    
    async def execute(self, user_id: UUID) -> bool:
        """Delete a user account."""
        async with self.deps.begin_transaction() as session:
            user_repo = await self.deps.get_user_repository()
            
            # Check if user exists
            user = await user_repo.get(user_id)
            if not user:
                raise NotFoundError("User", str(user_id))
            
            # Delete user
            deleted = await user_repo.delete(user_id)
            
            # Publish event
            event_store = await self.deps.get_event_store()
            await event_store.append(
                UserDeleted(aggregate_id=user_id)
            )
            
            await session.commit()
            
        return deleted