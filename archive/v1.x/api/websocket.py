import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.auth import verify_token_str
from app.utils.openai_client import elevenlabs_tts_stream, get_openai_stream

router = APIRouter()

async def websocket_auth(websocket: WebSocket):
    """
    Authenticate WebSocket connection using token from query parameters.
    
    Args:
        websocket: WebSocket connection
        
    Raises:
        WebSocketDisconnect: If authentication fails
    """
    token = websocket.query_params.get("token")
    if not token or not verify_token_str(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION)

async def process_llm_item(item, websocket, stream_json):
    """
    Process a single LLM item and stream the response.
    
    Args:
        item: Dictionary containing prompt and id
        websocket: WebSocket connection
        stream_json: Whether to include metadata in JSON response
    """
    try:
        prompt = item.get("prompt")
        req_id = item.get("id")
        if not prompt or not req_id:
            await websocket.send_json({"id": req_id, "error": "Missing prompt or id", "done": True})
            return
        async for chunk in get_openai_stream(prompt):
            msg = {"id": req_id, "chunk": chunk, "done": False}
            if stream_json:
                msg["meta"] = {"length": len(chunk)}
            await websocket.send_json(msg)
            await asyncio.sleep(0.01)
        await websocket.send_json({"id": req_id, "done": True})
    except Exception as e:
        await websocket.send_json({"id": item.get("id"), "error": str(e), "done": True})

async def process_tts_item(item, websocket, stream_json):
    """
    Process a single TTS item and stream the audio response.
    
    Args:
        item: Dictionary containing text and id
        websocket: WebSocket connection  
        stream_json: Whether to include metadata in JSON response
    """
    req_id = item.get("id")
    text = item.get("prompt") or item.get("text")
    if not text or not req_id:
        await websocket.send_json({"id": req_id, "error": "Missing text or id", "done": True})
        return
    try:
        async for chunk in elevenlabs_tts_stream(text):
            await websocket.send_json({"id": req_id, "chunk": chunk, "done": False, "tts": True})
            await asyncio.sleep(0.01)
        await websocket.send_json({"id": req_id, "done": True, "tts": True})
    except Exception as e:
        await websocket.send_json({"id": req_id, "error": str(e), "done": True, "tts": True})

def _parse_websocket_request(data: Dict[str, Any]) -> tuple[List[Dict], bool]:
    """
    Parse WebSocket request data and extract batch items and settings.
    
    Args:
        data: Raw request data from WebSocket
        
    Returns:
        Tuple of (batch_items, stream_json_flag)
    """
    batch = data.get("batch")
    stream_json = data.get("json", False)
    
    # Backward compatibility: single prompt
    if not batch:
        prompt = data.get("prompt")
        if not prompt:
            return None, stream_json
        # Wrap as batch
        batch = [{"id": "single", "prompt": prompt, "type": "llm"}]
    
    return batch, stream_json

async def _process_batch_items(batch: List[Dict], websocket: WebSocket, stream_json: bool) -> None:
    """
    Process all items in batch concurrently.
    
    Args:
        batch: List of items to process
        websocket: WebSocket connection
        stream_json: Whether to include metadata in responses
    """
    tasks = []
    for item in batch:
        item_type = item.get("type", "llm")
        if item_type == "llm":
            tasks.append(asyncio.create_task(process_llm_item(item, websocket, stream_json)))
        elif item_type == "tts":
            tasks.append(asyncio.create_task(process_tts_item(item, websocket, stream_json)))
        else:
            await websocket.send_json({"id": item.get("id"), "error": f"Unknown type: {item_type}", "done": True})
    
    if tasks:
        await asyncio.gather(*tasks)

@router.websocket("/ws/generate")
async def ws_generate(websocket: WebSocket):
    """
    WebSocket endpoint for generating LLM and TTS responses.
    Supports both single requests and batch processing.
    """
    await websocket.accept()
    try:
        # Authenticate connection
        await websocket_auth(websocket)
        
        # Receive and parse request
        data = await websocket.receive_json()
        batch, stream_json = _parse_websocket_request(data)
        
        # Handle missing prompt error
        if batch is None:
            await websocket.send_json({"error": "Missing prompt"})
            await websocket.close()
            return
        
        # Process batch items
        await _process_batch_items(batch, websocket, stream_json)
        
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        await websocket.close() 