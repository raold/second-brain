import asyncio
import json
import logging
import os
from datetime import datetime

import openai
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from openai import AsyncOpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

openai.api_key = os.getenv("OPENAI_API_KEY")

class PromptRequest(BaseModel):
    prompt: str
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 100


def _parse_json_message(data):
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return None

def _is_stop_command(message):
    return isinstance(message, dict) and message.get("command") == "stop"

def _validate_prompt_request(message):
    try:
        return PromptRequest.parse_obj(message), None
    except Exception as e:
        return None, str(e)

@router.websocket("/ws/generate")
async def websocket_generate(websocket: WebSocket):
    """
    WebSocket endpoint for streaming OpenAI completions with heartbeat and command handling.
    """
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
            message = _parse_json_message(data)
            if message is None:
                await websocket.send_text(json.dumps({"error": "Invalid JSON input."}))
                continue
            if _is_stop_command(message):
                logger.info("Stop command received.")
                stop_generation = True
                continue
            request_data, error = _validate_prompt_request(message)
            if error:
                logger.error(f"Invalid prompt input: {error}")
                await websocket.send_text(json.dumps({
                    "error": "Invalid input format. Expected JSON with prompt, model, temperature, max_tokens."
                }))
                continue
            stop_generation = False
            if request_data is not None:
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
        client = AsyncOpenAI()
        stream = await client.chat.completions.create(
            model=request.model,
            messages=[{"role": "user", "content": request.prompt}],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content if chunk.choices and chunk.choices[0].delta and hasattr(chunk.choices[0].delta, 'content') else None
            if content:
                yield {
                    "token": content,
                    "timestamp": datetime.utcnow().isoformat(),
                    "model": request.model
                }
    except Exception as e:
        logger.error(f"OpenAI streaming error: {e}")
        yield {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
