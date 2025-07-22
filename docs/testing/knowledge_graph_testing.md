# Knowledge Graph Builder Testing Plan v2.6.1-knowledge-graph

## Overview

The knowledge graph builder extracts entities and relationships from memories to create visual, interactive knowledge representations. This document outlines the comprehensive testing strategy.

## Test Coverage

### 1. Entity Extraction Tests

#### Pattern-Based Extraction
- ✅ Person names: "John Smith", "Dr. Jane Doe"
- ✅ Organizations: "OpenAI", "MIT", "Google"
- ✅ Technologies: "Python", "TensorFlow", "React"
- ✅ Locations: "San Francisco", "New York City"
- ✅ Concepts: "machine learning", "artificial intelligence"
- ✅ Skills: "programming", "data analysis"
- ✅ Events: "graduation", "conference", "meeting"

#### Confidence Scoring
- ✅ High confidence for clear patterns (titles, known entities)
- ✅ Medium confidence for contextual matches
- ✅ Low confidence for ambiguous terms
- ✅ Threshold filtering (min_confidence parameter)

#### Entity Deduplication
- ✅ Case-insensitive matching ("Python" == "python")
- ✅ Partial matching and aliases
- ✅ Keep highest confidence version
- ✅ Handle different entity types with same name

### 2. Relationship Detection Tests

#### Relationship Types
- ✅ CAUSED_BY: "A caused B", "B resulted from A"
- ✅ LEADS_TO: "A leads to B", "A resulted in B"
- ✅ PART_OF: "A is part of B", "B contains A"
- ✅ SIMILAR_TO: "A is similar to B", "A and B are alike"
- ✅ DEPENDS_ON: "A depends on B", "A requires B"
- ✅ TEMPORAL_BEFORE/AFTER: "A happened before B"
- ✅ LEARNED_FROM: "learned from", "studied under"

#### Pattern Recognition
- ✅ Context-based relationship detection
- ✅ Distance-based entity relationships
- ✅ Co-occurrence analysis
- ✅ TF-IDF similarity calculations

#### Memory Relationships
- ✅ Cross-memory entity connections
- ✅ Temporal relationship analysis
- ✅ Content similarity relationships
- ✅ Tag-based connections

### 3. Graph Building Tests

#### Graph Construction
- ✅ Node creation from entities
- ✅ Edge creation from relationships
- ✅ Weight calculation and normalization
- ✅ Graph metadata generation

#### Graph Analytics
- ✅ Density calculation
- ✅ Connected components analysis
- ✅ Degree distribution
- ✅ Hub identification
- ✅ Clustering coefficient

#### Performance Tests
- ✅ Large memory sets (100+ memories)
- ✅ Complex entity networks
- ✅ Memory usage optimization
- ✅ Build time performance

### 4. Database Integration Tests

#### Entity Storage
- ✅ Entity table operations
- ✅ Entity mention tracking
- ✅ Duplicate prevention
- ✅ Batch operations

#### Relationship Storage
- ✅ Relationship persistence
- ✅ Weight updates
- ✅ Bidirectional relationships
- ✅ Cleanup operations

#### Graph Metadata
- ✅ Statistics storage
- ✅ Build timestamps
- ✅ Version tracking
- ✅ Performance metrics

### 5. Error Handling Tests

#### Input Validation
- ✅ Empty memory lists
- ✅ Invalid memory IDs
- ✅ Malformed content
- ✅ Large input handling

#### Database Errors
- ✅ Connection failures
- ✅ Query timeouts
- ✅ Constraint violations
- ✅ Transaction rollbacks

#### Memory Constraints
- ✅ Large graph handling
- ✅ Out-of-memory scenarios
- ✅ Processing limits
- ✅ Graceful degradation

## Test Execution

### Unit Tests
Location: `tests/test_knowledge_graph_builder.py`

**Key Test Methods:**
- `test_extract_entities` - Entity extraction accuracy
- `test_deduplicate_entities` - Deduplication logic
- `test_detect_relationships` - Relationship detection
- `test_calculate_tfidf_similarity` - Similarity calculations
- `test_build_graph_from_memories` - End-to-end building
- `test_incremental_update` - Graph updates
- `test_analyze_graph_structure` - Analytics
- `test_error_handling` - Error scenarios

### Integration Tests
**Database Operations:**
- Entity CRUD operations
- Relationship management
- Transaction handling
- Performance with real data

### Performance Tests
**Benchmarks:**
- Entity extraction: 1000 entities/second
- Graph building: 500 memories in <5 seconds
- Memory usage: Stable under 1GB for 10K entities
- Database queries: <100ms for graph retrieval

## Test Data Requirements

### Memory Corpus
- **Size**: 200+ test memories minimum
- **Variety**: Technical, personal, academic content
- **Entities**: Clear named entities and concepts
- **Relationships**: Obvious connections and patterns
- **Languages**: English optimized, multilingual awareness

### Entity Test Cases
- **People**: "Dr. Sarah Johnson", "CEO Mark Davis"
- **Organizations**: "Stanford University", "Microsoft Corporation"
- **Technologies**: "Python 3.9", "Docker containers"
- **Locations**: "Silicon Valley", "Cambridge, MA"
- **Events**: "WWDC 2024", "team standup meeting"

### Relationship Test Cases
- **Causal**: "The bug caused the system to crash"
- **Temporal**: "After learning Python, I started Django"
- **Hierarchical**: "React is part of the JavaScript ecosystem"
- **Similarity**: "TensorFlow is similar to PyTorch"

## Success Criteria

### Functionality
- [ ] All unit tests pass (100%)
- [ ] Entity extraction accuracy >85%
- [ ] Relationship detection accuracy >75%
- [ ] Graph building completes successfully
- [ ] Database operations work correctly

### Performance
- [ ] Entity extraction: >500 entities/second
- [ ] Graph building: <10 seconds for 1000 memories
- [ ] Memory usage: Stable and predictable
- [ ] Database queries: <200ms average

### Quality
- [ ] Code coverage >90%
- [ ] No memory leaks
- [ ] Proper error handling
- [ ] Clean database transactions

## Database Schema Testing

### Tables Created
```sql
-- Entities table
CREATE TABLE entities (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    confidence DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Entity mentions table
CREATE TABLE entity_mentions (
    id UUID PRIMARY KEY,
    entity_id UUID REFERENCES entities(id),
    memory_id UUID NOT NULL,
    position_start INTEGER,
    position_end INTEGER,
    confidence DECIMAL(3,2)
);

-- Entity relationships table
CREATE TABLE entity_relationships (
    id UUID PRIMARY KEY,
    source_entity_id UUID REFERENCES entities(id),
    target_entity_id UUID REFERENCES entities(id),
    relationship_type VARCHAR(50) NOT NULL,
    weight DECIMAL(5,4),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Migration Testing
- [ ] Schema creation successful
- [ ] Indexes created properly
- [ ] Constraints working
- [ ] Data migration (if applicable)

## Testing Environment Setup

### Prerequisites
```bash
# Install additional dependencies
pip install scikit-learn  # For TF-IDF calculations
pip install networkx      # For graph analysis (optional)

# Database setup
export POSTGRES_URL="postgresql://test_user:pass@localhost/test_kb_graph"
```

### Run Tests
```bash
# Unit tests only
python -m pytest tests/test_knowledge_graph_builder.py -v

# All knowledge graph tests
python -m pytest tests/ -k "knowledge_graph" -v

# With coverage
python -m pytest tests/test_knowledge_graph_builder.py --cov=app.services.knowledge_graph_builder

# Database migration test
python scripts/run_knowledge_graph_migration.py --test-mode
```

### Test Database Setup
```sql
-- Create test database
CREATE DATABASE test_knowledge_graph;

-- Run migration
\i migrations/add_knowledge_graph_tables.sql

-- Add test data
INSERT INTO memories (id, content) VALUES 
('mem1', 'John Smith works at Google developing AI systems'),
('mem2', 'Google AI published a paper on transformer architecture');
```

## Known Limitations

1. **Language Support**: Optimized for English, limited multilingual support
2. **Entity Ambiguity**: Common names may be ambiguous without context
3. **Relationship Complexity**: Simple patterns may miss complex relationships
4. **Scalability**: Performance degrades with very large graphs (>50K entities)

## Quality Assurance

### Code Review Checklist
- [ ] Input validation comprehensive
- [ ] Error handling appropriate
- [ ] Database transactions safe
- [ ] Memory usage reasonable
- [ ] Performance acceptable
- [ ] Tests cover edge cases

### Security Considerations
- [ ] SQL injection prevention
- [ ] Input sanitization
- [ ] Access control (if applicable)
- [ ] Data privacy compliance

## Next Steps

1. **Enhanced Entity Recognition**: NLP models for better accuracy
2. **Relationship Sophistication**: ML-based relationship detection
3. **Real-time Updates**: Incremental graph maintenance
4. **Visualization Integration**: D3.js graph rendering tests

---

**Version**: 2.6.1-knowledge-graph  
**Last Updated**: 2025-08-01  
**Status**: Feature Testing Phase  
**Dependencies**: scikit-learn, PostgreSQL with UUID support