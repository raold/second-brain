# Second Brain v2.8.1 🧠 - **AI-Powered Reasoning & Advanced Content Analysis** 🚀

![License](https://img.shields.io/badge/License-AGPL%20v3-blue.svg) ![Python](https://img.shields.io/badge/python-3.11+-blue.svg) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue.svg) ![pgvector](https://img.shields.io/badge/pgvector-latest-green.svg) ![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg) ![D3.js](https://img.shields.io/badge/D3.js-v7-orange.svg) ![Tests](https://img.shields.io/badge/tests-100%20passing-brightgreen.svg) ![Coverage](https://img.shields.io/badge/coverage-75%25-green.svg) ![Build](https://img.shields.io/badge/build-stable-green.svg) ![Status](https://img.shields.io/badge/status-production-green.svg) ![Version](https://img.shields.io/badge/v2.8.1-stable-green.svg)

> **Major Release v2.8.1** - Enhanced with advanced content analysis, BERTopic modeling, NetworkX graphs, and transformer-based NLP capabilities

## 🚀 **v2.8.1 Enhanced Release - "Analysis"**

### 🔬 **NEW: Advanced Content Analysis Suite**
- **BERTopic Modeling** - Transformer-based topic discovery with hierarchical clustering
- **NetworkX Graph Analysis** - Centrality metrics, community detection, and path finding
- **Enhanced Structured Extraction** - Form parsing, schema inference, advanced table parsing
- **Multi-Label Domain Classification** - 15+ domains with ML and transformer support
- **Transformer Intent Recognition** - Zero-shot classification with BART for intent detection
- **11 New API Endpoints** - Comprehensive `/graph/*` and `/analysis/*` routes

## 🚀 **v2.8.0 Core Features - "Reasoning"**

### 🧠 **Revolutionary Reasoning Engine**
- **Multi-hop Reasoning** - Traverse knowledge connections up to 10 levels deep with intelligent path-finding
- **Beam Search Algorithm** - Advanced AI search strategy for optimal reasoning paths  
- **Confidence Scoring** - Quantified reliability metrics for all reasoning conclusions
- **Input Validation** - Comprehensive error handling with structured API responses
- **Performance Optimized** - Sub-100ms simple queries, <2s complex multi-hop analysis

### 📊 **Interactive Knowledge Graphs**
- **9 Entity Types** - person, organization, technology, concept, location, event, skill, topic, other
- **14 Relationship Types** - works_at, located_in, uses, part_of, related_to, and more
- **Bulk Processing** - Handle up to 1000 memories simultaneously with validation
- **Entity Extraction** - Automatic NLP-powered entity recognition and relationship detection
- **Graph Analytics** - Network analysis with centrality measures and community detection

### 🎨 **D3.js Graph Visualization**
- **Force-Directed Graphs** - Interactive physics-based layout with zoom, pan, and drag
- **Natural Language Queries** - "Show connections between Python and AI" - English interface
- **Entity Filtering** - Dynamic filtering by entity type with real-time graph updates
- **Export Capabilities** - PNG image export and JSON data export for analysis
- **Responsive Design** - Mobile-friendly interface with touch interaction support
- **Color-Coded Entities** - Visual distinction with optimized color palettes

### 🔗 **Integrated Intelligence Workflow**

The three core systems work together seamlessly:

```
Natural Language Query → Reasoning Engine → Knowledge Graph Builder → Interactive Visualization
          ↓                     ↓                      ↓                        ↓
"How are Python and ML   Extract entities &    Build graph with nodes    Render interactive
 connected through       find reasoning        & relationship edges      D3.js visualization
 data science?"          paths with confidence                           with export options
```

## 🎯 **Complete Feature Set**

### 🧠 **AI-Powered Core Intelligence**

**🤖 Reasoning & Analysis:**
- **Multi-hop Reasoning Engine** - Traverse complex knowledge paths with AI guidance
- **Pattern Detection System** - Discover temporal, semantic, behavioral, and structural patterns
- **Memory Clustering** - Intelligent grouping using K-means, DBSCAN, and hierarchical algorithms
- **Knowledge Gap Analysis** - Identify missing areas with AI-driven recommendations
- **Learning Progress Tracking** - Monitor knowledge growth and mastery levels

**📊 Knowledge Graph Intelligence:**
- **Entity-Relationship Extraction** - Automatic detection of people, places, concepts, and connections
- **Graph Analytics** - Network analysis with centrality, clustering, and pathfinding
- **Interactive Exploration** - Mouse/touch-enabled graph navigation with zoom and filters
- **Natural Language Interface** - Query graphs using plain English commands
- **Visual Intelligence** - Color-coded entities with importance-based sizing

**🎨 Advanced Visualization:**
- **D3.js Force-Directed Graphs** - Physics-based interactive layouts
- **Real-time Filtering** - Dynamic entity type and search-based filtering
- **Export & Sharing** - High-quality PNG and JSON export capabilities
- **Responsive Interface** - Works seamlessly on desktop, tablet, and mobile
- **Performance Optimized** - Smooth 60 FPS interactions with 1000+ node support

### 🧪 **Sophisticated Content Intelligence**

**🎯 Advanced Ingestion Pipeline:**
- **Intelligent Entity Extraction** - Automatic NER with SpaCy and custom patterns
- **Advanced Topic Modeling** - LDA, keyword-based classification, and domain detection
- **Relationship Detection** - Discover connections using dependency parsing and pattern matching
- **Intent Recognition** - Understand user intent with urgency and sentiment analysis
- **Automatic Embeddings** - Generate vector embeddings with chunking support
- **Structured Data Extraction** - Tables, lists, key-value pairs, and code snippets

**📈 Analytics & Insights:**
- **Usage Pattern Analysis** - Understand interaction patterns with your memories
- **Memory Growth Metrics** - Track knowledge accumulation over time
- **Access Pattern Insights** - Discover which memories are most valuable
- **Tag Evolution Tracking** - See how interests change over time
- **Importance Shift Detection** - Identify changing priorities in knowledge base

## 🏗️ **Production-Ready Architecture**

### 🗄️ **PostgreSQL-Centered Design**
Second Brain v2.8.0 maintains our proven **focused, simplified architecture** centered around PostgreSQL:

- **🗄️ PostgreSQL at the Center** - Single, robust database with native vector support
- **⚡ pgvector Integration** - Built-in semantic similarity search with vector indexes
- **📊 JSONB Metadata** - Flexible schema with structured storage for rich context
- **🚀 FastAPI Server** - Async REST API with comprehensive token authentication
- **🎨 Interactive Dashboard** - D3.js visualizations with real-time graph rendering
- **📡 API Client Support** - REST endpoints for any HTTP client integration

### 🧠 **Cognitive Memory Architecture**

Our memory system mirrors cognitive neuroscience principles with AI enhancements:

| Memory Component | Human Brain Analog | v2.8.0 Implementation |
|-----------------|-------------------|------------------------|
| **Hippocampus** | Memory formation & indexing | Vector embeddings + graph relationships |
| **Cortical Networks** | Associative connections | Multi-hop reasoning paths + entity graphs |
| **Memory Consolidation** | Strength over time | Importance scoring + relationship weights |
| **Episodic Context** | When/where memories formed | JSONB timestamp + rich metadata |
| **Semantic Networks** | Meaning relationships | 384D vector space + knowledge graphs |
| **Reasoning Pathways** | Logical connections | Beam search + confidence scoring |

### 🔄 **Enhanced Memory Types**

| Memory Type | Function | v2.8.0 Implementation |
|-------------|----------|----------------------|
| **🔥 Working** | Real-time processing | Immediate relevance + reasoning context |
| **⚡ Short-term** | Recent accessibility | Recency-based + connection strength |
| **💾 Long-term** | Persistent storage | Importance-based + graph centrality |
| **📖 Episodic** | Contextual memories | Rich JSONB + entity relationships |
| **🧩 Semantic** | Meaning & concepts | Vector embeddings + knowledge graphs |
| **⚙️ Procedural** | Learned behaviors | Tag patterns + reasoning templates |

## 🚀 **Quick Start**

### 1. Clone and Setup
```bash
git clone https://github.com/raold/second-brain.git
cd second-brain

# For latest features (v2.8.0 stable):
git checkout main

# For cutting-edge development:
git checkout develop
```

### 2. Environment Configuration
```bash
# Copy and edit environment variables
cp .env.example .env

# Required variables:
# OPENAI_API_KEY=sk-your-openai-key
# API_TOKENS=demo-token,production-token
# DATABASE_URL=postgresql://postgres:password@localhost:5432/second_brain
```

### 3. Docker Deployment (Recommended)
```bash
# Start all services
docker-compose up -d

# Check health
curl http://localhost:8000/health

# Access main dashboard
open http://localhost:8000/dashboard

# Access knowledge graph visualization
open http://localhost:8000/static/knowledge-graph.html
```

### 4. Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL with pgvector
docker-compose up postgres -d

# Run database migrations for knowledge graphs
psql $DATABASE_URL -f migrations/add_knowledge_graph_tables.sql

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📋 **Enhanced API Usage**

### Authentication
All API endpoints require bearer token authentication:
```bash
curl -H "Authorization: Bearer demo-token" http://localhost:8000/memories
```

### **NEW: Multi-hop Reasoning API**
```bash
curl -X POST http://localhost:8000/reasoning/multi-hop \
  -H "Authorization: Bearer demo-token" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How are Python and machine learning connected through data science?",
    "max_hops": 3,
    "beam_width": 5,
    "confidence_threshold": 0.7
  }'
```

### **NEW: Knowledge Graph Builder API**
```bash
curl -X POST http://localhost:8000/knowledge-graph/build \
  -H "Authorization: Bearer demo-token" \
  -H "Content-Type: application/json" \
  -d '{
    "memory_ids": [1, 2, 3, 4, 5],
    "include_relationships": true,
    "entity_types": ["person", "organization", "technology"]
  }'
```

### **NEW: Natural Language Graph Queries**
```bash
curl -X POST http://localhost:8000/graph/query/natural \
  -H "Authorization: Bearer demo-token" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show connections between Python and AI",
    "max_results": 50,
    "include_metadata": true
  }'
```

### Create Enhanced Memory
```bash
curl -X POST http://localhost:8000/memories \
  -H "Authorization: Bearer demo-token" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "PostgreSQL pgvector provides excellent semantic search capabilities for knowledge graphs",
    "importance": 8.5,
    "tags": ["postgresql", "vector", "database", "knowledge-graph"],
    "metadata": {
      "source": "documentation", 
      "topic": "database",
      "entities": ["PostgreSQL", "pgvector"],
      "relationships": [{"source": "PostgreSQL", "target": "pgvector", "type": "includes"}]
    }
  }'
```

### **NEW v2.8.1: Graph API Endpoints (`/graph/*`)**

#### Build Relationship Graph
```bash
curl -X POST http://localhost:8000/graph/build \
  -H "Authorization: Bearer demo-token" \
  -H "Content-Type: application/json" \
  -d '{
    "memory_ids": ["id1", "id2"],
    "tags": ["technology", "database"],
    "min_confidence": 0.5,
    "max_entities": 100,
    "enable_clustering": true
  }'
```

**Response:**
```json
{
  "status": "success",
  "statistics": {
    "nodes": 45,
    "edges": 78,
    "communities": 5,
    "density": 0.08
  },
  "graph": {
    "nodes": [...],
    "links": [...]
  },
  "layout": {
    "node_id": [x, y],
    ...
  },
  "metadata": {
    "num_memories": 10,
    "num_entities": 45,
    "num_relationships": 78
  }
}
```

#### Find Relationship Paths
```bash
curl -X POST http://localhost:8000/graph/paths \
  -H "Authorization: Bearer demo-token" \
  -H "Content-Type: application/json" \
  -d '{
    "source_entity_id": "entity-uuid-1",
    "target_entity_id": "entity-uuid-2",
    "max_paths": 5,
    "max_length": 5
  }'
```

**Response:**
```json
{
  "status": "success",
  "paths": [
    {
      "path": ["entity1", "entity2", "entity3"],
      "length": 2,
      "confidence": 0.85
    }
  ],
  "metadata": {
    "source": "entity-uuid-1",
    "target": "entity-uuid-2",
    "num_paths_found": 3
  }
}
```

#### Get Entity Neighborhood
```bash
curl -X POST http://localhost:8000/graph/neighborhood \
  -H "Authorization: Bearer demo-token" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "entity-uuid",
    "depth": 2,
    "min_confidence": 0.5
  }'
```

#### Get Central Entities
```bash
curl -X GET "http://localhost:8000/graph/centrality?top_n=10" \
  -H "Authorization: Bearer demo-token"
```

**Response:**
```json
{
  "status": "success",
  "centrality_metrics": {
    "degree_centrality": [
      {"entity": "Python", "score": 0.89},
      {"entity": "Machine Learning", "score": 0.76}
    ],
    "betweenness_centrality": [...],
    "eigenvector_centrality": [...]
  },
  "metadata": {
    "total_entities": 150,
    "total_relationships": 320
  }
}
```

#### Detect Communities
```bash
curl -X GET "http://localhost:8000/graph/communities?algorithm=spectral" \
  -H "Authorization: Bearer demo-token"
```

**Response:**
```json
{
  "status": "success",
  "communities": [
    {
      "id": 0,
      "entities": ["Python", "Django", "Flask"],
      "size": 15,
      "density": 0.72
    }
  ],
  "metadata": {
    "algorithm": "spectral",
    "total_entities": 150,
    "total_relationships": 320
  }
}
```

#### Export Graph
```bash
curl -X GET "http://localhost:8000/graph/export/json" \
  -H "Authorization: Bearer demo-token"
```

**Supported formats:** `json`, `graphml`, `gexf`

### **NEW v2.8.1: Analysis API Endpoints (`/analysis/*`)**

#### Analyze Content
```bash
curl -X POST http://localhost:8000/analysis/analyze \
  -H "Authorization: Bearer demo-token" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Machine learning with Python and TensorFlow for neural networks",
    "include_topics": true,
    "include_structure": true,
    "include_domain": true,
    "advanced_features": false
  }'
```

**Response:**
```json
{
  "status": "success",
  "analysis": {
    "topics": {
      "extracted_topics": [
        {
          "name": "Machine Learning",
          "keywords": ["learning", "neural", "networks"],
          "confidence": 0.92,
          "relevance": 0.88,
          "hierarchy": ["Technology", "AI", "Machine Learning"]
        }
      ],
      "statistics": {
        "total_topics": 3,
        "avg_confidence": 0.85
      }
    },
    "structured_data": {
      "key_value_pairs": {},
      "lists": [],
      "tables": [],
      "code_snippets": [],
      "metadata": {},
      "statistics": {
        "extraction_time_ms": 45
      }
    },
    "domains": {
      "domains": ["Technology", "Computer Science"],
      "confidence_scores": {
        "Technology": 0.95,
        "Computer Science": 0.88
      },
      "hierarchy": {
        "Technology": ["Computer Science", "AI"]
      }
    }
  }
}
```

#### Batch Analysis
```bash
curl -X POST http://localhost:8000/analysis/batch \
  -H "Authorization: Bearer demo-token" \
  -H "Content-Type: application/json" \
  -d '{
    "memory_ids": ["id1", "id2", "id3"],
    "tags": ["python", "ai"],
    "limit": 50,
    "include_topics": true,
    "include_structure": true,
    "include_domain": true
  }'
```

**Response:**
```json
{
  "status": "success",
  "analyzed_memories": [
    {
      "memory_id": "id1",
      "title": "Python ML Basics",
      "topics": ["Machine Learning", "Python", "Data Science"],
      "structured_summary": {
        "kv_pairs": 5,
        "lists": 2,
        "tables": 0,
        "code_snippets": 3
      },
      "domains": ["Technology", "Education"]
    }
  ],
  "statistics": {
    "total_memories": 3,
    "memories_analyzed": 3,
    "topic_statistics": {
      "unique_topics": 12,
      "topic_distribution": {...}
    },
    "domain_statistics": {
      "unique_domains": 5,
      "cross_domain_percentage": 33.3
    }
  }
}
```

#### Classify Domain
```bash
curl -X POST http://localhost:8000/analysis/classify-domain \
  -H "Authorization: Bearer demo-token" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Quantum computing algorithms for cryptography",
    "multi_label": true,
    "include_hierarchy": true,
    "confidence_threshold": 0.3
  }'
```

**Response:**
```json
{
  "status": "success",
  "classification": {
    "domains": ["Technology", "Physics", "Mathematics"],
    "confidence_scores": {
      "Technology": 0.92,
      "Physics": 0.88,
      "Mathematics": 0.75
    },
    "hierarchy": {
      "Technology": ["Computer Science", "Quantum Computing"],
      "Physics": ["Quantum Mechanics"],
      "Mathematics": ["Cryptography", "Algorithms"]
    }
  }
}
```

#### Get Trending Topics
```bash
curl -X GET "http://localhost:8000/analysis/topics/trending?days=7&limit=10" \
  -H "Authorization: Bearer demo-token"
```

**Response:**
```json
{
  "status": "success",
  "period_days": 7,
  "memories_analyzed": 45,
  "trending_topics": [
    {
      "topic": "Machine Learning",
      "occurrences": 23,
      "keywords": ["AI", "neural", "deep", "learning", "model"],
      "trend_score": 0.51
    }
  ]
}
```

#### Get Domain Distribution
```bash
curl -X GET http://localhost:8000/analysis/domains/distribution \
  -H "Authorization: Bearer demo-token"
```

**Response:**
```json
{
  "status": "success",
  "total_memories": 200,
  "domain_distribution": [
    {
      "domain": "Technology",
      "count": 85,
      "percentage": 42.5,
      "avg_confidence": 0.88
    }
  ],
  "cross_domain_percentage": 28.5,
  "unique_domains": 12
}
```

## 🗄️ **Enhanced Database Schema**

### Core Memories Table
```sql
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    content_vector vector(1536),                    -- pgvector for embeddings
    metadata JSONB DEFAULT '{}',                    -- Flexible metadata + entities
    importance REAL DEFAULT 1.0,                   -- 0-10 scale
    tags TEXT[] DEFAULT '{}',                       -- Array of tags
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    search_vector tsvector GENERATED ALWAYS AS     -- Full-text search
        (to_tsvector('english', content)) STORED
);
```

### **NEW: Knowledge Graph Tables**
```sql
-- Entities extracted from memories
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    entity_type entity_type_enum NOT NULL,
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Relationships between entities
CREATE TABLE relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entity_id UUID REFERENCES entities(id),
    target_entity_id UUID REFERENCES entities(id),
    relationship_type relationship_type_enum NOT NULL,
    weight REAL DEFAULT 1.0,
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Memory-Entity associations
CREATE TABLE memory_entities (
    memory_id UUID REFERENCES memories(id),
    entity_id UUID REFERENCES entities(id),
    relevance REAL DEFAULT 1.0,
    extraction_confidence REAL DEFAULT 1.0,
    PRIMARY KEY (memory_id, entity_id)
);
```

## 🎨 **Enhanced Dashboard Features**

### Knowledge Graph Visualization (`/static/knowledge-graph.html`)
- **Interactive D3.js Graph** - Force-directed layout with physics simulation
- **Natural Language Queries** - English-language graph exploration
- **Entity Filtering** - Filter by person, organization, technology, concept, etc.
- **Search Interface** - Real-time node highlighting and filtering
- **Export Functions** - PNG image and JSON data export
- **Mobile Responsive** - Touch-friendly interface for tablets and phones

### Classic Memory Dashboard (`/dashboard`)
- **Memory Network** - Node-link visualization of memory relationships
- **Real-time Search** - Live search with similarity scoring
- **Statistics Cards** - Enhanced metrics including graph analytics
- **Memory Browser** - Paginated list with rich metadata display
- **Tag Relationships** - Visual connections between related memories

### Advanced Analytics
- **Graph Metrics** - Node centrality, clustering coefficient, path lengths
- **Entity Analytics** - Most connected entities, relationship patterns
- **Memory Insights** - Connection strength, reasoning paths, cluster analysis
- **Performance Metrics** - API response times, query complexity analysis

## 🧪 **Comprehensive Testing**

### Test Coverage (75%)
```bash
# All v2.8.0 feature tests
pytest tests/test_reasoning_engine.py -v
pytest tests/test_knowledge_graph_builder.py -v
pytest tests/test_graph_visualization.py -v
pytest tests/test_graph_query_parser.py -v

# Integration tests
pytest test_integration_features.py -v

# Minimal feature validation
python test_reasoning_minimal.py
python test_knowledge_graph_minimal.py
python test_visualization_simple.py
```

### Performance Benchmarks
- **Reasoning Engine** - <100ms simple queries, <2s complex multi-hop
- **Knowledge Graph** - Build graphs from 1000+ memories in <5s
- **D3.js Visualization** - 60 FPS with 1000+ nodes, <3s initial load
- **API Responses** - <50ms average for standard operations
- **Database Queries** - Optimized indexes for sub-10ms vector searches

## 🔧 **Configuration**

### Environment Variables
```bash
# Database Connection
DATABASE_URL=postgresql://username:password@host:port/database

# Authentication
API_TOKENS=token1,token2,token3

# OpenAI Integration (for embeddings & NLP)
OPENAI_API_KEY=sk-your-openai-api-key

# v2.8.0 Features
ENABLE_REASONING=true
ENABLE_KNOWLEDGE_GRAPHS=true
ENABLE_GRAPH_VISUALIZATION=true

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

### Advanced Configuration
```bash
# Reasoning Engine Settings
REASONING_MAX_HOPS=10
REASONING_DEFAULT_BEAM_WIDTH=5
REASONING_CONFIDENCE_THRESHOLD=0.7

# Knowledge Graph Settings
KG_MAX_MEMORIES_PER_BATCH=1000
KG_ENTITY_EXTRACTION_MODEL=spacy_en_core_web_sm
KG_RELATIONSHIP_CONFIDENCE_THRESHOLD=0.6

# Visualization Settings
VIZ_DEFAULT_NODE_LIMIT=500
VIZ_ENABLE_PHYSICS=true
VIZ_EXPORT_QUALITY=high
```

## 📊 **Performance & Scaling**

### v2.8.0 Performance Characteristics
- **Multi-hop Reasoning** - Process complex queries in <2 seconds
- **Knowledge Graph Building** - Extract entities from 1000 memories in <5 seconds  
- **Graph Visualization** - Render 1000+ node graphs with 60 FPS performance
- **Natural Language Queries** - Parse and execute in <200ms
- **Concurrent Users** - Support 100+ simultaneous graph interactions

### API Performance  
- **2000+ RPS** - Enhanced concurrent request handling
- **<25ms Average** - Response time for simple queries
- **Sub-second Complex Queries** - Multi-hop reasoning with caching
- **Graceful Degradation** - Fallback when AI services unavailable
- **Enhanced Error Recovery** - Comprehensive error handling with retries

### Scaling Strategy
- **Read Replicas** - PostgreSQL read scaling for graph queries
- **Connection Pooling** - Optimized database connection management
- **Caching Layer** - Redis for frequently accessed graph data
- **CDN Distribution** - Static assets and graph visualization resources
- **Microservice Ready** - Modular design for horizontal scaling

## 🛠️ **Development**

### Requirements
- Python 3.11+
- PostgreSQL 16+ with pgvector extension
- Node.js 18+ (for D3.js development)
- OpenAI API key (optional, will use dummy data)

### Development Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install development tools
pip install pytest httpx ruff black

# Install D3.js and web dependencies (if modifying visualization)
npm install d3 @types/d3

# Run database migrations
psql $DATABASE_URL -f migrations/add_knowledge_graph_tables.sql

# Run all tests
pytest -v

# Start development server with hot reload
uvicorn app.main:app --reload
```

### Project Structure
```
second-brain/
├── app/
│   ├── services/
│   │   ├── reasoning_engine.py         # Multi-hop reasoning
│   │   ├── knowledge_graph_builder.py  # Entity extraction & graphs
│   │   └── graph_query_parser.py       # Natural language queries
│   ├── routes/
│   │   ├── reasoning_routes.py         # Reasoning API endpoints
│   │   └── knowledge_graph_routes.py   # Graph API endpoints
│   └── main.py                         # FastAPI application
├── static/
│   ├── knowledge-graph.html            # D3.js graph visualization
│   ├── js/
│   │   └── knowledge-graph-viz.js      # D3.js visualization component
│   └── dashboard.html                  # Classic memory dashboard
├── tests/
│   ├── test_reasoning_engine.py        # Reasoning tests
│   ├── test_knowledge_graph_builder.py # Knowledge graph tests
│   ├── test_graph_visualization.py     # Visualization tests
│   └── test_graph_query_parser.py      # Query parser tests
├── migrations/
│   └── add_knowledge_graph_tables.sql  # Database schema
├── docs/
│   └── testing/                        # Comprehensive test documentation
└── docker-compose.yml                  # Container orchestration
```

## 🔒 **Security**

### Enhanced Authentication
- **Bearer Token** - Stateless authentication with token validation
- **API Rate Limiting** - Configurable request throttling per endpoint
- **Input Validation** - Comprehensive Pydantic model validation
- **SQL Injection Protection** - Parameterized queries throughout
- **XSS Prevention** - Sanitized HTML output in visualizations

### Security Best Practices
- Use strong, unique API tokens (minimum 32 characters)
- Enable TLS/HTTPS in production environments
- Rotate tokens regularly (recommended: monthly)
- Monitor access logs and query patterns
- Implement proper CORS policies for web interfaces

## 🚢 **Production Deployment**

### Docker Production Setup
```bash
# Production deployment
docker-compose -f docker-compose.production.yml up -d

# Scale API instances
docker-compose up --scale api=3 -d

# Update to latest v2.8.0
docker-compose pull && docker-compose up -d
```

### Kubernetes Deployment
```yaml
# Example k8s deployment for v2.8.0
apiVersion: apps/v1
kind: Deployment
metadata:
  name: second-brain-v280
spec:
  replicas: 3
  selector:
    matchLabels:
      app: second-brain
      version: v2.8.0
  template:
    spec:
      containers:
      - name: api
        image: second-brain:v2.8.0
        env:
        - name: ENABLE_REASONING
          value: "true"
        - name: ENABLE_KNOWLEDGE_GRAPHS
          value: "true"
```

### Infrastructure Requirements
- **CPU** - 4 cores minimum (8 cores recommended for reasoning)
- **RAM** - 16GB minimum (32GB recommended for large graphs)
- **Storage** - SSD recommended for database performance
- **Network** - Low latency for real-time graph interactions

## 📚 **Documentation**

### v2.8.0 Documentation
- **[Reasoning Engine Guide](docs/testing/reasoning_engine_testing.md)** - Multi-hop reasoning system
- **[Knowledge Graph Guide](docs/testing/knowledge_graph_testing.md)** - Entity extraction & graphs
- **[Visualization Guide](docs/testing/visualization_testing.md)** - D3.js graph visualization
- **[API Documentation](http://localhost:8000/docs)** - Interactive OpenAPI docs with v2.8.0 endpoints

### Core Documentation
- **[Architecture Guide](docs/architecture/ARCHITECTURE.md)** - System design and patterns
- **[Database Schema](migrations/)** - Complete database setup including graphs
- **[Docker Guide](docker-compose.yml)** - Container configuration
- **[Release Notes](docs/releases/)** - Version history and v2.8.0 changes

## 🎯 **Migration from Previous Versions**

### From v2.5.0 to v2.8.0
```bash
# 1. Backup your database
pg_dump $DATABASE_URL > backup-pre-v280.sql

# 2. Run knowledge graph migrations
psql $DATABASE_URL -f migrations/add_knowledge_graph_tables.sql

# 3. Update environment variables
echo "ENABLE_REASONING=true" >> .env
echo "ENABLE_KNOWLEDGE_GRAPHS=true" >> .env
echo "ENABLE_GRAPH_VISUALIZATION=true" >> .env

# 4. Restart services
docker-compose down && docker-compose up -d
```

### Data Migration Tools
```bash
# Extract entities from existing memories
curl -X POST http://localhost:8000/knowledge-graph/migrate \
  -H "Authorization: Bearer your-token"

# Build initial knowledge graph
curl -X POST http://localhost:8000/knowledge-graph/build-all \
  -H "Authorization: Bearer your-token"
```

## 🤝 **Contributing**

### Development Guidelines for v2.8.0
1. Fork the repository
2. Create feature branch (`git checkout -b feature/graph-enhancement`)
3. Follow existing patterns for reasoning/graph features
4. Add comprehensive tests (reasoning, graph, visualization)
5. Update documentation
6. Submit pull request with detailed description

### Code Standards
- **Python** - Follow PEP 8, use type hints, comprehensive docstrings
- **JavaScript** - ES6+, JSDoc comments for D3.js components  
- **SQL** - Consistent naming, proper indexing, migration scripts
- **Testing** - Minimum 75% coverage, integration tests for new features

## 📄 **License**

This project is licensed under the AGPL v3 License - see the [LICENSE](LICENSE) file for details.

## 🙏 **Acknowledgments**

### Core Technologies
- **PostgreSQL & pgvector** - Robust database with vector similarity
- **FastAPI** - Modern, fast web framework with async support
- **D3.js** - Powerful data visualization and graph rendering
- **OpenAI** - Semantic embeddings and NLP capabilities

### v2.8.0 Innovations
- **Beam Search** - Inspired by machine translation and pathfinding algorithms
- **Entity-Relationship Extraction** - Built on spaCy and custom NLP models
- **Force-Directed Graphs** - Leveraging D3.js physics simulation
- **Natural Language Interfaces** - Democratizing graph query capabilities

---

**Second Brain v2.8.0** - AI-powered reasoning meets interactive knowledge graphs. The future of intelligent memory management. 🧠🚀✨

### 🎉 **What's Next: v2.9.0 & Beyond**

**Coming in v2.9.0 "Collaboration":**
- Real-time collaborative editing
- Mobile-first interface design
- Advanced migration system
- Shared memory spaces
- Offline capabilities

**Future Roadmap:**
- **v3.0.0**: Next-generation AI with GPT-4 integration
- **Enterprise Features**: Advanced security, audit trails, API management
- **Federated Learning**: Distributed intelligence across instances
- **Advanced Analytics**: Predictive insights and recommendation engines