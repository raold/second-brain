# Second Brain V2 API Usage Examples

## Overview

This document provides comprehensive usage examples for common scenarios when integrating with the Second Brain V2 API. Examples cover both REST API calls and WebSocket implementations across multiple programming languages and frameworks.

## Table of Contents

1. [Quick Start Examples](#quick-start-examples)
2. [Dashboard Integration](#dashboard-integration)
3. [Memory Management](#memory-management)
4. [Real-time Updates](#real-time-updates)
5. [Monitoring & Health Checks](#monitoring--health-checks)
6. [Error Handling Patterns](#error-handling-patterns)
7. [Performance Optimization](#performance-optimization)
8. [Production Deployment](#production-deployment)

## Quick Start Examples

### Basic API Client Setup

#### JavaScript/Browser
```javascript
class SecondBrainAPI {
    constructor(apiKey, baseUrl = 'http://localhost:8000/api/v2') {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        };
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: this.headers,
            ...options
        };

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(`API Error ${response.status}: ${error.detail}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    // Convenience methods
    async getMetrics() {
        return this.request('/metrics');
    }

    async getDetailedMetrics() {
        return this.request('/metrics/detailed');
    }

    async getHealth() {
        return this.request('/health');
    }

    async ingestMemory(content, type = 'semantic', tags = []) {
        return this.request('/memories/ingest', {
            method: 'POST',
            body: JSON.stringify({
                content,
                memory_type: type,
                tags
            })
        });
    }

    async getTodos() {
        return this.request('/todos');
    }

    async getGitActivity() {
        return this.request('/git/activity');
    }

    // WebSocket connection
    connectWebSocket(onMessage) {
        const ws = new WebSocket(`ws://localhost:8000/api/v2/ws`);
        
        ws.onopen = () => console.log('WebSocket connected');
        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            onMessage(message);
        };
        ws.onerror = (error) => console.error('WebSocket error:', error);
        ws.onclose = () => console.log('WebSocket closed');

        return ws;
    }
}

// Usage
const api = new SecondBrainAPI('your-api-key-here');

// Get simple metrics
api.getMetrics().then(metrics => {
    console.log('System metrics:', metrics);
});

// Connect to WebSocket
const ws = api.connectWebSocket((message) => {
    console.log('WebSocket message:', message.type, message.data);
});
```

#### Python
```python
import asyncio
import json
import aiohttp
import websockets
from typing import Dict, Any, Optional, Callable

class SecondBrainAPI:
    def __init__(self, api_key: str, base_url: str = "http://localhost:8000/api/v2"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make API request"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.request(method, url, json=data) as response:
                if response.status >= 400:
                    error_data = await response.json()
                    raise Exception(f"API Error {response.status}: {error_data.get('detail', 'Unknown error')}")
                
                return await response.json()
        except Exception as e:
            print(f"API request failed: {e}")
            raise

    async def get_metrics(self) -> Dict[str, Any]:
        """Get simple metrics"""
        return await self.request('/metrics')

    async def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed metrics"""
        return await self.request('/metrics/detailed')

    async def get_health(self) -> Dict[str, Any]:
        """Get health status"""
        return await self.request('/health')

    async def ingest_memory(self, content: str, memory_type: str = 'semantic', tags: list = None) -> Dict[str, Any]:
        """Ingest new memory"""
        data = {
            'content': content,
            'memory_type': memory_type,
            'tags': tags or []
        }
        return await self.request('/memories/ingest', method='POST', data=data)

    async def get_todos(self) -> Dict[str, Any]:
        """Get TODO list"""
        return await self.request('/todos')

    async def get_git_activity(self) -> Dict[str, Any]:
        """Get git activity"""
        return await self.request('/git/activity')

    async def connect_websocket(self, message_handler: Callable[[Dict], None]):
        """Connect to WebSocket for real-time updates"""
        uri = "ws://localhost:8000/api/v2/ws"
        
        try:
            async with websockets.connect(uri) as websocket:
                print("WebSocket connected")
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        await message_handler(data)
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse WebSocket message: {e}")
                    except Exception as e:
                        print(f"Message handler error: {e}")
                        
        except Exception as e:
            print(f"WebSocket connection failed: {e}")

# Usage example
async def main():
    async with SecondBrainAPI('your-api-key-here') as api:
        # Get metrics
        metrics = await api.get_metrics()
        print(f"Memories: {metrics['memories']}")
        print(f"System Health: {metrics['system_health']}")

        # Ingest memory
        result = await api.ingest_memory(
            "Learned about async/await in Python today",
            "episodic",
            ["python", "learning", "async"]
        )
        print(f"Memory created: {result['memory_id']}")

        # WebSocket handler
        async def handle_message(message):
            print(f"Received: {message['type']}")
            if message['type'] == 'memory_created':
                print(f"New memory: {message['data']['id']}")

        # Connect to WebSocket (runs indefinitely)
        await api.connect_websocket(handle_message)

if __name__ == "__main__":
    asyncio.run(main())
```

#### Node.js
```javascript
const fetch = require('node-fetch');
const WebSocket = require('ws');

class SecondBrainAPI {
    constructor(apiKey, baseUrl = 'http://localhost:8000/api/v2') {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        };
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: this.headers,
            ...options
        };

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(`API Error ${response.status}: ${error.detail}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API request failed:', error.message);
            throw error;
        }
    }

    async getMetrics() {
        return this.request('/metrics');
    }

    async getDetailedMetrics() {
        return this.request('/metrics/detailed');
    }

    async ingestMemory(content, type = 'semantic', tags = []) {
        return this.request('/memories/ingest', {
            method: 'POST',
            body: JSON.stringify({
                content,
                memory_type: type,
                tags
            })
        });
    }

    connectWebSocket(messageHandler) {
        const ws = new WebSocket('ws://localhost:8000/api/v2/ws');
        
        ws.on('open', () => {
            console.log('WebSocket connected');
        });

        ws.on('message', (data) => {
            try {
                const message = JSON.parse(data);
                messageHandler(message);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        });

        ws.on('error', (error) => {
            console.error('WebSocket error:', error);
        });

        ws.on('close', () => {
            console.log('WebSocket closed');
        });

        return ws;
    }
}

// Usage
async function main() {
    const api = new SecondBrainAPI('your-api-key-here');

    try {
        // Get metrics
        const metrics = await api.getMetrics();
        console.log('System metrics:', metrics);

        // Ingest memory
        const result = await api.ingestMemory(
            'Working on Node.js integration for Second Brain API',
            'episodic',
            ['nodejs', 'api', 'integration']
        );
        console.log('Memory created:', result.memory_id);

        // Connect WebSocket
        const ws = api.connectWebSocket((message) => {
            console.log(`WebSocket: ${message.type}`, message.data);
        });

        // Keep process alive
        process.on('SIGINT', () => {
            console.log('Closing WebSocket...');
            ws.close();
            process.exit(0);
        });

    } catch (error) {
        console.error('Error:', error.message);
    }
}

main();
```

## Dashboard Integration

### Complete React Dashboard

```jsx
import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const SecondBrainDashboard = () => {
    const [metrics, setMetrics] = useState(null);
    const [detailedMetrics, setDetailedMetrics] = useState(null);
    const [health, setHealth] = useState(null);
    const [todos, setTodos] = useState(null);
    const [gitActivity, setGitActivity] = useState(null);
    const [wsConnected, setWsConnected] = useState(false);
    const [notifications, setNotifications] = useState([]);
    const [metricsHistory, setMetricsHistory] = useState([]);

    const API_KEY = process.env.REACT_APP_SECOND_BRAIN_API_KEY;
    const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000/api/v2';

    // Initialize data fetching
    useEffect(() => {
        const fetchInitialData = async () => {
            try {
                const headers = {
                    'Authorization': `Bearer ${API_KEY}`,
                    'Content-Type': 'application/json'
                };

                const [metricsRes, detailedRes, healthRes, todosRes, gitRes] = await Promise.all([
                    fetch(`${API_BASE}/metrics`, { headers }),
                    fetch(`${API_BASE}/metrics/detailed`, { headers }),
                    fetch(`${API_BASE}/health`, { headers }),
                    fetch(`${API_BASE}/todos`, { headers }),
                    fetch(`${API_BASE}/git/activity`, { headers })
                ]);

                const [metricsData, detailedData, healthData, todosData, gitData] = await Promise.all([
                    metricsRes.json(),
                    detailedRes.json(),
                    healthRes.json(),
                    todosRes.json(),
                    gitRes.json()
                ]);

                setMetrics(metricsData);
                setDetailedMetrics(detailedData);
                setHealth(healthData);
                setTodos(todosData);
                setGitActivity(gitData);

                // Initialize metrics history
                setMetricsHistory([{
                    timestamp: new Date().toLocaleTimeString(),
                    memories: metricsData.memories,
                    activeUsers: metricsData.active_users
                }]);
            } catch (error) {
                console.error('Failed to fetch initial data:', error);
                addNotification('error', 'Data Load Error', 'Failed to load dashboard data');
            }
        };

        fetchInitialData();
    }, [API_KEY, API_BASE]);

    // WebSocket connection
    useEffect(() => {
        const ws = new WebSocket(`${API_BASE.replace('http', 'ws')}/ws`);

        ws.onopen = () => {
            setWsConnected(true);
            addNotification('success', 'Connected', 'Real-time updates enabled');
        };

        ws.onclose = () => {
            setWsConnected(false);
            addNotification('warning', 'Disconnected', 'Real-time updates paused');
        };

        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            handleWebSocketMessage(message);
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            addNotification('error', 'Connection Error', 'WebSocket connection failed');
        };

        return () => ws.close();
    }, [API_BASE]);

    const handleWebSocketMessage = (message) => {
        switch (message.type) {
            case 'metrics_update':
                setMetrics(message.data);
                // Add to history for charting
                setMetricsHistory(prev => [
                    ...prev.slice(-20), // Keep last 20 points
                    {
                        timestamp: new Date().toLocaleTimeString(),
                        memories: message.data.memories,
                        activeUsers: message.data.active_users
                    }
                ]);
                break;

            case 'memory_created':
                addNotification('info', 'Memory Created', 
                    `New ${message.data.memory_type} memory added`);
                break;

            case 'health_change':
                if (message.data.new_status !== 'healthy') {
                    addNotification('warning', 'Health Alert', 
                        `System status: ${message.data.new_status}`);
                }
                break;

            case 'system_error':
                addNotification('error', 'System Error', message.data.message);
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

        setNotifications(prev => [notification, ...prev.slice(0, 9)]);

        // Auto-remove
        setTimeout(() => {
            setNotifications(prev => prev.filter(n => n.id !== notification.id));
        }, type === 'error' ? 10000 : 5000);
    };

    const ingestMemory = async () => {
        const content = prompt('Enter memory content:');
        if (!content) return;

        try {
            const response = await fetch(`${API_BASE}/memories/ingest`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${API_KEY}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content,
                    memory_type: 'semantic',
                    tags: ['dashboard', 'manual']
                })
            });

            const result = await response.json();
            if (result.success) {
                addNotification('success', 'Memory Ingested', `ID: ${result.memory_id}`);
            }
        } catch (error) {
            addNotification('error', 'Ingestion Failed', error.message);
        }
    };

    if (!metrics || !detailedMetrics || !health) {
        return (
            <div className="dashboard-loading">
                <div className="loading-spinner"></div>
                <p>Loading Second Brain Dashboard...</p>
            </div>
        );
    }

    return (
        <div className="second-brain-dashboard">
            {/* Header */}
            <header className="dashboard-header">
                <h1>Second Brain Dashboard</h1>
                <div className="header-controls">
                    <div className={`connection-status ${wsConnected ? 'connected' : 'disconnected'}`}>
                        <span className="status-dot"></span>
                        {wsConnected ? 'Live' : 'Offline'}
                    </div>
                    <button onClick={ingestMemory} className="btn-primary">
                        Add Memory
                    </button>
                </div>
            </header>

            {/* Key Metrics */}
            <div className="metrics-grid">
                <div className="metric-card">
                    <h3>Total Memories</h3>
                    <div className="metric-value">{detailedMetrics.memories.total}</div>
                    <div className="metric-trend">
                        +{detailedMetrics.memories.last_24h} today
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
                    <h3>Active Users</h3>
                    <div className="metric-value">{metrics.active_users}</div>
                    <div className="metric-detail">
                        {detailedMetrics.memories.unique_users} total users
                    </div>
                </div>

                <div className="metric-card">
                    <h3>TODO Progress</h3>
                    <div className="metric-value">{todos?.stats.completion_rate || 0}%</div>
                    <div className="metric-detail">
                        {todos?.stats.completed || 0}/{todos?.stats.total || 0} completed
                    </div>
                </div>
            </div>

            {/* Charts */}
            <div className="charts-section">
                <div className="chart-container">
                    <h3>Memory Growth</h3>
                    <ResponsiveContainer width="100%" height={300}>
                        <LineChart data={metricsHistory}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="timestamp" />
                            <YAxis />
                            <Tooltip />
                            <Line 
                                type="monotone" 
                                dataKey="memories" 
                                stroke="#8884d8" 
                                strokeWidth={2}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </div>

                <div className="performance-metrics">
                    <h3>Performance</h3>
                    <div className="performance-grid">
                        <div className="perf-item">
                            <label>Response Time</label>
                            <span>{detailedMetrics.performance.api_response_time}</span>
                        </div>
                        <div className="perf-item">
                            <label>Memory Usage</label>
                            <span>{detailedMetrics.performance.memory_usage}</span>
                        </div>
                        <div className="perf-item">
                            <label>Cache Hit Rate</label>
                            <span>{detailedMetrics.performance.cache_hit_rate}</span>
                        </div>
                        <div className="perf-item">
                            <label>Active Connections</label>
                            <span>{detailedMetrics.performance.active_connections}</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Recent Activity */}
            <div className="activity-section">
                <div className="recent-todos">
                    <h3>Pending TODOs</h3>
                    <div className="todo-list">
                        {todos?.todos
                            .filter(todo => todo.status === 'pending')
                            .slice(0, 5)
                            .map(todo => (
                                <div key={todo.id} className={`todo-item priority-${todo.priority}`}>
                                    <span className="todo-content">{todo.content}</span>
                                    <span className="todo-category">{todo.category}</span>
                                </div>
                            ))
                        }
                    </div>
                </div>

                <div className="recent-commits">
                    <h3>Recent Commits</h3>
                    <div className="commit-list">
                        {gitActivity?.commits.slice(0, 5).map(commit => (
                            <div key={commit.hash} className="commit-item">
                                <code className="commit-hash">{commit.hash}</code>
                                <span className="commit-message">{commit.message}</span>
                                <span className="commit-time">{commit.relative_time}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Notifications */}
            <div className="notifications-panel">
                {notifications.map(notification => (
                    <div 
                        key={notification.id} 
                        className={`notification ${notification.type}`}
                    >
                        <div className="notification-header">
                            <strong>{notification.title}</strong>
                            <button 
                                onClick={() => setNotifications(prev => 
                                    prev.filter(n => n.id !== notification.id)
                                )}
                                className="close-btn"
                            >
                                ×
                            </button>
                        </div>
                        <div className="notification-message">
                            {notification.message}
                        </div>
                        <div className="notification-time">
                            {new Date(notification.timestamp).toLocaleString()}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default SecondBrainDashboard;
```

### CSS Styles for Dashboard

```css
.second-brain-dashboard {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #f5f5f7;
    min-height: 100vh;
    padding: 20px;
}

.dashboard-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: white;
    padding: 20px 30px;
    border-radius: 12px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    margin-bottom: 30px;
}

.dashboard-header h1 {
    margin: 0;
    color: #1d1d1f;
    font-size: 28px;
    font-weight: 600;
}

.header-controls {
    display: flex;
    align-items: center;
    gap: 20px;
}

.connection-status {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    border-radius: 20px;
    font-size: 14px;
    font-weight: 500;
}

.connection-status.connected {
    background: #d1f2eb;
    color: #00a86b;
}

.connection-status.disconnected {
    background: #fadbd8;
    color: #e74c3c;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: currentColor;
}

.btn-primary {
    background: #007aff;
    color: white;
    border: none;
    padding: 12px 24px;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s;
}

.btn-primary:hover {
    background: #0056cc;
}

.metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.metric-card {
    background: white;
    padding: 24px;
    border-radius: 12px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.metric-card h3 {
    margin: 0 0 16px 0;
    color: #86868b;
    font-size: 14px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.metric-value {
    font-size: 36px;
    font-weight: 700;
    color: #1d1d1f;
    margin-bottom: 8px;
}

.metric-trend, .metric-detail {
    color: #86868b;
    font-size: 14px;
}

.health-status {
    font-size: 24px;
    font-weight: 600;
    text-transform: capitalize;
    padding: 8px 16px;
    border-radius: 8px;
    display: inline-block;
}

.health-status.healthy {
    background: #d1f2eb;
    color: #00a86b;
}

.health-status.degraded {
    background: #fef9e7;
    color: #f39c12;
}

.health-status.unhealthy {
    background: #fadbd8;
    color: #e74c3c;
}

.charts-section {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 30px;
    margin-bottom: 30px;
}

.chart-container, .performance-metrics {
    background: white;
    padding: 24px;
    border-radius: 12px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.chart-container h3, .performance-metrics h3 {
    margin: 0 0 20px 0;
    color: #1d1d1f;
    font-size: 18px;
    font-weight: 600;
}

.performance-grid {
    display: grid;
    gap: 16px;
}

.perf-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 0;
    border-bottom: 1px solid #f2f2f7;
}

.perf-item:last-child {
    border-bottom: none;
}

.perf-item label {
    color: #86868b;
    font-size: 14px;
}

.perf-item span {
    font-weight: 600;
    color: #1d1d1f;
}

.activity-section {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 30px;
    margin-bottom: 30px;
}

.recent-todos, .recent-commits {
    background: white;
    padding: 24px;
    border-radius: 12px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.recent-todos h3, .recent-commits h3 {
    margin: 0 0 20px 0;
    color: #1d1d1f;
    font-size: 18px;
    font-weight: 600;
}

.todo-item, .commit-item {
    padding: 12px 0;
    border-bottom: 1px solid #f2f2f7;
    display: flex;
    align-items: center;
    gap: 12px;
}

.todo-item:last-child, .commit-item:last-child {
    border-bottom: none;
}

.todo-content, .commit-message {
    flex: 1;
    color: #1d1d1f;
    font-size: 14px;
}

.todo-category {
    background: #f2f2f7;
    color: #86868b;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    text-transform: uppercase;
}

.todo-item.priority-high .todo-category {
    background: #fadbd8;
    color: #e74c3c;
}

.commit-hash {
    font-family: 'SF Mono', monospace;
    background: #f2f2f7;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    color: #007aff;
}

.commit-time {
    color: #86868b;
    font-size: 12px;
    white-space: nowrap;
}

.notifications-panel {
    position: fixed;
    top: 20px;
    right: 20px;
    width: 350px;
    z-index: 1000;
}

.notification {
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    margin-bottom: 12px;
    padding: 16px;
    border-left: 4px solid #007aff;
    animation: slideIn 0.3s ease-out;
}

.notification.success {
    border-left-color: #00a86b;
}

.notification.warning {
    border-left-color: #f39c12;
}

.notification.error {
    border-left-color: #e74c3c;
}

.notification-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.notification-header strong {
    color: #1d1d1f;
    font-size: 14px;
}

.close-btn {
    background: none;
    border: none;
    font-size: 18px;
    color: #86868b;
    cursor: pointer;
    padding: 0;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.close-btn:hover {
    color: #1d1d1f;
}

.notification-message {
    color: #86868b;
    font-size: 13px;
    margin-bottom: 8px;
}

.notification-time {
    color: #c7c7cc;
    font-size: 11px;
}

.dashboard-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    color: #86868b;
}

.loading-spinner {
    width: 40px;
    height: 40px;
    border: 3px solid #f2f2f7;
    border-top: 3px solid #007aff;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 20px;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

@keyframes slideIn {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

@media (max-width: 768px) {
    .second-brain-dashboard {
        padding: 10px;
    }
    
    .metrics-grid {
        grid-template-columns: 1fr;
    }
    
    .charts-section,
    .activity-section {
        grid-template-columns: 1fr;
    }
    
    .notifications-panel {
        width: calc(100vw - 40px);
        right: 10px;
    }
}
```

## Memory Management

### Bulk Memory Operations

```javascript
class BulkMemoryManager {
    constructor(apiKey, baseUrl = 'http://localhost:8000/api/v2') {
        this.api = new SecondBrainAPI(apiKey, baseUrl);
    }

    async ingestFromFile(file, options = {}) {
        const {
            chunkSize = 1000,
            memoryType = 'semantic',
            tagPrefix = 'imported',
            batchSize = 10
        } = options;

        const content = await this.readFile(file);
        const chunks = this.chunkText(content, chunkSize);
        
        console.log(`Ingesting ${chunks.length} chunks from ${file.name}`);
        
        const results = [];
        const errors = [];

        // Process in batches to avoid overwhelming the API
        for (let i = 0; i < chunks.length; i += batchSize) {
            const batch = chunks.slice(i, i + batchSize);
            const batchPromises = batch.map((chunk, index) => 
                this.ingestChunk(chunk, {
                    memoryType,
                    tags: [tagPrefix, file.name, `chunk-${i + index}`],
                    source: file.name
                })
            );

            try {
                const batchResults = await Promise.allSettled(batchPromises);
                
                batchResults.forEach((result, index) => {
                    if (result.status === 'fulfilled') {
                        results.push(result.value);
                    } else {
                        errors.push({
                            chunk: i + index,
                            error: result.reason.message
                        });
                    }
                });

                // Small delay between batches
                if (i + batchSize < chunks.length) {
                    await this.delay(100);
                }

            } catch (error) {
                console.error('Batch processing error:', error);
            }

            // Progress update
            const progress = Math.min(i + batchSize, chunks.length);
            console.log(`Progress: ${progress}/${chunks.length} chunks processed`);
        }

        return {
            success: results.length,
            errors: errors.length,
            results,
            errorDetails: errors
        };
    }

    async ingestChunk(content, options) {
        const { memoryType, tags, source } = options;
        
        try {
            const result = await this.api.ingestMemory(content, memoryType, tags);
            return {
                ...result,
                source,
                content_preview: content.substring(0, 100) + '...'
            };
        } catch (error) {
            throw new Error(`Failed to ingest chunk: ${error.message}`);
        }
    }

    chunkText(text, maxSize) {
        const chunks = [];
        let currentChunk = '';
        const sentences = text.split(/[.!?]+/);

        for (const sentence of sentences) {
            if (currentChunk.length + sentence.length > maxSize) {
                if (currentChunk.trim()) {
                    chunks.push(currentChunk.trim());
                }
                currentChunk = sentence;
            } else {
                currentChunk += sentence + '.';
            }
        }

        if (currentChunk.trim()) {
            chunks.push(currentChunk.trim());
        }

        return chunks.filter(chunk => chunk.length > 50); // Filter out very short chunks
    }

    async readFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = reject;
            reader.readAsText(file);
        });
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Usage
const bulkManager = new BulkMemoryManager('your-api-key');

// Handle file upload
document.getElementById('file-input').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    try {
        const result = await bulkManager.ingestFromFile(file, {
            chunkSize: 800,
            memoryType: 'semantic',
            tagPrefix: 'document',
            batchSize: 5
        });

        console.log(`Ingestion complete: ${result.success} successful, ${result.errors} errors`);
        
        if (result.errors > 0) {
            console.error('Errors:', result.errorDetails);
        }
    } catch (error) {
        console.error('Bulk ingestion failed:', error);
    }
});
```

### Memory Search and Retrieval

```javascript
class MemorySearchManager {
    constructor(apiKey, baseUrl = 'http://localhost:8000/api/v1') {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        };
    }

    async searchMemories(query, options = {}) {
        const {
            limit = 20,
            memoryTypes = null,
            tags = null,
            dateRange = null,
            minImportance = null
        } = options;

        const params = new URLSearchParams({
            q: query,
            limit: limit.toString()
        });

        if (memoryTypes) {
            memoryTypes.forEach(type => params.append('memory_type', type));
        }

        if (tags) {
            tags.forEach(tag => params.append('tag', tag));
        }

        if (dateRange) {
            if (dateRange.start) params.append('start_date', dateRange.start);
            if (dateRange.end) params.append('end_date', dateRange.end);
        }

        if (minImportance) {
            params.append('min_importance', minImportance.toString());
        }

        try {
            const response = await fetch(`${this.baseUrl}/memories/search?${params}`, {
                headers: this.headers
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(`Search failed: ${error.detail}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Memory search failed:', error);
            throw error;
        }
    }

    async findSimilarMemories(memoryId, limit = 10) {
        try {
            const response = await fetch(`${this.baseUrl}/memories/${memoryId}/similar?limit=${limit}`, {
                headers: this.headers
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(`Similar search failed: ${error.detail}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Similar memory search failed:', error);
            throw error;
        }
    }

    async getMemoryConnections(memoryId) {
        try {
            const response = await fetch(`${this.baseUrl}/memories/${memoryId}/connections`, {
                headers: this.headers
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(`Connection fetch failed: ${error.detail}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Memory connections fetch failed:', error);
            throw error;
        }
    }

    async exportMemories(filters = {}) {
        const params = new URLSearchParams();
        
        Object.entries(filters).forEach(([key, value]) => {
            if (Array.isArray(value)) {
                value.forEach(v => params.append(key, v));
            } else if (value !== null && value !== undefined) {
                params.append(key, value.toString());
            }
        });

        try {
            const response = await fetch(`${this.baseUrl}/memories/export?${params}`, {
                headers: this.headers
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(`Export failed: ${error.detail}`);
            }

            const blob = await response.blob();
            
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `memories-export-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            return { success: true, message: 'Export downloaded successfully' };
        } catch (error) {
            console.error('Memory export failed:', error);
            throw error;
        }
    }
}

// Usage examples
const searchManager = new MemorySearchManager('your-api-key');

// Search for memories
async function searchExample() {
    try {
        const results = await searchManager.searchMemories('machine learning', {
            limit: 10,
            memoryTypes: ['semantic', 'episodic'],
            tags: ['ai', 'research'],
            minImportance: 0.7
        });

        console.log(`Found ${results.total} memories:`);
        results.items.forEach(memory => {
            console.log(`- ${memory.content.substring(0, 100)}...`);
        });
    } catch (error) {
        console.error('Search failed:', error);
    }
}

// Find similar memories
async function findSimilarExample(memoryId) {
    try {
        const similar = await searchManager.findSimilarMemories(memoryId, 5);
        console.log('Similar memories:', similar);
    } catch (error) {
        console.error('Similar search failed:', error);
    }
}

// Export memories
async function exportExample() {
    try {
        await searchManager.exportMemories({
            memory_type: 'semantic',
            min_importance: 0.5,
            start_date: '2025-01-01'
        });
    } catch (error) {
        console.error('Export failed:', error);
    }
}
```

## Real-time Updates

### Advanced WebSocket Client

```javascript
class AdvancedWebSocketClient {
    constructor(url, options = {}) {
        this.url = url;
        this.options = {
            reconnectInterval: 1000,
            maxReconnectInterval: 30000,
            reconnectDecay: 1.5,
            maxReconnectAttempts: 10,
            timeoutInterval: 2000,
            enableLogging: true,
            ...options
        };

        this.reconnectAttempts = 0;
        this.connectionState = 'CLOSED';
        this.messageQueue = [];
        this.subscriptions = new Map();
        this.messageId = 0;
        this.lastHeartbeat = null;
        this.heartbeatTimer = null;

        this.connect();
    }

    connect() {
        if (this.connectionState === 'CONNECTING' || this.connectionState === 'OPEN') {
            return;
        }

        this.connectionState = 'CONNECTING';
        this.log('Connecting to WebSocket...');

        try {
            this.ws = new WebSocket(this.url);
            this.setupEventHandlers();
        } catch (error) {
            this.log('Connection failed:', error);
            this.scheduleReconnect();
        }
    }

    setupEventHandlers() {
        this.ws.onopen = (event) => {
            this.log('WebSocket connected');
            this.connectionState = 'OPEN';
            this.reconnectAttempts = 0;
            
            // Process queued messages
            this.processMessageQueue();
            
            // Start heartbeat monitoring
            this.startHeartbeatMonitoring();
            
            // Trigger connected event
            this.trigger('connected', event);
        };

        this.ws.onclose = (event) => {
            this.log('WebSocket closed:', event.code, event.reason);
            this.connectionState = 'CLOSED';
            this.stopHeartbeatMonitoring();
            
            // Trigger disconnected event
            this.trigger('disconnected', event);
            
            // Attempt reconnection unless it was a normal closure
            if (event.code !== 1000) {
                this.scheduleReconnect();
            }
        };

        this.ws.onerror = (error) => {
            this.log('WebSocket error:', error);
            this.trigger('error', error);
        };

        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                this.handleMessage(message);
            } catch (error) {
                this.log('Failed to parse message:', error);
            }
        };
    }

    handleMessage(message) {
        this.log('Received message:', message.type);

        // Handle heartbeat
        if (message.type === 'heartbeat') {
            this.lastHeartbeat = Date.now();
            this.trigger('heartbeat', message);
            return;
        }

        // Handle connection confirmation
        if (message.type === 'connection') {
            this.trigger('connection', message);
            return;
        }

        // Handle subscribed events
        const handlers = this.subscriptions.get(message.type);
        if (handlers) {
            handlers.forEach(handler => {
                try {
                    handler(message);
                } catch (error) {
                    this.log('Handler error:', error);
                }
            });
        }

        // Trigger general message event
        this.trigger('message', message);
    }

    send(data) {
        const message = {
            id: ++this.messageId,
            timestamp: new Date().toISOString(),
            ...data
        };

        if (this.connectionState === 'OPEN') {
            try {
                this.ws.send(JSON.stringify(message));
                this.log('Sent message:', message.type || 'unknown');
            } catch (error) {
                this.log('Send failed:', error);
                this.messageQueue.push(message);
            }
        } else {
            this.log('Queuing message (connection not ready):', message.type || 'unknown');
            this.messageQueue.push(message);
        }
    }

    subscribe(eventType, handler) {
        if (!this.subscriptions.has(eventType)) {
            this.subscriptions.set(eventType, []);
        }
        this.subscriptions.get(eventType).push(handler);

        // Return unsubscribe function
        return () => {
            const handlers = this.subscriptions.get(eventType);
            if (handlers) {
                const index = handlers.indexOf(handler);
                if (index > -1) {
                    handlers.splice(index, 1);
                }
                if (handlers.length === 0) {
                    this.subscriptions.delete(eventType);
                }
            }
        };
    }

    unsubscribe(eventType, handler) {
        const handlers = this.subscriptions.get(eventType);
        if (handlers) {
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
            }
        }
    }

    processMessageQueue() {
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            try {
                this.ws.send(JSON.stringify(message));
                this.log('Sent queued message:', message.type || 'unknown');
            } catch (error) {
                this.log('Failed to send queued message:', error);
                // Put it back at the front
                this.messageQueue.unshift(message);
                break;
            }
        }
    }

    scheduleReconnect() {
        if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
            this.log('Max reconnection attempts reached');
            this.trigger('maxReconnectAttemptsReached');
            return;
        }

        const timeout = Math.min(
            this.options.reconnectInterval * Math.pow(this.options.reconnectDecay, this.reconnectAttempts),
            this.options.maxReconnectInterval
        );

        this.reconnectAttempts++;
        this.log(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${timeout}ms`);

        setTimeout(() => {
            this.connect();
        }, timeout);
    }

    startHeartbeatMonitoring() {
        this.lastHeartbeat = Date.now();
        
        this.heartbeatTimer = setInterval(() => {
            const timeSinceHeartbeat = Date.now() - this.lastHeartbeat;
            
            if (timeSinceHeartbeat > 60000) { // 1 minute without heartbeat
                this.log('Heartbeat timeout detected');
                this.trigger('heartbeatTimeout');
                
                // Force reconnection
                if (this.ws) {
                    this.ws.close(4000, 'Heartbeat timeout');
                }
            }
        }, 30000); // Check every 30 seconds
    }

    stopHeartbeatMonitoring() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }

    close() {
        this.log('Closing WebSocket connection');
        this.stopHeartbeatMonitoring();
        
        if (this.ws) {
            this.ws.close(1000, 'Client closing');
        }
        
        this.connectionState = 'CLOSED';
    }

    getConnectionState() {
        return this.connectionState;
    }

    getStatistics() {
        return {
            connectionState: this.connectionState,
            reconnectAttempts: this.reconnectAttempts,
            queuedMessages: this.messageQueue.length,
            subscriptions: Array.from(this.subscriptions.keys()),
            lastHeartbeat: this.lastHeartbeat ? new Date(this.lastHeartbeat) : null
        };
    }

    // Event system
    trigger(eventName, data) {
        const event = new CustomEvent(eventName, { detail: data });
        if (this.options.enableLogging) {
            this.log('Event triggered:', eventName);
        }
        
        // If running in browser, dispatch on window
        if (typeof window !== 'undefined') {
            window.dispatchEvent(event);
        }
        
        // Also call direct handlers if they exist
        const handlerName = `on${eventName.charAt(0).toUpperCase()}${eventName.slice(1)}`;
        if (typeof this[handlerName] === 'function') {
            this[handlerName](data);
        }
    }

    log(...args) {
        if (this.options.enableLogging) {
            console.log('[WebSocket]', ...args);
        }
    }
}

// Usage example
const wsClient = new AdvancedWebSocketClient('ws://localhost:8000/api/v2/ws', {
    reconnectInterval: 2000,
    maxReconnectAttempts: 5,
    enableLogging: true
});

// Subscribe to specific events
const unsubscribeMetrics = wsClient.subscribe('metrics_update', (message) => {
    console.log('Metrics updated:', message.data);
    updateDashboard(message.data);
});

const unsubscribeMemory = wsClient.subscribe('memory_created', (message) => {
    console.log('New memory created:', message.data.id);
    showNotification('Memory created successfully');
});

// Handle connection events
wsClient.onConnected = () => {
    console.log('Successfully connected to Second Brain');
    showConnectionStatus('connected');
};

wsClient.onDisconnected = () => {
    console.log('Disconnected from Second Brain');
    showConnectionStatus('disconnected');
};

wsClient.onHeartbeatTimeout = () => {
    console.warn('Connection appears to be stale');
    showConnectionStatus('stale');
};

// Monitor connection health
setInterval(() => {
    const stats = wsClient.getStatistics();
    console.log('WebSocket stats:', stats);
}, 60000);

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    wsClient.close();
});
```

## Monitoring & Health Checks

### Comprehensive Health Monitor

```javascript
class HealthMonitor {
    constructor(apiKey, options = {}) {
        this.apiKey = apiKey;
        this.baseUrl = options.baseUrl || 'http://localhost:8000/api/v2';
        this.checkInterval = options.checkInterval || 30000; // 30 seconds
        this.alertThresholds = {
            responseTime: options.maxResponseTime || 5000,
            errorRate: options.maxErrorRate || 0.1,
            ...options.alertThresholds
        };
        
        this.metrics = {
            checks: [],
            errors: [],
            responseTimeHistory: [],
            uptime: null
        };
        
        this.alertHandlers = [];
        this.isMonitoring = false;
        
        this.headers = {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        };
    }

    async startMonitoring() {
        if (this.isMonitoring) return;
        
        this.isMonitoring = true;
        console.log('Health monitoring started');
        
        // Initial health check
        await this.performHealthCheck();
        
        // Schedule regular checks
        this.monitoringInterval = setInterval(() => {
            this.performHealthCheck();
        }, this.checkInterval);
    }

    stopMonitoring() {
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
            this.monitoringInterval = null;
        }
        this.isMonitoring = false;
        console.log('Health monitoring stopped');
    }

    async performHealthCheck() {
        const startTime = Date.now();
        
        try {
            // Perform multiple health checks
            const [basicHealth, metrics, detailedMetrics] = await Promise.allSettled([
                this.checkEndpoint('/health'),
                this.checkEndpoint('/metrics'),
                this.checkEndpoint('/metrics/detailed')
            ]);

            const endTime = Date.now();
            const responseTime = endTime - startTime;

            // Record response time
            this.metrics.responseTimeHistory.push({
                timestamp: new Date().toISOString(),
                responseTime
            });

            // Keep only last 100 response times
            if (this.metrics.responseTimeHistory.length > 100) {
                this.metrics.responseTimeHistory = this.metrics.responseTimeHistory.slice(-100);
            }

            // Analyze results
            const healthResult = {
                timestamp: new Date().toISOString(),
                responseTime,
                status: 'healthy',
                checks: {
                    basic_health: this.getCheckResult(basicHealth),
                    metrics: this.getCheckResult(metrics),
                    detailed_metrics: this.getCheckResult(detailedMetrics)
                }
            };

            // Determine overall status
            const failedChecks = Object.values(healthResult.checks).filter(c => c.status !== 'success');
            if (failedChecks.length > 0) {
                healthResult.status = failedChecks.length === Object.keys(healthResult.checks).length ? 'down' : 'degraded';
            }

            // Check response time
            if (responseTime > this.alertThresholds.responseTime) {
                healthResult.status = 'degraded';
                healthResult.alerts = healthResult.alerts || [];
                healthResult.alerts.push(`High response time: ${responseTime}ms`);
            }

            // Record check
            this.metrics.checks.push(healthResult);
            
            // Keep only last 100 checks
            if (this.metrics.checks.length > 100) {
                this.metrics.checks = this.metrics.checks.slice(-100);
            }

            // Calculate uptime
            this.calculateUptime();

            // Trigger alerts if needed
            this.checkAlerts(healthResult);

        } catch (error) {
            console.error('Health check failed:', error);
            
            this.metrics.errors.push({
                timestamp: new Date().toISOString(),
                error: error.message
            });

            // Keep only last 50 errors
            if (this.metrics.errors.length > 50) {
                this.metrics.errors = this.metrics.errors.slice(-50);
            }
        }
    }

    async checkEndpoint(endpoint) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            headers: this.headers,
            timeout: 10000
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    }

    getCheckResult(settledResult) {
        if (settledResult.status === 'fulfilled') {
            return {
                status: 'success',
                data: settledResult.value
            };
        } else {
            return {
                status: 'failed',
                error: settledResult.reason.message
            };
        }
    }

    calculateUptime() {
        if (this.metrics.checks.length === 0) {
            this.metrics.uptime = 100;
            return;
        }

        const recentChecks = this.metrics.checks.slice(-20); // Last 20 checks
        const successfulChecks = recentChecks.filter(c => c.status === 'healthy').length;
        this.metrics.uptime = (successfulChecks / recentChecks.length) * 100;
    }

    checkAlerts(healthResult) {
        const alerts = [];

        // Service down alert
        if (healthResult.status === 'down') {
            alerts.push({
                level: 'critical',
                type: 'service_down',
                message: 'Second Brain API is down',
                details: healthResult.checks
            });
        }

        // Service degraded alert
        if (healthResult.status === 'degraded') {
            alerts.push({
                level: 'warning',
                type: 'service_degraded',
                message: 'Second Brain API performance degraded',
                details: healthResult
            });
        }

        // High response time alert
        if (healthResult.responseTime > this.alertThresholds.responseTime) {
            alerts.push({
                level: 'warning',
                type: 'high_response_time',
                message: `High response time: ${healthResult.responseTime}ms`,
                threshold: this.alertThresholds.responseTime
            });
        }

        // Low uptime alert
        if (this.metrics.uptime < 95) {
            alerts.push({
                level: 'warning',
                type: 'low_uptime',
                message: `Low uptime: ${this.metrics.uptime.toFixed(1)}%`,
                threshold: 95
            });
        }

        // Trigger alert handlers
        alerts.forEach(alert => {
            this.alertHandlers.forEach(handler => {
                try {
                    handler(alert);
                } catch (error) {
                    console.error('Alert handler failed:', error);
                }
            });
        });
    }

    onAlert(handler) {
        this.alertHandlers.push(handler);
        
        // Return unsubscribe function
        return () => {
            const index = this.alertHandlers.indexOf(handler);
            if (index > -1) {
                this.alertHandlers.splice(index, 1);
            }
        };
    }

    getHealthReport() {
        const recentChecks = this.metrics.checks.slice(-10);
        const recentErrors = this.metrics.errors.slice(-5);
        const avgResponseTime = this.metrics.responseTimeHistory.length > 0 
            ? this.metrics.responseTimeHistory.reduce((sum, r) => sum + r.responseTime, 0) / this.metrics.responseTimeHistory.length
            : 0;

        return {
            status: recentChecks.length > 0 ? recentChecks[recentChecks.length - 1].status : 'unknown',
            uptime: this.metrics.uptime,
            averageResponseTime: Math.round(avgResponseTime),
            recentChecks,
            recentErrors,
            monitoring: this.isMonitoring,
            lastCheck: recentChecks.length > 0 ? recentChecks[recentChecks.length - 1].timestamp : null
        };
    }

    exportMetrics() {
        const report = {
            generated: new Date().toISOString(),
            summary: this.getHealthReport(),
            fullMetrics: this.metrics
        };

        const blob = new Blob([JSON.stringify(report, null, 2)], {
            type: 'application/json'
        });

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `second-brain-health-report-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }
}

// Usage
const healthMonitor = new HealthMonitor('your-api-key', {
    checkInterval: 30000, // 30 seconds
    maxResponseTime: 3000, // 3 seconds
    baseUrl: 'http://localhost:8000/api/v2'
});

// Set up alert handlers
healthMonitor.onAlert((alert) => {
    console.log(`ALERT [${alert.level}]: ${alert.message}`);
    
    // Show browser notification
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(`Second Brain Alert`, {
            body: alert.message,
            icon: '/favicon.ico'
        });
    }
    
    // Send to external monitoring service
    // sendToSlack(alert);
    // sendToEmail(alert);
});

// Start monitoring
healthMonitor.startMonitoring();

// Health status display component
function createHealthStatusDisplay() {
    const container = document.createElement('div');
    container.className = 'health-status-display';
    
    const updateDisplay = () => {
        const report = healthMonitor.getHealthReport();
        
        container.innerHTML = `
            <div class="health-header">
                <h3>Second Brain Health Status</h3>
                <div class="status-badge status-${report.status}">${report.status}</div>
            </div>
            <div class="health-metrics">
                <div class="metric">
                    <label>Uptime</label>
                    <span>${report.uptime?.toFixed(1) || 0}%</span>
                </div>
                <div class="metric">
                    <label>Avg Response Time</label>
                    <span>${report.averageResponseTime}ms</span>
                </div>
                <div class="metric">
                    <label>Last Check</label>
                    <span>${report.lastCheck ? new Date(report.lastCheck).toLocaleTimeString() : 'Never'}</span>
                </div>
            </div>
            ${report.recentErrors.length > 0 ? `
                <div class="recent-errors">
                    <h4>Recent Errors</h4>
                    ${report.recentErrors.map(error => `
                        <div class="error-item">
                            <span class="error-time">${new Date(error.timestamp).toLocaleTimeString()}</span>
                            <span class="error-message">${error.error}</span>
                        </div>
                    `).join('')}
                </div>
            ` : ''}
        `;
    };
    
    // Update every 30 seconds
    updateDisplay();
    setInterval(updateDisplay, 30000);
    
    return container;
}

// Add to page
document.body.appendChild(createHealthStatusDisplay());

// Export health report button
const exportButton = document.createElement('button');
exportButton.textContent = 'Export Health Report';
exportButton.onclick = () => healthMonitor.exportMetrics();
document.body.appendChild(exportButton);
```

This comprehensive usage guide provides practical examples for integrating with the Second Brain V2 API across different scenarios and programming languages. Each example includes error handling, best practices, and real-world implementation patterns.