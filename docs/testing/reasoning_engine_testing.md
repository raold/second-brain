# Reasoning Engine Testing Plan v2.6.0-reasoning

## Overview

The reasoning engine enables multi-hop traversal through memories to answer complex questions and discover insights. This document outlines the comprehensive testing strategy.

## Test Coverage

### 1. Core Functionality Tests

#### Query Parsing
- ✅ Parse natural language queries into structured format
- ✅ Detect reasoning types (causal, temporal, semantic, evolutionary, comparative)
- ✅ Handle optional parameters (max_hops, reasoning_type)
- ✅ Validate input parameters and lengths

#### Reasoning Type Detection
- ✅ Causal: "What caused X?" "Why did Y happen?"
- ✅ Temporal: "What happened before/after X?"
- ✅ Evolutionary: "How did X evolve?" "How has Y changed?"
- ✅ Comparative: "Compare X to Y" "What's the difference?"
- ✅ Semantic: Default fallback for general queries

#### Multi-hop Traversal
- ✅ Find starting nodes from query
- ✅ Execute beam search algorithm
- ✅ Traverse relationships up to max_hops
- ✅ Score and rank reasoning paths
- ✅ Extract insights from paths

### 2. Algorithm Tests

#### Beam Search
- ✅ Maintain beam_width candidates at each hop
- ✅ Prune low-scoring paths efficiently  
- ✅ Handle edge cases (no paths found, single node)
- ✅ Respect max_hops limits

#### Path Scoring
- ✅ Calculate relevance scores with decay
- ✅ Apply relationship type weights
- ✅ Consider memory importance scores
- ✅ Handle confidence thresholds

#### Insight Extraction
- ✅ Generate insights from reasoning paths
- ✅ Identify patterns and connections
- ✅ Provide contextual explanations
- ✅ Handle different reasoning types appropriately

### 3. Error Handling Tests

#### Input Validation
- ✅ Empty or null queries
- ✅ Queries too short (<3 characters)
- ✅ Invalid max_hops values
- ✅ Invalid reasoning types
- ✅ Malformed requests

#### Database Errors
- ✅ Database connection failures
- ✅ Query timeouts
- ✅ Memory not found errors
- ✅ Graceful degradation

#### Performance Limits
- ✅ Large result sets
- ✅ Complex queries with many hops
- ✅ Memory usage constraints
- ✅ Timeout handling

### 4. Integration Tests

#### Database Integration
- ✅ Memory retrieval and search
- ✅ Relationship traversal
- ✅ Contextual search functionality
- ✅ Performance with real data

#### API Integration
- ✅ Request/response validation
- ✅ Authentication handling
- ✅ Error response formats
- ✅ Concurrent request handling

## Test Execution

### Unit Tests
Location: `tests/test_reasoning_engine.py`

**Key Test Methods:**
- `test_parse_query` - Query parsing validation
- `test_detect_reasoning_type` - Type detection accuracy
- `test_multi_hop_query_integration` - End-to-end flow
- `test_find_causal_chains` - Causal relationship analysis
- `test_trace_reasoning_path` - Path finding between memories
- `test_error_handling` - Error scenarios
- `test_beam_search_pruning` - Algorithm efficiency

### API Tests
Location: `tests/test_reasoning_routes.py` (to be created)

**Endpoints to Test:**
- `POST /reasoning/query` - Multi-hop reasoning
- `POST /reasoning/trace` - Path tracing
- `POST /reasoning/causal` - Causal analysis

### Performance Tests
**Metrics to Measure:**
- Query response time (<2s for 3 hops)
- Memory usage (stable under load)
- Concurrent request handling (10+ simultaneous)
- Cache hit rates (>80% for repeated queries)

## Test Data Requirements

### Memory Corpus
- Minimum 100 test memories
- Variety of content types (personal, work, learning)
- Clear relationship chains
- Different importance levels
- Temporal spread (dates/times)

### Query Test Cases
- Simple causal queries: "What caused me to change jobs?"
- Complex evolutionary: "How did my programming skills develop?"
- Temporal sequences: "What happened after I learned Python?"
- Comparative analysis: "How do my work projects compare?"

## Success Criteria

### Functionality
- [ ] All unit tests pass (100%)
- [ ] API endpoints respond correctly
- [ ] Error handling works as expected
- [ ] Different reasoning types produce appropriate results

### Performance
- [ ] Average query time < 1.5 seconds
- [ ] Memory usage remains stable
- [ ] No memory leaks under sustained load
- [ ] Cache improves performance by >50%

### Quality
- [ ] Code coverage > 90%
- [ ] No critical security vulnerabilities
- [ ] Proper input validation
- [ ] Comprehensive error messages

## Known Limitations

1. **Cold Start Performance**: First queries may be slower due to cache warming
2. **Complex Queries**: Very abstract questions may not find clear paths
3. **Data Dependency**: Quality depends on memory relationships
4. **Language Support**: Currently optimized for English queries

## Testing Environment Setup

### Prerequisites
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Set environment variables
export TESTING_DATABASE_URL="postgresql://..."
export LOG_LEVEL="DEBUG"
```

### Run Tests
```bash
# Unit tests only
python -m pytest tests/test_reasoning_engine.py -v

# All reasoning tests
python -m pytest tests/ -k "reasoning" -v

# With coverage
python -m pytest tests/test_reasoning_engine.py --cov=app.services.reasoning_engine
```

### Test Database
- Use separate test database
- Populate with sample data
- Reset between test runs
- Mock external dependencies

## Next Steps

1. **Complete Integration Testing**: API endpoint validation
2. **Performance Benchmarking**: Load testing with realistic data
3. **User Acceptance Testing**: Real-world query validation
4. **Documentation**: Update API docs with test results

---

**Version**: 2.6.0-reasoning  
**Last Updated**: 2025-08-01  
**Status**: Feature Testing Phase