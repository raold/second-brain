"""
Memory endpoints.

CRUD operations for memories.
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.api.dependencies import (
    Pagination,
    get_current_user_id,
    get_dependencies,
)
from src.application import Dependencies
from src.application.dto.memory_dto import (
    CreateMemoryDTO,
    MemoryDTO,
    MemoryListDTO,
    UpdateMemoryDTO,
)
from src.application.use_cases.memory_use_cases import (
    CreateMemoryUseCase,
    DeleteMemoryUseCase,
    FindSimilarMemoriesUseCase,
    GetMemoryUseCase,
    LinkMemoriesUseCase,
    SearchMemoriesUseCase,
    UpdateMemoryUseCase,
)
from src.domain.models.memory import MemoryType

router = APIRouter()


@router.post("/", response_model=MemoryDTO, status_code=status.HTTP_201_CREATED)
async def create_memory(
    request: CreateMemoryDTO,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
):
    """
    Create a new memory.
    
    Creates a memory with the provided content and metadata.
    """
    use_case = CreateMemoryUseCase(deps)
    return await use_case(request)


@router.get("/{memory_id}", response_model=MemoryDTO)
async def get_memory(
    memory_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
):
    """
    Get a memory by ID.
    
    Retrieves a specific memory and updates its access time.
    """
    use_case = GetMemoryUseCase(deps)
    return await use_case(memory_id)


@router.put("/{memory_id}", response_model=MemoryDTO)
async def update_memory(
    memory_id: UUID,
    request: UpdateMemoryDTO,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
):
    """
    Update a memory.
    
    Updates the specified fields of a memory.
    """
    use_case = UpdateMemoryUseCase(deps)
    return await use_case((memory_id, request))


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: UUID,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
):
    """
    Delete a memory.
    
    Permanently removes a memory and its associations.
    """
    use_case = DeleteMemoryUseCase(deps)
    await use_case(memory_id)


@router.get("/", response_model=MemoryListDTO)
async def list_memories(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    deps: Annotated[Dependencies, Depends(get_dependencies)],
    pagination: Annotated[Pagination, Depends()],
    memory_type: Optional[MemoryType] = None,
    tag: Optional[str] = None,
):
    """
    List user's memories.
    
    Returns a paginated list of memories with optional filtering.
    """
    # Simple implementation - in production, create a proper list use case
    memory_repo = await deps.get_memory_repository()
    async with deps.begin_transaction() as session:
        memories = await memory_repo.get_by_user(
            user_id,
            skip=pagination.skip,
            limit=pagination.limit,
            memory_type=memory_type,
        )
        total = await memory_repo.count_by_user(user_id)
    
    return MemoryListDTO(
        memories=[MemoryDTO.from_domain(m) for m in memories],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/search", response_model=MemoryListDTO)
async def search_memories(
    q: str = Query(..., description="Search query"),
    user_id: Annotated[UUID, Depends(get_current_user_id)] = None,
    deps: Annotated[Dependencies, Depends(get_dependencies)] = None,
    limit: int = Query(50, ge=1, le=100),
):
    """
    Search memories.
    
    Searches memories by content and returns matching results.
    """
    use_case = SearchMemoriesUseCase(deps)
    return await use_case((user_id, q, limit))


@router.get("/similar", response_model=MemoryListDTO)
async def find_similar_memories(
    q: str = Query(..., description="Query text to find similar memories"),
    user_id: Annotated[UUID, Depends(get_current_user_id)] = None,
    deps: Annotated[Dependencies, Depends(get_dependencies)] = None,
    limit: int = Query(10, ge=1, le=50),
    threshold: float = Query(0.8, ge=0.0, le=1.0, description="Similarity threshold"),
):
    """
    Find similar memories using vector similarity.
    
    Uses embeddings to find memories semantically similar to the query text.
    """
    use_case = FindSimilarMemoriesUseCase(deps)
    return await use_case((user_id, q, limit, threshold))


@router.post("/{memory_id}/link/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def link_memories(
    memory_id: UUID,
    target_id: UUID,
    link_type: str = Query("related", description="Type of link"),
    user_id: Annotated[UUID, Depends(get_current_user_id)] = None,
    deps: Annotated[Dependencies, Depends(get_dependencies)] = None,
):
    """
    Link two memories.
    
    Creates a relationship between two memories.
    """
    use_case = LinkMemoriesUseCase(deps)
    await use_case((memory_id, target_id, link_type))