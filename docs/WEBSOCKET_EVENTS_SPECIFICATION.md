# WebSocket Events Specification - Second Brain V2 API

## Overview

The Second Brain V2 API provides real-time WebSocket communication for live updates across all connected clients. This document describes all WebSocket message formats, event types, and client implementation patterns.

**WebSocket URL**: `ws://localhost:8000/api/v2/ws`

## Connection Management

### Establishing Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v2/ws');

ws.onopen = (event) => {
    console.log('Connected to Second Brain WebSocket');
};

ws.onclose = (event) => {
    console.log('WebSocket closed:', event.code, event.reason);
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};
```

### Connection States

| State | Description | Client Action |
|-------|-------------|---------------|
| `CONNECTING` | Initial connection attempt | Wait for open/error |
| `OPEN` | Connected and ready | Send/receive messages |
| `CLOSING` | Connection closing | Wait for close event |
| `CLOSED` | Connection closed | Implement reconnection |

### Reconnection Strategy

```javascript
class SecondBrainWebSocket {
    constructor(url) {
        this.url = url;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000; // Start with 1 second
        this.maxReconnectDelay = 30000; // Max 30 seconds
        this.connect();
    }

    connect() {
        this.ws = new WebSocket(this.url);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
        };

        this.ws.onclose = (event) => {
            if (event.code !== 1000) { // Not normal closure
                this.scheduleReconnect();
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.ws.onmessage = (event) => {
            this.handleMessage(JSON.parse(event.data));
        };
    }

    scheduleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(
                this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
                this.maxReconnectDelay
            );
            
            console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
            setTimeout(() => this.connect(), delay);
        } else {
            console.error('Max reconnection attempts reached');
        }
    }

    handleMessage(message) {
        // Handle different message types
        switch (message.type) {
            case 'connection':
                this.onConnection(message);
                break;
            case 'heartbeat':
                this.onHeartbeat(message);
                break;
            case 'metrics_update':
                this.onMetricsUpdate(message);
                break;
            case 'memory_created':
                this.onMemoryCreated(message);
                break;
            default:
                console.warn('Unknown message type:', message.type);
        }
    }
}
```

## Message Format

All WebSocket messages follow this base structure:

```typescript
interface WebSocketMessage {
    type: string;           // Message type identifier
    data?: any;            // Message payload (optional)
    status?: string;       // Status for connection messages
    timestamp: string;     // ISO 8601 timestamp
}
```

## Event Types

### 1. Connection Events

#### Connection Established
Sent immediately when client connects successfully.

```json
{
    "type": "connection",
    "status": "connected",
    "timestamp": "2025-08-01T10:30:00Z"
}
```

**Client Handling**:
```javascript
ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    if (message.type === 'connection') {
        console.log('WebSocket connection confirmed');
        // Initialize UI, start timers, etc.
        initializeRealTimeFeatures();
    }
};
```

#### Heartbeat
Sent every 30 seconds to maintain connection and detect disconnects.

```json
{
    "type": "heartbeat",
    "timestamp": "2025-08-01T10:30:30Z"
}
```

**Client Handling**:
```javascript
let lastHeartbeat = Date.now();

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    if (message.type === 'heartbeat') {
        lastHeartbeat = Date.now();
        updateConnectionStatus('healthy');
    }
};

// Monitor heartbeat health
setInterval(() => {
    const timeSinceHeartbeat = Date.now() - lastHeartbeat;
    if (timeSinceHeartbeat > 60000) { // 1 minute without heartbeat
        updateConnectionStatus('stale');
        console.warn('WebSocket connection may be stale');
    }
}, 30000);
```

### 2. System Metrics Events

#### Metrics Update
Sent every minute with updated system metrics.

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

**Client Handling**:
```javascript
function handleMetricsUpdate(message) {
    const metrics = message.data;
    
    // Update dashboard elements
    document.getElementById('memory-count').textContent = metrics.memories;
    document.getElementById('active-users').textContent = metrics.active_users;
    document.getElementById('system-health').textContent = metrics.system_health;
    document.getElementById('system-health').className = `status ${metrics.system_health}`;
    
    // Update charts/graphs
    updateMemoryChart(metrics.memories);
    updateHealthIndicator(metrics.system_health);
    
    // Store for historical tracking
    storeMetricsHistory(metrics, message.timestamp);
}
```

#### System Health Change
Sent immediately when system health status changes.

```json
{
    "type": "health_change",
    "data": {
        "old_status": "healthy",
        "new_status": "degraded",
        "affected_components": ["cpu", "memory"],
        "details": {
            "cpu_percent": 85.4,
            "memory_percent": 92.1
        }
    },
    "timestamp": "2025-08-01T10:32:15Z"
}
```

**Client Handling**:
```javascript
function handleHealthChange(message) {
    const { old_status, new_status, affected_components, details } = message.data;
    
    // Show alert for degraded health
    if (new_status === 'degraded' || new_status === 'unhealthy') {
        showHealthAlert({
            type: 'warning',
            title: 'System Health Alert',
            message: `System status changed from ${old_status} to ${new_status}`,
            components: affected_components,
            details: details
        });
    }
    
    // Update health status display
    updateSystemHealthDisplay(new_status, affected_components);
}
```

### 3. Memory Events

#### Memory Created
Sent when a new memory is ingested via API.

```json
{
    "type": "memory_created",
    "data": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "memory_type": "semantic",
        "tags": ["ai", "research", "embeddings"],
        "created_at": "2025-08-01T10:30:15Z",
        "importance_score": 0.75,
        "content_preview": "Important insights from today's research..."
    },
    "timestamp": "2025-08-01T10:30:15Z"
}
```

**Client Handling**:
```javascript
function handleMemoryCreated(message) {
    const memory = message.data;
    
    // Show notification
    showNotification({
        type: 'success',
        title: 'New Memory Created',
        message: `${memory.memory_type} memory with ${memory.tags.length} tags`,
        duration: 5000
    });
    
    // Update memory list if visible
    if (isMemoryListVisible()) {
        prependMemoryToList(memory);
    }
    
    // Update memory count in UI
    incrementMemoryCounter();
    
    // Trigger memory list refresh
    refreshMemoryList();
}
```

#### Memory Updated
Sent when an existing memory is modified.

```json
{
    "type": "memory_updated", 
    "data": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "changes": {
            "tags": {
                "old": ["ai", "research"],
                "new": ["ai", "research", "embeddings", "learning"]
            },
            "importance_score": {
                "old": 0.75,
                "new": 0.85
            }
        },
        "updated_at": "2025-08-01T10:35:20Z"
    },
    "timestamp": "2025-08-01T10:35:20Z"
}
```

#### Memory Deleted
Sent when a memory is deleted.

```json
{
    "type": "memory_deleted",
    "data": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "memory_type": "semantic",
        "deleted_at": "2025-08-01T10:40:00Z"
    },
    "timestamp": "2025-08-01T10:40:00Z"
}
```

### 4. Analysis Events

#### Analysis Started
Sent when background analysis begins.

```json
{
    "type": "analysis_started",
    "data": {
        "analysis_id": "analysis_123",
        "type": "memory_clustering",
        "estimated_duration": 120,
        "memory_count": 150
    },
    "timestamp": "2025-08-01T10:45:00Z"
}
```

#### Analysis Progress
Sent periodically during long-running analysis.

```json
{
    "type": "analysis_progress",
    "data": {
        "analysis_id": "analysis_123",
        "progress_percent": 45,
        "current_stage": "embedding_generation",
        "processed_items": 68,
        "total_items": 150,
        "eta_seconds": 75
    },
    "timestamp": "2025-08-01T10:46:30Z"
}
```

#### Analysis Completed
Sent when analysis finishes.

```json
{
    "type": "analysis_completed",
    "data": {
        "analysis_id": "analysis_123",
        "type": "memory_clustering",
        "duration_seconds": 115,
        "results": {
            "clusters_found": 8,
            "outliers": 3,
            "avg_cluster_size": 18
        },
        "completed_at": "2025-08-01T10:46:55Z"
    },
    "timestamp": "2025-08-01T10:46:55Z"
}
```

### 5. User Activity Events

#### User Joined
Sent when a new user becomes active.

```json
{
    "type": "user_joined",
    "data": {
        "user_id": "user_456",
        "username": "researcher_jane",
        "joined_at": "2025-08-01T10:50:00Z"
    },
    "timestamp": "2025-08-01T10:50:00Z"
}
```

#### User Left
Sent when a user goes inactive.

```json
{
    "type": "user_left",
    "data": {
        "user_id": "user_456",
        "username": "researcher_jane",
        "left_at": "2025-08-01T11:20:00Z",
        "session_duration": 1800
    },
    "timestamp": "2025-08-01T11:20:00Z"
}
```

### 6. System Events

#### System Maintenance
Sent before scheduled maintenance.

```json
{
    "type": "system_maintenance",
    "data": {
        "scheduled_at": "2025-08-01T12:00:00Z",
        "estimated_duration": 300,
        "maintenance_type": "database_optimization",
        "warning_seconds": 600
    },
    "timestamp": "2025-08-01T11:50:00Z"
}
```

#### Error Event
Sent when system errors occur that affect users.

```json
{
    "type": "system_error",
    "data": {
        "error_id": "err_789",
        "severity": "warning",
        "component": "embedding_service",
        "message": "Embedding service temporarily unavailable",
        "estimated_resolution": "2025-08-01T11:05:00Z"
    },
    "timestamp": "2025-08-01T11:00:00Z"
}
```

## Client Implementation Examples

### Complete React Component

```jsx
import React, { useState, useEffect, useCallback } from 'react';

const WebSocketManager = () => {
    const [ws, setWs] = useState(null);
    const [connected, setConnected] = useState(false);
    const [metrics, setMetrics] = useState(null);
    const [notifications, setNotifications] = useState([]);
    const [connectionHealth, setConnectionHealth] = useState('unknown');

    // Initialize WebSocket connection
    useEffect(() => {
        const websocket = new WebSocket('ws://localhost:8000/api/v2/ws');
        
        websocket.onopen = () => {
            console.log('WebSocket connected');
            setConnected(true);
            setWs(websocket);
            setConnectionHealth('healthy');
        };

        websocket.onclose = (event) => {
            console.log('WebSocket closed:', event.code, event.reason);
            setConnected(false);
            setWs(null);
            setConnectionHealth('disconnected');
            
            // Attempt reconnection
            if (event.code !== 1000) {
                setTimeout(() => {
                    console.log('Attempting to reconnect...');
                    // Re-run this effect
                }, 5000);
            }
        };

        websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
            setConnectionHealth('error');
        };

        websocket.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                handleWebSocketMessage(message);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };

        return () => {
            websocket.close(1000, 'Component unmounting');
        };
    }, []);

    const handleWebSocketMessage = useCallback((message) => {
        console.log('WebSocket message:', message.type, message);
        
        switch (message.type) {
            case 'connection':
                addNotification('info', 'Connected', 'WebSocket connection established');
                break;
                
            case 'heartbeat':
                setConnectionHealth('healthy');
                break;
                
            case 'metrics_update':
                setMetrics(message.data);
                break;
                
            case 'memory_created':
                addNotification(
                    'success', 
                    'Memory Created', 
                    `New ${message.data.memory_type} memory added`
                );
                // Trigger memory list refresh
                break;
                
            case 'memory_updated':
                addNotification(
                    'info',
                    'Memory Updated',
                    `Memory ${message.data.id} was modified`
                );
                break;
                
            case 'memory_deleted':
                addNotification(
                    'warning',
                    'Memory Deleted', 
                    `Memory ${message.data.id} was deleted`
                );
                break;
                
            case 'analysis_started':
                addNotification(
                    'info',
                    'Analysis Started',
                    `${message.data.type} analysis begun`
                );
                break;
                
            case 'analysis_completed':
                addNotification(
                    'success',
                    'Analysis Complete',
                    `${message.data.type} finished in ${message.data.duration_seconds}s`
                );
                break;
                
            case 'system_error':
                addNotification(
                    'error',
                    'System Error',
                    message.data.message
                );
                break;
                
            case 'health_change':
                const { new_status, affected_components } = message.data;
                if (new_status === 'degraded' || new_status === 'unhealthy') {
                    addNotification(
                        'warning',
                        'Health Alert',
                        `System ${new_status}: ${affected_components.join(', ')}`
                    );
                }
                break;
                
            default:
                console.warn('Unknown WebSocket message type:', message.type);
        }
    }, []);

    const addNotification = useCallback((type, title, message) => {
        const notification = {
            id: Date.now() + Math.random(),
            type,
            title,
            message,
            timestamp: new Date().toISOString()
        };
        
        setNotifications(prev => [notification, ...prev.slice(0, 9)]); // Keep last 10
        
        // Auto-remove after delay
        setTimeout(() => {
            setNotifications(prev => prev.filter(n => n.id !== notification.id));
        }, type === 'error' ? 10000 : 5000);
    }, []);

    const clearNotification = useCallback((id) => {
        setNotifications(prev => prev.filter(n => n.id !== id));
    }, []);

    // Monitor connection health
    useEffect(() => {
        const healthCheck = setInterval(() => {
            if (connected && connectionHealth === 'healthy') {
                // Check if we've received a heartbeat recently
                // This would require tracking last heartbeat timestamp
                setConnectionHealth('healthy');
            }
        }, 30000);

        return () => clearInterval(healthCheck);
    }, [connected, connectionHealth]);

    return (
        <div className="websocket-manager">
            {/* Connection Status */}
            <div className={`connection-status ${connectionHealth}`}>
                <span className="indicator"></span>
                {connected ? 'Connected' : 'Disconnected'}
                {connectionHealth === 'error' && ' (Error)'}
            </div>

            {/* Real-time Metrics */}
            {metrics && (
                <div className="real-time-metrics">
                    <div className="metric">
                        <label>Memories:</label>
                        <span>{metrics.memories}</span>
                    </div>
                    <div className="metric">
                        <label>Active Users:</label>
                        <span>{metrics.active_users}</span>
                    </div>
                    <div className="metric">
                        <label>System Health:</label>
                        <span className={`health ${metrics.system_health}`}>
                            {metrics.system_health}
                        </span>
                    </div>
                </div>
            )}

            {/* Notifications */}
            <div className="notifications">
                {notifications.map(notification => (
                    <div 
                        key={notification.id} 
                        className={`notification ${notification.type}`}
                    >
                        <div className="notification-header">
                            <strong>{notification.title}</strong>
                            <button 
                                onClick={() => clearNotification(notification.id)}
                                className="close-btn"
                            >
                                ×
                            </button>
                        </div>
                        <div className="notification-message">
                            {notification.message}
                        </div>
                        <div className="notification-time">
                            {new Date(notification.timestamp).toLocaleTimeString()}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default WebSocketManager;
```

### Vue.js Composition API Example

```vue
<template>
  <div class="websocket-status">
    <div :class="`status-indicator ${connectionStatus}`">
      {{ connectionStatus }}
    </div>
    
    <div v-if="metrics" class="metrics">
      <div>Memories: {{ metrics.memories }}</div>
      <div>Users: {{ metrics.active_users }}</div>
      <div>Health: {{ metrics.system_health }}</div>
    </div>

    <div class="notifications">
      <div 
        v-for="notification in notifications" 
        :key="notification.id"
        :class="`notification ${notification.type}`"
      >
        <h4>{{ notification.title }}</h4>
        <p>{{ notification.message }}</p>
        <button @click="removeNotification(notification.id)">×</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';

const ws = ref(null);
const connectionStatus = ref('disconnected');
const metrics = ref(null);
const notifications = ref([]);

const connect = () => {
  ws.value = new WebSocket('ws://localhost:8000/api/v2/ws');
  
  ws.value.onopen = () => {
    connectionStatus.value = 'connected';
    console.log('WebSocket connected');
  };
  
  ws.value.onclose = (event) => {
    connectionStatus.value = 'disconnected';
    console.log('WebSocket closed:', event.code);
    
    // Reconnect after delay
    if (event.code !== 1000) {
      setTimeout(connect, 5000);
    }
  };
  
  ws.value.onerror = () => {
    connectionStatus.value = 'error';
  };
  
  ws.value.onmessage = (event) => {
    const message = JSON.parse(event.data);
    handleMessage(message);
  };
};

const handleMessage = (message) => {
  switch (message.type) {
    case 'connection':
      addNotification('info', 'Connected', 'WebSocket connected');
      break;
      
    case 'metrics_update':
      metrics.value = message.data;
      break;
      
    case 'memory_created':
      addNotification('success', 'Memory Created', 
        `New ${message.data.memory_type} memory`);
      break;
      
    case 'health_change':
      if (message.data.new_status !== 'healthy') {
        addNotification('warning', 'Health Alert', 
          `System ${message.data.new_status}`);
      }
      break;
  }
};

const addNotification = (type, title, message) => {
  const notification = {
    id: Date.now(),
    type,
    title,
    message,
    timestamp: new Date().toISOString()
  };
  
  notifications.value.unshift(notification);
  
  // Auto-remove
  setTimeout(() => {
    removeNotification(notification.id);
  }, 5000);
};

const removeNotification = (id) => {
  const index = notifications.value.findIndex(n => n.id === id);
  if (index > -1) {
    notifications.value.splice(index, 1);
  }
};

onMounted(() => {
  connect();
});

onUnmounted(() => {
  if (ws.value) {
    ws.value.close(1000);
  }
});
</script>

<style scoped>
.status-indicator {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
}

.status-indicator.connected {
  background: #4caf50;
  color: white;
}

.status-indicator.disconnected {
  background: #f44336;
  color: white;
}

.status-indicator.error {
  background: #ff9800;
  color: white;
}

.notification {
  margin: 8px 0;
  padding: 12px;
  border-radius: 4px;
  position: relative;
}

.notification.info { background: #e3f2fd; }
.notification.success { background: #e8f5e8; }
.notification.warning { background: #fff3e0; }
.notification.error { background: #ffebee; }
</style>
```

## Error Handling

### Connection Errors

```javascript
class WebSocketErrorHandler {
    constructor(onReconnect) {
        this.onReconnect = onReconnect;
        this.errorCounts = new Map();
    }

    handleError(error, errorType) {
        const count = this.errorCounts.get(errorType) || 0;
        this.errorCounts.set(errorType, count + 1);

        switch (errorType) {
            case 'connection_failed':
                if (count < 5) {
                    console.log(`Connection failed, retrying... (${count + 1}/5)`);
                    setTimeout(this.onReconnect, 2000 * Math.pow(2, count));
                } else {
                    console.error('Max connection attempts reached');
                    this.showPersistentError('Unable to connect to server');
                }
                break;

            case 'message_parse_error':
                console.error('Failed to parse WebSocket message:', error);
                // Don't reconnect for parse errors
                break;

            case 'unexpected_close':
                console.log('WebSocket closed unexpectedly, reconnecting...');
                setTimeout(this.onReconnect, 1000);
                break;
        }
    }

    reset() {
        this.errorCounts.clear();
    }

    showPersistentError(message) {
        // Show user-facing error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'websocket-error persistent';
        errorDiv.innerHTML = `
            <strong>Connection Error</strong>
            <p>${message}</p>
            <button onclick="location.reload()">Reload Page</button>
        `;
        document.body.appendChild(errorDiv);
    }
}
```

### Message Validation

```javascript
function validateWebSocketMessage(message) {
    // Basic structure validation
    if (!message || typeof message !== 'object') {
        throw new Error('Message must be an object');
    }

    if (!message.type || typeof message.type !== 'string') {
        throw new Error('Message must have a string type field');
    }

    if (!message.timestamp) {
        throw new Error('Message must have a timestamp field');
    }

    // Validate timestamp format
    const timestamp = new Date(message.timestamp);
    if (isNaN(timestamp.getTime())) {
        throw new Error('Invalid timestamp format');
    }

    // Type-specific validation
    switch (message.type) {
        case 'metrics_update':
            if (!message.data || typeof message.data !== 'object') {
                throw new Error('metrics_update requires data object');
            }
            break;

        case 'memory_created':
            if (!message.data?.id) {
                throw new Error('memory_created requires data.id');
            }
            break;

        case 'connection':
            if (!message.status) {
                throw new Error('connection message requires status');
            }
            break;
    }

    return true;
}

// Usage
ws.onmessage = (event) => {
    try {
        const message = JSON.parse(event.data);
        validateWebSocketMessage(message);
        handleMessage(message);
    } catch (error) {
        console.error('Invalid WebSocket message:', error.message);
        // Don't break the connection for invalid messages
    }
};
```

## Performance Considerations

### Message Throttling

```javascript
class MessageThrottler {
    constructor(maxMessagesPerSecond = 10) {
        this.maxMessages = maxMessagesPerSecond;
        this.messageCount = 0;
        this.windowStart = Date.now();
        this.queue = [];
    }

    shouldProcess(message) {
        const now = Date.now();
        
        // Reset window if 1 second has passed
        if (now - this.windowStart >= 1000) {
            this.messageCount = 0;
            this.windowStart = now;
        }

        // Always process critical messages immediately
        if (this.isCriticalMessage(message)) {
            return true;
        }

        // Throttle non-critical messages
        if (this.messageCount < this.maxMessages) {
            this.messageCount++;
            return true;
        }

        // Queue for later processing
        this.queue.push(message);
        return false;
    }

    isCriticalMessage(message) {
        return [
            'connection',
            'system_error', 
            'health_change',
            'system_maintenance'
        ].includes(message.type);
    }

    processQueued() {
        if (this.queue.length > 0 && this.messageCount < this.maxMessages) {
            const message = this.queue.shift();
            this.messageCount++;
            return message;
        }
        return null;
    }
}

// Usage
const throttler = new MessageThrottler(5); // 5 messages per second

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    if (throttler.shouldProcess(message)) {
        handleMessage(message);
    }
};

// Process queued messages periodically
setInterval(() => {
    const message = throttler.processQueued();
    if (message) {
        handleMessage(message);
    }
}, 200); // Check every 200ms
```

### Memory Management

```javascript
class WebSocketMemoryManager {
    constructor(maxHistorySize = 1000) {
        this.maxHistorySize = maxHistorySize;
        this.messageHistory = [];
        this.metricsHistory = [];
        this.notifications = [];
    }

    addMessage(message) {
        this.messageHistory.push({
            ...message,
            received_at: Date.now()
        });

        // Trim history if too large
        if (this.messageHistory.length > this.maxHistorySize) {
            this.messageHistory = this.messageHistory.slice(-this.maxHistorySize);
        }

        // Handle specific message types
        if (message.type === 'metrics_update') {
            this.addMetrics(message.data, message.timestamp);
        }
    }

    addMetrics(metrics, timestamp) {
        this.metricsHistory.push({
            ...metrics,
            timestamp: timestamp
        });

        // Keep only last hour of metrics (assuming 1 per minute)
        if (this.metricsHistory.length > 60) {
            this.metricsHistory = this.metricsHistory.slice(-60);
        }
    }

    addNotification(notification) {
        this.notifications.unshift(notification);

        // Keep only last 50 notifications
        if (this.notifications.length > 50) {
            this.notifications = this.notifications.slice(0, 50);
        }
    }

    cleanup() {
        // Remove old messages (older than 1 hour)
        const oneHourAgo = Date.now() - (60 * 60 * 1000);
        this.messageHistory = this.messageHistory.filter(
            msg => msg.received_at > oneHourAgo
        );

        // Remove old notifications (older than 10 minutes)
        const tenMinutesAgo = Date.now() - (10 * 60 * 1000);
        this.notifications = this.notifications.filter(
            notif => new Date(notif.timestamp).getTime() > tenMinutesAgo
        );
    }

    getMemoryUsage() {
        return {
            messageHistory: this.messageHistory.length,
            metricsHistory: this.metricsHistory.length,
            notifications: this.notifications.length,
            estimatedSizeKB: Math.round(
                (JSON.stringify(this.messageHistory).length +
                 JSON.stringify(this.metricsHistory).length +
                 JSON.stringify(this.notifications).length) / 1024
            )
        };
    }
}

// Usage
const memoryManager = new WebSocketMemoryManager();

// Cleanup every 5 minutes
setInterval(() => {
    memoryManager.cleanup();
    console.log('WebSocket memory usage:', memoryManager.getMemoryUsage());
}, 5 * 60 * 1000);
```

## Security Considerations

### Message Validation
- Always validate message structure and types
- Sanitize any user-displayable content
- Implement rate limiting for message processing
- Never execute code from WebSocket messages

### Connection Security
- Use WSS (WebSocket Secure) in production
- Implement proper authentication/authorization
- Monitor for suspicious connection patterns
- Implement connection limits per client

### Data Handling
- Don't store sensitive data in WebSocket messages
- Implement proper error handling to prevent information leakage
- Log security-relevant events
- Use content security policies

This specification provides comprehensive coverage of all WebSocket events and implementation patterns for the Second Brain V2 API. For additional security and performance considerations, refer to the main API documentation.