# Second Brain API Specification v2.8.2

## Synthesis API Endpoints

This document provides detailed specifications for the v2.8.2 "Synthesis" feature endpoints.

### Table of Contents

1. [Consolidation API](#consolidation-api)
2. [Summarization API](#summarization-api)
3. [Suggestions API](#suggestions-api)
4. [Metrics API](#metrics-api)
5. [Cache API](#cache-api)

---

## Consolidation API

### Find Consolidation Candidates

Find memories that are candidates for consolidation based on similarity.

**Endpoint:** `GET /api/synthesis/consolidation/candidates`

**Query Parameters:**
- `similarity_threshold` (float, optional): Minimum similarity score (0.0-1.0). Default: 0.85
- `time_window_days` (int, optional): Look for memories within this time window. Default: 30
- `max_candidates` (int, optional): Maximum number of candidate groups. Default: 10
- `min_group_size` (int, optional): Minimum memories per group. Default: 2
- `max_group_size` (int, optional): Maximum memories per group. Default: 10

**Response:**
```json
{
  "candidates": [
    {
      "id": "cand_123",
      "memory_ids": ["mem_1", "mem_2", "mem_3"],
      "similarity_score": 0.92,
      "common_topics": ["machine learning", "neural networks"],
      "common_entities": ["TensorFlow", "PyTorch"],
      "time_span": "P5D",
      "suggested_strategy": "merge_similar",
      "confidence_score": 0.88,
      "preview_available": true
    }
  ],
  "total_candidates": 3,
  "analysis_time_ms": 245
}
```

### Preview Consolidation

Preview the result of consolidating memories before execution.

**Endpoint:** `POST /api/synthesis/consolidation/preview`

**Request Body:**
```json
{
  "memory_ids": ["mem_1", "mem_2", "mem_3"],
  "strategy": "merge_similar",
  "custom_title": "Machine Learning Overview",
  "preserve_originals": true
}
```

**Response:**
```json
{
  "preview_id": "prev_123",
  "proposed_title": "Machine Learning Overview",
  "proposed_content": "Consolidated content...",
  "strategy": "merge_similar",
  "key_insights": [
    "Neural networks are fundamental to deep learning",
    "Supervised learning requires labeled data"
  ],
  "preserved_details": {
    "mem_1": ["specific implementation detail"],
    "mem_2": ["unique observation"]
  },
  "estimated_quality_score": 0.92,
  "information_retention": 0.95,
  "warnings": []
}
```

### Execute Consolidation

Consolidate multiple memories into a single, comprehensive memory.

**Endpoint:** `POST /api/synthesis/consolidate`

**Request Body:**
```json
{
  "memory_ids": ["mem_1", "mem_2"],
  "strategy": "topic_based",
  "preserve_originals": true,
  "custom_title": "Complete ML Guide",
  "custom_content": null,
  "metadata": {
    "reason": "duplicate content",
    "tags": ["ml", "ai"]
  }
}
```

**Response:**
```json
{
  "id": "cons_123",
  "new_memory_id": "mem_999",
  "source_memory_ids": ["mem_1", "mem_2"],
  "title": "Complete ML Guide",
  "content": "Consolidated memory content...",
  "strategy": "topic_based",
  "quality_assessment": {
    "information_retention": 0.94,
    "coherence_score": 0.91,
    "semantic_accuracy": 0.96,
    "overall_score": 0.937,
    "warnings": []
  },
  "preserved_originals": true,
  "consolidation_metadata": {
    "key_insights": ["insight1", "insight2"],
    "preserved_details": {},
    "processing_time_ms": 2341
  },
  "created_at": "2025-01-22T10:30:00Z"
}
```

### Undo Consolidation

Revert a consolidation operation.

**Endpoint:** `POST /api/synthesis/consolidation/{consolidation_id}/undo`

**Response:**
```json
{
  "success": true,
  "restored_memory_ids": ["mem_1", "mem_2"],
  "deleted_consolidated_id": "mem_999",
  "message": "Consolidation successfully undone"
}
```

### Get Consolidation History

Retrieve consolidation history for the user.

**Endpoint:** `GET /api/synthesis/consolidation/history`

**Query Parameters:**
- `limit` (int, optional): Maximum results. Default: 20
- `offset` (int, optional): Pagination offset. Default: 0

**Response:**
```json
{
  "consolidations": [
    {
      "id": "cons_123",
      "title": "Machine Learning Overview",
      "source_count": 3,
      "strategy": "merge_similar",
      "quality_score": 0.92,
      "created_at": "2025-01-22T10:30:00Z",
      "can_undo": true
    }
  ],
  "total": 15,
  "limit": 20,
  "offset": 0
}
```

---

## Summarization API

### Generate Topic Summary

Generate an AI-powered summary for a specific topic.

**Endpoint:** `POST /api/synthesis/summarize/topic`

**Request Body:**
```json
{
  "topic": "machine learning",
  "max_memories": 50,
  "min_importance": 0.5,
  "include_graph": true,
  "language": "en",
  "style": "professional"
}
```

**Response:**
```json
{
  "topic": "machine learning",
  "summary": "Machine learning is a subset of artificial intelligence...",
  "key_insights": [
    "Supervised learning uses labeled data",
    "Deep learning models can learn hierarchical features",
    "Transfer learning accelerates model development"
  ],
  "related_entities": [
    {"name": "TensorFlow", "type": "framework", "relevance": 0.9},
    {"name": "neural networks", "type": "concept", "relevance": 0.95}
  ],
  "related_topics": ["deep learning", "artificial intelligence", "data science"],
  "memory_count": 23,
  "time_range": {
    "start": "2024-12-01T00:00:00Z",
    "end": "2025-01-22T23:59:59Z"
  },
  "confidence_score": 0.88,
  "word_count": 342,
  "generated_at": "2025-01-22T10:35:00Z",
  "metadata": {
    "model": "gpt-4-turbo-preview",
    "generation_time_ms": 3456
  }
}
```

### Generate Period Summary

Generate a summary for a specific time period.

**Endpoint:** `POST /api/synthesis/summarize/period`

**Request Body:**
```json
{
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "period_type": "monthly",
  "include_metrics": true,
  "focus_areas": ["learning", "projects"]
}
```

**Response:**
```json
{
  "start_date": "2025-01-01T00:00:00Z",
  "end_date": "2025-01-31T23:59:59Z",
  "period_type": "monthly",
  "summary": "January was a productive month focused on deep learning...",
  "highlights": [
    "Completed neural network implementation",
    "Studied transformer architectures",
    "Built image classification project"
  ],
  "new_topics": ["transformers", "attention mechanisms", "vision models"],
  "new_entities": ["BERT", "GPT-4", "ViT"],
  "top_memories": [
    {
      "id": "mem_123",
      "title": "Transformer Architecture Study",
      "importance": 0.9,
      "created_at": "2025-01-15T14:30:00Z"
    }
  ],
  "statistics": {
    "total_memories": 145,
    "average_importance": 0.72,
    "most_active_day": "2025-01-15",
    "memory_types": {
      "semantic": 89,
      "episodic": 45,
      "procedural": 11
    }
  },
  "trends": [
    {
      "trend": "Increasing focus on deep learning",
      "strength": 0.8,
      "evidence": ["23 deep learning memories", "5 related projects"]
    }
  ],
  "generated_at": "2025-01-22T10:40:00Z"
}
```

### Generate Executive Summary

Generate a high-level executive summary with actionable insights.

**Endpoint:** `POST /api/synthesis/summarize/executive`

**Request Body:**
```json
{
  "memory_ids": ["mem_1", "mem_2", "mem_3"],
  "include_graph": true,
  "style": "professional",
  "focus_areas": ["implementation", "theory", "applications"],
  "include_metrics": true
}
```

**Response:**
```json
{
  "title": "Machine Learning Knowledge Overview",
  "summary": "This executive summary covers your machine learning knowledge base...",
  "key_points": [
    "Strong foundation in neural network architectures",
    "Practical experience with TensorFlow and PyTorch",
    "Growing expertise in transformer models"
  ],
  "action_items": [
    "Explore advanced optimization techniques",
    "Implement attention mechanisms in current project",
    "Study recent papers on vision transformers"
  ],
  "questions_raised": [
    "How do vision transformers compare to CNNs?",
    "What are the latest advances in few-shot learning?"
  ],
  "opportunities": [
    "Apply transformer models to current projects",
    "Contribute to open-source ML libraries"
  ],
  "risks": [
    "Need to stay updated with rapid advances",
    "Potential knowledge gaps in reinforcement learning"
  ],
  "memory_ids": ["mem_1", "mem_2", "mem_3"],
  "graph_visualization": {
    "nodes": [
      {"id": "1", "label": "Neural Networks", "importance": 0.9},
      {"id": "2", "label": "Transformers", "importance": 0.85}
    ],
    "edges": [
      {"source": "1", "target": "2", "weight": 0.7}
    ]
  },
  "metrics": {
    "total_memories": 3,
    "average_importance": 0.83,
    "knowledge_density": 0.75,
    "topic_diversity": 0.6
  },
  "confidence_score": 0.87,
  "generated_at": "2025-01-22T10:45:00Z",
  "generation_time_ms": 4532
}
```

---

## Suggestions API

### Get Smart Suggestions

Get intelligent suggestions based on current context.

**Endpoint:** `POST /api/synthesis/suggestions`

**Request Body:**
```json
{
  "max_suggestions": 10,
  "suggestion_types": ["related_memory", "follow_up_question"],
  "context": {
    "current_memory_id": "mem_123",
    "recent_memory_ids": ["mem_120", "mem_121"],
    "current_topics": ["machine learning", "neural networks"],
    "current_entities": ["TensorFlow", "PyTorch"],
    "user_goals": ["master deep learning", "build AI projects"],
    "time_of_day": "morning",
    "activity_level": "high"
  }
}
```

**Response:**
```json
{
  "suggestions": [
    {
      "id": "sug_001",
      "type": "related_memory",
      "title": "Related: Advanced Neural Network Techniques",
      "description": "This memory covers advanced optimization methods",
      "reason": "High similarity to current memory (0.89)",
      "confidence": 0.85,
      "priority": 0.9,
      "action_url": "/memories/mem_456",
      "action_text": "View Memory",
      "metadata": {
        "memory_id": "mem_456",
        "relevance_score": 0.89,
        "common_topics": ["neural networks", "optimization"]
      }
    },
    {
      "id": "sug_002",
      "type": "follow_up_question",
      "title": "Explore Further",
      "description": "How do attention mechanisms improve transformer performance?",
      "reason": "Natural progression from current topic",
      "confidence": 0.8,
      "priority": 0.75,
      "metadata": {
        "question": "How do attention mechanisms improve transformer performance?",
        "expected_answer_type": "exploratory",
        "related_topics": ["transformers", "attention"]
      }
    }
  ],
  "context": {
    "current_memory_id": "mem_123",
    "time_of_day": "morning",
    "activity_level": "high"
  },
  "total_available": 15,
  "generation_time_ms": 234,
  "algorithm_version": "1.0.0",
  "filtering_applied": ["relevance_ranking", "diversity_filtering"]
}
```

### Dismiss Suggestion

Dismiss a suggestion and provide optional feedback.

**Endpoint:** `POST /api/synthesis/suggestions/{suggestion_id}/dismiss`

**Request Body:**
```json
{
  "reason": "not_relevant",
  "feedback": "This suggestion is about a different topic"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Suggestion dismissed and feedback recorded"
}
```

---

## Metrics API

### Get Current Metrics

Get real-time graph metrics.

**Endpoint:** `GET /api/synthesis/metrics/current`

**Query Parameters:**
- `graph_id` (string, optional): Graph identifier. Default: "main"
- `use_cache` (boolean, optional): Use cached metrics. Default: true

**Response:**
```json
{
  "graph_id": "main",
  "timestamp": "2025-01-22T10:50:00Z",
  "node_count": 1523,
  "edge_count": 3847,
  "density": 0.0033,
  "average_degree": 5.05,
  "clustering_coefficient": 0.342,
  "connected_components": 3,
  "largest_component_size": 1498,
  "diameter": 12,
  "average_path_length": 4.32,
  "degree_centrality": {
    "mem_123": 0.0234,
    "mem_456": 0.0198
  },
  "betweenness_centrality": {
    "mem_789": 0.0567,
    "mem_012": 0.0423
  },
  "growth_rate_nodes_per_day": 12.3,
  "growth_rate_edges_per_day": 28.7,
  "new_nodes_last_hour": 3,
  "new_edges_last_hour": 7,
  "calculation_time_ms": 156,
  "cache_hit": true
}
```

### Get Metrics Dashboard

Get comprehensive metrics dashboard with trends and insights.

**Endpoint:** `GET /api/synthesis/metrics/dashboard`

**Query Parameters:**
- `days` (int, optional): Time range in days. Default: 7
- `graph_id` (string, optional): Graph identifier. Default: "main"

**Response:**
```json
{
  "current_metrics": { /* current metrics object */ },
  "historical_metrics": [ /* array of historical metrics */ ],
  "trends": {
    "node_count": {
      "metric_name": "node_count",
      "trend_direction": "increasing",
      "trend_strength": 0.82,
      "average_value": 1450,
      "forecast_next_value": 1535,
      "confidence_interval": [1510, 1560]
    }
  },
  "active_anomalies": [
    {
      "id": "anom_123",
      "metric_name": "growth_rate_nodes_per_day",
      "anomaly_type": "spike",
      "severity": "medium",
      "current_value": 45.2,
      "expected_value": 12.3,
      "deviation_percentage": 267.5,
      "description": "Unusual spike in daily node creation",
      "suggested_investigation": [
        "Check for bulk import operations",
        "Review recent user activity"
      ]
    }
  ],
  "insights": [
    "Your knowledge graph is growing rapidly (12.3 nodes/day)",
    "High clustering indicates well-organized knowledge domains",
    "Consider creating more connections between isolated clusters"
  ],
  "recommendations": [
    "Use memory consolidation to merge similar memories",
    "Review 23 isolated memories and connect them to main graph",
    "Enable caching to improve dashboard performance"
  ],
  "predictions": {
    "node_count": {
      "next_value": 1535,
      "confidence": 0.75,
      "timeframe": "next_day"
    }
  },
  "summary": {
    "total_knowledge_items": 1523,
    "total_connections": 3847,
    "knowledge_density": "0.33%",
    "largest_topic_cluster": 234,
    "active_anomalies": 1
  },
  "time_range_days": 7,
  "generated_at": "2025-01-22T10:55:00Z",
  "generation_time_ms": 423
}
```

### Create Metrics Snapshot

Create a snapshot of current metrics for later comparison.

**Endpoint:** `POST /api/synthesis/metrics/snapshot`

**Request Body:**
```json
{
  "name": "Weekly Review Snapshot",
  "description": "End of week metrics snapshot for analysis",
  "tags": ["weekly", "review", "january"]
}
```

**Response:**
```json
{
  "id": "snap_123",
  "name": "Weekly Review Snapshot",
  "description": "End of week metrics snapshot for analysis",
  "metrics": { /* full metrics object */ },
  "notable_nodes": [
    {
      "id": "mem_123",
      "title": "Core ML Concepts",
      "metric": "degree_centrality",
      "value": 0.0234,
      "description": "Highly connected memory"
    }
  ],
  "notable_communities": [
    {
      "id": "community_0",
      "size": 234,
      "representative_node": "mem_456",
      "representative_title": "Neural Networks",
      "description": "Knowledge cluster with 234 memories"
    }
  ],
  "tags": ["weekly", "review", "january"],
  "created_at": "2025-01-22T11:00:00Z",
  "created_by": "user_123"
}
```

### Configure Alerts

Set up alerts for metric thresholds.

**Endpoint:** `POST /api/synthesis/metrics/alerts`

**Request Body:**
```json
{
  "name": "High Growth Alert",
  "metric_name": "growth_rate_nodes_per_day",
  "condition": "greater_than",
  "threshold": 50,
  "time_window_minutes": 60,
  "enabled": true,
  "notification_channels": ["email", "dashboard"]
}
```

**Response:**
```json
{
  "id": "alert_123",
  "name": "High Growth Alert",
  "metric_name": "growth_rate_nodes_per_day",
  "condition": "greater_than",
  "threshold": 50,
  "enabled": true,
  "created_at": "2025-01-22T11:05:00Z"
}
```

---

## Cache API

### Get Cache Statistics

Get Redis cache performance statistics.

**Endpoint:** `GET /api/synthesis/cache/stats`

**Response:**
```json
{
  "connected": true,
  "used_memory": "45.3 MB",
  "total_keys": 1234,
  "hits": 98765,
  "misses": 12345,
  "hit_rate": 88.9,
  "evicted_keys": 234,
  "expired_keys": 567,
  "cache_uptime_seconds": 345600
}
```

### Clear User Cache

Clear all cached data for a specific user.

**Endpoint:** `DELETE /api/synthesis/cache/user/{user_id}`

**Response:**
```json
{
  "success": true,
  "keys_deleted": 45,
  "message": "User cache successfully cleared"
}
```

### Warm Cache

Pre-warm cache with commonly accessed data.

**Endpoint:** `POST /api/synthesis/cache/warm`

**Request Body:**
```json
{
  "target": "metrics",
  "graph_ids": ["main", "archive"]
}
```

**Response:**
```json
{
  "success": true,
  "items_cached": 12,
  "time_taken_ms": 234,
  "message": "Cache successfully warmed"
}
```

---

## Error Responses

All endpoints may return these error responses:

### 400 Bad Request
```json
{
  "error": "Invalid request",
  "details": "Memory IDs must be an array of valid UUIDs"
}
```

### 401 Unauthorized
```json
{
  "error": "Authentication required",
  "details": "Please provide a valid API key"
}
```

### 404 Not Found
```json
{
  "error": "Resource not found",
  "details": "Memory with ID mem_123 does not exist"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "similarity_threshold"],
      "msg": "ensure this value is less than or equal to 1",
      "type": "value_error.number.not_le"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "details": "An unexpected error occurred. Please try again later."
}
```

---

## Rate Limiting

All synthesis endpoints are subject to rate limiting:

- **Consolidation operations**: 100 per hour
- **Summary generation**: 50 per hour (uses OpenAI API)
- **Suggestion requests**: 1000 per hour
- **Metrics queries**: 2000 per hour
- **Cache operations**: 500 per hour

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp when limit resets

---

## Webhooks

Configure webhooks to receive notifications:

### Consolidation Complete
```json
{
  "event": "consolidation.complete",
  "consolidation_id": "cons_123",
  "user_id": "user_123",
  "memory_count": 3,
  "quality_score": 0.92,
  "timestamp": "2025-01-22T11:10:00Z"
}
```

### Anomaly Detected
```json
{
  "event": "metrics.anomaly",
  "anomaly_id": "anom_123",
  "metric_name": "growth_rate",
  "severity": "high",
  "current_value": 89.2,
  "expected_value": 12.3,
  "timestamp": "2025-01-22T11:15:00Z"
}
```

### Summary Generated
```json
{
  "event": "summary.generated",
  "summary_type": "executive",
  "user_id": "user_123",
  "memory_count": 45,
  "confidence_score": 0.88,
  "timestamp": "2025-01-22T11:20:00Z"
}
```