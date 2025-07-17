# app/router.py


from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import openai
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, delete, select, update

from app.auth import verify_token
from app.config import config
from app.models import Memory, MemoryFeedback, Payload, PayloadType, Priority
from app.storage.dual_storage import get_dual_storage
from app.storage.markdown_writer import write_markdown
from app.storage.postgres_client import get_postgres_client, AsyncSessionLocal, get_async_session
from app.storage.qdrant_client import client, qdrant_search, qdrant_upsert, to_uuid, get_qdrant_stats
from app.utils.logger import logger
from app.utils.cache import get_all_cache_stats, clear_all_caches

router = APIRouter()

# Stub for detect_intent_via_llm if not defined
async def detect_intent_via_llm(note):
    return "note"  # TODO: Replace with actual implementation

# Stub for UnexpectedResponse if not defined
class UnexpectedResponse(Exception):
    pass

async def store_memory_pg_background(payload: Payload):
    """Store memory in PostgreSQL in background."""
    try:
        async with AsyncSessionLocal() as session:
            await store_memory_pg(payload, session)
            await session.commit()
    except Exception as e:
        logger.error(f"Background PostgreSQL storage failed for {payload.id}: {e}")

async def store_memory_pg(payload: Payload, session):
    """Store memory in PostgreSQL."""
    memory = Memory(
        id=payload.id,
        qdrant_id=str(to_uuid(payload.id)),
        note=payload.data.get("note", ""),
        intent=payload.intent,
        type=payload.type.value if payload.type else None,
        user=payload.data.get("user"),
        meta=payload.meta
    )
    session.add(memory)
    if session.is_modified:
        await session.commit()
    else:
        await session.flush()
    return memory

async def _detect_or_assign_intent(payload: Payload) -> str:
    """Detect or assign intent for the payload."""
    try:
        if payload.intent:
            return payload.intent
            
        # Extract text content for intent detection
        text_content = payload.data.get("note", "") or str(payload.data)
        
        # Use simple heuristics for now (TODO: implement LLM-based detection)
        text_lower = text_content.lower()
        
        if any(word in text_lower for word in ["?", "how", "what", "why", "when", "where"]):
            return "question"
        elif any(word in text_lower for word in ["todo", "task", "need to", "should", "must"]):
            return "todo"
        elif any(word in text_lower for word in ["remind", "reminder", "remember", "don't forget"]):
            return "reminder"
        elif any(word in text_lower for word in ["command", "run", "execute", "cmd"]):
            return "command"
        else:
            return "note"
            
    except Exception as e:
        logger.warning(f"Intent detection failed for {payload.id}: {e}")
        return "note"


async def _store_in_qdrant_background(payload: Payload, embedding_vector: Optional[List[float]]):
    """Store in Qdrant in background for vector search compatibility."""
    try:
        if embedding_vector:
            await qdrant_upsert(payload, embedding_vector)
            logger.info(f"Stored {payload.id} in Qdrant")
        else:
            logger.warning(f"No embedding available for Qdrant storage: {payload.id}")
    except Exception as e:
        logger.error(f"Background Qdrant storage failed for {payload.id}: {e}")

def _perform_storage_operations(payload: Payload, background_tasks: BackgroundTasks) -> None:
    """
    Perform all storage operations for the payload.
    
    Args:
        payload: Payload to store
        background_tasks: FastAPI background tasks for async operations
    """
    # Store in markdown file
    write_markdown(payload)
    
    # Store in vector database
    qdrant_upsert(payload.model_dump())
    
    # Store in Postgres (background)
    background_tasks.add_task(store_memory_pg_background, payload)

def _build_ingest_response(payload: Payload) -> Dict[str, Any]:
    """
    Build the response dictionary for successful ingestion.
    
    Args:
        payload: Successfully ingested payload
        
    Returns:
        Response dictionary
    """
    return {
        "status": "ingested", 
        "id": payload.id, 
        "intent": payload.intent
    }

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint with PostgreSQL status."""
    from app.storage.postgres_client import postgres_client
    
    try:
        # Check PostgreSQL health
        pg_health = await postgres_client.health_check()
        
        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "version": "1.5.0",
            "services": {
                "postgresql": pg_health,
                "qdrant": "ok"  # Assume OK for now, could add Qdrant health check
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "degraded",
            "timestamp": datetime.now().isoformat(),
            "version": "1.5.0",
            "error": str(e),
            "services": {
                "postgresql": {"status": "unhealthy", "error": str(e)},
                "qdrant": "ok"
            }
        }

@router.post("/ingest")
async def ingest_endpoint(payload: Payload, background_tasks: BackgroundTasks, _: None = Depends(verify_token)) -> Dict[str, Any]:
    """
    Ingest a payload into the second brain system using dual storage.
    
    Args:
        payload: The payload to ingest
        background_tasks: FastAPI background tasks
        
    Returns:
        Dict containing status and payload ID
        
    Raises:
        HTTPException: If ingestion fails
    """
    try:
        logger.info(f"Received ingestion request: {payload.id}")
        
        # Auto-detect intent if not provided
        intent_type = await _detect_or_assign_intent(payload)
        
        # Get dual storage handler
        storage = await get_dual_storage()
        
        # Extract content from payload
        text_content = payload.data.get("note", "") or str(payload.data)
        user = payload.data.get("user")
        
        # Determine priority and tags
        priority = "normal"
        if payload.priority:
            priority = payload.priority.value
        
        tags = []
        if payload.type:
            tags.append(payload.type.value)
        if intent_type:
            tags.append(intent_type)
        
        # Store using dual storage system
        memory_id, embedding_vector = await storage.store_memory(
            payload_id=payload.id,
            text_content=text_content,
            intent_type=intent_type,
            priority=priority,
            source="api",
            tags=tags,
            metadata=payload.meta,
            user=user,
            create_embedding=True
        )
        
        # Also store in Qdrant for vector search (maintaining compatibility)
        background_tasks.add_task(_store_in_qdrant_background, payload, embedding_vector)
        
        logger.info(f"Successfully ingested payload: {payload.id} as memory: {memory_id}")
        
        return {
            "status": "success",
            "message": "Payload ingested successfully",
            "payload_id": payload.id,
            "memory_id": memory_id,
            "intent": intent_type,
            "priority": priority,
            "dual_storage": "enabled",
            "embedding_generated": embedding_vector is not None
        }
        
    except Exception as e:
        logger.error(f"Failed to ingest payload {payload.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest payload: {str(e)}"
        ) from e

@router.get("/search")
async def search_endpoint(
    q: str,
    model_version: Optional[str] = Query(None, description="Filter by model version"),
    embedding_model: Optional[str] = Query(None, description="Filter by embedding model"),
    type: Optional[str] = Query(None, description="Filter by record type"),
    timestamp_from: Optional[str] = Query(None, description="Filter: timestamp >= (ISO8601)"),
    timestamp_to: Optional[str] = Query(None, description="Filter: timestamp <= (ISO8601)"),
    _: None = Depends(verify_token)
) -> dict:
    """
    Search for semantically similar content, with optional metadata filtering.
    
    Args:
        q: Search query string
        model_version: Filter by model version
        embedding_model: Filter by embedding model
        type: Filter by record type
        timestamp_from: Filter: timestamp >= (ISO8601)
        timestamp_to: Filter: timestamp <= (ISO8601)
    Returns:
        Dict containing query and search results
    Raises:
        HTTPException: If search fails
    """
    try:
        logger.info(f"Received search query: q={q}, model_version={model_version}, embedding_model={embedding_model}, type={type}, timestamp_from={timestamp_from}, timestamp_to={timestamp_to}")
        filters = {}
        if model_version:
            filters["model_version"] = model_version
        if embedding_model:
            filters["embedding_model"] = embedding_model
        if type:
            filters["type"] = type
        if timestamp_from or timestamp_to:
            filters["timestamp"] = {"from": timestamp_from, "to": timestamp_to}
        results = qdrant_search(q, filters=filters)
        logger.info(f"Search completed: q={q}, num_results={len(results)}")
        return {"query": q, "results": results}
    except Exception as e:
        logger.error(f"Search failed for query '{q}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        ) from e

def _build_search_filters(model_version, embedding_model, type, timestamp_from, timestamp_to):
    """
    Build search filters dictionary from query parameters.
    
    Args:
        model_version: Optional model version filter
        embedding_model: Optional embedding model filter  
        type: Optional type filter
        timestamp_from: Optional start timestamp filter
        timestamp_to: Optional end timestamp filter
        
    Returns:
        Dictionary of filters for search
    """
    filters = {}
    if model_version:
        filters["model_version"] = model_version
    if embedding_model:
        filters["embedding_model"] = embedding_model
    if type:
        filters["type"] = type
    if timestamp_from or timestamp_to:
        filters["timestamp"] = {"from": timestamp_from, "to": timestamp_to}
    return filters

def _score_and_explain_result(r, filters):
    """
    Calculate metadata score and explanation for a search result.
    
    Args:
        r: Search result dictionary
        filters: Applied search filters
        
    Returns:
        Enhanced result with scores and explanation
    """
    meta_score = 0.0
    explanation = []
    model_version = filters.get("model_version")
    embedding_model = filters.get("embedding_model")
    type_ = filters.get("type")
    ts_filter = filters.get("timestamp")
    if model_version and r.get("model_version") == model_version:
        meta_score += 0.5
        explanation.append("model_version match")
    if embedding_model and r.get("embedding_model") == embedding_model:
        meta_score += 0.2
        explanation.append("embedding_model match")
    if type_ and r.get("type") == type_:
        meta_score += 0.2
        explanation.append("type match")
    if ts_filter:
        ts = r.get("timestamp")
        tf = ts_filter.get("from")
        tt = ts_filter.get("to")
        if ts and ((not tf or ts >= tf) and (not tt or ts <= tt)):
            meta_score += 0.1
            explanation.append("timestamp in range")
    meta_score = min(meta_score, 1.0)
    vector_score = r["score"]
    final_score = 0.8 * vector_score + 0.2 * meta_score
    return {
        **r,
        "vector_score": vector_score,
        "metadata_score": meta_score,
        "final_score": final_score,
        "explanation": ", ".join(explanation) or "vector only"
    }

def _rank_and_score_results(results: List[Dict], filters: Dict) -> List[Dict]:
    """
    Apply scoring and ranking to search results.
    
    Args:
        results: Raw search results from vector database
        filters: Applied search filters
        
    Returns:
        Ranked and scored results
    """
    ranked = [_score_and_explain_result(r, filters) for r in results]
    ranked.sort(key=lambda x: x["final_score"], reverse=True)
    return ranked

def _build_ranked_search_response(query: str, ranked_results: List[Dict]) -> Dict:
    """
    Build the response dictionary for ranked search.
    
    Args:
        query: Original search query
        ranked_results: Ranked and scored results
        
    Returns:
        Response dictionary
    """
    return {"query": query, "results": ranked_results}

@router.get("/ranked-search", tags=["Search"])
async def ranked_search_endpoint(
    q: str,
    model_version: Optional[str] = Query(None, description="Filter by model version"),
    embedding_model: Optional[str] = Query(None, description="Filter by embedding model"),
    type: Optional[str] = Query(None, description="Filter by record type"),
    timestamp_from: Optional[str] = Query(None, description="Filter: timestamp >= (ISO8601)"),
    timestamp_to: Optional[str] = Query(None, description="Filter: timestamp <= (ISO8601)"),
    _: None = Depends(verify_token)
) -> dict:
    """
    Hybrid ranked search: combines vector similarity and metadata relevance.
    Returns ranked results with score explanations.
    """
    try:
        logger.info(f"Received ranked search query: q={q}, model_version={model_version}, embedding_model={embedding_model}, type={type}, timestamp_from={timestamp_from}, timestamp_to={timestamp_to}")
        
        # Build search filters
        filters = _build_search_filters(model_version, embedding_model, type, timestamp_from, timestamp_to)
        
        # Get vector search results
        results = qdrant_search(q, filters=filters)
        
        # Rank and score results
        ranked_results = _rank_and_score_results(results, filters)
        
        logger.info(f"Ranked search completed: q={q}, num_results={len(ranked_results)}")
        return _build_ranked_search_response(q, ranked_results)
        
    except Exception as e:
        logger.error(f"Ranked search failed for query '{q}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ranked search failed: {str(e)}"
        ) from e

@router.post("/transcribe", tags=["Transcription"])
async def transcribe_endpoint(
    file: UploadFile = File(...),
    _: None = Depends(verify_token)
) -> dict:
    """
    Accept an audio file, transcribe it using OpenAI Whisper API, and return the transcript.
    """
    try:
        # Read audio file bytes
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file.")
        # Call OpenAI Whisper API
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=(file.filename, audio_bytes, file.content_type)
        )
        # OpenAI may return an object or dict; handle both
        text = getattr(transcript, "text", None) or (transcript["text"] if isinstance(transcript, dict) and "text" in transcript else None)
        if not text:
            raise HTTPException(status_code=500, detail="No transcript text returned.")
        return {"transcript": text}
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

@router.get("/records/{id}/version-history", tags=["Records"])
async def get_version_history(id: str, _: None = Depends(verify_token)) -> Dict[str, Any]:
    """
    Retrieve the version history for a given record ID.
    """
    try:
        result = client.retrieve(
            collection_name=config.qdrant['collection'],
            ids=[str(to_uuid(id))],
            with_payload=True
        )
        payload = getattr(result[0], "payload", None) if result and len(result) > 0 else None
        meta = payload.get("metadata", {}) if payload else None
        version_history = meta.get("version_history") if meta else None
        if not version_history:
            raise HTTPException(status_code=404, detail="Version history not found for this record.")
        return {"id": id, "version_history": version_history}
    except UnexpectedResponse:
        raise HTTPException(status_code=404, detail="Record not found.")
    except Exception as e:
        logger.error(f"Failed to fetch version history for {id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch version history: {e}") from e

@router.get("/zzzzzzzzzz", tags=["Records"])
async def zzzzzzzzzz_handler(
    type: Optional[str] = Query(None, description="Filter by record type"),
    note: Optional[str] = Query(None, description="Filter by note substring"),
    limit: int = Query(20, ge=1, le=100, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Records to skip"),
    _: None = Depends(verify_token)
) -> dict:
    """
    List records with optional filtering and pagination. (TEMP: /zzzzzzzzzz for deep conflict test)
    """
    try:
        # Qdrant scroll API for pagination
        scroll_result = client.scroll(
            collection_name=config.qdrant['collection'],
            limit=limit,
            offset=offset,
            with_payload=True
        )
        records = []
        for point in scroll_result[0]:
            payload = getattr(point, "payload", {}) or {}
            meta = payload.get("metadata", {}) if payload else {}
            data = payload.get("data", {}) if payload else {}
            # Filtering
            if type and payload.get("type") != type:
                continue
            if note and note.lower() not in data.get("note", "").lower():
                continue
            records.append({
                "id": str(point.id),
                "note": data.get("note", ""),
                "type": payload.get("type", ""),
                "timestamp": meta.get("timestamp", "")
            })
        return {"records": records, "total": len(records)}
    except Exception as e:
        logger.error(f"Failed to list records: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list records: {e}") from e

@router.get("/models", tags=["Models"])
def get_models():
    """
    Returns the current LLM and embedding model versions in use.
    """
    return {"model_versions": config.model_versions}

@router.get("/memories/search", tags=["Memories"])
async def memories_search(
    intent: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    note: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    include_deleted: bool = False,
    session=Depends(get_async_session)
):
    filters = []
    if intent:
        filters.append(Memory.intent == intent)
    if type:
        filters.append(Memory.type == type)
    if note:
        filters.append(Memory.note.ilike(f"%{note}%"))
    if date_from:
        filters.append(Memory.timestamp >= date_from)
    if date_to:
        filters.append(Memory.timestamp <= date_to)
    if not include_deleted:
        filters.append(not Memory.deleted)
    stmt = select(Memory).where(and_(*filters)) if filters else select(Memory)
    result = await session.execute(stmt)
    memories = [dict(row._mapping["Memory"].__dict__) for row in result.fetchall()]
    for m in memories:
        m.pop("_sa_instance_state", None)
    return {"results": memories}

@router.delete("/memories/{id}", tags=["Memories"])
async def delete_memory(id: str, hard: bool = False, session=Depends(get_async_session)):
    if hard:
        await session.execute(delete(Memory).where(Memory.id == id))
    else:
        await session.execute(update(Memory).where(Memory.id == id).values(deleted=True))
    await session.commit()
    # Delete from Qdrant if hard
    if hard:
        from app.storage.qdrant_client import client, to_uuid
        try:
            client.delete(collection_name=config.qdrant['collection'], points_selector=[str(to_uuid(id))])
        except Exception as e:
            logger.warning(f"Qdrant delete failed for {id}: {e}")
    return {"status": "deleted", "id": id, "hard": hard}

@router.put("/memories/{id}", tags=["Memories"])
async def update_memory(
    id: str,
    note: str,
    intent: Optional[str] = None,
    type: Optional[str] = None,
    session=Depends(get_async_session)
):
    # Update in Postgres
    stmt = update(Memory).where(Memory.id == id).values(note=note, intent=intent, type=type)
    await session.execute(stmt)
    await session.commit()
    # Re-embed and upsert in Qdrant
    from app.storage.qdrant_client import qdrant_upsert
    payload = Payload(
        id=id,
        type=PayloadType(type) if type else PayloadType.NOTE,
        intent=intent,
        context="corrected",
        priority=Priority.NORMAL,
        ttl="1d",
        data={"note": note},
        meta={"intent": intent},
        target="default"
    )
    qdrant_upsert(payload.model_dump())
    return {"status": "updated", "id": id, "note": note, "intent": intent, "type": type}

@router.post("/memories/summarize", tags=["Memories"])
async def summarize_memories(
    ids: Optional[List[str]] = None,
    query: Optional[str] = None,
    session=Depends(get_async_session)
):
    # Fetch memories by IDs or query
    memories = []
    if ids:
        result = await session.execute(select(Memory).where(Memory.id.in_(ids), not Memory.deleted))
        memories = [row._mapping["Memory"] for row in result.fetchall()]
    elif query:
        result = await session.execute(select(Memory).where(Memory.note.ilike(f"%{query}%"), not Memory.deleted))
        memories = [row._mapping["Memory"] for row in result.fetchall()]
    if not memories:
        return {"summary": "No memories found."}
    # Summarize with LLM (stub)
    notes = '\n'.join(m.note for m in memories)
    # TODO: Replace with real LLM call
    summary = f"Summary of {len(memories)} memories: {notes[:500]}..."
    return {"summary": summary}

@router.post("/memories/{id}/feedback", tags=["Memories"])
async def memory_feedback(id: str, feedback_type: str, user: Optional[str] = None, session=Depends(get_async_session)):
    import uuid

    from sqlalchemy import insert
    await session.execute(insert(MemoryFeedback).values(
        id=str(uuid.uuid4()),
        memory_id=id,
        user=user,
        feedback_type=feedback_type,
        timestamp=datetime.utcnow()
    ))
    await session.commit()
    return {"status": "ok"}

# New PostgreSQL-powered endpoints

@router.get("/memories/{memory_id}")
async def get_memory_endpoint(memory_id: str, _: None = Depends(verify_token)) -> Dict[str, Any]:
    """Get a specific memory by ID from PostgreSQL."""
    try:
        storage = await get_dual_storage()
        memory = await storage.get_memory(memory_id)
        
        if not memory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory not found: {memory_id}"
            )
        
        return {"memory": memory}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get memory {memory_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve memory: {str(e)}"
        )


@router.get("/memories")
async def search_memories_endpoint(
    query: Optional[str] = Query(None, description="Text to search for"),
    intent_types: Optional[str] = Query(None, description="Comma-separated intent types"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    priority: Optional[str] = Query(None, description="Priority level"),
    source: Optional[str] = Query(None, description="Source type"),
    date_from: Optional[str] = Query(None, description="Date from (ISO format)"),
    date_to: Optional[str] = Query(None, description="Date to (ISO format)"),
    limit: int = Query(20, description="Maximum results", ge=1, le=100),
    offset: int = Query(0, description="Results offset", ge=0),
    _: None = Depends(verify_token)
) -> Dict[str, Any]:
    """Search memories with advanced PostgreSQL filtering."""
    try:
        storage = await get_dual_storage()
        
        # Parse parameters
        intent_list = intent_types.split(",") if intent_types else None
        tag_list = tags.split(",") if tags else None
        
        date_from_obj = None
        date_to_obj = None
        
        if date_from:
            date_from_obj = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
        if date_to:
            date_to_obj = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
        
        # Search memories
        results = await storage.search_memories(
            query_text=query,
            intent_types=intent_list,
            tags=tag_list,
            priority=priority,
            source=source,
            date_from=date_from_obj,
            date_to=date_to_obj,
            limit=limit,
            offset=offset
        )
        
        return {
            "memories": results,
            "count": len(results),
            "filters": {
                "query": query,
                "intent_types": intent_list,
                "tags": tag_list,
                "priority": priority,
                "source": source,
                "date_from": date_from,
                "date_to": date_to
            },
            "pagination": {
                "limit": limit,
                "offset": offset
            }
        }
        
    except Exception as e:
        logger.error(f"Memory search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.put("/memories/{memory_id}")
async def update_memory_endpoint(
    memory_id: str,
    updates: Dict[str, Any],
    create_version: bool = Query(True, description="Create version history"),
    _: None = Depends(verify_token)
) -> Dict[str, Any]:
    """Update a memory with optional version history."""
    try:
        storage = await get_dual_storage()
        
        success = await storage.update_memory(memory_id, updates, create_version)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory not found or update failed: {memory_id}"
            )
        
        return {
            "status": "success",
            "message": "Memory updated successfully",
            "memory_id": memory_id,
            "version_created": create_version
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update memory {memory_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Update failed: {str(e)}"
        )


@router.post("/memories/{memory_id}/feedback")
async def submit_feedback_endpoint(
    memory_id: str,
    feedback_type: str,
    feedback_value: Optional[str] = None,
    feedback_score: Optional[float] = None,
    context: Optional[Dict[str, Any]] = None,
    _: None = Depends(verify_token)
) -> Dict[str, Any]:
    """Submit feedback for a memory."""
    try:
        storage = await get_dual_storage()
        
        success = await storage.submit_feedback(
            memory_id, feedback_type, feedback_value, feedback_score, context
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to submit feedback"
            )
        
        return {
            "status": "success",
            "message": "Feedback submitted successfully",
            "memory_id": memory_id,
            "feedback_type": feedback_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit feedback for {memory_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feedback submission failed: {str(e)}"
        )


@router.get("/analytics")
async def get_analytics_endpoint(_: None = Depends(verify_token)) -> Dict[str, Any]:
    """Get system analytics from dual storage."""
    try:
        storage = await get_dual_storage()
        analytics = await storage.get_analytics()
        
        return {
            "analytics": analytics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Analytics retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analytics failed: {str(e)}"
        )

@router.get("/performance", tags=["Monitoring"])
async def performance_stats_endpoint(_: None = Depends(verify_token)) -> Dict[str, Any]:
    """
    Get comprehensive performance statistics including cache metrics, database performance,
    and system optimization data.
    """
    try:
        logger.info("Collecting performance statistics")
        
        # Collect cache statistics
        cache_stats = get_all_cache_stats()
        
        # Collect PostgreSQL performance data
        postgres_stats = {}
        try:
            postgres_client = await get_postgres_client()
            postgres_health = await postgres_client.health_check()
            postgres_cache_stats = postgres_client.get_cache_stats()
            
            postgres_stats = {
                "health": postgres_health,
                "cache_statistics": postgres_cache_stats,
                "connection_pool": postgres_health.get("connection_pool", {})
            }
        except Exception as e:
            logger.warning(f"Failed to get PostgreSQL stats: {e}")
            postgres_stats = {"status": "error", "error": str(e)}
        
        # Collect Qdrant performance data
        qdrant_stats = {}
        try:
            qdrant_stats = get_qdrant_stats()
        except Exception as e:
            logger.warning(f"Failed to get Qdrant stats: {e}")
            qdrant_stats = {"status": "error", "error": str(e)}
        
        # Collect dual storage performance data
        dual_storage_stats = {}
        try:
            storage = await get_dual_storage()
            dual_storage_stats = storage.get_performance_stats()
        except Exception as e:
            logger.warning(f"Failed to get dual storage stats: {e}")
            dual_storage_stats = {"status": "error", "error": str(e)}
        
        # Calculate overall system health score
        system_health_score = _calculate_system_health_score(
            cache_stats, postgres_stats, qdrant_stats, dual_storage_stats
        )
        
        performance_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system_health_score": system_health_score,
            "cache_performance": cache_stats,
            "database_performance": {
                "postgresql": postgres_stats,
                "qdrant": qdrant_stats
            },
            "storage_performance": dual_storage_stats,
            "optimizations_enabled": {
                "lru_caching": True,
                "connection_pooling": True,
                "smart_eviction": True,
                "async_operations": True,
                "query_result_caching": True,
                "embedding_caching": True,
                "intent_detection_caching": True,
                "grpc_enabled": True
            },
            "recommendations": _generate_performance_recommendations(
                cache_stats, postgres_stats, qdrant_stats, dual_storage_stats
            )
        }
        
        logger.info("Performance statistics collected successfully")
        return performance_data
        
    except Exception as e:
        logger.error(f"Failed to collect performance statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Performance statistics collection failed: {str(e)}"
        ) from e

@router.get("/performance/cache", tags=["Monitoring"])
async def cache_stats_endpoint(_: None = Depends(verify_token)) -> Dict[str, Any]:
    """
    Get detailed cache performance statistics for all cache instances.
    """
    try:
        logger.info("Collecting cache statistics")
        
        cache_stats = get_all_cache_stats()
        
        # Add detailed analysis
        cache_analysis = {
            "total_cache_hit_rate": cache_stats.get("_summary", {}).get("overall_hit_rate_percent", 0),
            "cache_efficiency": _analyze_cache_efficiency(cache_stats),
            "recommendations": _generate_cache_recommendations(cache_stats),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return {
            "cache_statistics": cache_stats,
            "analysis": cache_analysis
        }
        
    except Exception as e:
        logger.error(f"Failed to collect cache statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache statistics collection failed: {str(e)}"
        ) from e

@router.post("/performance/cache/clear", tags=["Monitoring"])
async def clear_caches_endpoint(_: None = Depends(verify_token)) -> Dict[str, str]:
    """
    Clear all application caches. Use with caution as this will impact performance temporarily.
    """
    try:
        logger.warning("Clearing all application caches")
        
        # Clear all registered caches
        clear_all_caches()
        
        # Also clear specific storage caches
        try:
            postgres_client = await get_postgres_client()
            # PostgreSQL caches are cleared automatically when records are modified
        except Exception as e:
            logger.warning(f"Failed to access PostgreSQL client for cache clearing: {e}")
        
        logger.info("All caches cleared successfully")
        return {
            "status": "success", 
            "message": "All caches have been cleared",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to clear caches: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache clearing failed: {str(e)}"
        ) from e

@router.get("/performance/database", tags=["Monitoring"])
async def database_performance_endpoint(_: None = Depends(verify_token)) -> Dict[str, Any]:
    """
    Get detailed database performance metrics for PostgreSQL and Qdrant.
    """
    try:
        logger.info("Collecting database performance metrics")
        
        # PostgreSQL metrics
        postgres_metrics = {}
        try:
            postgres_client = await get_postgres_client()
            postgres_health = await postgres_client.health_check()
            postgres_cache_stats = postgres_client.get_cache_stats()
            
            postgres_metrics = {
                "status": postgres_health.get("status", "unknown"),
                "health_check": postgres_health,
                "cache_performance": postgres_cache_stats,
                "connection_pool_utilization": _calculate_pool_utilization(postgres_health),
                "query_performance": {
                    "avg_query_time_ms": postgres_health.get("query_time_ms", 0),
                    "health": "good" if postgres_health.get("query_time_ms", 0) < 100 else "slow"
                }
            }
        except Exception as e:
            logger.warning(f"Failed to get PostgreSQL metrics: {e}")
            postgres_metrics = {"status": "error", "error": str(e)}
        
        # Qdrant metrics
        qdrant_metrics = {}
        try:
            qdrant_metrics = get_qdrant_stats()
            qdrant_metrics["performance_analysis"] = _analyze_qdrant_performance(qdrant_metrics)
        except Exception as e:
            logger.warning(f"Failed to get Qdrant metrics: {e}")
            qdrant_metrics = {"status": "error", "error": str(e)}
        
        database_performance = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "postgresql": postgres_metrics,
            "qdrant": qdrant_metrics,
            "overall_status": _determine_overall_db_status(postgres_metrics, qdrant_metrics)
        }
        
        logger.info("Database performance metrics collected successfully")
        return database_performance
        
    except Exception as e:
        logger.error(f"Failed to collect database performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database performance collection failed: {str(e)}"
        ) from e

@router.get("/performance/recommendations", tags=["Monitoring"])
async def performance_recommendations_endpoint(_: None = Depends(verify_token)) -> Dict[str, Any]:
    """
    Get AI-generated performance optimization recommendations based on current system metrics.
    """
    try:
        logger.info("Generating performance recommendations")
        
        # Collect all performance data
        cache_stats = get_all_cache_stats()
        
        postgres_stats = {}
        try:
            postgres_client = await get_postgres_client()
            postgres_health = await postgres_client.health_check()
            postgres_cache_stats = postgres_client.get_cache_stats()
            postgres_stats = {"health": postgres_health, "cache": postgres_cache_stats}
        except Exception as e:
            postgres_stats = {"status": "error", "error": str(e)}
        
        qdrant_stats = {}
        try:
            qdrant_stats = get_qdrant_stats()
        except Exception as e:
            qdrant_stats = {"status": "error", "error": str(e)}
        
        dual_storage_stats = {}
        try:
            storage = await get_dual_storage()
            dual_storage_stats = storage.get_performance_stats()
        except Exception as e:
            dual_storage_stats = {"status": "error", "error": str(e)}
        
        # Generate comprehensive recommendations
        recommendations = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cache_recommendations": _generate_cache_recommendations(cache_stats),
            "database_recommendations": _generate_database_recommendations(postgres_stats, qdrant_stats),
            "storage_recommendations": _generate_storage_recommendations(dual_storage_stats),
            "system_recommendations": _generate_system_recommendations(
                cache_stats, postgres_stats, qdrant_stats, dual_storage_stats
            ),
            "priority_actions": _identify_priority_actions(
                cache_stats, postgres_stats, qdrant_stats, dual_storage_stats
            )
        }
        
        logger.info("Performance recommendations generated successfully")
        return recommendations
        
    except Exception as e:
        logger.error(f"Failed to generate performance recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Performance recommendations generation failed: {str(e)}"
        ) from e

# Helper functions for performance analysis

def _calculate_system_health_score(cache_stats, postgres_stats, qdrant_stats, dual_storage_stats) -> float:
    """Calculate overall system health score (0-100)."""
    try:
        score = 100.0
        
        # Cache performance (25% weight)
        cache_hit_rate = cache_stats.get("_summary", {}).get("overall_hit_rate_percent", 0)
        cache_score = min(cache_hit_rate, 100) * 0.25
        
        # Database performance (35% weight)
        db_score = 0
        if postgres_stats.get("health", {}).get("status") == "healthy":
            db_score += 15
        if qdrant_stats.get("status") == "healthy":
            db_score += 20
        
        # Storage performance (25% weight)
        storage_score = 0
        storage_success_rates = dual_storage_stats.get("storage_success_rates", {})
        postgres_success = storage_success_rates.get("postgres", {}).get("success_rate", 0)
        markdown_success = storage_success_rates.get("markdown", {}).get("success_rate", 0)
        storage_score = ((postgres_success + markdown_success) / 2) * 0.25
        
        # System optimization (15% weight)
        optimization_score = 15.0  # Assume optimizations are enabled
        
        total_score = cache_score + db_score + storage_score + optimization_score
        return round(min(max(total_score, 0), 100), 1)
        
    except Exception as e:
        logger.warning(f"Failed to calculate system health score: {e}")
        return 50.0  # Default neutral score

def _analyze_cache_efficiency(cache_stats) -> Dict[str, Any]:
    """Analyze cache efficiency and identify issues."""
    analysis = {
        "overall_efficiency": "good",
        "issues": [],
        "strengths": []
    }
    
    try:
        summary = cache_stats.get("_summary", {})
        hit_rate = summary.get("overall_hit_rate_percent", 0)
        
        if hit_rate > 80:
            analysis["overall_efficiency"] = "excellent"
            analysis["strengths"].append(f"High cache hit rate: {hit_rate:.1f}%")
        elif hit_rate > 60:
            analysis["overall_efficiency"] = "good"
            analysis["strengths"].append(f"Good cache hit rate: {hit_rate:.1f}%")
        elif hit_rate > 40:
            analysis["overall_efficiency"] = "fair"
            analysis["issues"].append(f"Moderate cache hit rate: {hit_rate:.1f}%")
        else:
            analysis["overall_efficiency"] = "poor"
            analysis["issues"].append(f"Low cache hit rate: {hit_rate:.1f}%")
        
        # Analyze individual caches
        for cache_name, cache_data in cache_stats.items():
            if cache_name == "_summary":
                continue
                
            cache_hit_rate = cache_data.get("hit_rate_percent", 0)
            eviction_count = cache_data.get("eviction_count", 0)
            
            if cache_hit_rate < 50:
                analysis["issues"].append(f"{cache_name} cache has low hit rate: {cache_hit_rate:.1f}%")
            
            if eviction_count > 100:
                analysis["issues"].append(f"{cache_name} cache has high eviction count: {eviction_count}")
        
    except Exception as e:
        logger.warning(f"Cache efficiency analysis failed: {e}")
        analysis["issues"].append("Analysis error occurred")
    
    return analysis

def _generate_cache_recommendations(cache_stats) -> List[str]:
    """Generate cache optimization recommendations."""
    recommendations = []
    
    try:
        summary = cache_stats.get("_summary", {})
        hit_rate = summary.get("overall_hit_rate_percent", 0)
        
        if hit_rate < 60:
            recommendations.append("Consider increasing cache sizes for frequently accessed data")
            recommendations.append("Review cache TTL settings - may be too short")
        
        if hit_rate < 40:
            recommendations.append("Investigate cache key generation - may have too much variation")
            recommendations.append("Consider implementing cache warming strategies")
        
        # Analyze individual caches
        for cache_name, cache_data in cache_stats.items():
            if cache_name == "_summary":
                continue
                
            size = cache_data.get("size", 0)
            max_size = cache_data.get("max_size", 1)
            eviction_count = cache_data.get("eviction_count", 0)
            
            if size / max_size > 0.9:
                recommendations.append(f"Consider increasing {cache_name} cache size (currently {size}/{max_size})")
            
            if eviction_count > 50:
                recommendations.append(f"High eviction rate in {cache_name} cache - consider larger size or longer TTL")
        
        if not recommendations:
            recommendations.append("Cache performance is optimal - no immediate optimizations needed")
            
    except Exception as e:
        logger.warning(f"Cache recommendations generation failed: {e}")
        recommendations.append("Unable to generate cache recommendations due to analysis error")
    
    return recommendations

def _calculate_pool_utilization(postgres_health) -> Dict[str, Any]:
    """Calculate database connection pool utilization."""
    try:
        pool_stats = postgres_health.get("connection_pool", {})
        checked_out = pool_stats.get("checked_out", 0)
        size = pool_stats.get("size", 1)
        
        utilization = (checked_out / size * 100) if size > 0 else 0
        
        return {
            "utilization_percent": round(utilization, 1),
            "status": "high" if utilization > 80 else "normal" if utilization > 40 else "low",
            "checked_out": checked_out,
            "pool_size": size
        }
    except Exception:
        return {"utilization_percent": 0, "status": "unknown"}

def _analyze_qdrant_performance(qdrant_stats) -> Dict[str, Any]:
    """Analyze Qdrant performance metrics."""
    analysis = {
        "status": "good",
        "issues": [],
        "optimizations": []
    }
    
    try:
        if qdrant_stats.get("status") != "healthy":
            analysis["status"] = "poor"
            analysis["issues"].append("Qdrant is not healthy")
        
        cache_stats = qdrant_stats.get("cache_statistics", {})
        search_cache = cache_stats.get("search_cache", {})
        
        if search_cache.get("hit_rate_percent", 0) < 50:
            analysis["issues"].append("Low search cache hit rate")
            analysis["optimizations"].append("Consider adjusting search cache TTL")
        
        performance_opts = qdrant_stats.get("performance_optimizations", {})
        if performance_opts.get("grpc_enabled"):
            analysis["optimizations"].append("gRPC enabled for better performance")
        
    except Exception as e:
        logger.warning(f"Qdrant performance analysis failed: {e}")
        analysis["issues"].append("Analysis error occurred")
    
    return analysis

def _determine_overall_db_status(postgres_stats, qdrant_stats) -> str:
    """Determine overall database system status."""
    try:
        postgres_healthy = postgres_stats.get("status") == "healthy" or postgres_stats.get("health", {}).get("status") == "healthy"
        qdrant_healthy = qdrant_stats.get("status") == "healthy"
        
        if postgres_healthy and qdrant_healthy:
            return "excellent"
        elif postgres_healthy or qdrant_healthy:
            return "partial"
        else:
            return "poor"
    except Exception:
        return "unknown"

def _generate_database_recommendations(postgres_stats, qdrant_stats) -> List[str]:
    """Generate database optimization recommendations."""
    recommendations = []
    
    try:
        # PostgreSQL recommendations
        if postgres_stats.get("status") != "healthy":
            recommendations.append("PostgreSQL connection issues detected - check database availability")
        
        pool_util = _calculate_pool_utilization(postgres_stats.get("health", {}))
        if pool_util.get("utilization_percent", 0) > 80:
            recommendations.append("High database connection pool utilization - consider increasing pool size")
        
        query_time = postgres_stats.get("health", {}).get("query_time_ms", 0)
        if query_time > 100:
            recommendations.append("Slow database queries detected - consider query optimization or indexing")
        
        # Qdrant recommendations
        if qdrant_stats.get("status") != "healthy":
            recommendations.append("Qdrant connection issues detected - check vector database availability")
        
        if not recommendations:
            recommendations.append("Database performance is optimal")
            
    except Exception as e:
        logger.warning(f"Database recommendations generation failed: {e}")
        recommendations.append("Unable to generate database recommendations")
    
    return recommendations

def _generate_storage_recommendations(dual_storage_stats) -> List[str]:
    """Generate storage optimization recommendations."""
    recommendations = []
    
    try:
        success_rates = dual_storage_stats.get("storage_success_rates", {})
        postgres_rate = success_rates.get("postgres", {}).get("success_rate", 0)
        markdown_rate = success_rates.get("markdown", {}).get("success_rate", 0)
        
        if postgres_rate < 95:
            recommendations.append(f"PostgreSQL storage success rate is {postgres_rate:.1f}% - investigate failures")
        
        if markdown_rate < 90:
            recommendations.append(f"Markdown storage success rate is {markdown_rate:.1f}% - check file system permissions")
        
        cache_stats = dual_storage_stats.get("dual_storage_cache", {})
        if cache_stats.get("hit_rate_percent", 0) < 60:
            recommendations.append("Dual storage cache hit rate is low - consider increasing cache size or TTL")
        
        if not recommendations:
            recommendations.append("Storage performance is optimal")
            
    except Exception as e:
        logger.warning(f"Storage recommendations generation failed: {e}")
        recommendations.append("Unable to generate storage recommendations")
    
    return recommendations

def _generate_system_recommendations(cache_stats, postgres_stats, qdrant_stats, dual_storage_stats) -> List[str]:
    """Generate overall system optimization recommendations."""
    recommendations = []
    
    try:
        system_health = _calculate_system_health_score(cache_stats, postgres_stats, qdrant_stats, dual_storage_stats)
        
        if system_health < 70:
            recommendations.append("System health score is below optimal - review individual component recommendations")
        
        if system_health < 50:
            recommendations.append("Critical: System performance is poor - immediate attention required")
            recommendations.append("Consider scaling resources or optimizing configuration")
        
        # General optimizations
        overall_hit_rate = cache_stats.get("_summary", {}).get("overall_hit_rate_percent", 0)
        if overall_hit_rate < 70:
            recommendations.append("Implement cache warming strategies for frequently accessed data")
        
        if not recommendations:
            recommendations.append("System is performing well - continue monitoring for optimization opportunities")
            
    except Exception as e:
        logger.warning(f"System recommendations generation failed: {e}")
        recommendations.append("Unable to generate system recommendations")
    
    return recommendations

def _identify_priority_actions(cache_stats, postgres_stats, qdrant_stats, dual_storage_stats) -> List[Dict[str, str]]:
    """Identify high-priority performance actions."""
    priority_actions = []
    
    try:
        # Critical issues first
        if postgres_stats.get("status") == "error":
            priority_actions.append({
                "priority": "critical",
                "action": "Fix PostgreSQL connection issues",
                "impact": "Database operations failing"
            })
        
        if qdrant_stats.get("status") == "error":
            priority_actions.append({
                "priority": "critical", 
                "action": "Fix Qdrant connection issues",
                "impact": "Vector search operations failing"
            })
        
        # High priority optimizations
        overall_hit_rate = cache_stats.get("_summary", {}).get("overall_hit_rate_percent", 0)
        if overall_hit_rate < 40:
            priority_actions.append({
                "priority": "high",
                "action": "Optimize cache configuration",
                "impact": "Poor cache performance affecting response times"
            })
        
        # Medium priority optimizations  
        pool_util = _calculate_pool_utilization(postgres_stats.get("health", {}))
        if pool_util.get("utilization_percent", 0) > 85:
            priority_actions.append({
                "priority": "medium",
                "action": "Increase database connection pool size",
                "impact": "High connection pool utilization may cause bottlenecks"
            })
        
        if not priority_actions:
            priority_actions.append({
                "priority": "low",
                "action": "Continue monitoring performance metrics",
                "impact": "System is performing well"
            })
            
    except Exception as e:
        logger.warning(f"Priority actions identification failed: {e}")
        priority_actions.append({
            "priority": "unknown",
            "action": "Review system manually",
            "impact": "Unable to analyze performance data"
        })
    
    return priority_actions

def _generate_performance_recommendations(cache_stats, postgres_stats, qdrant_stats, dual_storage_stats) -> List[str]:
    """Generate comprehensive performance recommendations based on all system metrics."""
    recommendations = []
    
    try:
        # Cache recommendations
        cache_hit_rate = cache_stats.get("_summary", {}).get("overall_hit_rate_percent", 0)
        if cache_hit_rate < 50:
            recommendations.append("Consider increasing cache sizes and TTL values for better hit rates")
        
        # Database recommendations
        postgres_status = postgres_stats.get("health", {}).get("status", "unknown")
        if postgres_status != "healthy":
            recommendations.append("Investigate PostgreSQL connection issues")
        
        query_time = postgres_stats.get("health", {}).get("query_time_ms", 0)
        if query_time > 100:
            recommendations.append("Optimize slow PostgreSQL queries")
        
        # Qdrant recommendations
        qdrant_status = qdrant_stats.get("status", "unknown")
        if qdrant_status != "healthy":
            recommendations.append("Check Qdrant service health and connectivity")
        
        # Storage recommendations
        storage_success_rates = dual_storage_stats.get("storage_success_rates", {})
        postgres_success = storage_success_rates.get("postgres", {}).get("success_rate", 100)
        if postgres_success < 95:
            recommendations.append("Investigate PostgreSQL storage failures")
        
        # General recommendations
        if not recommendations:
            recommendations.append("System is performing well - monitor regularly")
        
        return recommendations
        
    except Exception as e:
        logger.warning(f"Failed to generate performance recommendations: {e}")
        return ["Unable to generate recommendations - check system metrics"]
