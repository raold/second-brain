# Second Brain Unified V2 API Specification

## Overview

The Second Brain Unified V2 API provides a comprehensive REST API with real-time WebSocket support, combining the robustness of V1's PostgreSQL backend with modern real-time features. This API serves as the single source of truth for all frontend interfaces.

**Base URL**: `http://localhost:8000/api/v2`  
**WebSocket URL**: `ws://localhost:8000/api/v2/ws`  
**OpenAPI Docs**: `http://localhost:8000/docs`

## Architecture

- **Backend**: FastAPI with PostgreSQL + pgvector
- **Real-time**: WebSocket connections for live updates
- **Authentication**: API key-based authentication
- **Data**: Real PostgreSQL data (no mocks)
- **Cache**: Redis for performance optimization

## Authentication

All endpoints require API key authentication.

### Headers
```http
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

### Authentication Methods

1. **HTTP Header** (Recommended)
```http
Authorization: Bearer sk-1234567890abcdef
```

2. **Query Parameter** (For development only)
```http
GET /api/v2/metrics?api_key=sk-1234567890abcdef
```

## Core Endpoints

### System Metrics

#### Get Simple Metrics
**Endpoint**: `GET /api/v2/metrics`  
**Purpose**: Get simplified metrics for user-facing interfaces

**Response**:
```json
{
  "tests": 436,
  "patterns": 27,
  "version": "3.0.0",
  "agents": 27,
  "token_usage": "6x",
  "memories": 150,
  "active_users": 3,
  "system_health": "healthy"
}
```

#### Get Detailed Metrics  
**Endpoint**: `GET /api/v2/metrics/detailed`  
**Purpose**: Comprehensive metrics for development dashboards

**Response**:
```json
{
  "memories": {
    "total": 150,
    "unique_users": 5,
    "avg_importance": 0.65,
    "last_created": "2025-08-01T10:30:00Z",
    "with_embeddings": 142,
    "avg_length": 485,
    "last_24h": 12,
    "last_7d": 89,
    "last_30d": 150,
    "type_distribution": {
      "semantic": 85,
      "episodic": 45,
      "procedural": 20
    },
    "unique_tags": 47,
    "top_tags": ["ai", "learning", "productivity", "work", "research"]
  },
  "performance": {
    "api_response_time": "45ms",
    "rps_capacity": "1000+",
    "memory_usage": "42%",
    "cpu_usage": "15%",
    "disk_usage": "35%",
    "active_connections": 5,
    "cache_hit_rate": "87%",
    "system_memory_mb": 2048,
    "system_memory_available_mb": 6144,
    "uptime_seconds": 86400
  },
  "system": {
    "platform": "posix",
    "cpu_count": 8,
    "boot_time": "2025-07-31T08:00:00Z",
    "python_version": "3.11.5"
  },
  "database": {
    "size_mb": 245,
    "active_connections": 5,
    "index_count": 12,
    "type": "PostgreSQL"
  },
  "timestamp": "2025-08-01T10:30:00Z"
}
```

### Git Activity

#### Get Git Activity
**Endpoint**: `GET /api/v2/git/activity`  
**Purpose**: Retrieve git commit history and repository statistics

**Response**:
```json
{
  "commits": [
    {
      "hash": "10cd929",
      "message": "feat: Implement Second Brain v2.0 interface with Apple-inspired design",
      "timestamp": "2025-07-31T15:30:00Z",
      "author": "Developer",
      "relative_time": "2 hours ago"
    }
  ],
  "timeline": [
    {"label": "2h", "timestamp": "2025-08-01T08:30:00Z"},
    {"label": "1d", "timestamp": "2025-07-31T10:30:00Z"},
    {"label": "3d", "timestamp": "2025-07-29T10:30:00Z"},
    {"label": "1w", "timestamp": "2025-07-25T10:30:00Z"},
    {"label": "1m", "timestamp": "2025-07-01T10:30:00Z"}
  ],
  "stats": {
    "total_commits": 10,
    "authors": 1,
    "branch": "main"
  }
}
```

### Project Management

#### Get TODOs
**Endpoint**: `GET /api/v2/todos`  
**Purpose**: Parse and return TODO items from TODO.md with categorization

**Response**:
```json
{
  "todos": [
    {
      "id": "todo-0",
      "content": "Implement load testing suite",
      "status": "pending",
      "priority": "high",
      "description": "Add performance benchmarks to CI",
      "category": "testing"
    },
    {
      "id": "todo-1", 
      "content": "Fix authentication middleware",
      "status": "completed",
      "priority": "high",
      "description": null,
      "category": "bugfix"
    }
  ],
  "stats": {
    "total": 45,
    "completed": 23,
    "in_progress": 3,
    "pending": 19,
    "high_priority": 12,
    "completion_rate": 51
  },
  "last_updated": "2025-08-01T10:30:00Z"
}
```

### System Health

#### Get Health Status
**Endpoint**: `GET /api/v2/health`  
**Purpose**: Comprehensive system health monitoring

**Response**:
```json
{
  "status": "healthy",
  "checks": {
    "api": "healthy",
    "database": "healthy", 
    "redis": "healthy",
    "disk": "healthy",
    "memory": "healthy",
    "cpu": "healthy"
  },
  "metrics": {
    "cpu_percent": 15.2,
    "memory_percent": 42.1,
    "disk_percent": 35.8
  },
  "timestamp": "2025-08-01T10:30:00Z"
}
```

**Health Status Values**:
- `healthy`: Operating normally
- `degraded`: Operating with reduced performance
- `unhealthy`: Critical issues detected

### Memory Operations

#### Ingest Memory
**Endpoint**: `POST /api/v2/memories/ingest`  
**Purpose**: Create new memory and broadcast real-time update

**Request**:
```json
{
  "content": "Important insights from today's research session on AI embeddings",
  "memory_type": "semantic",
  "tags": ["ai", "research", "embeddings"]
}
```

**Response**:
```json
{
  "success": true,
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Memory ingested successfully"
}
```

**Side Effect**: Broadcasts WebSocket event to all connected clients:
```json
{
  "type": "memory_created",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "memory_type": "semantic",
    "tags": ["ai", "research", "embeddings"],
    "created_at": "2025-08-01T10:30:15Z"
  },
  "timestamp": "2025-08-01T10:30:15Z"
}
```

## WebSocket Real-Time API

### Connection

Connect to WebSocket endpoint for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v2/ws');
```

### Message Types

#### Connection Events

**Connection Established**:
```json
{
  "type": "connection",
  "status": "connected",
  "timestamp": "2025-08-01T10:30:00Z"
}
```

**Heartbeat** (every 30 seconds):
```json
{
  "type": "heartbeat", 
  "timestamp": "2025-08-01T10:30:30Z"
}
```

#### Data Updates

**Metrics Update** (every minute):
```json
{
  "type": "metrics_update",
  "data": {
    "tests": 436,
    "patterns": 27,
    "version": "3.0.0",
    "agents": 27,
    "token_usage": "6x",
    "memories": 151,
    "active_users": 3,
    "system_health": "healthy"
  },
  "timestamp": "2025-08-01T10:31:00Z"
}
```

**Memory Created**:
```json
{
  "type": "memory_created",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "memory_type": "semantic",
    "tags": ["ai", "research"],  
    "created_at": "2025-08-01T10:30:15Z"
  },
  "timestamp": "2025-08-01T10:30:15Z"
}
```

### WebSocket Client Examples

#### JavaScript/Browser
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v2/ws');

ws.onopen = () => {
    console.log('Connected to Second Brain WebSocket');
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    switch(message.type) {
        case 'connection':
            console.log('WebSocket connection confirmed');
            break;
            
        case 'metrics_update':
            updateDashboard(message.data);
            break;
            
        case 'memory_created':
            showNotification('New memory created', message.data);
            refreshMemoryList();
            break;
            
        case 'heartbeat':
            // Connection is alive
            break;
            
        default:
            console.log('Unknown message type:', message.type);
    }
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};

ws.onclose = (event) => {
    console.log('WebSocket closed:', event.code, event.reason);
    // Implement reconnection logic
    setTimeout(() => connectWebSocket(), 5000);
};
```

#### React Hook
```jsx
import { useEffect, useState, useCallback } from 'react';

function useSecondBrainWebSocket() {
    const [ws, setWs] = useState(null);
    const [connected, setConnected] = useState(false);
    const [metrics, setMetrics] = useState(null);
    const [notifications, setNotifications] = useState([]);

    useEffect(() => {
        const websocket = new WebSocket('ws://localhost:8000/api/v2/ws');

        websocket.onopen = () => {
            setConnected(true);
            setWs(websocket);
        };

        websocket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            
            switch(message.type) {
                case 'metrics_update':
                    setMetrics(message.data);
                    break;
                    
                case 'memory_created':
                    setNotifications(prev => [...prev, {
                        id: Date.now(),
                        type: 'success',
                        title: 'Memory Created',
                        message: `New ${message.data.memory_type} memory added`,
                        timestamp: message.timestamp
                    }]);
                    break;
            }
        };

        websocket.onclose = () => {
            setConnected(false);
            setWs(null);
        };

        return () => websocket.close();
    }, []);

    const clearNotification = useCallback((id) => {
        setNotifications(prev => prev.filter(n => n.id !== id));
    }, []);

    return { 
        connected, 
        metrics, 
        notifications, 
        clearNotification 
    };
}

// Usage in component
function Dashboard() {
    const { connected, metrics, notifications, clearNotification } = useSecondBrainWebSocket();

    return (
        <div>
            <div className={`status ${connected ? 'connected' : 'disconnected'}`}>
                {connected ? 'Connected' : 'Disconnected'}
            </div>
            
            {metrics && (
                <div className="metrics">
                    <div>Memories: {metrics.memories}</div>
                    <div>Active Users: {metrics.active_users}</div>
                    <div>System Health: {metrics.system_health}</div>
                </div>
            )}
            
            <div className="notifications">
                {notifications.map(notification => (
                    <div key={notification.id} className={`notification ${notification.type}`}>
                        <h4>{notification.title}</h4>
                        <p>{notification.message}</p>
                        <button onClick={() => clearNotification(notification.id)}>×</button>
                    </div>
                ))}
            </div>
        </div>
    );
}
```

#### Python Client
```python
import asyncio
import json
import websockets
from typing import Callable, Dict, Any

class SecondBrainWebSocket:
    def __init__(self, url: str = "ws://localhost:8000/api/v2/ws"):
        self.url = url
        self.handlers: Dict[str, Callable] = {}
        self.connected = False
        
    def on(self, event_type: str, handler: Callable[[Dict[str, Any]], None]):
        """Register event handler"""
        self.handlers[event_type] = handler
        
    async def connect(self):
        """Connect to WebSocket and handle messages"""
        try:
            async with websockets.connect(self.url) as websocket:
                self.connected = True
                print("Connected to Second Brain WebSocket")
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        event_type = data.get('type')
                        
                        if event_type in self.handlers:
                            await self.handlers[event_type](data)
                        else:
                            print(f"Unhandled event: {event_type}")
                            
                    except json.JSONDecodeError:
                        print(f"Invalid JSON received: {message}")
                        
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            self.connected = False

# Usage example
async def main():
    ws = SecondBrainWebSocket()
    
    # Register event handlers
    ws.on('connection', lambda data: print("Connected:", data))
    ws.on('metrics_update', lambda data: print("Metrics:", data['data']))
    ws.on('memory_created', lambda data: print("New memory:", data['data']['id']))
    ws.on('heartbeat', lambda data: print("Heartbeat at", data['timestamp']))
    
    # Connect and listen
    await ws.connect()

if __name__ == "__main__":
    asyncio.run(main())
```

## Error Handling

### HTTP Status Codes

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Missing or invalid API key
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

### Error Response Format

```json
{
  "detail": "Error description",
  "status_code": 400,
  "timestamp": "2025-08-01T10:30:00Z",
  "path": "/api/v2/metrics"
}
```

### WebSocket Error Codes

- `4001`: Authentication required
- `4000`: Internal error
- `1000`: Normal closure
- `1001`: Going away
- `1006`: Abnormal closure

## Rate Limiting

- **Default Limit**: 1000 requests per hour per API key
- **Burst Limit**: 60 requests per minute
- **WebSocket**: 1 connection per API key

Rate limit headers:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 847
X-RateLimit-Reset: 1722506400
```

## Performance Characteristics

### Response Times
- **Simple Metrics**: < 50ms
- **Detailed Metrics**: < 200ms  
- **Memory Ingestion**: < 100ms
- **Health Check**: < 25ms

### Throughput
- **Peak RPS**: 1000+
- **Sustained RPS**: 500+
- **WebSocket Messages**: 10,000+ per second

### Caching
- **Metrics**: 30 second cache
- **Git Activity**: 5 minute cache
- **TODO Parsing**: 1 minute cache
- **Health Status**: 10 second cache

## Data Models

### SimpleMetrics
```typescript
interface SimpleMetrics {
  tests: number;
  patterns: number;
  version: string;
  agents: number;
  token_usage: string;
  memories: number;
  active_users: number;
  system_health: 'healthy' | 'degraded' | 'unhealthy';
}
```

### DetailedMetrics
```typescript
interface DetailedMetrics {
  memories: {
    total: number;
    unique_users: number;
    avg_importance: number;
    last_created: string | null;
    with_embeddings: number;
    avg_length: number;
    last_24h: number;
    last_7d: number;
    last_30d: number;
    type_distribution: Record<string, number>;
    unique_tags: number;
    top_tags: string[];
  };
  performance: {
    api_response_time: string;
    rps_capacity: string;
    memory_usage: string;
    cpu_usage: string;
    disk_usage: string;
    active_connections: number;
    cache_hit_rate: string;
    system_memory_mb: number;
    system_memory_available_mb: number;
    uptime_seconds: number;
  };
  system: {
    platform: string;
    cpu_count: number;
    boot_time: string;
    python_version: string;
  };
  database: {
    size_mb: number;
    active_connections: number;
    index_count: number;
    type: string;
  };
  timestamp: string;
}
```

### WebSocketMessage
```typescript
interface WebSocketMessage {
  type: 'connection' | 'heartbeat' | 'metrics_update' | 'memory_created';
  data?: any;
  status?: string;
  timestamp: string;
}
```

## Integration Examples

### Complete React Dashboard
```jsx
import React, { useState, useEffect } from 'react';

function SecondBrainDashboard() {
    const [metrics, setMetrics] = useState(null);
    const [health, setHealth] = useState(null);
    const [todos, setTodos] = useState(null);
    const [gitActivity, setGitActivity] = useState(null);
    const [wsConnected, setWsConnected] = useState(false);
    
    const API_KEY = 'your-api-key-here';
    const API_BASE = 'http://localhost:8000/api/v2';
    
    // REST API calls
    useEffect(() => {
        const fetchData = async () => {
            try {
                const [metricsRes, healthRes, todosRes, gitRes] = await Promise.all([
                    fetch(`${API_BASE}/metrics/detailed?api_key=${API_KEY}`),
                    fetch(`${API_BASE}/health?api_key=${API_KEY}`),
                    fetch(`${API_BASE}/todos?api_key=${API_KEY}`),
                    fetch(`${API_BASE}/git/activity?api_key=${API_KEY}`)
                ]);
                
                setMetrics(await metricsRes.json());
                setHealth(await healthRes.json());
                setTodos(await todosRes.json());
                setGitActivity(await gitRes.json());
            } catch (error) {
                console.error('Failed to fetch data:', error);
            }
        };
        
        fetchData();
        const interval = setInterval(fetchData, 60000); // Refresh every minute
        return () => clearInterval(interval);
    }, []);
    
    // WebSocket connection
    useEffect(() => {
        const ws = new WebSocket(`ws://localhost:8000/api/v2/ws`);
        
        ws.onopen = () => setWsConnected(true);
        ws.onclose = () => setWsConnected(false);
        
        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            
            if (message.type === 'metrics_update') {
                // Update simple metrics in real-time
                setMetrics(prev => prev ? {
                    ...prev,
                    memories: { ...prev.memories, total: message.data.memories }
                } : null);
            }
        };
        
        return () => ws.close();
    }, []);
    
    if (!metrics || !health || !todos || !gitActivity) {
        return <div>Loading...</div>;
    }
    
    return (
        <div className="dashboard">
            <header>
                <h1>Second Brain Dashboard</h1>
                <div className={`status ${wsConnected ? 'connected' : 'disconnected'}`}>
                    WebSocket: {wsConnected ? 'Connected' : 'Disconnected'}
                </div>
            </header>
            
            <div className="metrics-grid">
                <div className="metric-card">
                    <h3>Memories</h3>
                    <div className="metric-value">{metrics.memories.total}</div>
                    <div className="metric-detail">
                        {metrics.memories.last_24h} added today
                    </div>
                </div>
                
                <div className="metric-card">
                    <h3>System Health</h3>
                    <div className={`health-status ${health.status}`}>
                        {health.status}
                    </div>
                    <div className="metric-detail">
                        CPU: {health.metrics.cpu_percent.toFixed(1)}%
                    </div>
                </div>
                
                <div className="metric-card">
                    <h3>TODO Progress</h3>
                    <div className="metric-value">{todos.stats.completion_rate}%</div>
                    <div className="metric-detail">
                        {todos.stats.completed}/{todos.stats.total} completed
                    </div>
                </div>
                
                <div className="metric-card">
                    <h3>Recent Activity</h3>
                    <div className="metric-value">{gitActivity.commits.length}</div>
                    <div className="metric-detail">
                        Last: {gitActivity.commits[0]?.relative_time}
                    </div>
                </div>
            </div>
            
            <div className="details-section">
                <div className="performance-metrics">
                    <h3>Performance</h3>
                    <ul>
                        <li>Response Time: {metrics.performance.api_response_time}</li>
                        <li>Memory Usage: {metrics.performance.memory_usage}</li>
                        <li>Cache Hit Rate: {metrics.performance.cache_hit_rate}</li>
                        <li>Active Connections: {metrics.performance.active_connections}</li>
                    </ul>
                </div>
                
                <div className="recent-todos">
                    <h3>Pending TODOs</h3>
                    <ul>
                        {todos.todos
                            .filter(todo => todo.status === 'pending')
                            .slice(0, 5)
                            .map(todo => (
                                <li key={todo.id} className={`priority-${todo.priority}`}>
                                    <span className="todo-content">{todo.content}</span>
                                    <span className="todo-category">{todo.category}</span>
                                </li>
                            ))
                        }
                    </ul>
                </div>
            </div>
        </div>
    );
}

export default SecondBrainDashboard;
```

### Memory Ingestion Example
```javascript
async function ingestMemory(content, type = 'semantic', tags = []) {
    try {
        const response = await fetch('http://localhost:8000/api/v2/memories/ingest', {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer your-api-key',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                content,
                memory_type: type,
                tags
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log('Memory ingested:', result.memory_id);
        
        // WebSocket will automatically broadcast the update to all clients
        return result;
        
    } catch (error) {
        console.error('Failed to ingest memory:', error);
        throw error;
    }
}

// Usage
ingestMemory(
    "Learned about FastAPI's dependency injection system today. Very powerful for testing.",
    "episodic",
    ["learning", "fastapi", "python"]
);
```

## Migration from V1 Dashboard

### Quick Migration Checklist

1. **Update Base URL**:
   ```javascript
   // Old
   const API_BASE = '/api/v1/dashboard';
   
   // New  
   const API_BASE = '/api/v2';
   ```

2. **Update Endpoint Paths**:
   ```javascript
   // Old
   fetch(`${API_BASE}/metrics`)
   
   // New
   fetch(`${API_BASE}/metrics/detailed`)
   ```

3. **Add WebSocket Support**:
   ```javascript
   const ws = new WebSocket('ws://localhost:8000/api/v2/ws');
   ws.onmessage = (event) => {
       const data = JSON.parse(event.data);
       if (data.type === 'metrics_update') {
           updateUI(data.data);
       }
   };
   ```

4. **Update Response Parsing**:
   - Metrics now have nested structure
   - Health checks return comprehensive data
   - TODOs include categorization and stats

## Security Considerations

### API Key Management
- Store API keys securely (environment variables)
- Never expose API keys in frontend code
- Rotate keys regularly
- Use different keys for different environments

### WebSocket Security
- WebSocket connections inherit API authentication
- Implement reconnection with exponential backoff
- Handle connection drops gracefully
- Validate all incoming messages

### Rate Limiting
- Implement client-side rate limiting
- Handle 429 responses appropriately
- Use exponential backoff for retries

## Monitoring and Observability

### Health Monitoring
```javascript
// Continuous health monitoring
setInterval(async () => {
    try {
        const health = await fetch('/api/v2/health?api_key=YOUR_KEY');
        const data = await health.json();
        
        if (data.status !== 'healthy') {
            console.warn('System health degraded:', data.checks);
            // Alert user or take corrective action
        }
    } catch (error) {
        console.error('Health check failed:', error);
    }
}, 30000); // Check every 30 seconds
```

### Performance Monitoring
```javascript
// Monitor API response times
const startTime = performance.now();
await fetch('/api/v2/metrics');
const responseTime = performance.now() - startTime;

if (responseTime > 1000) {
    console.warn(`Slow API response: ${responseTime}ms`);
}
```

### WebSocket Monitoring
```javascript
// Monitor WebSocket connection health
let lastHeartbeat = Date.now();

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    if (message.type === 'heartbeat') {
        lastHeartbeat = Date.now();
    }
};

// Check for missed heartbeats
setInterval(() => {
    if (Date.now() - lastHeartbeat > 60000) {
        console.warn('WebSocket heartbeat missed, connection may be stale');
        // Implement reconnection logic
    }
}, 30000);
```

## Future Enhancements

### Planned Features
- GraphQL endpoint for flexible queries
- Server-sent events (SSE) alternative to WebSocket
- Batch operations API
- Advanced filtering and pagination
- Webhook support for external integrations

### API Versioning
- V2 is the current stable version
- V1 endpoints are deprecated but supported
- V3 planning with GraphQL integration
- Semantic versioning for all releases

## Support and Resources

- **OpenAPI Documentation**: `/docs` endpoint
- **API Status Page**: `/api/v2/health`
- **WebSocket Test Page**: Available in development
- **Example Code**: Check `static/` directory for implementations
- **Migration Guide**: See `docs/V2_API_MIGRATION_GUIDE.md`

---

This specification covers the complete Second Brain Unified V2 API. For additional examples and implementation details, refer to the OpenAPI documentation at `/docs` when running the application.