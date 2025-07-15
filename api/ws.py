from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from datetime import datetime
import asyncio
import logging
import json
import openai
import os

logger = logging.getLogger(__name__)

router = APIRouter()

openai.api_key = os.getenv("OPENAI_API_KEY")

class PromptRequest(BaseModel):
    prompt: str
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 100


@router.websocket("/ws/generate")
async def websocket_generate(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection accepted")

    stop_generation = False

    async def heartbeat():
        """Send periodic ping to client to keep connection alive."""
        while True:
            await asyncio.sleep(10)
            try:
                await websocket.send_text(json.dumps({"event": "ping", "timestamp": datetime.utcnow().isoformat()}))
            except Exception:
                logger.info("Heartbeat failed, connection might be closed")
                break

    heartbeat_task = asyncio.create_task(heartbeat())

    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received input: {data}")

            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON input."}))
                continue

            if isinstance(message, dict) and message.get("command") == "stop":
                logger.info("Stop command received.")
                stop_generation = True
                continue

            try:
                request_data = PromptRequest.parse_obj(message)
            except Exception as e:
                logger.error(f"Invalid prompt input: {e}")
                await websocket.send_text(json.dumps({
                    "error": "Invalid input format. Expected JSON with prompt, model, temperature, max_tokens."
                }))
                continue

            stop_generation = False

            async for token_data in generate_openai_stream(request_data):
                if stop_generation:
                    logger.info("Generation stopped by client.")
                    break
                await websocket.send_text(json.dumps(token_data))

            await websocket.send_text(json.dumps({"event": "end_of_stream"}))

    except WebSocketDisconnect:
        logger.info("WebSocket connection disconnected")
    finally:
        heartbeat_task.cancel()


async def generate_openai_stream(request: PromptRequest):
    try:
        response = await openai.ChatCompletion.acreate(
            model=request.model,
            messages=[{"role": "user", "content": request.prompt}],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True
        )

        async for chunk in response:
            content = chunk["choices"][0].get("delta", {}).get("content")
            if content:
                yield {
                    "token": content,
                    "timestamp": datetime.utcnow().isoformat(),
                    "model": request.model
                }
    except Exception as e:
        logger.error(f"OpenAI streaming error: {e}")
        yield {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
