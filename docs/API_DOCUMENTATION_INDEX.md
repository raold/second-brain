# Second Brain V2 API Documentation Index

## Overview

This directory contains comprehensive documentation for the Second Brain V2 Unified API. The API provides real-time capabilities through WebSocket connections, complete system monitoring, and seamless integration with PostgreSQL data.

## Quick Start

1. **Get Started**: Read [API_V2_UNIFIED_SPECIFICATION.md](API_V2_UNIFIED_SPECIFICATION.md) for complete API overview
2. **See Examples**: Check [API_USAGE_EXAMPLES.md](API_USAGE_EXAMPLES.md) for practical implementation patterns
3. **Real-time Features**: Review [WEBSOCKET_EVENTS_SPECIFICATION.md](WEBSOCKET_EVENTS_SPECIFICATION.md) for WebSocket integration
4. **Migration**: Follow [V2_API_MIGRATION_GUIDE.md](V2_API_MIGRATION_GUIDE.md) to upgrade from older versions

## Core Documentation Files

### API Specifications

#### [API_V2_UNIFIED_SPECIFICATION.md](API_V2_UNIFIED_SPECIFICATION.md)
**Complete API reference and specifications**
- All endpoints with request/response examples
- Authentication methods and security
- Data models and type definitions
- Error handling and status codes
- Performance characteristics and rate limits

#### [openapi_v2_unified.yaml](openapi_v2_unified.yaml)
**OpenAPI 3.0 specification file**
- Machine-readable API specification
- Compatible with code generation tools
- Importable into Postman, Insomnia, etc.
- Supports automatic TypeScript generation

### Real-Time Communication

#### [WEBSOCKET_EVENTS_SPECIFICATION.md](WEBSOCKET_EVENTS_SPECIFICATION.md)
**Comprehensive WebSocket documentation**
- All WebSocket event types and formats
- Connection management and error handling
- Client implementation examples (React, Vue, Python, Node.js)
- Performance optimization patterns
- Security considerations

### Practical Implementation

#### [API_USAGE_EXAMPLES.md](API_USAGE_EXAMPLES.md)
**Detailed usage examples and patterns**
- Quick start code snippets
- Complete dashboard integration examples
- Memory management workflows
- Health monitoring implementations
- Error handling patterns
- Production deployment examples

### Migration Support

#### [V2_API_MIGRATION_GUIDE.md](V2_API_MIGRATION_GUIDE.md)
**Complete migration guide from older versions**
- Step-by-step migration phases
- Endpoint mapping and changes
- Breaking changes and compatibility
- Testing and validation strategies
- Common issues and solutions
- Timeline and support resources

## API Feature Overview

### Core Endpoints

| Category | Endpoint | Purpose | Documentation |
|----------|----------|---------|---------------|
| **Metrics** | `GET /api/v2/metrics` | Simple system metrics | [API Spec](API_V2_UNIFIED_SPECIFICATION.md#get-simple-metrics) |
| **Metrics** | `GET /api/v2/metrics/detailed` | Comprehensive metrics | [API Spec](API_V2_UNIFIED_SPECIFICATION.md#get-detailed-metrics) |
| **Health** | `GET /api/v2/health` | System health status | [API Spec](API_V2_UNIFIED_SPECIFICATION.md#get-health-status) |
| **Memory** | `POST /api/v2/memories/ingest` | Create new memory | [API Spec](API_V2_UNIFIED_SPECIFICATION.md#ingest-memory) |
| **Project** | `GET /api/v2/todos` | TODO management | [API Spec](API_V2_UNIFIED_SPECIFICATION.md#get-todos) |
| **Git** | `GET /api/v2/git/activity` | Repository activity | [API Spec](API_V2_UNIFIED_SPECIFICATION.md#get-git-activity) |

### Real-Time Features

| Feature | WebSocket Event | Purpose | Documentation |
|---------|-----------------|---------|---------------|
| **Connection** | `connection` | Connection established | [WebSocket Spec](WEBSOCKET_EVENTS_SPECIFICATION.md#connection-events) |
| **Heartbeat** | `heartbeat` | Connection health | [WebSocket Spec](WEBSOCKET_EVENTS_SPECIFICATION.md#connection-events) |
| **Metrics** | `metrics_update` | Live metric updates | [WebSocket Spec](WEBSOCKET_EVENTS_SPECIFICATION.md#system-metrics-events) |
| **Memory** | `memory_created` | New memory notifications | [WebSocket Spec](WEBSOCKET_EVENTS_SPECIFICATION.md#memory-events) |
| **Health** | `health_change` | System health alerts | [WebSocket Spec](WEBSOCKET_EVENTS_SPECIFICATION.md#system-metrics-events) |

## Integration Examples by Framework

### JavaScript/Browser
```javascript
// Quick setup example
const api = new SecondBrainAPI('your-api-key');

// Get metrics
const metrics = await api.getMetrics();

// WebSocket for real-time updates
const ws = api.connectWebSocket((message) => {
    console.log('Real-time update:', message.type);
});
```
**Full examples**: [API_USAGE_EXAMPLES.md#javascript-browser](API_USAGE_EXAMPLES.md#javascript-browser)

### React
```jsx
// Hook for WebSocket integration
const { connected, metrics, notifications } = useSecondBrainWebSocket();

return (
    <Dashboard 
        metrics={metrics} 
        isLive={connected}
        notifications={notifications}
    />
);
```
**Full examples**: [API_USAGE_EXAMPLES.md#complete-react-dashboard](API_USAGE_EXAMPLES.md#complete-react-dashboard)

### Python
```python
# Async API client
async with SecondBrainAPI('your-api-key') as api:
    metrics = await api.get_metrics()
    await api.ingest_memory("Python integration test")
    
    # WebSocket for real-time updates
    await api.connect_websocket(handle_message)
```
**Full examples**: [API_USAGE_EXAMPLES.md#python](API_USAGE_EXAMPLES.md#python)

### Node.js
```javascript
// Server-side integration
const api = new SecondBrainAPI('your-api-key');

// Create memory and broadcast to clients
const result = await api.ingestMemory(content, 'semantic', ['nodejs']);

// WebSocket for server-side real-time processing
const ws = api.connectWebSocket(processServerUpdate);
```
**Full examples**: [API_USAGE_EXAMPLES.md#node-js](API_USAGE_EXAMPLES.md#node-js)

## Authentication & Security

### API Key Setup
```javascript
// Environment variable (recommended)
const API_KEY = process.env.SECOND_BRAIN_API_KEY;

// Header authentication
const headers = {
    'Authorization': `Bearer ${API_KEY}`,
    'Content-Type': 'application/json'
};
```

### Rate Limiting
- **Default**: 1000 requests/hour per API key
- **Burst**: 60 requests/minute
- **WebSocket**: 1 connection per API key
- **Headers**: `X-RateLimit-*` headers included in responses

**Details**: [API_V2_UNIFIED_SPECIFICATION.md#rate-limiting](API_V2_UNIFIED_SPECIFICATION.md#rate-limiting)

## Data Models & Types

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
    memories: MemoryMetrics;
    performance: PerformanceMetrics;
    system: SystemMetrics;
    database: DatabaseMetrics;
    timestamp: string;
}
```

**Complete models**: [API_V2_UNIFIED_SPECIFICATION.md#data-models](API_V2_UNIFIED_SPECIFICATION.md#data-models)

## Error Handling

### Standard Error Response
```json
{
    "detail": "Error description",
    "status_code": 400,
    "timestamp": "2025-08-01T10:30:00Z",
    "path": "/api/v2/metrics"
}
```

### Common HTTP Status Codes
- `200 OK`: Success
- `400 Bad Request`: Invalid parameters
- `401 Unauthorized`: Invalid/missing API key
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

**Details**: [API_V2_UNIFIED_SPECIFICATION.md#error-handling](API_V2_UNIFIED_SPECIFICATION.md#error-handling)

## WebSocket Connection Management

### Basic Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v2/ws');

ws.onopen = () => console.log('Connected');
ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    handleWebSocketMessage(message);
};
```

### Advanced Connection with Reconnection
```javascript
class SecondBrainWebSocket {
    constructor() {
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.connect();
    }

    connect() {
        // Implementation with exponential backoff
    }
}
```

**Complete examples**: [WEBSOCKET_EVENTS_SPECIFICATION.md#advanced-websocket-client](WEBSOCKET_EVENTS_SPECIFICATION.md#advanced-websocket-client)

## Performance & Optimization

### Response Times
- **Simple Metrics**: < 50ms
- **Detailed Metrics**: < 200ms
- **Memory Ingestion**: < 100ms
- **Health Check**: < 25ms

### Throughput
- **Peak RPS**: 1000+
- **Sustained RPS**: 500+
- **WebSocket Messages**: 10,000+ per second

### Caching Strategy
- **Metrics**: 30-second cache
- **Git Activity**: 5-minute cache
- **TODO Parsing**: 1-minute cache
- **Health Status**: 10-second cache

**Details**: [API_V2_UNIFIED_SPECIFICATION.md#performance-characteristics](API_V2_UNIFIED_SPECIFICATION.md#performance-characteristics)

## Migration from V1

### Quick Migration Checklist
- [ ] Update base URL from `/api/v1` to `/api/v2`
- [ ] Add API key authentication
- [ ] Update response parsing for new data structures
- [ ] Implement WebSocket for real-time updates
- [ ] Test all functionality

### Common Migration Issues
1. **Authentication**: API key now required
2. **Data Structure**: Some metrics moved to nested objects
3. **WebSocket**: New real-time capabilities replace polling
4. **Error Format**: Standardized error responses

**Complete guide**: [V2_API_MIGRATION_GUIDE.md](V2_API_MIGRATION_GUIDE.md)

## Development Tools

### OpenAPI Documentation
- **Interactive Docs**: Available at `/docs` when server is running
- **Swagger UI**: Full API exploration and testing
- **Code Generation**: Use OpenAPI spec for client generation

### Testing Tools
- **Postman Collection**: Import [openapi_v2_unified.yaml](openapi_v2_unified.yaml)
- **cURL Examples**: Provided in all documentation
- **WebSocket Testing**: Examples for all major platforms

### Monitoring & Observability

#### Health Monitoring
```javascript
// Continuous health checks
const healthMonitor = new HealthMonitor('your-api-key');
healthMonitor.startMonitoring();

healthMonitor.onAlert((alert) => {
    console.log(`ALERT: ${alert.message}`);
});
```

#### Performance Monitoring
```javascript
// API response time tracking
const startTime = performance.now();
await api.getMetrics();
const responseTime = performance.now() - startTime;
```

**Complete examples**: [API_USAGE_EXAMPLES.md#monitoring--health-checks](API_USAGE_EXAMPLES.md#monitoring--health-checks)

## Support & Community

### Getting Help
1. **Documentation**: Start with this index and linked documents
2. **Examples**: Check usage examples for your specific use case
3. **Interactive Testing**: Use `/docs` endpoint for API exploration
4. **Issues**: File GitHub issues for bugs or feature requests

### Best Practices
- Use environment variables for API keys
- Implement proper error handling and retry logic
- Use WebSocket for real-time features instead of polling
- Monitor API rate limits and implement backoff strategies
- Cache responses appropriately to improve performance

### Contributing
- Documentation improvements welcome
- Example code contributions encouraged
- Bug reports and feature requests appreciated
- Follow the existing documentation patterns

## File Organization

```
docs/
├── API_DOCUMENTATION_INDEX.md          # This file - start here
├── API_V2_UNIFIED_SPECIFICATION.md     # Complete API reference
├── openapi_v2_unified.yaml            # OpenAPI specification
├── WEBSOCKET_EVENTS_SPECIFICATION.md   # WebSocket documentation
├── API_USAGE_EXAMPLES.md              # Practical examples
├── V2_API_MIGRATION_GUIDE.md          # Migration guide
└── [other documentation files]
```

## Version Information

- **Current Version**: V2.0.0
- **API Base URL**: `/api/v2`
- **WebSocket URL**: `/api/v2/ws`
- **Specification**: OpenAPI 3.0.3
- **Authentication**: Bearer token (API key)

---

**Need Help?** Start with the [API_V2_UNIFIED_SPECIFICATION.md](API_V2_UNIFIED_SPECIFICATION.md) for a complete overview, then check the [API_USAGE_EXAMPLES.md](API_USAGE_EXAMPLES.md) for practical implementation patterns in your preferred programming language.