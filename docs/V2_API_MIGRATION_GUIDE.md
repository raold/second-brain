# Second Brain V2 Unified API Migration Guide

## Overview

The Second Brain V2 Unified API represents a major evolution, combining the robustness of V1's PostgreSQL backend with modern real-time WebSocket capabilities. This comprehensive migration guide helps developers transition from older API versions to the new unified system.

## What's New in V2 Unified API

### Major Improvements
- **Real-Time Updates**: WebSocket support with automatic broadcasting
- **Unified Data Source**: Single PostgreSQL backend for all endpoints
- **Enhanced Metrics**: Comprehensive system monitoring and analytics
- **Better Performance**: Optimized queries and intelligent caching
- **Improved Documentation**: Complete OpenAPI specifications
- **Modern Architecture**: Clean separation of concerns with dependency injection

### Breaking Changes
- Authentication now required for all endpoints (except health checks)
- Response structures updated for consistency
- WebSocket events replace some polling-based updates
- Error response formats standardized

## Endpoint Migration Map

### Core System Endpoints

| Old Endpoint | New Endpoint | Status | Changes |
|--------------|--------------|--------|---------|
| `GET /api/v1/health` | `GET /api/v2/health` | ✅ Enhanced | Comprehensive health checks with component status |
| `GET /api/v1/metrics` | `GET /api/v2/metrics` | ✅ Enhanced | Real PostgreSQL data, simplified for UI |
| `GET /api/v1/dashboard/metrics` | `GET /api/v2/metrics/detailed` | ✅ Replaced | Comprehensive metrics with performance data |
| `GET /api/v1/status` | `GET /api/v2/health` | ✅ Merged | Combined into unified health endpoint |

### Memory Management

| Old Endpoint | New Endpoint | Status | Changes |
|--------------|--------------|--------|---------|
| `POST /api/v1/memories` | `POST /api/v2/memories/ingest` | ✅ Enhanced | WebSocket broadcast on creation |
| `GET /api/v1/memories` | Use V1 endpoint | ⚠️ Partial | Full V2 memory API coming in next release |
| `GET /api/v1/memories/{id}` | Use V1 endpoint | ⚠️ Partial | Full V2 memory API coming in next release |
| `PUT /api/v1/memories/{id}` | Use V1 endpoint | ⚠️ Partial | Full V2 memory API coming in next release |

### Project Management

| Old Endpoint | New Endpoint | Status | Changes |
|--------------|--------------|--------|---------|
| `GET /api/v1/dashboard/todos` | `GET /api/v2/todos` | ✅ Enhanced | Better parsing, categorization, statistics |
| `GET /api/v1/dashboard/activity` | WebSocket `/api/v2/ws` | ✅ Replaced | Real-time activity via WebSocket events |
| `GET /api/v1/git/activity` | `GET /api/v2/git/activity` | ✅ Enhanced | More commit details, branch info, statistics |

### Real-Time Updates

| Old Method | New Method | Status | Changes |
|------------|------------|--------|---------|
| Polling endpoints | WebSocket `/api/v2/ws` | ✅ New | Real-time updates for all data changes |
| Server-sent events | WebSocket `/api/v2/ws` | ✅ Replaced | More reliable bi-directional communication |

## Key Improvements

### 1. Real Data Everywhere
- All endpoints now use real PostgreSQL data
- No more hardcoded values or mocks
- Consistent data across all interfaces

### 2. WebSocket Support
- Real-time updates for all clients
- Automatic broadcasting when data changes
- Heartbeat to maintain connections

### 3. Unified Health Monitoring
- Single health endpoint for all consumers
- Comprehensive system checks
- Resource usage metrics

### 4. Better TODO Management
- Improved parsing from TODO.md
- Category detection
- Priority tracking

## WebSocket Events

Connect to `ws://localhost:8000/api/v2/ws` to receive:

```javascript
// Connection confirmed
{
  "type": "connection",
  "status": "connected",
  "timestamp": "2025-08-01T10:00:00Z"
}

// Periodic metrics updates (every minute)
{
  "type": "metrics_update",
  "data": {
    "tests": 436,
    "patterns": 27,
    "version": "3.0.0",
    "agents": 27,
    "token_usage": "6x",
    "memories": 150,
    "active_users": 3,
    "system_health": "healthy"
  },
  "timestamp": "2025-08-01T10:01:00Z"
}

// When new memory is created
{
  "type": "memory_created",
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "memory_type": "semantic",
    "tags": ["ai", "learning"],
    "created_at": "2025-08-01T10:00:30Z"
  },
  "timestamp": "2025-08-01T10:00:30Z"
}

// Heartbeat (every 30 seconds)
{
  "type": "heartbeat",
  "timestamp": "2025-08-01T10:00:30Z"
}
```

## Step-by-Step Migration Guide

### Phase 1: Preparation (Planning)

#### 1. Review Current API Usage
```bash
# Audit current API calls in your codebase
grep -r "api/v1" src/
grep -r "localhost:8000" src/
```

#### 2. Update Dependencies
```javascript
// Install WebSocket libraries if needed
npm install ws # Node.js
// or use native WebSocket in browsers
```

#### 3. Environment Configuration
```javascript
// Update environment variables
const API_BASE_URL = process.env.REACT_APP_API_BASE || 'http://localhost:8000/api/v2';
const WS_BASE_URL = process.env.REACT_APP_WS_BASE || 'ws://localhost:8000/api/v2';
const API_KEY = process.env.REACT_APP_API_KEY;
```

### Phase 2: Authentication Setup

#### 1. Add API Key Authentication
```javascript
// Old - No authentication
fetch('/api/v1/metrics')

// New - API key required
fetch('/api/v2/metrics', {
    headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json'
    }
})
```

#### 2. Handle Authentication Errors
```javascript
async function apiRequest(endpoint, options = {}) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        headers: {
            'Authorization': `Bearer ${API_KEY}`,
            'Content-Type': 'application/json',
            ...options.headers
        },
        ...options
    });

    if (response.status === 401) {
        // Handle authentication error
        throw new Error('Invalid API key');
    }

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail);
    }

    return response.json();
}
```

### Phase 3: Endpoint Migration

#### 1. Update Simple Metrics (User Interfaces)
```javascript
// Old
const getMetrics = async () => {
    const response = await fetch('/api/v1/metrics');
    return response.json();
};

// New - Same endpoint, enhanced data
const getMetrics = async () => {
    return apiRequest('/metrics');
};

// Response format remains compatible:
// {
//   tests: 436,
//   patterns: 27,
//   version: "3.0.0",
//   memories: 150,
//   active_users: 3,
//   system_health: "healthy"
// }
```

#### 2. Update Detailed Metrics (Dashboards)
```javascript
// Old
const getDashboardMetrics = async () => {
    const response = await fetch('/api/v1/dashboard/metrics');
    return response.json();
};

// New - Enhanced structure
const getDetailedMetrics = async () => {
    return apiRequest('/metrics/detailed');
};

// Handle new response structure:
const metrics = await getDetailedMetrics();
console.log('Total memories:', metrics.memories.total);
console.log('Performance:', metrics.performance);
console.log('System info:', metrics.system);
```

#### 3. Update Health Checks
```javascript
// Old - Basic health
const getHealth = async () => {
    const response = await fetch('/api/v1/health');
    return response.json();
};

// New - Comprehensive health
const getHealth = async () => {
    return apiRequest('/health');
};

// Handle enhanced health response:
const health = await getHealth();
console.log('Overall status:', health.status);
console.log('Component checks:', health.checks);
console.log('Resource metrics:', health.metrics);
```

#### 4. Update Memory Operations
```javascript
// Old
const createMemory = async (content, tags) => {
    const response = await fetch('/api/v1/memories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, tags })
    });
    return response.json();
};

// New - Enhanced with WebSocket broadcast
const ingestMemory = async (content, memoryType = 'semantic', tags = []) => {
    return apiRequest('/memories/ingest', {
        method: 'POST',
        body: JSON.stringify({
            content,
            memory_type: memoryType,
            tags
        })
    });
};

// WebSocket will automatically broadcast to all connected clients:
// {
//   "type": "memory_created",
//   "data": { "id": "...", "memory_type": "semantic", "tags": [...] }
// }
```

### Phase 4: WebSocket Integration

#### 1. Basic WebSocket Setup
```javascript
class SecondBrainWebSocket {
    constructor(apiKey) {
        this.apiKey = apiKey;
        this.ws = null;
        this.subscribers = new Map();
        this.connect();
    }

    connect() {
        // Note: WebSocket authentication happens at connection time
        this.ws = new WebSocket(`${WS_BASE_URL}/ws`);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.notifySubscribers('connected', { status: 'connected' });
        };

        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.notifySubscribers(message.type, message);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.notifySubscribers('disconnected', { status: 'disconnected' });
            // Implement reconnection logic
            setTimeout(() => this.connect(), 5000);
        };
    }

    subscribe(eventType, callback) {
        if (!this.subscribers.has(eventType)) {
            this.subscribers.set(eventType, []);
        }
        this.subscribers.get(eventType).push(callback);
    }

    notifySubscribers(eventType, data) {
        const callbacks = this.subscribers.get(eventType) || [];
        callbacks.forEach(callback => callback(data));
    }
}

// Usage
const ws = new SecondBrainWebSocket(API_KEY);

ws.subscribe('metrics_update', (message) => {
    updateDashboard(message.data);
});

ws.subscribe('memory_created', (message) => {
    showNotification(`New ${message.data.memory_type} memory created`);
});
```

#### 2. Replace Polling with WebSocket Events
```javascript
// Old - Polling approach
setInterval(async () => {
    try {
        const metrics = await getMetrics();
        updateUI(metrics);
    } catch (error) {
        console.error('Failed to fetch metrics:', error);
    }
}, 30000); // Poll every 30 seconds

// New - Event-driven approach
ws.subscribe('metrics_update', (message) => {
    updateUI(message.data);
    // Automatically receives updates every minute
});

ws.subscribe('connection', (message) => {
    // Receive initial metrics on connection
    if (message.status === 'connected') {
        console.log('Connected to real-time updates');
    }
});
```

### Phase 5: Error Handling Updates

#### 1. Standardized Error Responses
```javascript
// Old - Inconsistent error formats
try {
    const response = await fetch('/api/v1/metrics');
    const data = await response.json();
} catch (error) {
    // Various error formats
}

// New - Standardized error handling
try {
    const data = await apiRequest('/metrics');
} catch (error) {
    // All errors follow this format:
    // {
    //   "detail": "Error description",
    //   "status_code": 400,
    //   "timestamp": "2025-08-01T10:30:00Z",
    //   "path": "/api/v2/metrics"
    // }
    
    if (error.message.includes('Invalid API key')) {
        // Handle authentication error
        redirectToLogin();
    } else if (error.message.includes('Rate limit')) {
        // Handle rate limiting
        showRateLimitWarning();
    } else {
        // Handle general errors
        showErrorMessage(error.message);
    }
}
```

#### 2. WebSocket Error Handling
```javascript
ws.ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    showConnectionError('Real-time updates unavailable');
};

ws.ws.onclose = (event) => {
    if (event.code === 4001) {
        // Authentication error
        console.error('WebSocket authentication failed');
        showAuthError('Invalid credentials for real-time updates');
    } else if (event.code !== 1000) {
        // Unexpected close
        console.log('WebSocket closed unexpectedly, reconnecting...');
        setTimeout(() => this.connect(), 5000);
    }
};
```

### Phase 6: Testing Migration

#### 1. Parallel Testing
```javascript
// Test both APIs during migration
const testMigration = async () => {
    try {
        // Test V1 (existing)
        const v1Response = await fetch('/api/v1/metrics');
        const v1Data = await v1Response.json();

        // Test V2 (new)
        const v2Data = await apiRequest('/metrics');

        // Compare responses
        console.log('V1 memories:', v1Data.memories || 'N/A');
        console.log('V2 memories:', v2Data.memories);
        
        // Validate data consistency
        if (v1Data.memories && Math.abs(v1Data.memories - v2Data.memories) > 10) {
            console.warn('Large discrepancy in memory counts');
        }
    } catch (error) {
        console.error('Migration test failed:', error);
    }
};
```

#### 2. Feature Validation
```javascript
// Test all new features work correctly
const validateFeatures = async () => {
    console.log('Testing V2 API features...');

    // Test enhanced metrics
    const detailedMetrics = await apiRequest('/metrics/detailed');
    console.log('✓ Detailed metrics:', Object.keys(detailedMetrics));

    // Test enhanced health
    const health = await apiRequest('/health');
    console.log('✓ Health checks:', Object.keys(health.checks));

    // Test memory ingestion with WebSocket
    let memoryCreated = false;
    ws.subscribe('memory_created', () => {
        memoryCreated = true;
        console.log('✓ WebSocket memory broadcast received');
    });

    await ingestMemory('Test migration memory', 'semantic', ['test']);
    
    // Wait for WebSocket event
    setTimeout(() => {
        if (!memoryCreated) {
            console.warn('⚠ WebSocket broadcast not received');
        }
    }, 2000);

    console.log('Feature validation complete');
};
```

### Phase 7: User Interface Updates

#### 1. Update Dashboard Components
```jsx
// Old React component
const Dashboard = () => {
    const [metrics, setMetrics] = useState(null);
    
    useEffect(() => {
        const fetchData = async () => {
            const data = await fetch('/api/v1/dashboard/metrics').then(r => r.json());
            setMetrics(data);
        };
        
        fetchData();
        const interval = setInterval(fetchData, 30000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div>
            <h1>Memories: {metrics?.memories || 0}</h1>
        </div>
    );
};

// New React component with WebSocket
const Dashboard = () => {
    const [metrics, setMetrics] = useState(null);
    const [detailedMetrics, setDetailedMetrics] = useState(null);
    const [wsConnected, setWsConnected] = useState(false);

    useEffect(() => {
        // Initial data fetch
        const fetchInitialData = async () => {
            try {
                const [simple, detailed] = await Promise.all([
                    apiRequest('/metrics'),
                    apiRequest('/metrics/detailed')
                ]);
                setMetrics(simple);
                setDetailedMetrics(detailed);
            } catch (error) {
                console.error('Failed to fetch initial data:', error);
            }
        };

        fetchInitialData();

        // WebSocket connection
        const ws = new SecondBrainWebSocket(API_KEY);
        
        ws.subscribe('connected', () => setWsConnected(true));
        ws.subscribe('disconnected', () => setWsConnected(false));
        ws.subscribe('metrics_update', (message) => {
            setMetrics(message.data);
        });

        return () => ws.disconnect();
    }, []);

    return (
        <div>
            <div className={`status ${wsConnected ? 'connected' : 'disconnected'}`}>
                {wsConnected ? 'Live Updates' : 'Offline'}
            </div>
            <h1>Total Memories: {detailedMetrics?.memories.total || 0}</h1>
            <h2>Active Users: {metrics?.active_users || 0}</h2>
            <div>System Health: {metrics?.system_health || 'Unknown'}</div>
            
            {detailedMetrics && (
                <div className="performance-metrics">
                    <h3>Performance</h3>
                    <p>Response Time: {detailedMetrics.performance.api_response_time}</p>
                    <p>Memory Usage: {detailedMetrics.performance.memory_usage}</p>
                    <p>CPU Usage: {detailedMetrics.performance.cpu_usage}</p>
                </div>
            )}
        </div>
    );
};
```

#### 2. Add Real-Time Notifications
```jsx
const NotificationSystem = () => {
    const [notifications, setNotifications] = useState([]);

    useEffect(() => {
        const ws = new SecondBrainWebSocket(API_KEY);
        
        ws.subscribe('memory_created', (message) => {
            addNotification('success', 'Memory Created', 
                `New ${message.data.memory_type} memory added`);
        });

        ws.subscribe('health_change', (message) => {
            if (message.data.new_status !== 'healthy') {
                addNotification('warning', 'System Health Alert', 
                    `Status changed to ${message.data.new_status}`);
            }
        });

        ws.subscribe('system_error', (message) => {
            addNotification('error', 'System Error', message.data.message);
        });

        return () => ws.disconnect();
    }, []);

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
        }, 5000);
    };

    return (
        <div className="notifications">
            {notifications.map(notification => (
                <div key={notification.id} className={`notification ${notification.type}`}>
                    <strong>{notification.title}</strong>
                    <p>{notification.message}</p>
                </div>
            ))}
        </div>
    );
};
```

## Migration Checklist

### Pre-Migration
- [ ] Review current API usage patterns
- [ ] Identify all endpoints currently in use
- [ ] Set up API key authentication
- [ ] Update environment configuration
- [ ] Install required dependencies (WebSocket libraries)

### Core Migration
- [ ] Update authentication headers for all API calls
- [ ] Migrate `/metrics` endpoints (if using detailed metrics)
- [ ] Migrate `/health` endpoints
- [ ] Update memory ingestion endpoints
- [ ] Migrate TODO and git activity endpoints

### WebSocket Integration
- [ ] Implement WebSocket connection management
- [ ] Replace polling with event-driven updates
- [ ] Add real-time notification system
- [ ] Handle WebSocket connection errors and reconnection

### Testing & Validation
- [ ] Test all migrated endpoints
- [ ] Validate WebSocket functionality
- [ ] Compare data consistency between old and new APIs
- [ ] Test error handling scenarios
- [ ] Perform user acceptance testing

### Cleanup
- [ ] Remove old API calls
- [ ] Update documentation
- [ ] Remove unused dependencies
- [ ] Update deployment configurations

## Benefits of Migration

### 1. **Unified Architecture**
- Single API serving all frontend interfaces
- Consistent data structures across all endpoints
- Simplified maintenance and development

### 2. **Real-Time Capabilities**
- WebSocket support for live updates
- Automatic broadcasting of data changes
- Reduced server load (no more polling)

### 3. **Enhanced Performance**
- Optimized PostgreSQL queries
- Intelligent caching strategies
- Better resource utilization

### 4. **Improved Developer Experience**
- Comprehensive OpenAPI documentation
- Standardized error handling
- Better TypeScript support

### 5. **Future-Ready**
- Easy to extend with new features
- Scalable architecture
- Modern standards compliance

## Common Migration Issues & Solutions

### Authentication Errors
```javascript
// Issue: 401 Unauthorized
// Solution: Ensure API key is correctly formatted
const API_KEY = 'sk-your-actual-api-key-here'; // Must start with 'sk-'

// Issue: API key not being sent
// Solution: Check header format
headers: {
    'Authorization': `Bearer ${API_KEY}`, // Note: 'Bearer ' prefix required
    'Content-Type': 'application/json'
}
```

### WebSocket Connection Issues
```javascript
// Issue: WebSocket won't connect
// Solution: Check URL format and protocol
const wsUrl = 'ws://localhost:8000/api/v2/ws'; // Note: 'ws://' not 'http://'

// Issue: Connection drops frequently
// Solution: Implement proper reconnection logic
const reconnectWithBackoff = (attempt) => {
    const delay = Math.min(1000 * Math.pow(2, attempt), 30000);
    setTimeout(() => connect(), delay);
};
```

### Data Structure Changes
```javascript
// Issue: metrics.memories is undefined
// Old V1: response.memories
// New V2: response.memories (simple) or response.memories.total (detailed)

// Solution: Check which endpoint you're using
const simple = await apiRequest('/metrics');
console.log(simple.memories); // Direct value

const detailed = await apiRequest('/metrics/detailed');
console.log(detailed.memories.total); // Nested value
```

## Performance Considerations

### API Rate Limits
```javascript
// V2 API has rate limiting - implement proper retry logic
const apiRequestWithRetry = async (endpoint, options = {}, retries = 3) => {
    try {
        return await apiRequest(endpoint, options);
    } catch (error) {
        if (error.message.includes('Rate limit') && retries > 0) {
            const delay = Math.pow(2, 4 - retries) * 1000; // Exponential backoff
            await new Promise(resolve => setTimeout(resolve, delay));
            return apiRequestWithRetry(endpoint, options, retries - 1);
        }
        throw error;
    }
};
```

### WebSocket Message Throttling
```javascript
// Prevent WebSocket message flooding
class MessageThrottler {
    constructor(maxPerSecond = 10) {
        this.maxPerSecond = maxPerSecond;
        this.messageCount = 0;
        this.windowStart = Date.now();
    }

    canProcess() {
        const now = Date.now();
        if (now - this.windowStart >= 1000) {
            this.messageCount = 0;
            this.windowStart = now;
        }
        
        if (this.messageCount < this.maxPerSecond) {
            this.messageCount++;
            return true;
        }
        return false;
    }
}
```

## Migration Timeline & Phases

### Phase 1: Preparation (Week 1)
- [ ] Audit current API usage
- [ ] Set up development environment with V2 API
- [ ] Obtain and configure API keys
- [ ] Review documentation and examples

### Phase 2: Core Migration (Week 2-3)
- [ ] Migrate authentication
- [ ] Update primary endpoints (metrics, health)
- [ ] Implement basic WebSocket connection
- [ ] Update error handling

### Phase 3: Feature Enhancement (Week 4)
- [ ] Implement real-time updates
- [ ] Add notification system
- [ ] Enhance user interface with live data
- [ ] Performance optimization

### Phase 4: Testing & Deployment (Week 5)
- [ ] Comprehensive testing
- [ ] User acceptance testing
- [ ] Production deployment
- [ ] Monitor and resolve issues

### Phase 5: Cleanup (Week 6)
- [ ] Remove old API calls
- [ ] Clean up unused code
- [ ] Update documentation
- [ ] Team training on new features

## Support & Resources

### Documentation
- **API Specification**: `docs/API_V2_UNIFIED_SPECIFICATION.md`
- **WebSocket Events**: `docs/WEBSOCKET_EVENTS_SPECIFICATION.md`
- **Usage Examples**: `docs/API_USAGE_EXAMPLES.md`
- **OpenAPI Docs**: Available at `/docs` endpoint

### Development Tools
- **Postman Collection**: Available in repository
- **TypeScript Definitions**: Auto-generated from OpenAPI spec
- **Test Suite**: Complete test examples provided

### Getting Help
1. **Documentation First**: Check the comprehensive docs
2. **Example Code**: Review usage examples for your use case
3. **OpenAPI Explorer**: Use `/docs` endpoint for interactive testing
4. **Issue Tracking**: File GitHub issues for migration problems

### Migration Support Checklist
- [ ] API key configured and working
- [ ] All endpoints returning expected data
- [ ] WebSocket connection stable
- [ ] Error handling implemented
- [ ] Performance metrics acceptable
- [ ] User interface updated
- [ ] Team trained on new features

---

**Migration Success**: You'll know the migration is complete when all your applications are using the V2 API endpoints, receiving real-time updates via WebSocket, and taking advantage of the enhanced features like detailed metrics and comprehensive health monitoring.