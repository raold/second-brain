"""
Tag endpoints.

CRUD operations for tags.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_current_user_id, get_dependencies
from src.application import Dependencies
from src.application.dto.tag_dto import CreateTagDTO, TagDTO, TagListDTO, UpdateTagDTO
from src.application.use_cases.tag_use_cases import (
    CreateTagUseCase,
    DeleteTagUseCase,
    GetTagUseCase,
    GetUserTagsUseCase,
    UpdateTagUseCase,
)

router = APIRouter()


@router.post("/", response_model=TagDTO, status_code=status.HTTP_201_CREATED)
async def create_tag(
    request: CreateTagDTO,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
):
    """
    Create a new tag.
    
    Creates a tag for organizing memories.
    """
    use_case = CreateTagUseCase(deps)
    return await use_case(request)


@router.get("/{tag_id}", response_model=TagDTO)
async def get_tag(
    tag_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
):
    """
    Get a tag by ID.
    
    Retrieves a specific tag.
    """
    use_case = GetTagUseCase(deps)
    return await use_case(tag_id)


@router.put("/{tag_id}", response_model=TagDTO)
async def update_tag(
    tag_id: UUID,
    request: UpdateTagDTO,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
):
    """
    Update a tag.
    
    Updates tag properties.
    """
    use_case = UpdateTagUseCase(deps)
    return await use_case((tag_id, request))


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
):
    """
    Delete a tag.
    
    Removes a tag and its associations.
    """
    use_case = DeleteTagUseCase(deps)
    await use_case(tag_id)


@router.get("/", response_model=TagListDTO)
async def list_tags(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
):
    """
    List user's tags.
    
    Returns all tags for the user.
    """
    use_case = GetUserTagsUseCase(deps)
    return await use_case(user_id)