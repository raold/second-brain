"""
Session endpoints.

CRUD operations for chat sessions.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.api.dependencies import (
    Pagination,
    get_current_user_id,
    get_dependencies,
)
from src.application import Dependencies
from src.application.dto.session_dto import (
    AddMessageDTO,
    CreateSessionDTO,
    SessionDTO,
    SessionListDTO,
    UpdateSessionDTO,
)
from src.application.use_cases.session_use_cases import (
    AddMessageUseCase,
    CloseSessionUseCase,
    CreateSessionUseCase,
    GetSessionUseCase,
    UpdateSessionUseCase,
)

router = APIRouter()


@router.post("/", response_model=SessionDTO, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionDTO,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
):
    """
    Create a new session.
    
    Creates a chat session for conversations.
    """
    use_case = CreateSessionUseCase(deps)
    return await use_case(request)


@router.get("/{session_id}", response_model=SessionDTO)
async def get_session(
    session_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
):
    """
    Get a session by ID.
    
    Retrieves a specific session with its messages.
    """
    use_case = GetSessionUseCase(deps)
    return await use_case(session_id)


@router.put("/{session_id}", response_model=SessionDTO)
async def update_session(
    session_id: UUID,
    request: UpdateSessionDTO,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
):
    """
    Update a session.
    
    Updates session metadata and properties.
    """
    use_case = UpdateSessionUseCase(deps)
    return await use_case((session_id, request))


@router.post("/{session_id}/close", status_code=status.HTTP_204_NO_CONTENT)
async def close_session(
    session_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
):
    """
    Close a session.
    
    Marks a session as inactive.
    """
    use_case = CloseSessionUseCase(deps)
    await use_case(session_id)


@router.get("/", response_model=SessionListDTO)
async def list_sessions(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
    pagination: Annotated[Pagination, Depends()],
    is_active: bool = None,
):
    """
    List user's sessions.
    
    Returns a paginated list of sessions.
    """
    session_repo = await deps.get_session_repository()
    async with deps.begin_transaction() as session:
        sessions = await session_repo.get_by_user(
            user_id,
            skip=pagination.skip,
            limit=pagination.limit,
            is_active=is_active,
        )
        total = await session_repo.count_by_user(user_id, is_active=is_active)
    
    return SessionListDTO(
        sessions=[SessionDTO.from_domain(s) for s in sessions],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/{session_id}/messages", response_model=SessionDTO)
async def add_message(
    session_id: UUID,
    request: AddMessageDTO,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
):
    """
    Add a message to a session.
    
    Appends a new message to the session conversation.
    """
    use_case = AddMessageUseCase(deps)
    return await use_case((session_id, request))