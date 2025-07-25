# Intelligence Features Quick Start Guide

## Overview

The Intelligence features (v2.8.3) provide advanced analytics, predictive insights, anomaly detection, and knowledge gap analysis for your Second Brain. This guide will help you get started quickly.

## Key Features

### 1. Analytics Dashboard
- **10+ metric types** tracking system performance and knowledge growth
- **Time series analysis** with configurable granularity (minute to year)
- **Real-time metrics** including response times, usage patterns, and health scores
- **Export capabilities** to JSON and CSV formats

### 2. Predictive Insights
- **6 insight categories**: Performance, Knowledge, Behavior, System, Opportunity, Warning
- **Impact scoring** to prioritize important insights
- **Actionable recommendations** for each insight
- **Confidence ratings** to gauge reliability

### 3. Anomaly Detection
- **Multiple detection algorithms**: Statistical, Moving Average, Pattern Break, Frequency
- **5 anomaly types**: Spike, Drop, Pattern Break, Threshold Breach, Unusual Frequency
- **Severity scoring** to prioritize critical anomalies
- **Ensemble methods** combining multiple detectors for accuracy

### 4. Knowledge Gap Analysis
- **Topic coverage analysis** using LDA and TF-IDF
- **Relationship gap detection** finding isolated knowledge islands
- **Unanswered question identification**
- **Focus area tracking** for targeted learning

## Quick Start Examples

### 1. Generate Your First Analytics Dashboard

```bash
# Get a comprehensive analytics dashboard
curl -X POST http://localhost:8000/intelligence/analytics/dashboard \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "granularity": "hour",
    "include_insights": true,
    "include_anomalies": true,
    "include_knowledge_gaps": true
  }'
```

### 2. Get High-Priority Insights

```bash
# Get insights with high impact (>0.7) and confidence (>0.8)
curl -X GET "http://localhost:8000/intelligence/analytics/insights?min_impact=0.7&min_confidence=0.8" \
  -H "Authorization: Bearer your-token"
```

### 3. Check for Recent Anomalies

```bash
# Get anomalies from the last 24 hours
curl -X GET "http://localhost:8000/intelligence/analytics/anomalies?hours=24&min_severity=0.6" \
  -H "Authorization: Bearer your-token"
```

### 4. Analyze Knowledge Gaps

```bash
# Find gaps in your knowledge base
curl -X GET "http://localhost:8000/intelligence/analytics/knowledge-gaps?limit=10" \
  -H "Authorization: Bearer your-token"
```

## Understanding the Metrics

### Core Metrics Explained

1. **Memory Count & Growth**
   - Tracks total memories and growth rate
   - Helps identify knowledge acquisition patterns

2. **Query Performance**
   - Monitors search and retrieval speeds
   - Alerts on performance degradation

3. **Embedding Quality**
   - Measures vector embedding effectiveness
   - Impacts search accuracy

4. **Relationship Density**
   - Tracks knowledge graph connectivity
   - Higher density = better knowledge integration

5. **Knowledge Coverage**
   - Measures topic breadth
   - Identifies under-represented areas

6. **System Health**
   - Composite score of system performance
   - Includes CPU, memory, and database health

## Interpreting Insights

### Insight Categories

- **🔴 Warning**: Immediate attention needed
- **🟡 Opportunity**: Growth or optimization potential
- **🔵 System**: Infrastructure-related insights
- **🟢 Performance**: Speed and efficiency insights
- **🧠 Knowledge**: Content and learning insights
- **👤 Behavior**: Usage pattern insights

### Impact Scores

- **0.9-1.0**: Critical - Address immediately
- **0.7-0.8**: High - Address within days
- **0.5-0.6**: Medium - Address within weeks
- **<0.5**: Low - Nice to have improvements

## Setting Up Alerts

### Configure Metric Thresholds

```bash
# Set alert for slow queries (>500ms)
curl -X POST http://localhost:8000/intelligence/analytics/thresholds \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "metric_type": "query_performance",
    "max_value": 500.0,
    "alert_on_breach": true,
    "breach_duration_minutes": 5
  }'
```

## Best Practices

### 1. Regular Monitoring
- Check dashboard daily for system health
- Review insights weekly for optimization opportunities
- Investigate anomalies as they occur

### 2. Knowledge Gap Management
- Run gap analysis monthly
- Focus on high-importance gaps first
- Use suggested queries to fill gaps

### 3. Performance Optimization
- Monitor query performance trends
- Address performance insights promptly
- Export metrics for long-term analysis

### 4. Proactive Maintenance
- Set thresholds for critical metrics
- Act on predictive insights before issues occur
- Keep system health score above 0.8

## Advanced Usage

### Custom Time Ranges

```bash
# Analyze specific date range
curl -X POST http://localhost:8000/intelligence/analytics/dashboard \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-01-01T00:00:00Z",
    "end_date": "2025-01-29T00:00:00Z",
    "granularity": "day",
    "metrics": ["memory_growth", "knowledge_coverage"]
  }'
```

### Focus Area Analysis

```bash
# Check gaps in specific topics
curl -X GET "http://localhost:8000/intelligence/analytics/knowledge-gaps?focus_areas=machine%20learning&focus_areas=python" \
  -H "Authorization: Bearer your-token"
```

### Export for External Analysis

```bash
# Export to CSV for Excel/Sheets
curl -X GET "http://localhost:8000/intelligence/analytics/export?format=csv" \
  -H "Authorization: Bearer your-token" \
  -o analytics_export.csv
```

## Troubleshooting

### Common Issues

1. **No insights generated**
   - Ensure you have sufficient data (>100 memories)
   - Check time range includes recent activity

2. **High false positive anomalies**
   - Adjust sensitivity in anomaly detection
   - Review threshold configurations

3. **Incomplete knowledge gaps**
   - Ensure memories have descriptive titles
   - Add tags to improve topic detection

### Performance Tips

- Use caching for frequently accessed dashboards
- Limit metric selection to needed ones
- Use appropriate time granularity
- Refresh cache after major data changes

## Next Steps

1. **Set up regular monitoring** - Create scripts to check key metrics
2. **Integrate with workflows** - Use insights to guide learning
3. **Automate responses** - Build tools that act on insights
4. **Share dashboards** - Export and share analytics with team

For detailed API documentation, see [Intelligence API Documentation](./api/intelligence_api.md).