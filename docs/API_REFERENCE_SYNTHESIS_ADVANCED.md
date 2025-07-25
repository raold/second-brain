# Advanced Synthesis API Reference

## Overview

The Advanced Synthesis API provides sophisticated memory synthesis, knowledge graph visualization, workflow automation, and export/import capabilities.

Base URL: `/synthesis/advanced`

## Authentication

All endpoints require API key authentication:
```
X-API-Key: your-api-key
```

## Endpoints

### Memory Synthesis

#### POST /synthesize
Synthesize memories using advanced strategies.

**Request Body:**
```json
{
  "memory_ids": ["uuid1", "uuid2"],  // Optional: specific memories
  "strategy": "hierarchical",         // Required: synthesis strategy
  "parameters": {                     // Optional: strategy-specific params
    "max_depth": 3,
    "min_cluster_size": 2
  },
  "filters": {                        // Optional: memory filters
    "tags": ["important"],
    "min_importance": 7,
    "date_range": {
      "start": "2024-01-01T00:00:00Z",
      "end": "2024-12-31T23:59:59Z"
    }
  },
  "user_id": "user123"               // Optional: auto-filled from auth
}
```

**Strategies:**
- `hierarchical`: Multi-level abstractions
- `temporal`: Timeline-based synthesis
- `semantic`: Meaning-based grouping
- `causal`: Cause-effect relationships
- `comparative`: Compare and contrast
- `abstractive`: High-level insights

**Response:**
```json
[
  {
    "id": "synth-uuid",
    "source_memory_ids": ["uuid1", "uuid2"],
    "synthesis_type": "hierarchical",
    "content": "Synthesized insight...",
    "confidence_score": 0.85,
    "metadata": {
      "depth": 2,
      "cluster_count": 3
    },
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

#### GET /strategies
List available synthesis strategies.

**Response:**
```json
["hierarchical", "temporal", "semantic", "causal", "comparative", "abstractive"]
```

### Knowledge Graph Visualization

#### POST /graph/generate
Generate an interactive knowledge graph.

**Request Body:**
```json
{
  "layout": "force_directed",        // Required: layout algorithm
  "max_nodes": 100,                  // Optional: node limit (default: 100)
  "include_orphans": false,          // Optional: include unconnected nodes
  "filters": {                       // Optional: node filters
    "tags": ["core"],
    "types": ["semantic", "episodic"],
    "min_importance": 5
  },
  "time_range": {                    // Optional: temporal filter
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-12-31T23:59:59Z"
  },
  "cluster_by": "community",         // Optional: clustering method
  "node_size_by": "importance",      // Optional: size metric
  "edge_weight_by": "strength",      // Optional: edge metric
  "color_scheme": "type"             // Optional: color scheme
}
```

**Layouts:**
- `force_directed`: Physics simulation
- `hierarchical`: Tree structure
- `circular`: Circle arrangement
- `radial`: Central focus
- `timeline`: Temporal sequence
- `clustered`: Community groups

**Color Schemes:**
- `default`: By memory type
- `importance`: Gradient by importance
- `type`: By memory type
- `age`: By creation date
- `cluster`: By cluster membership

**Response:**
```json
{
  "nodes": [
    {
      "id": "node1",
      "label": "Memory Title",
      "type": "memory",
      "x": 150.5,
      "y": 200.3,
      "size": 1.5,
      "color": "#4ECDC4",
      "icon": "🧠",
      "properties": {
        "importance": 8,
        "memory_type": "semantic",
        "created_at": "2024-01-15T10:00:00Z"
      }
    }
  ],
  "edges": [
    {
      "source": "node1",
      "target": "node2",
      "type": "semantic",
      "weight": 0.85,
      "style": "solid",
      "properties": {
        "strength": 0.85
      }
    }
  ],
  "metadata": {
    "layout": "force_directed",
    "node_count": 50,
    "edge_count": 75,
    "density": 0.03,
    "clusters": 5
  }
}
```

#### GET /graph/layouts
List available graph layouts.

**Response:**
```json
["force_directed", "hierarchical", "circular", "radial", "timeline", "clustered"]
```

### Workflow Automation

#### POST /workflows
Create an automated workflow.

**Request Body:**
```json
{
  "name": "Daily Synthesis",
  "description": "Daily memory synthesis and report",
  "trigger": "schedule",
  "schedule": "0 9 * * *",           // Cron expression (for schedule trigger)
  "actions": [
    {
      "action": "synthesize",
      "parameters": {
        "strategy": "temporal",
        "time_window": "24h"
      },
      "condition": "step_0_result.count > 5",  // Optional: conditional execution
      "retry_on_failure": true
    },
    {
      "action": "generate_report",
      "parameters": {
        "report_type": "daily_summary",
        "include_visualizations": true
      }
    }
  ],
  "enabled": true,
  "max_retries": 3
}
```

**Triggers:**
- `schedule`: Cron-based scheduling
- `event`: System events
- `threshold`: Metric thresholds
- `manual`: Manual only
- `chain`: Other workflows

**Actions:**
- `synthesize`: Memory synthesis
- `analyze`: Generate analytics
- `export`: Export knowledge
- `notify`: Send notifications
- `archive`: Archive old memories
- `consolidate`: Merge similar memories
- `generate_report`: Create reports
- `update_graph`: Update knowledge graph

**Response:**
```json
{
  "id": "workflow-uuid",
  "name": "Daily Synthesis",
  "trigger": "schedule",
  "schedule": "0 9 * * *",
  "next_run": "2024-01-16T09:00:00Z",
  "last_run": null,
  "enabled": true,
  "created_at": "2024-01-15T10:00:00Z"
}
```

#### GET /workflows
List workflows.

**Query Parameters:**
- `enabled_only`: Boolean - only return enabled workflows

**Response:**
```json
[
  {
    "id": "workflow-uuid",
    "name": "Daily Synthesis",
    "trigger": "schedule",
    "enabled": true,
    "next_run": "2024-01-16T09:00:00Z"
  }
]
```

#### POST /workflows/{workflow_id}/execute
Manually execute a workflow.

**Request Body:**
```json
{
  "context": {                       // Optional: execution context
    "custom_param": "value"
  }
}
```

**Response:**
```json
{
  "id": "execution-uuid",
  "workflow_id": "workflow-uuid",
  "status": "running",
  "started_at": "2024-01-15T10:30:00Z",
  "current_step": 0,
  "actions_completed": 0
}
```

#### GET /workflows/executions
List workflow executions.

**Query Parameters:**
- `workflow_id`: Filter by workflow
- `status`: Filter by status (pending, running, completed, failed)
- `limit`: Maximum results (default: 100)

### Export/Import

#### POST /export
Export knowledge base to various formats.

**Request Body:**
```json
{
  "format": "obsidian",              // Required: export format
  "memory_ids": ["uuid1", "uuid2"],  // Optional: specific memories
  "filters": {                       // Optional: memory filters
    "tags": ["project"],
    "importance_threshold": 7,
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-12-31"
    }
  },
  "include_metadata": true,          // Optional: include metadata
  "include_relationships": true,     // Optional: include relationships
  "format_options": {                // Optional: format-specific options
    "use_folders": true,
    "sort_by": "date"
  }
}
```

**Formats:**
- `markdown`: Human-readable markdown
- `json`: Structured JSON
- `csv`: Tabular format
- `obsidian`: Obsidian vault
- `roam`: Roam Research
- `anki`: Anki flashcards
- `graphml`: Graph format
- `pdf`: PDF document

**Response (JSON/text formats):**
```json
{
  "format": "json",
  "content": "{...}",
  "memory_count": 150,
  "relationship_count": 200,
  "file_size_bytes": 45678,
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Response (binary formats):**
Binary stream with appropriate content-type header.

#### POST /import
Import knowledge from external sources.

**Request Body:**
```json
{
  "format": "json",                  // Required: import format
  "source": "{...}",                 // Required: source content
  "merge_strategy": "append",        // Optional: merge strategy
  "detect_duplicates": true,         // Optional: duplicate detection
  "default_tags": ["imported"],      // Optional: tags to add
  "field_mapping": {                 // Optional: field mapping
    "title": "name",
    "content": "description"
  }
}
```

**Merge Strategies:**
- `append`: Add all as new
- `replace`: Replace existing
- `merge`: Merge with existing

**Response:**
```json
{
  "total_items": 50,
  "imported_count": 45,
  "skipped_count": 5,
  "error_count": 0,
  "imported_memory_ids": ["uuid1", "uuid2", ...],
  "errors": [],
  "duration_seconds": 2.5
}
```

#### POST /import/file
Import from uploaded file.

**Form Data:**
- `file`: File upload
- `format`: Export format
- `merge_strategy`: Merge strategy
- `detect_duplicates`: Boolean

### Utility Endpoints

#### GET /workflow/actions
List available workflow actions.

#### GET /workflow/triggers
List available workflow triggers.

#### GET /export/formats
List available export formats.

#### POST /scheduler/start
Start the workflow scheduler.

#### POST /scheduler/stop
Stop the workflow scheduler.

## Error Responses

All endpoints return standard error responses:

```json
{
  "error": {
    "code": 400,
    "message": "Invalid synthesis strategy",
    "type": "ValidationError",
    "timestamp": "2024-01-15T10:30:00Z",
    "path": "/synthesis/advanced/synthesize",
    "method": "POST"
  }
}
```

## Rate Limiting

- 100 requests per minute for synthesis operations
- 50 requests per minute for graph generation
- 200 requests per minute for other operations

## Best Practices

1. **Synthesis**: Use appropriate strategies for your use case
2. **Graphs**: Limit nodes for better performance
3. **Workflows**: Test thoroughly before enabling schedules
4. **Export**: Use filters to reduce data size
5. **Import**: Always enable duplicate detection