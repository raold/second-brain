import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.auth import verify_token_str
from app.utils.openai_client import elevenlabs_tts_stream, get_openai_stream

router = APIRouter()

async def websocket_auth(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token or not verify_token_str(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION)

async def process_llm_item(item, websocket, stream_json):
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

# Placeholder for TTS processing (to be implemented)
async def process_tts_item(item, websocket, stream_json):
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

@router.websocket("/ws/generate")
async def ws_generate(websocket: WebSocket):
    await websocket.accept()
    try:
        await websocket_auth(websocket)
        data = await websocket.receive_json()
        batch = data.get("batch")
        stream_json = data.get("json", False)
        # Backward compatibility: single prompt
        if not batch:
            prompt = data.get("prompt")
            if not prompt:
                await websocket.send_json({"error": "Missing prompt"})
                await websocket.close()
                return
            # Wrap as batch
            batch = [{"id": "single", "prompt": prompt, "type": "llm"}]
        # Process all items in parallel
        tasks = []
        for item in batch:
            item_type = item.get("type", "llm")
            if item_type == "llm":
                tasks.append(asyncio.create_task(process_llm_item(item, websocket, stream_json)))
            elif item_type == "tts":
                tasks.append(asyncio.create_task(process_tts_item(item, websocket, stream_json)))
            else:
                await websocket.send_json({"id": item.get("id"), "error": f"Unknown type: {item_type}", "done": True})
        await asyncio.gather(*tasks)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        await websocket.close() 