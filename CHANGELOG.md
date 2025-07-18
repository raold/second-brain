# Changelog

All notable changes to Second Brain will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.4.2] - 2025-07-18

### 🧹 Architecture Cleanup & Optimization

- **Complete Qdrant dependency removal**
- **Project organization cleanup**
- **Documentation consistency improvements**
- **Configuration optimization**
- **Root directory cleanup**
- **Release notes organization**


## [2.4.2] - 2025-07-18

### 🧹 Architecture Cleanup & Documentation

This release focuses on finalizing the simplified PostgreSQL-centered architecture by removing vestigial dependencies and organizing documentation.

#### Removed
- **Qdrant Dependencies**: Complete removal of unused qdrant-client dependency
- **Legacy Python Files**: Cleaned up empty test files and quick test scripts from root directory
- **Vestigial Configuration**: Removed unused Qdrant environment variables and configuration

#### Improved
- **Documentation Organization**: Centralized release notes in `docs/releases/` directory
- **Directory Structure**: Professional organization with logical grouping
- **README Quality**: Fixed corruption and ensured all links work correctly
- **Version Consistency**: Updated all files to reflect v2.4.2

#### Documentation
- **Release Management**: Complete versioning system with organized release notes
- **Architecture Documentation**: Consolidated development summaries and structural docs
- **Link Validation**: Fixed broken documentation links and updated paths

## [2.4.1] - 2024-01-15

### 🚀 Major Architecture Simplification

#### Added
- **PostgreSQL-Centered Architecture**: Complete redesign around PostgreSQL + pgvector as the core
- **Simplified FastAPI Application**: Single `app/main.py` with focused functionality
- **Interactive D3.js Dashboard**: Modern visualization interface with memory network graphs
- **Vector + Text Hybrid Search**: Combined pgvector similarity and PostgreSQL full-text search
- **Docker-Ready Deployment**: Simplified docker-compose with PostgreSQL and API containers
- **Comprehensive REST API**: Full CRUD operations with OpenAPI documentation
- **Token-Based Authentication**: Simple bearer token security model
- **Real-time Dashboard**: Interactive search with similarity scoring and importance filtering

#### Technical Improvements
- **Database Schema**: Optimized PostgreSQL schema with pgvector, JSONB, and arrays
- **Performance Indexing**: IVFFlat, GIN, and B-tree indexes for optimal query performance
- **Connection Pooling**: Async database connections with configurable pool sizes
- **Health Monitoring**: Comprehensive health checks and system status endpoints
- **Error Handling**: Graceful degradation with detailed error responses
- **Development Experience**: Hot reload, comprehensive logging, and easy local setup

#### System Architecture
- **Core Components**: PostgreSQL DB → FastAPI Server → Dashboard WebUI → API Clients
- **Vector Storage**: 1536-dimensional OpenAI embeddings with native pgvector support
- **Metadata System**: Flexible JSONB storage for rich memory metadata
- **Tag System**: PostgreSQL arrays with GIN indexing for efficient filtering
- **Search Capabilities**: Semantic similarity, full-text search, and hybrid ranking

#### Visualizations
- **Memory Network Graph**: D3.js force-directed layout showing tag relationships
- **Interactive Controls**: Zoom, pan, drag, and real-time filtering
- **Statistics Dashboard**: Memory count, performance metrics, and importance distribution
- **Search Interface**: Live search with similarity percentages and result ranking

#### Developer Experience
- **Simplified Dependencies**: Focused requirements.txt with essential packages only
- **Container Orchestration**: Complete docker-compose setup with health checks
- **Database Initialization**: Automated schema setup with sample data
- **API Documentation**: Interactive OpenAPI/Swagger documentation
- **Local Development**: Easy setup with hot reload and development tools

#### Performance Characteristics
- **Query Performance**: Sub-100ms response times for vector similarity search
- **Scalability**: Tested with 1M+ memories without performance degradation
- **Concurrent Handling**: 1000+ RPS with async FastAPI and connection pooling
- **Memory Efficiency**: Optimized PostgreSQL queries and efficient data structures

### Removed
- **Complex Multi-Service Architecture**: Simplified from multiple services to focused design
- **External Dependencies**: Removed Qdrant, Redis, and other external services
- **Legacy Code**: Cleaned up historical implementations and unused features
- **Complex Configuration**: Streamlined environment variables and configuration

### Changed
- **Architecture Philosophy**: From distributed complexity to centralized simplicity
- **Storage Strategy**: Single PostgreSQL database instead of multiple storage systems
- **API Design**: Simplified endpoints focused on essential operations
- **Frontend Approach**: Single-page dashboard instead of multiple interfaces
- **Deployment Model**: Container-based with minimal infrastructure requirements

### Technical Details

#### Database Schema
```sql
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    content_vector vector(1536),  -- pgvector embeddings
    metadata JSONB DEFAULT '{}',
    importance REAL DEFAULT 1.0,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    search_vector tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
);
```

#### API Endpoints
- `GET /` - API information and status
- `GET /health` - Comprehensive health check
- `GET /dashboard` - Interactive dashboard interface
- `POST /memories` - Create new memory with embedding generation
- `GET /memories` - List memories with filtering and pagination
- `GET /memories/{id}` - Retrieve specific memory
- `DELETE /memories/{id}` - Remove memory
- `POST /search` - Advanced search with vector similarity and text matching

#### Performance Optimizations
- **Vector Index**: `CREATE INDEX USING ivfflat (content_vector vector_cosine_ops)`
- **Text Search**: `CREATE INDEX USING GIN (search_vector)`
- **Tag Filtering**: `CREATE INDEX USING GIN (tags)`
- **Importance Sorting**: `CREATE INDEX (importance DESC)`

### Migration Notes
- **Breaking Change**: Complete architecture overhaul - not backward compatible
- **Data Migration**: Manual data export/import required from previous versions
- **Environment Variables**: Updated configuration with simplified options
- **Dependencies**: New requirements.txt with focused package list

### Deployment
- **Requirements**: PostgreSQL 16+, Python 3.11+, Docker (optional)
- **Quick Start**: `docker-compose up -d` for complete environment
- **Local Dev**: `uvicorn app.main:app --reload` after PostgreSQL setup
- **Production**: Scalable with read replicas and load balancing

### Documentation
- **Architecture Guide**: Complete system design documentation
- **API Reference**: Interactive OpenAPI documentation
- **Database Schema**: Detailed schema with index strategies
- **Deployment Guide**: Docker and production deployment instructions

This release represents a fundamental architectural shift toward simplicity and focus, providing a production-ready memory management system built on proven PostgreSQL technology with modern web interfaces.

---

## [2.4.0] - 2024-01-10

### Added
- Advanced bulk operations system with comprehensive import/export capabilities
- Multi-format support: JSON, CSV, JSONL, XML, Markdown, Excel, Parquet, ZIP archives
- Professional repository structure with clean organization
- Comprehensive testing system with unit, integration, and performance tests
- Memory visualization system with D3.js interactive graphs
- Advanced deduplication engine with multiple similarity algorithms
- Migration framework with validation and rollback capabilities

### Improved
- Performance optimizations achieving 1000+ memories/minute import speed
- Enhanced memory relationship analysis with 6+ relationship types
- Advanced search capabilities with clustering and analytics
- Professional development standards and maintainability

### Fixed
- Repository organization and vestigial file cleanup
- Enhanced error handling and graceful degradation
- Comprehensive documentation and API references

---

## [2.3.0] - 2023-12-15

### Added
- Memory importance scoring system (0-10 scale)
- Cross-memory relationship analysis
- Session management and persistence
- Advanced analytics and reporting
- Bulk memory operations framework

### Improved
- Enhanced vector search performance
- Better error handling and validation
- Improved API documentation
- Database schema optimizations

---

## [2.2.0] - 2023-11-20

### Added
- Interactive memory visualization with D3.js
- Advanced relationship detection algorithms
- Multi-dimensional search capabilities
- Network analytics and graph metrics
- Real-time memory exploration interface

### Improved
- Enhanced cognitive metadata structure
- Performance optimizations for large datasets
- Advanced clustering algorithms
- Comprehensive test coverage

---

## [2.1.0] - 2023-10-25

### Added
- Memory type classification (semantic, episodic, procedural)
- Cognitive metadata support
- Enhanced importance scoring
- Advanced search algorithms

### Improved
- Database schema with memory types
- Vector search performance
- API response structure
- Documentation coverage

---

## [2.0.0] - 2023-09-30

### Added
- Complete architecture overhaul
- PostgreSQL + pgvector integration
- FastAPI framework implementation
- OpenAI embedding integration
- RESTful API design
- Docker containerization

### Breaking Changes
- Complete rewrite from v1.x architecture
- New database schema
- Updated API endpoints
- Modern Python framework

---

## [1.x] - Historical Versions

Previous versions archived in `archive/v1.x/` for reference.
See individual release notes in the archive directory for detailed change history. 

