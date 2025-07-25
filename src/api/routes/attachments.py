"""
Attachment endpoints.

File upload and download for memories.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from uuid import UUID

from src.api.dependencies import get_current_user_id, get_dependencies
from src.application import Dependencies
from src.application.services.attachment_service import AttachmentService
from src.domain.models.memory import MemoryId

router = APIRouter()


@router.post("/memories/{memory_id}/attachments", status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    memory_id: UUID,
    file: UploadFile = File(...),
    user_id: Annotated[UUID, Depends(get_current_user_id)] = None,
    deps: Annotated[Dependencies, Depends(get_dependencies)] = None,
):
    """
    Upload an attachment for a memory.
    
    Args:
        memory_id: Memory ID
        file: File to upload
        
    Returns:
        Attachment URL
    """
    # Verify memory exists and belongs to user
    memory_repo = await deps.get_memory_repository()
    async with deps.begin_transaction():
        memory = await memory_repo.get(MemoryId(memory_id))
        if not memory or memory.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found",
            )
    
    # Read file data
    data = await file.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file",
        )
    
    # Check file size (10MB limit)
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large (max 10MB)",
        )
    
    # Upload attachment
    attachment_service = AttachmentService()
    url = await attachment_service.upload_attachment(
        memory_id=MemoryId(memory_id),
        filename=file.filename,
        data=data,
        content_type=file.content_type,
    )
    
    if not url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload attachment",
        )
    
    # Update memory with attachment
    async with deps.begin_transaction() as session:
        memory.attachments.append(url)
        await memory_repo.save(memory)
        await session.commit()
    
    return {"url": url}


@router.get("/attachments/{attachment_id:path}")
async def download_attachment(
    attachment_id: str,
    user_id: Annotated[UUID, Depends(get_current_user_id)] = None,
    deps: Annotated[Dependencies, Depends(get_dependencies)] = None,
):
    """
    Download an attachment.
    
    Args:
        attachment_id: Attachment path
        
    Returns:
        File response
    """
    # Build full URL
    import os
    storage_endpoint = os.getenv("STORAGE_ENDPOINT", "http://localhost:9000")
    bucket = "secondbrain-attachments"
    attachment_url = f"{storage_endpoint}/{bucket}/{attachment_id}"
    
    # Download attachment
    attachment_service = AttachmentService()
    result = await attachment_service.download_attachment(attachment_url)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )
    
    data, content_type, filename = result
    
    return Response(
        content=data,
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
        },
    )


@router.delete("/memories/{memory_id}/attachments/{attachment_url:path}")
async def delete_attachment(
    memory_id: UUID,
    attachment_url: str,
    user_id: Annotated[UUID, Depends(get_current_user_id)] = None,
    deps: Annotated[Dependencies, Depends(get_dependencies)] = None,
):
    """
    Delete an attachment from a memory.
    
    Args:
        memory_id: Memory ID
        attachment_url: Attachment URL
        
    Returns:
        Success response
    """
    # Verify memory exists and belongs to user
    memory_repo = await deps.get_memory_repository()
    async with deps.begin_transaction() as session:
        memory = await memory_repo.get(MemoryId(memory_id))
        if not memory or memory.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found",
            )
        
        # Check if attachment belongs to memory
        if attachment_url not in memory.attachments:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attachment not found in memory",
            )
        
        # Delete from storage
        attachment_service = AttachmentService()
        deleted = await attachment_service.delete_attachment(attachment_url)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete attachment",
            )
        
        # Update memory
        memory.attachments.remove(attachment_url)
        await memory_repo.save(memory)
        await session.commit()
    
    return {"message": "Attachment deleted successfully"}