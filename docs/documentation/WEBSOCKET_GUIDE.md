# WebSocket Guide

Connect: `ws://localhost:8000/ws`

## Events

### Memory Created
```json
{
  "type": "memory.created",
  "data": {
    "id": "uuid",
    "content": "New memory",
    "timestamp": "2025-08-07T12:00:00Z"
  }
}
```

### Memory Updated
```json
{
  "type": "memory.updated",
  "data": {"id": "uuid", "changes": {...}}
}
```

### Memory Deleted
```json
{
  "type": "memory.deleted",
  "data": {"id": "uuid"}
}
```

## Client Example
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
    const {type, data} = JSON.parse(event.data);
    console.log(`Event: ${type}`, data);
};

ws.onerror = (error) => console.error('WebSocket error:', error);
```

## Python Client
```python
import websockets
import json

async with websockets.connect('ws://localhost:8000/ws') as ws:
    async for message in ws:
        event = json.loads(message)
        print(f"Event: {event['type']}")
```