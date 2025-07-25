# Week 2 API Documentation - v2.8.2 "Synthesis"

This document covers the new API endpoints and features implemented in Week 2 of the v2.8.2 release.

## Table of Contents

1. [Automated Report Generation](#automated-report-generation)
2. [Spaced Repetition Scheduling](#spaced-repetition-scheduling)
3. [Real-time WebSocket Updates](#real-time-websocket-updates)

---

## Automated Report Generation

The report generation system provides comprehensive analytics and insights about your knowledge base.

### Base URL
```
/synthesis/reports
```

### Authentication
All endpoints require Bearer token authentication:
```
Authorization: Bearer <your_token>
```

### Report Types

- `daily`: Daily activity summary
- `weekly`: Weekly progress report
- `monthly`: Monthly comprehensive report
- `quarterly`: Quarterly analysis
- `annual`: Annual review
- `insights`: AI-powered insights report
- `progress`: Learning progress report
- `knowledge_map`: Visual knowledge map
- `learning_path`: Personalized learning path

### Endpoints

#### Generate Report
```http
POST /synthesis/reports/generate
```

**Request Body:**
```json
{
  "report_type": "weekly",
  "format": "pdf",
  "period_days": 7,
  "include_visualizations": true,
  "include_metrics": true,
  "include_recommendations": true,
  "custom_sections": ["summary", "highlights", "statistics"]
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user123",
  "report_type": "weekly",
  "title": "Weekly Progress Report",
  "subtitle": "January 15-22, 2025",
  "executive_summary": "This week showed significant progress...",
  "sections": [
    {
      "type": "highlights",
      "title": "Key Highlights",
      "content": "..."
    }
  ],
  "format": "pdf",
  "file_path": "/reports/2025/01/weekly_report_jan15-22.pdf",
  "generation_time_ms": 1234,
  "created_at": "2025-01-22T10:00:00Z"
}
```

#### Get Report Templates
```http
GET /synthesis/reports/templates
```

**Response:**
```json
[
  {
    "id": "template1",
    "name": "Weekly Summary",
    "description": "Comprehensive weekly activity summary",
    "report_type": "weekly",
    "sections": ["executive_summary", "highlights", "statistics"],
    "include_visualizations": true
  }
]
```

#### Schedule Report
```http
POST /synthesis/reports/schedules
```

**Request Body:**
```json
{
  "template_id": "template1",
  "report_type": "weekly",
  "format": "email",
  "schedule_type": "weekly",
  "schedule_config": {
    "day_of_week": "monday",
    "time": "09:00"
  },
  "recipients": ["user@example.com"],
  "enabled": true
}
```

#### Get Report History
```http
GET /synthesis/reports/history?report_type=weekly&limit=10
```

#### Download Report
```http
GET /synthesis/reports/{report_id}/download?format=pdf
```

---

## Spaced Repetition Scheduling

The spaced repetition system optimizes memory retention through scientifically-proven review scheduling.

### Base URL
```
/synthesis/repetition
```

### Algorithms

- `sm2`: SuperMemo 2 algorithm (default)
- `anki`: Anki-style algorithm
- `leitner`: Leitner box system
- `custom`: Custom algorithm

### Difficulty Ratings

- `again`: Complete blackout (0)
- `hard`: Difficult recall (1)
- `good`: Correct recall (2)
- `easy`: Perfect recall (3)

### Endpoints

#### Schedule Memory for Review
```http
POST /synthesis/repetition/schedule/{memory_id}?algorithm=sm2
```

**Response:**
```json
{
  "id": "review123",
  "memory_id": "memory456",
  "user_id": "user123",
  "scheduled_for": "2025-01-23T10:00:00Z",
  "interval_days": 1,
  "ease_factor": 2.5,
  "algorithm": "sm2",
  "status": "scheduled",
  "created_at": "2025-01-22T10:00:00Z"
}
```

#### Get Due Reviews
```http
GET /synthesis/repetition/due?date=2025-01-22&limit=20&include_overdue=true
```

**Response:**
```json
[
  {
    "id": "review123",
    "memory_id": "memory456",
    "scheduled_for": "2025-01-22T10:00:00Z",
    "status": "overdue",
    "interval_days": 3,
    "review_count": 5
  }
]
```

#### Complete Review
```http
POST /synthesis/repetition/review/{review_id}/complete
```

**Request Body:**
```json
{
  "memory_id": "memory456",
  "difficulty": "good",
  "time_taken_seconds": 25,
  "confidence_score": 0.85
}
```

**Response:**
```json
{
  "id": "review789",
  "memory_id": "memory456",
  "scheduled_for": "2025-01-25T10:00:00Z",
  "interval_days": 3,
  "ease_factor": 2.5,
  "status": "scheduled"
}
```

#### Get Memory Strength
```http
GET /synthesis/repetition/strength/{memory_id}
```

**Response:**
```json
{
  "memory_id": "memory456",
  "strength": 0.85,
  "stability_days": 30,
  "retrievability": 0.92,
  "last_review": "2025-01-20T10:00:00Z",
  "next_review": "2025-01-25T10:00:00Z",
  "review_count": 5,
  "average_ease": 2.4
}
```

#### Get Review Statistics
```http
GET /synthesis/repetition/statistics?period=week
```

**Response:**
```json
{
  "period": "week",
  "total_reviews": 50,
  "reviews_completed": 45,
  "success_rate": 0.9,
  "average_difficulty": 2.3,
  "current_streak": 7,
  "longest_streak": 15,
  "daily_average": 6.4
}
```

#### Get Optimal Review Time
```http
GET /synthesis/repetition/optimal-time
```

**Response:**
```json
{
  "recommended_hour": 9,
  "recommended_time": "09:00",
  "performance_by_hour": {
    "9": 0.92,
    "14": 0.78,
    "20": 0.85
  },
  "confidence_score": 0.87
}
```

#### Get Learning Curve
```http
GET /synthesis/repetition/learning-curve/{subject}?days=30
```

**Response:**
```json
{
  "subject": "Machine Learning",
  "data_points": [
    {"date": "2024-12-23", "performance": 0.65, "review_count": 2}
  ],
  "trend": "improving",
  "initial_mastery": 0.45,
  "current_mastery": 0.85,
  "projected_mastery": 0.92,
  "learning_rate": 0.015
}
```

#### Update Settings
```http
PUT /synthesis/repetition/settings
```

**Request Body:**
```json
{
  "algorithm": "sm2",
  "daily_review_limit": 20,
  "new_memories_per_day": 10,
  "initial_ease": 2.5,
  "easy_bonus": 1.3,
  "hard_penalty": 0.8,
  "enable_fuzz": true
}
```

---

## Real-time WebSocket Updates

The WebSocket system provides real-time notifications and updates for all synthesis features.

### Connection URL
```
ws://localhost:8000/ws/connect?token=<your_token>
```

### Event Types

#### Memory Events
- `memory.created`: New memory created
- `memory.updated`: Memory updated
- `memory.deleted`: Memory deleted

#### Connection Events
- `connection.created`: New connection established
- `connection.deleted`: Connection removed

#### Metrics Events
- `metrics.updated`: Metrics updated
- `metrics.anomaly`: Anomaly detected

#### Review Events
- `review.due`: Review is due
- `review.completed`: Review completed

#### Synthesis Events
- `consolidation.suggested`: Memory consolidation suggested
- `summary.generated`: Summary generated
- `insight.discovered`: New insight discovered
- `milestone.achieved`: Learning milestone achieved

#### System Events
- `system.notification`: System notification

### Message Format

#### Subscribe to Events
```json
{
  "type": "subscribe",
  "action": "subscribe",
  "subscription_types": ["memories", "reviews", "metrics"]
}
```

#### Unsubscribe from Events
```json
{
  "type": "unsubscribe",
  "action": "unsubscribe",
  "subscription_types": ["metrics"]
}
```

#### Heartbeat (Ping/Pong)
```json
// Client sends:
{
  "type": "ping",
  "sequence": 123
}

// Server responds:
{
  "type": "pong",
  "sequence": 123
}
```

### Event Message Structure

```json
{
  "type": "memory.created",
  "timestamp": "2025-01-22T10:00:00Z",
  "data": {
    "memory_id": "memory123",
    "memory_data": {
      "title": "New Memory",
      "content": "Content here",
      "created_at": "2025-01-22T10:00:00Z"
    }
  }
}
```

### JavaScript Example

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/connect?token=your_token');

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
            console.log('New memory:', message.data);
            break;
        case 'review.due':
            console.log('Review due:', message.data);
            break;
        case 'system.notification':
            showNotification(message.data.title, message.data.message);
            break;
    }
};

// Send heartbeat every 30 seconds
setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'ping',
            sequence: Date.now()
        }));
    }
}, 30000);
```

### Python Example

```python
import asyncio
import json
import websockets

async def connect():
    uri = "ws://localhost:8000/ws/connect?token=your_token"
    
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
            
            if data['type'] == 'memory.created':
                print(f"New memory: {data['data']['memory_data']['title']}")

asyncio.run(connect())
```

### React Hook Example

```jsx
import { useEffect, useState, useCallback } from 'react';

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
```

### Status Endpoint

```http
GET /ws/status
```

**Response:**
```json
{
  "status": "active",
  "statistics": {
    "total_connections": 15,
    "connections_by_user": {
      "user123": 3,
      "user456": 2
    },
    "subscriptions": {
      "memories": 10,
      "reviews": 8,
      "metrics": 5
    },
    "messages_sent": 1234,
    "uptime_seconds": 3600
  },
  "server_time": "2025-01-22T10:00:00Z"
}
```

## Error Codes

### HTTP Status Codes
- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `404`: Not Found
- `429`: Rate Limited
- `500`: Internal Server Error

### WebSocket Close Codes
- `1000`: Normal closure
- `4000`: Internal error
- `4001`: Authentication required
- `4002`: Invalid message format
- `4003`: Subscription error

## Rate Limits

- Report Generation: 10 per hour
- Review Operations: 100 per hour
- WebSocket Connections: 5 per user
- WebSocket Messages: 100 per minute per connection

## Integration Examples

### Complete Review Flow

1. Get due reviews
2. Create review session
3. For each review:
   - Present memory to user
   - Record completion with difficulty
   - Receive next review schedule via WebSocket
4. Update statistics

### Report Generation Workflow

1. Choose report type and format
2. Specify time period and sections
3. Generate report
4. Receive completion notification via WebSocket
5. Download or share report

### Real-time Dashboard

1. Connect to WebSocket
2. Subscribe to all event types
3. Update UI based on events:
   - New memories appear instantly
   - Review notifications show up
   - Metrics update in real-time
   - System notifications display