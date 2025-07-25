"""
Session-related use cases.

Contains business logic for session operations.
"""

from datetime import datetime
from uuid import UUID, uuid4

from src.application.dto.session_dto import (
    AddMessageDTO,
    CreateSessionDTO,
    SessionDTO,
    UpdateSessionDTO,
)
from src.application.exceptions import NotFoundError
from src.application.use_cases.base import UseCase
from src.domain.events.session_events import (
    SessionClosed,
    SessionCreated,
    SessionMessageAdded,
    SessionUpdated,
)
from src.domain.models.session import Session, SessionId
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


class CreateSessionUseCase(UseCase[CreateSessionDTO, SessionDTO]):
    """Use case for creating a new session."""
    
    async def execute(self, request: CreateSessionDTO) -> SessionDTO:
        """Create a new session."""
        # Get user from context (would come from auth in real app)
        user_id = UUID("00000000-0000-0000-0000-000000000001")  # Placeholder
        
        async with self.deps.begin_transaction() as session:
            # Create session
            chat_session = Session(
                id=SessionId(uuid4()),
                user_id=user_id,
                title=request.title,
                description=request.description,
                tags=request.tags,
                metadata=request.metadata,
            )
            
            # Save session
            session_repo = await self.deps.get_session_repository()
            saved_session = await session_repo.save(chat_session)
            
            # Publish event
            event_store = await self.deps.get_event_store()
            await event_store.append(
                SessionCreated(
                    aggregate_id=chat_session.id.value,
                    title=chat_session.title,
                )
            )
            
            await session.commit()
            
        return SessionDTO.from_domain(saved_session)


class GetSessionUseCase(UseCase[UUID, SessionDTO]):
    """Use case for retrieving a session."""
    
    async def execute(self, session_id: UUID) -> SessionDTO:
        """Get a session by ID."""
        async with self.deps.begin_transaction() as session:
            session_repo = await self.deps.get_session_repository()
            
            chat_session = await session_repo.get(SessionId(session_id))
            if not chat_session:
                raise NotFoundError("Session", str(session_id))
            
        return SessionDTO.from_domain(chat_session)


class UpdateSessionUseCase(UseCase[tuple[UUID, UpdateSessionDTO], SessionDTO]):
    """Use case for updating a session."""
    
    async def execute(self, request: tuple[UUID, UpdateSessionDTO]) -> SessionDTO:
        """Update a session."""
        session_id, update_dto = request
        
        async with self.deps.begin_transaction() as session:
            session_repo = await self.deps.get_session_repository()
            
            # Get existing session
            chat_session = await session_repo.get(SessionId(session_id))
            if not chat_session:
                raise NotFoundError("Session", str(session_id))
            
            # Update fields
            if update_dto.title is not None:
                chat_session.title = update_dto.title
            if update_dto.description is not None:
                chat_session.description = update_dto.description
            if update_dto.is_active is not None:
                chat_session.is_active = update_dto.is_active
            if update_dto.tags is not None:
                chat_session.tags = update_dto.tags
            if update_dto.metadata is not None:
                chat_session.metadata.update(update_dto.metadata)
            
            # Save updated session
            updated_session = await session_repo.save(chat_session)
            
            # Publish event
            event_store = await self.deps.get_event_store()
            await event_store.append(
                SessionUpdated(
                    aggregate_id=chat_session.id.value,
                )
            )
            
            await session.commit()
            
        return SessionDTO.from_domain(updated_session)


class CloseSessionUseCase(UseCase[UUID, bool]):
    """Use case for closing a session."""
    
    async def execute(self, session_id: UUID) -> bool:
        """Close a session."""
        async with self.deps.begin_transaction() as session:
            session_repo = await self.deps.get_session_repository()
            
            # Get session
            chat_session = await session_repo.get(SessionId(session_id))
            if not chat_session:
                raise NotFoundError("Session", str(session_id))
            
            # Mark as inactive
            chat_session.is_active = False
            await session_repo.save(chat_session)
            
            # Publish event
            event_store = await self.deps.get_event_store()
            await event_store.append(
                SessionClosed(aggregate_id=session_id)
            )
            
            await session.commit()
            
        return True


class AddMessageUseCase(UseCase[tuple[UUID, AddMessageDTO], SessionDTO]):
    """Use case for adding a message to a session."""
    
    async def execute(self, request: tuple[UUID, AddMessageDTO]) -> SessionDTO:
        """Add a message to a session."""
        session_id, message_dto = request
        
        async with self.deps.begin_transaction() as session:
            session_repo = await self.deps.get_session_repository()
            
            # Get session
            chat_session = await session_repo.get(SessionId(session_id))
            if not chat_session:
                raise NotFoundError("Session", str(session_id))
            
            # Add message
            message = {
                "role": message_dto.role,
                "content": message_dto.content,
                "metadata": message_dto.metadata,
                "timestamp": datetime.utcnow().isoformat(),
            }
            chat_session.messages.append(message)
            
            # Update activity
            await session_repo.update_activity(chat_session.id)
            
            # Save session
            updated_session = await session_repo.save(chat_session)
            
            # Publish event
            event_store = await self.deps.get_event_store()
            await event_store.append(
                SessionMessageAdded(
                    aggregate_id=session_id,
                    message=message,
                )
            )
            
            await session.commit()
            
        return SessionDTO.from_domain(updated_session)