"""
User endpoints.

User profile and management operations.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.api.dependencies import (
    get_current_user_id,
    get_dependencies,
    require_admin,
)
from src.application import Dependencies
from src.application.dto.user_dto import UpdateUserDTO, UserDTO
from src.application.use_cases.user_use_cases import (
    DeleteUserUseCase,
    GetUserUseCase,
    UpdateUserUseCase,
)

router = APIRouter()


@router.get("/me", response_model=UserDTO)
async def get_current_user(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
):
    """
    Get current user profile.
    
    Returns the authenticated user's information.
    """
    use_case = GetUserUseCase(deps)
    return await use_case(user_id)


@router.put("/me", response_model=UserDTO)
async def update_current_user(
    request: UpdateUserDTO,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
):
    """
    Update current user profile.
    
    Updates the authenticated user's information.
    """
    use_case = UpdateUserUseCase(deps)
    return await use_case((user_id, request))


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
):
    """
    Delete current user account.
    
    Permanently deletes the user account and all associated data.
    """
    use_case = DeleteUserUseCase(deps)
    await use_case(user_id)


@router.get("/{user_id}", response_model=UserDTO)
async def get_user(
    user_id: UUID,
    admin_id: Annotated[UUID, Depends(require_admin)],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
):
    """
    Get user by ID (admin only).
    
    Retrieves any user's information.
    """
    use_case = GetUserUseCase(deps)
    return await use_case(user_id)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    admin_id: Annotated[UUID, Depends(require_admin)],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
):
    """
    Delete user by ID (admin only).
    
    Permanently deletes a user account.
    """
    use_case = DeleteUserUseCase(deps)
    await use_case(user_id)