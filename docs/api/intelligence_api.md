# Intelligence API Documentation

## Overview

The Intelligence API provides advanced analytics, predictive insights, anomaly detection, and knowledge gap analysis capabilities for the Second Brain system. These features are part of v2.8.3 "Intelligence" release.

## Base URL

```
/intelligence
```

## Authentication

All endpoints require authentication via Bearer token:

```
Authorization: Bearer <your-token>
```

## Endpoints

### Analytics Dashboard

#### Generate Analytics Dashboard

```http
POST /intelligence/analytics/dashboard
```

Generate a comprehensive analytics dashboard with metrics, insights, and anomalies.

**Request Body:**
```json
{
  "metrics": ["memory_count", "query_performance", "api_usage"],
  "granularity": "hour",
  "start_date": "2025-01-01T00:00:00Z",
  "end_date": "2025-01-29T00:00:00Z",
  "include_insights": true,
  "include_anomalies": true,
  "include_knowledge_gaps": true,
  "user_id": "optional-user-id"
}
```

**Response:**
```json
{
  "metrics": {
    "memory_count": {
      "metric_type": "memory_count",
      "data_points": [...],
      "trend": "increasing",
      "average": 1234.5
    }
  },
  "anomalies": [...],
  "insights": [...],
  "knowledge_gaps": [...],
  "total_memories": 12456,
  "active_users": 42,
  "system_health_score": 0.85,
  "generated_at": "2025-01-29T12:00:00Z"
}
```

#### List Available Metrics

```http
GET /intelligence/analytics/metrics
```

Get a list of all available metric types.

**Response:**
```json
[
  "memory_count",
  "memory_growth",
  "query_performance",
  "embedding_quality",
  "relationship_density",
  "knowledge_coverage",
  "review_completion",
  "retention_rate",
  "api_usage",
  "system_health"
]
```

### Predictive Insights

#### Get Predictive Insights

```http
GET /intelligence/analytics/insights
```

Retrieve predictive insights based on current metrics.

**Query Parameters:**
- `category` (optional): Filter by category (performance, knowledge, behavior, system, opportunity, warning)
- `min_confidence` (optional): Minimum confidence score (0.0-1.0, default: 0.5)
- `min_impact` (optional): Minimum impact score (0.0-1.0, default: 0.5)
- `limit` (optional): Maximum number of insights (1-50, default: 10)

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "category": "performance",
    "title": "Query Performance Degradation",
    "description": "Query response times have increased by 45.2% over the past 24 hours.",
    "confidence": 0.85,
    "impact_score": 0.8,
    "timeframe": "next 48 hours",
    "recommendations": [
      "Consider optimizing database indexes",
      "Review and optimize complex queries"
    ],
    "supporting_metrics": ["query_performance"],
    "created_at": "2025-01-29T12:00:00Z"
  }
]
```

### Anomaly Detection

#### Get Detected Anomalies

```http
GET /intelligence/analytics/anomalies
```

Retrieve detected anomalies in metrics.

**Query Parameters:**
- `metric_type` (optional): Filter by metric type
- `anomaly_type` (optional): Filter by anomaly type (spike, drop, pattern_break, threshold_breach, unusual_frequency)
- `min_severity` (optional): Minimum severity (0.0-1.0, default: 0.5)
- `hours` (optional): Time window in hours (1-168, default: 24)

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "metric_type": "api_usage",
    "anomaly_type": "spike",
    "timestamp": "2025-01-29T10:30:00Z",
    "severity": 0.8,
    "expected_value": 100.0,
    "actual_value": 500.0,
    "confidence": 0.9,
    "description": "Value deviates 4.2 standard deviations from mean",
    "metadata": {
      "z_score": 4.2,
      "method": "z_score"
    }
  }
]
```

### Knowledge Gap Analysis

#### Analyze Knowledge Gaps

```http
GET /intelligence/analytics/knowledge-gaps
```

Analyze and identify gaps in the knowledge base.

**Query Parameters:**
- `limit` (optional): Maximum number of gaps (1-50, default: 20)
- `focus_areas` (optional): List of focus areas to check

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "topic": "Machine Learning Fundamentals",
    "related_concepts": ["neural networks", "backpropagation", "gradient descent"],
    "gap_score": 0.8,
    "importance_score": 0.9,
    "suggested_queries": [
      "What is backpropagation?",
      "How do neural networks learn?"
    ],
    "potential_sources": [
      "Academic papers",
      "Online courses",
      "Documentation"
    ],
    "identified_at": "2025-01-29T12:00:00Z"
  }
]
```

### Performance Benchmarks

#### Get Performance Benchmarks

```http
GET /intelligence/analytics/benchmarks
```

Retrieve current performance benchmarks.

**Response:**
```json
[
  {
    "operation": "memory_search",
    "p50_ms": 45.2,
    "p90_ms": 89.5,
    "p99_ms": 234.1,
    "throughput_per_second": 156.7,
    "error_rate": 0.002,
    "measured_at": "2025-01-29T12:00:00Z"
  }
]
```

### Metric Thresholds

#### Set Metric Threshold

```http
POST /intelligence/analytics/thresholds
```

Configure alerting threshold for a metric.

**Request Body:**
```json
{
  "metric_type": "query_performance",
  "min_value": null,
  "max_value": 1000.0,
  "alert_on_breach": true,
  "breach_duration_minutes": 5
}
```

**Response:**
```json
{
  "success": true,
  "message": "Threshold configured successfully"
}
```

#### Get Metric Thresholds

```http
GET /intelligence/analytics/thresholds
```

Retrieve all configured metric thresholds.

**Response:**
```json
[
  {
    "metric_type": "query_performance",
    "min_value": null,
    "max_value": 1000.0,
    "alert_on_breach": true,
    "breach_duration_minutes": 5
  }
]
```

### Export

#### Export Analytics Data

```http
GET /intelligence/analytics/export
```

Export analytics data in various formats.

**Query Parameters:**
- `format`: Export format (json, csv)
- `start_date` (optional): Start date for export
- `end_date` (optional): End date for export

**Response (JSON):**
```json
{
  "metrics": {...},
  "insights": [...],
  "anomalies": [...],
  "knowledge_gaps": [...]
}
```

**Response (CSV):**
```json
{
  "content": "Metric,Timestamp,Value,Trend,Average\n...",
  "media_type": "text/csv",
  "filename": "analytics_20250129_120000.csv"
}
```

### Cache Management

#### Refresh Analytics Cache

```http
POST /intelligence/analytics/refresh
```

Force refresh of the analytics cache.

**Response:**
```json
{
  "success": true,
  "message": "Analytics cache cleared successfully"
}
```

## Data Models

### MetricType
- `memory_count`: Total number of memories
- `memory_growth`: Growth rate of memories
- `query_performance`: Query response times
- `embedding_quality`: Quality of vector embeddings
- `relationship_density`: Density of knowledge graph
- `knowledge_coverage`: Topic coverage percentage
- `review_completion`: Spaced repetition completion rate
- `retention_rate`: Memory retention rate
- `api_usage`: API request volume
- `system_health`: Overall system health score

### TimeGranularity
- `minute`: Minute-level aggregation
- `hour`: Hourly aggregation
- `day`: Daily aggregation
- `week`: Weekly aggregation
- `month`: Monthly aggregation
- `quarter`: Quarterly aggregation
- `year`: Yearly aggregation

### InsightCategory
- `performance`: Performance-related insights
- `knowledge`: Knowledge base insights
- `behavior`: User behavior insights
- `system`: System health insights
- `opportunity`: Growth opportunities
- `warning`: Warning alerts

### AnomalyType
- `spike`: Sudden increase in value
- `drop`: Sudden decrease in value
- `pattern_break`: Break in regular pattern
- `threshold_breach`: Value exceeds threshold
- `unusual_frequency`: Abnormal event frequency

## Examples

### Example: Generate Weekly Analytics Report

```bash
curl -X POST http://localhost:8000/intelligence/analytics/dashboard \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "granularity": "day",
    "start_date": "2025-01-22T00:00:00Z",
    "end_date": "2025-01-29T00:00:00Z",
    "include_insights": true,
    "include_anomalies": true
  }'
```

### Example: Get High-Impact Insights

```bash
curl -X GET "http://localhost:8000/intelligence/analytics/insights?min_impact=0.8&limit=5" \
  -H "Authorization: Bearer your-token"
```

### Example: Detect API Usage Anomalies

```bash
curl -X GET "http://localhost:8000/intelligence/analytics/anomalies?metric_type=api_usage&hours=48" \
  -H "Authorization: Bearer your-token"
```

### Example: Analyze Knowledge Gaps in ML Topics

```bash
curl -X GET "http://localhost:8000/intelligence/analytics/knowledge-gaps?focus_areas=machine%20learning&focus_areas=deep%20learning" \
  -H "Authorization: Bearer your-token"
```

## Error Handling

All endpoints follow standard HTTP status codes:

- `200 OK`: Success
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Missing or invalid authentication
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

Error responses include a detail message:

```json
{
  "detail": "Error description"
}
```