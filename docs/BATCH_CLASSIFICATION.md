# Batch Classification System

The Second Brain batch classification system provides powerful tools for automatically categorizing and organizing memories at scale.

## Overview

The batch classification engine supports multiple classification methods that can be used individually or combined for optimal results:

- **Keyword-based**: Matches specific keywords to categories
- **Pattern-based**: Uses regex patterns for content analysis
- **Rules-based**: Applies custom business logic
- **Hybrid**: Combines multiple methods with weighted scoring
- **Auto**: Intelligently selects the best method per memory

## Classification Methods

### 1. Keyword Classification
Categorizes memories based on keyword presence.

```json
{
  "method": "keyword",
  "keywords": {
    "work": ["meeting", "project", "deadline"],
    "personal": ["family", "vacation", "hobby"],
    "learning": ["study", "course", "tutorial"]
  }
}
```

### 2. Pattern Classification
Uses regex patterns for advanced content matching.

```json
{
  "method": "pattern",
  "confidence_threshold": 0.8
}
```

Default patterns include:
- **Technical**: Code snippets, programming languages
- **Communication**: Emails, mentions (@user)
- **Documentation**: Headers, structured documents
- **Tasks**: TODOs, checkboxes

### 3. Rules-Based Classification
Applies custom rules with complex conditions.

```json
{
  "method": "rules_based",
  "custom_rules": [
    {
      "name": "urgent_task",
      "condition": "lambda m: 'urgent' in m.get('content', '').lower() and '!' in m.get('content', '')",
      "category": "high_priority",
      "confidence": 0.95
    }
  ]
}
```

### 4. Hybrid Classification
Combines multiple methods with configurable weights.

```json
{
  "method": "hybrid",
  "confidence_threshold": 0.7
}
```

Weights:
- Keyword: 30%
- Pattern: 30%
- Rules: 40%

## API Usage

### Classify Memories

```bash
curl -X POST "http://localhost:8000/bulk/classify" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "method": "hybrid",
      "auto_apply_results": true,
      "confidence_threshold": 0.8,
      "batch_size": 100
    },
    "filter_criteria": {
      "memory_type": "note",
      "created_after": "2024-01-01"
    }
  }'
```

### Response Format

```json
{
  "classified_count": 150,
  "failed_count": 2,
  "processed_memories": 152,
  "performance_metrics": {
    "processing_time": 3.45,
    "memories_per_second": 44.06,
    "success_rate": 0.987,
    "average_confidence": 0.84
  },
  "classification_results": [
    {
      "memory_id": "mem_123",
      "original_category": "general",
      "new_category": "work",
      "confidence": 0.92,
      "method_used": "hybrid",
      "tags_added": ["professional", "career"]
    }
  ]
}
```

## Configuration Options

### ClassificationConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| method | enum | AUTO | Classification method to use |
| auto_apply_results | bool | false | Automatically apply classifications |
| confidence_threshold | float | 0.7 | Minimum confidence to accept |
| batch_size | int | 100 | Memories per batch |
| parallel_workers | int | 4 | Concurrent processing threads |
| custom_rules | list | null | Custom classification rules |
| keywords | dict | null | Category keyword mappings |

### Filter Criteria

Filter memories before classification:

```json
{
  "memory_type": "note",
  "content_contains": "project",
  "created_after": "2024-01-01",
  "created_before": "2024-12-31",
  "min_length": 50,
  "max_length": 5000
}
```

## Bulk Operations Integration

The classification system integrates seamlessly with other bulk operations:

### 1. Import and Classify
```bash
# Import CSV and auto-classify
curl -X POST "http://localhost:8000/bulk/import" \
  -F "file=@memories.csv" \
  -F "format_type=csv" \
  -F 'options={"auto_classify":true,"classification_method":"hybrid"}'
```

### 2. Export by Category
```bash
# Export only "work" memories
curl -X POST "http://localhost:8000/bulk/export" \
  -d '{
    "format_type": "json",
    "filter_criteria": {"category": "work"}
  }'
```

### 3. Reclassify After Import
```bash
# Reclassify recently imported memories
curl -X POST "http://localhost:8000/bulk/classify" \
  -d '{
    "filter_criteria": {"source": "bulk_import"},
    "config": {"method": "auto"}
  }'
```

## Performance Optimization

### Batch Processing
- Optimal batch size: 100-500 memories
- Larger batches for keyword/pattern methods
- Smaller batches for complex rules

### Parallel Processing
```json
{
  "parallel_workers": 8,  // For multi-core systems
  "batch_size": 200
}
```

### Caching
The engine caches classification results for repeated content:
- Cache hit rate visible in statistics
- Clear cache endpoint available

## Custom Categories

Define custom categories and keywords:

```python
{
  "keywords": {
    "research": ["paper", "study", "analysis", "hypothesis"],
    "creative": ["design", "art", "sketch", "inspiration"],
    "health": ["workout", "nutrition", "doctor", "wellness"],
    "finance": ["budget", "investment", "expense", "savings"]
  }
}
```

## Statistics and Monitoring

### Get Classification Statistics
```bash
curl -X GET "http://localhost:8000/bulk/classify/statistics" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

Response:
```json
{
  "total_classified": 10234,
  "total_failed": 45,
  "cache_hits": 2341,
  "cache_misses": 7893,
  "processing_time_avg": 0.23
}
```

### Clear Cache
```bash
curl -X POST "http://localhost:8000/bulk/classify/cache/clear" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## Best Practices

### 1. Method Selection
- **Keyword**: Best for well-defined categories
- **Pattern**: Technical content, structured data
- **Rules**: Complex business logic
- **Hybrid**: General-purpose, balanced approach

### 2. Confidence Thresholds
- 0.9+: High precision, fewer classifications
- 0.7-0.9: Balanced (recommended)
- 0.5-0.7: High recall, more classifications

### 3. Performance Tips
- Process similar content together
- Use appropriate batch sizes
- Monitor cache effectiveness
- Clear cache periodically

### 4. Category Design
- Keep categories mutually exclusive
- Use descriptive keywords
- Test patterns on sample data
- Iterate based on results

## Troubleshooting

### Low Classification Rate
- Lower confidence threshold
- Add more keywords/patterns
- Use hybrid method
- Check filter criteria

### Poor Accuracy
- Review classification results
- Adjust method weights
- Refine keywords/patterns
- Add custom rules

### Performance Issues
- Reduce batch size
- Increase parallel workers
- Use simpler methods
- Enable caching

## Advanced Usage

### Custom Classification Method
```python
from app.batch_classification_engine import FileParser

class SentimentClassifier:
    def classify(self, content: str) -> tuple[str, float]:
        # Custom sentiment analysis
        sentiment = analyze_sentiment(content)
        return sentiment.category, sentiment.confidence
```

### Webhook Integration
Configure webhooks for classification events:
```json
{
  "webhook_url": "https://your-app.com/classification-complete",
  "events": ["classification_complete", "batch_processed"]
}
```

## Migration Guide

### From Manual to Automatic
1. Export current categories
2. Analyze keyword patterns
3. Create classification config
4. Run on test batch
5. Apply to all memories

### Category Consolidation
1. Identify similar categories
2. Create mapping rules
3. Run reclassification
4. Verify results
5. Clean up old categories