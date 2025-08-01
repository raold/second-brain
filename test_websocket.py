#!/usr/bin/env python3
"""Test WebSocket connection to V2 API"""

import asyncio
import json
import websockets

async def test_websocket():
    uri = "ws://localhost:8000/api/v2/ws?api_key=test-token-for-development"
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Waiting for messages...")
            
            # Listen for messages
            message_count = 0
            while message_count < 3:  # Get first 3 messages
                message = await websocket.recv()
                data = json.loads(message)
                
                print(f"\nMessage {message_count + 1}:")
                print(f"Type: {data.get('type')}")
                print(f"Timestamp: {data.get('timestamp')}")
                
                if data['type'] == 'metrics_update':
                    print(f"Metrics: {json.dumps(data['data'], indent=2)}")
                elif data['type'] == 'connection':
                    print(f"Status: {data.get('status')}")
                
                message_count += 1
                
            print("\nWebSocket test successful!")
            
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())