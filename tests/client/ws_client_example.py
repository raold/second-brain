"""
ws_client_example.py

Manual test/example client for the /ws/generate WebSocket endpoint.
- Supports both JSON and plain text streaming (toggle USE_JSON).
- Demonstrates authentication and chunked streaming.

Usage:
    python ws_client_example.py

Requires:
    pip install websockets
"""
import asyncio
import websockets
import json

API_TOKEN = "test-token"  # Replace with your valid token
PROMPT = "Hello world this is a test of real-time streaming"
USE_JSON = True  # Toggle: True for JSON chunks, False for plain text

async def consume_stream():
    url = f"ws://localhost:8000/ws/generate?token={API_TOKEN}"
    async with websockets.connect(url) as ws:
        # Send initial payload
        await ws.send(json.dumps({"prompt": PROMPT, "json": USE_JSON}))
        print(f"Connected. Streaming with USE_JSON={USE_JSON} ...")
        try:
            while True:
                msg = await ws.recv()
                if USE_JSON:
                    data = json.loads(msg)
                    if "error" in data:
                        print("Error:", data["error"])
                        break
                    print("Chunk:", data["text"], "| Meta:", data.get("meta"))
                else:
                    print("Chunk:", msg)
        except websockets.ConnectionClosed:
            print("WebSocket closed.")

if __name__ == "__main__":
    asyncio.run(consume_stream()) 