# Cognitive Memory Architecture Specification
**Second Brain v2.3.0 "Cognitive" - Memory Type Implementation**

## 📋 **Overview**

The Cognitive Memory Architecture represents a strategic evolution from simple vector storage to sophisticated memory type classification, mimicking human cognitive memory systems. This implementation introduces three distinct memory types with specialized retrieval and aging mechanisms.

## 🧠 **Memory Type Classification**

### **1. Semantic Memory**
**Definition**: Facts, concepts, and general knowledge independent of personal experience
**Characteristics**:
- **Timeless**: No specific temporal context
- **Objective**: Factual information
- **Stable**: Low decay rate
- **Interconnected**: Strong semantic relationships

**Examples**:
```json
{
  "content": "PostgreSQL pgvector extension enables efficient vector similarity search",
  "memory_type": "semantic",
  "metadata": {
    "category": "technology",
    "domain": "database",
    "confidence": 0.95,
    "verified": true
  }
}
```

### **2. Episodic Memory**
**Definition**: Time-bound experiences and contextual events
**Characteristics**:
- **Temporal**: Tied to specific time/context
- **Subjective**: Personal experience-based
- **Decay-prone**: Higher forgetting curve
- **Context-rich**: Environmental details

**Examples**:
```json
{
  "content": "Fixed critical CI/CD pipeline issue on July 17, 2025 - Python path configuration",
  "memory_type": "episodic",
  "metadata": {
    "timestamp": "2025-07-17T16:30:00Z",
    "context": "debugging_session",
    "location": "development_environment",
    "outcome": "resolved",
    "emotional_valence": "relief"
  }
}
```

### **3. Procedural Memory**
**Definition**: Process knowledge, workflows, and skill-based instructions
**Characteristics**:
- **Action-oriented**: How-to knowledge
- **Sequential**: Step-by-step processes
- **Reinforced**: Strengthened through repetition
- **Skill-based**: Competency development

**Examples**:
```json
{
  "content": "CI/CD Pipeline Fix Process: 1) Identify missing dependencies 2) Update requirements.txt 3) Fix linting violations 4) Test locally 5) Commit and push",
  "memory_type": "procedural",
  "metadata": {
    "skill_level": "expert",
    "complexity": "medium",
    "success_rate": 0.98,
    "steps": 5,
    "domain": "devops"
  }
}
```

## 🔍 **Advanced Search with Contextual Retrieval**

### **Multi-Dimensional Search Matrix**

| Dimension | Weight | Algorithm | Purpose |
|-----------|--------|-----------|---------|
| **Vector Similarity** | 40% | Cosine similarity | Semantic matching |
| **Memory Type** | 25% | Classification filter | Cognitive relevance |
| **Temporal Context** | 20% | Recency + decay | Time-aware retrieval |
| **Importance Score** | 15% | Consolidation weight | Priority-based ranking |

### **Contextual Retrieval Algorithm**
```python
def contextual_search(query, context=None):
    """
    Advanced search combining multiple cognitive dimensions
    """
    # Base vector similarity
    vector_matches = semantic_search(query)
    
    # Memory type filtering
    if context.get('memory_type'):
        filtered_matches = filter_by_memory_type(vector_matches, context['memory_type'])
    
    # Temporal context weighting
    temporal_weights = calculate_temporal_relevance(filtered_matches, context.get('timeframe'))
    
    # Importance consolidation
    importance_scores = get_consolidation_weights(filtered_matches)
    
    # Combined scoring
    final_scores = combine_scores(
        vector_similarity=vector_matches.scores,
        temporal_relevance=temporal_weights,
        importance=importance_scores,
        weights=[0.4, 0.2, 0.15]
    )
    
    return rank_by_score(filtered_matches, final_scores)
```

## ⏰ **Memory Consolidation and Intelligent Aging**

### **Consolidation Algorithm**

**Memory Importance Scoring**:
```python
importance_score = (
    access_frequency * 0.3 +
    recency_weight * 0.2 +
    semantic_connections * 0.2 +
    user_feedback * 0.15 +
    cross_references * 0.15
)
```

**Memory Type-Specific Decay Models**:

1. **Semantic Memory**: Exponential decay with reinforcement
   ```python
   semantic_strength = initial_strength * e^(-decay_rate * time) + reinforcement_factor
   ```

2. **Episodic Memory**: Power law decay (Ebbinghaus forgetting curve)
   ```python
   episodic_strength = initial_strength * (time + 1)^(-decay_exponent)
   ```

3. **Procedural Memory**: Skill-based retention with practice reinforcement
   ```python
   procedural_strength = base_strength + practice_count * skill_multiplier * e^(-forgetting_rate * time)
   ```

### **Intelligent Aging Process**

**Daily Consolidation Cycle**:
1. **Importance Evaluation** - Score all memories accessed in last 24h
2. **Decay Application** - Apply memory-type specific decay functions
3. **Connection Strengthening** - Reinforce frequently co-accessed memories
4. **Archival Decision** - Move low-importance memories to cold storage
5. **Index Optimization** - Rebuild vector indices with consolidated weights

## 📊 **Database Schema Evolution**

### **Enhanced Memory Table**
```sql
CREATE TABLE memories_v23 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(1536),
    
    -- Memory type classification
    memory_type memory_type_enum NOT NULL, -- semantic, episodic, procedural
    
    -- Cognitive metadata
    importance_score DECIMAL(5,4) DEFAULT 0.5000,
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Type-specific metadata
    semantic_metadata JSONB, -- domain, category, confidence
    episodic_metadata JSONB,  -- timestamp, context, location, outcome
    procedural_metadata JSONB, -- skill_level, steps, success_rate
    
    -- Consolidation tracking
    consolidation_score DECIMAL(5,4) DEFAULT 0.5000,
    last_consolidated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    decay_applied BOOLEAN DEFAULT FALSE,
    
    -- Search optimization
    memory_metadata JSONB DEFAULT '{}',
    
    -- Indices
    CONSTRAINT valid_importance CHECK (importance_score >= 0.0000 AND importance_score <= 1.0000),
    CONSTRAINT valid_consolidation CHECK (consolidation_score >= 0.0000 AND consolidation_score <= 1.0000)
);

-- Memory type enum
CREATE TYPE memory_type_enum AS ENUM ('semantic', 'episodic', 'procedural');

-- Specialized indices
CREATE INDEX idx_memories_memory_type ON memories_v23(memory_type);
CREATE INDEX idx_memories_importance ON memories_v23(importance_score DESC);
CREATE INDEX idx_memories_consolidation ON memories_v23(consolidation_score DESC);
CREATE INDEX idx_memories_last_accessed ON memories_v23(last_accessed DESC);

-- Vector index with importance weighting
CREATE INDEX idx_memories_embedding_weighted ON memories_v23 
USING ivfflat (embedding vector_cosine_ops) 
WHERE importance_score > 0.1000;
```

## 🚀 **API Evolution**

### **New Endpoints for v2.3.0**

```python
# Memory type-specific storage
POST /memories/semantic
POST /memories/episodic  
POST /memories/procedural

# Advanced contextual search
POST /memories/search/contextual
{
  "query": "CI/CD debugging",
  "memory_types": ["episodic", "procedural"],
  "timeframe": "last_week",
  "importance_threshold": 0.6
}

# Memory consolidation management
POST /memories/consolidate      # Trigger consolidation cycle
GET /memories/consolidation/stats  # View consolidation metrics
PUT /memories/{id}/importance   # Manual importance adjustment

# Memory aging and lifecycle
GET /memories/aging/stats       # View decay statistics
POST /memories/aging/apply      # Force aging cycle
GET /memories/archived         # View archived memories
```

## 📈 **Success Metrics**

### **Cognitive Performance KPIs**
| Metric | Current (v2.1.1) | Target (v2.3.0) |
|--------|-------------------|------------------|
| **Search Precision** | 75% | 90% |
| **Memory Type Classification Accuracy** | N/A | 95% |
| **Contextual Relevance Score** | N/A | 85% |
| **Consolidation Efficiency** | N/A | 80% reduction in storage |
| **Response Time (Contextual Search)** | N/A | <150ms |

### **User Experience Improvements**
- **Temporal Context**: "Show me what I learned about CI/CD last week"
- **Memory Type Focus**: "Find all procedural knowledge about database setup"
- **Importance Filtering**: "Show only my most important semantic memories about PostgreSQL"
- **Aging Insights**: "What knowledge am I forgetting that needs reinforcement?"

## 🔬 **Implementation Strategy**

### **Phase 1: Foundation (Week 1)**
- Database schema migration
- Memory type classification system
- Basic consolidation algorithms

### **Phase 2: Search Enhancement (Week 2)**  
- Contextual retrieval implementation
- Multi-dimensional scoring
- Advanced API endpoints

### **Phase 3: Intelligence Layer (Week 3)**
- Intelligent aging algorithms
- Automated consolidation cycles
- Performance optimization

### **Phase 4: Validation (Week 4)**
- Comprehensive testing
- Performance benchmarking
- User experience validation

## 🧪 **Testing Strategy**

### **Cognitive Testing Framework**
```python
@pytest.mark.cognitive
class TestMemoryTypeClassification:
    def test_semantic_memory_storage(self):
        """Test semantic memory classification and storage"""
        
    def test_episodic_temporal_context(self):
        """Test episodic memory with temporal metadata"""
        
    def test_procedural_skill_tracking(self):
        """Test procedural memory with skill progression"""

@pytest.mark.consolidation  
class TestMemoryConsolidation:
    def test_importance_scoring(self):
        """Test automatic importance calculation"""
        
    def test_decay_application(self):
        """Test memory type-specific decay models"""
        
    def test_aging_cycle(self):
        """Test complete consolidation cycle"""
```

---

**Status**: 📋 **Specification Complete - Ready for Implementation**  
**Target Release**: v2.3.0 "Cognitive" - August 7, 2025  
**Strategic Impact**: Evolution toward human-like cognitive memory architecture
