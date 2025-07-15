from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse
from app.auth import verify_token_str
from app.utils.openai_client import get_openai_stream
import asyncio
import json

router = APIRouter()

async def websocket_auth(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token or not verify_token_str(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION)

@router.websocket("/ws/generate")
async def ws_generate(websocket: WebSocket):
    await websocket.accept()
    try:
        await websocket_auth(websocket)
        # Receive initial payload from client (e.g., prompt)
        data = await websocket.receive_json()
        prompt = data.get("prompt")
        stream_json = data.get("json", False)
        if not prompt:
            await websocket.send_json({"error": "Missing prompt"})
            await websocket.close()
            return
        # Simulate OpenAI streaming (replace with real OpenAI stream=True logic)
        async for chunk in get_openai_stream(prompt):
            if stream_json:
                await websocket.send_json({"text": chunk, "meta": {"length": len(chunk)}})
            else:
                await websocket.send_text(chunk)
            # Heartbeat ping (optional)
            await asyncio.sleep(0.01)
    except WebSocketDisconnect:
        # Handle disconnects gracefully
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        await websocket.close() 