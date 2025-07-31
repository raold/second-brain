"""
WebSocket routes for real-time updates
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.synthesis.websocket_service import get_websocket_service
from app.dependencies import get_db_instance
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/connect")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="Authentication token"),
    db: AsyncSession = Depends(get_db_instance)
):
    """
    WebSocket endpoint for real-time updates.

    Authentication:
    - Pass authentication token as query parameter: ws://localhost:8000/ws/connect?token=your_token

    Message Types:
    - ping/pong: Heartbeat messages
    - subscribe/unsubscribe: Manage event subscriptions

    Event Types:
    - memory.created/updated/deleted: Memory events
    - connection.created/deleted: Connection events
    - metrics.updated/anomaly: Metrics events
    - review.due/completed: Review events
    - synthesis.*: Synthesis events (consolidation, summary, etc.)
    - system.notification: System notifications

    Example Messages:

    Subscribe to events:
    ```json
    {
        "type": "subscribe",
        "action": "subscribe",
        "subscription_types": ["memories", "metrics"]
    }
    ```

    Heartbeat:
    ```json
    {
        "type": "ping",
        "sequence": 1
    }
    ```
    """
    # Validate token (simplified for demo)
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    # Extract user_id from token (simplified)
    # In production, properly decode and validate JWT token
    user_id = token.split("_")[0] if "_" in token else "demo_user"

    # Generate connection ID
    connection_id = str(uuid.uuid4())

    # Get WebSocket service
    ws_service = await get_websocket_service(db)

    try:
        # Handle connection
        await ws_service.handle_connection(websocket, user_id, connection_id)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=4000, reason="Internal error")


@router.get("/status")
async def get_websocket_status(
    db: AsyncSession = Depends(get_db_instance)
) -> dict:
    """Get WebSocket service status and statistics."""
    ws_service = await get_websocket_service(db)
    stats = ws_service.connection_manager.get_connection_stats()

    return {
        "status": "active",
        "statistics": stats,
        "server_time": datetime.utcnow().isoformat()
    }


# Example usage documentation
WEBSOCKET_EXAMPLES = """
# WebSocket Connection Examples

## JavaScript/Browser

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/connect?token=user123_token');

// Connection opened
ws.onopen = function(event) {
    console.log('Connected to WebSocket');

    // Subscribe to events
    ws.send(JSON.stringify({
        type: 'subscribe',
        action: 'subscribe',
        subscription_types: ['memories', 'reviews']
    }));
};

// Handle messages
ws.onmessage = function(event) {
    const message = JSON.parse(event.data);

    switch(message.type) {
        case 'memory.created':
            console.log('New memory created:', message.data);
            break;
        case 'review.due':
            console.log('Review due:', message.data);
            break;
        case 'system.notification':
            showNotification(message.data.title, message.data.message);
            break;
        case 'pong':
            console.log('Heartbeat response:', message.sequence);
            break;
    }
};

// Send heartbeat
setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'ping',
            sequence: Date.now()
        }));
    }
}, 30000);

// Handle errors
ws.onerror = function(error) {
    console.error('WebSocket error:', error);
};

// Handle close
ws.onclose = function(event) {
    console.log('WebSocket closed:', event.code, event.reason);
};
```

## Python Client

```python
import asyncio
import json
import websockets

async def client():
    uri = "ws://localhost:8000/ws/connect?token=user123_token"

    async with websockets.connect(uri) as websocket:
        # Subscribe to events
        await websocket.send(json.dumps({
            "type": "subscribe",
            "action": "subscribe",
            "subscription_types": ["memories", "metrics"]
        }))

        # Listen for messages
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data['type']}")

            # Handle different message types
            if data['type'] == 'memory.created':
                print(f"New memory: {data['data']['title']}")
            elif data['type'] == 'metrics.updated':
                print(f"Metrics update: {data['data']}")

asyncio.run(client())
```

## React Hook Example

```jsx
import { useEffect, useState, useCallback } from 'react';
from typing import Optional
from fastapi import Query
from fastapi import Depends
from fastapi import APIRouter
from datetime import datetime
from app.dependencies.auth import verify_api_key, get_current_user, get_db_instance

function useWebSocket(token) {
    const [ws, setWs] = useState(null);
    const [messages, setMessages] = useState([]);
    const [connected, setConnected] = useState(false);

    useEffect(() => {
        const websocket = new WebSocket(`ws://localhost:8000/ws/connect?token=${token}`);

        websocket.onopen = () => {
            setConnected(true);
            setWs(websocket);

            // Subscribe to all events
            websocket.send(JSON.stringify({
                type: 'subscribe',
                action: 'subscribe',
                subscription_types: ['all']
            }));
        };

        websocket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            setMessages(prev => [...prev, message]);
        };

        websocket.onclose = () => {
            setConnected(false);
        };

        return () => {
            websocket.close();
        };
    }, [token]);

    const sendMessage = useCallback((message) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(message));
        }
    }, [ws]);

    return { connected, messages, sendMessage };
}

// Usage
function MyComponent() {
    const { connected, messages, sendMessage } = useWebSocket('user123_token');

    // Handle real-time updates
    useEffect(() => {
        const latestMessage = messages[messages.length - 1];
        if (latestMessage?.type === 'memory.created') {
            // Update UI with new memory
        }
    }, [messages]);

    return (
        <div>
            <div>Status: {connected ? 'Connected' : 'Disconnected'}</div>
            <div>Messages: {messages.length}</div>
        </div>
    );
}
```
"""
