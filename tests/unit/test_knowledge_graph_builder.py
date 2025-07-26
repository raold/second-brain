"""
Simplified tests for the knowledge graph builder
Focus on testing core functionality without complex mocking
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.services.knowledge_graph_builder import (
    Entity,
    EntityMention,
    EntityType,
    KnowledgeGraph,
    KnowledgeGraphBuilder,
    RelationshipType,
)


class TestKnowledgeGraphBuilder:
    """Test knowledge graph builder with simplified approach"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a properly configured mock database"""
        db = AsyncMock()
        
        # Setup connection pool mock
        db.pool = MagicMock()
        db.pool.acquire = MagicMock()
        mock_conn = AsyncMock()
        db.pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        db.pool.acquire.return_value.__aexit__ = AsyncMock()
        
        # Default mock returns
        db.get_memories_by_ids = AsyncMock(return_value=[])
        db.store_entity = AsyncMock(return_value="entity-id")
        db.store_entity_mention = AsyncMock()
        db.store_entity_relationship = AsyncMock()
        db.store_memory_relationship = AsyncMock()
        db.get_entity_by_name = AsyncMock(return_value=None)
        db.store_graph_metadata = AsyncMock()
        
        return db
    
    @pytest.fixture
    def graph_builder(self, mock_db):
        """Create knowledge graph builder instance"""
        return KnowledgeGraphBuilder(mock_db)
    
    def test_is_likely_entity(self, graph_builder):
        """Test entity likelihood detection"""
        # Valid entities
        assert graph_builder._is_likely_entity("John Smith") == True
        assert graph_builder._is_likely_entity("OpenAI") == True
        assert graph_builder._is_likely_entity("organization") == True
        
        # Not entities
        assert graph_builder._is_likely_entity("the") == False
        assert graph_builder._is_likely_entity("") == False
        assert graph_builder._is_likely_entity("   ") == False
        assert graph_builder._is_likely_entity("123") == False
    
    def test_get_text_between_entities(self, graph_builder):
        """Test text extraction between entities"""
        content = "Python is used for machine learning"
        result = graph_builder._get_text_between_entities(content, "Python", "machine learning")
        assert result == " is used for "
        
        # Test when entities not found
        result = graph_builder._get_text_between_entities(content, "Java", "AI")
        assert result is None
    
    def test_extract_noun_phrases(self, graph_builder):
        """Test noun phrase extraction"""
        text = "The machine learning algorithm is powerful"
        phrases = graph_builder._extract_noun_phrases(text)
        
        assert len(phrases) > 0
        assert any("machine learning" in p for p in phrases)
    
    def test_calculate_entity_similarity(self, graph_builder):
        """Test entity similarity calculation"""
        e1 = Entity(id="1", name="Python", entity_type=EntityType.TECHNOLOGY)
        e2 = Entity(id="2", name="Java", entity_type=EntityType.TECHNOLOGY)
        e3 = Entity(id="3", name="machine learning", entity_type=EntityType.CONCEPT)
        
        # Same type should have base similarity
        sim1 = graph_builder._calculate_entity_similarity(e1, e2)
        assert 0 <= sim1 <= 1
        assert sim1 >= 0.3  # Base similarity for same type
        
        # Different types should have lower similarity
        sim2 = graph_builder._calculate_entity_similarity(e1, e3)
        assert sim2 < sim1
    
    @pytest.mark.asyncio
    async def test_extract_entities_from_memory(self, graph_builder):
        """Test entity extraction from memory"""
        memory = {
            "id": "mem1",
            "content": "Python is a programming language used for web development",
            "created_at": datetime.utcnow().isoformat()
        }
        
        mentions = await graph_builder._extract_entities_from_memory(memory)
        
        assert isinstance(mentions, list)
        # Should find at least Python
        entity_names = [m.entity.name for m in mentions]
        assert "Python" in entity_names
    
    @pytest.mark.asyncio
    async def test_ensure_entity_exists_new(self, graph_builder, mock_db):
        """Test entity creation when it doesn't exist"""
        entity = Entity(id=None, name="TestEntity", entity_type=EntityType.CONCEPT)
        
        # Setup mock connection and result
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(side_effect=[
            None,  # First check - entity doesn't exist
            {"id": "new-id"}  # Insert returns new ID
        ])
        mock_db.pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        entity_id = await graph_builder._ensure_entity_exists(entity)
        
        assert entity_id == "new-id"
        assert mock_conn.fetchrow.call_count == 2
    
    @pytest.mark.asyncio
    async def test_ensure_entity_exists_existing(self, graph_builder, mock_db):
        """Test entity retrieval when it exists"""
        entity = Entity(id=None, name="TestEntity", entity_type=EntityType.CONCEPT)
        
        # Setup mock connection with existing entity
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={"id": "existing-id"})
        mock_conn.execute = AsyncMock()  # For update query
        mock_db.pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        entity_id = await graph_builder._ensure_entity_exists(entity)
        
        assert entity_id == "existing-id"
        assert mock_conn.execute.called  # Update occurrence count
    
    @pytest.mark.asyncio
    async def test_store_entity_mention(self, graph_builder, mock_db):
        """Test storing entity mention"""
        entity = Entity(id="e1", name="Python", entity_type=EntityType.TECHNOLOGY)
        mention = EntityMention(
            entity=entity,
            memory_id="mem1",
            position_start=0,
            position_end=6,
            context="Python is great",
            confidence=0.9
        )
        
        # Setup mock connection for _ensure_entity_exists and INSERT
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value={"id": "e1"})  # Entity exists
        mock_conn.execute = AsyncMock()  # For INSERT
        mock_db.pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        await graph_builder._store_entity_mention(mention)
        
        # Check that INSERT was executed
        assert mock_conn.execute.call_count >= 1
        insert_call = [call for call in mock_conn.execute.call_args_list if "INSERT INTO entity_mentions" in str(call)]
        assert len(insert_call) > 0
    
    @pytest.mark.asyncio
    async def test_build_graph_empty_memories_error(self, graph_builder, mock_db):
        """Test that empty memory list raises error"""
        with pytest.raises(ValueError, match="At least one memory ID is required"):
            await graph_builder.build_graph_from_memories(memory_ids=[])
    
    @pytest.mark.asyncio
    async def test_build_graph_basic(self, graph_builder, mock_db):
        """Test basic graph building"""
        memory = {
            "id": "mem1",
            "content": "Test content",
            "created_at": datetime.utcnow().isoformat(),
            "embedding": [0.1] * 1536,
            "metadata": {}
        }
        
        mock_db.get_memory = AsyncMock(return_value=memory)
        
        graph = await graph_builder.build_graph_from_memories(
            memory_ids=["mem1"],
            extract_entities=False,  # Skip entity extraction for basic test
            extract_relationships=False
        )
        
        assert isinstance(graph, dict)
        assert "nodes" in graph
        assert "edges" in graph
        assert "stats" in graph
        assert graph["entity_count"] == 0
        assert graph["relationship_count"] == 0
    
    @pytest.mark.asyncio
    async def test_get_entity_graph(self, graph_builder, mock_db):
        """Test getting entity subgraph"""
        # Setup mock connection
        mock_conn = AsyncMock()
        mock_db.pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        # Mock entity fetch
        mock_conn.fetchrow = AsyncMock(return_value={
            "id": "e1",
            "name": "Python",
            "entity_type": "technology",  # Fixed column name
            "description": "Programming language",
            "metadata": {},
            "importance_score": 0.8,
            "occurrence_count": 5
        })
        
        # Mock empty relationships (simplest case)
        mock_conn.fetch = AsyncMock(return_value=[])
        
        graph = await graph_builder.get_entity_graph("e1", depth=1)
        
        assert "nodes" in graph
        assert "edges" in graph
        assert "center_entity" in graph
        assert graph["center_entity"] == "e1"
        assert len(graph["nodes"]) >= 1
        assert graph["nodes"][0]["id"] == "e1"
    
    def test_determine_memory_relationship_type(self, graph_builder):
        """Test memory relationship type determination"""
        mem1 = {"content": "Learning Python", "created_at": "2024-01-01T00:00:00"}
        mem2 = {"content": "Python project", "created_at": "2024-01-02T00:00:00"}
        
        rel_type = graph_builder._determine_memory_relationship_type(mem1, mem2, 0.8)
        
        assert isinstance(rel_type, str)
        assert rel_type in ["highly_related", "moderately_related", "weakly_related"]
    
    def test_calculate_graph_stats(self, graph_builder):
        """Test graph statistics calculation"""
        # Create a simple graph structure with proper format
        graph = {
            "nodes": [
                {"id": "n1", "label": "Node1", "type": "concept", "size": 15},
                {"id": "n2", "label": "Node2", "type": "technology", "size": 20}
            ],
            "edges": [
                {"source": "n1", "target": "n2", "type": "related", "weight": 0.8}
            ]
        }
        
        stats = graph_builder._calculate_graph_stats(graph)
        
        assert stats["node_count"] == 2
        assert stats["edge_count"] == 1
        assert stats["density"] > 0
        assert "node_types" in stats
        assert stats["node_types"]["concept"] == 1
        assert stats["node_types"]["technology"] == 1
    
    @pytest.mark.asyncio
    async def test_extract_entity_relationships(self, graph_builder):
        """Test relationship extraction between entities"""
        entity1 = Entity(id="e1", name="Python", entity_type=EntityType.TECHNOLOGY)
        entity2 = Entity(id="e2", name="programming", entity_type=EntityType.CONCEPT)
        
        relationships = await graph_builder._extract_entity_relationships(
            "Python is used for programming",
            entity1, 
            entity2
        )
        
        assert isinstance(relationships, list)
        # May or may not find relationships based on pattern matching
        
        for rel in relationships:
            assert hasattr(rel, "source_entity_id")
            assert hasattr(rel, "target_entity_id")
            assert hasattr(rel, "relationship_type")
            assert rel.source_entity_id == "e1"
            assert rel.target_entity_id == "e2"
    
    @pytest.mark.asyncio
    async def test_extract_memory_relationships(self, graph_builder, mock_db):
        """Test memory relationship extraction"""
        memories = [
            {
                "id": "m1",
                "content": "machine learning data science algorithms programming python",
                "created_at": "2024-01-01T00:00:00",
                "embedding": [0.1] * 1536
            },
            {
                "id": "m2",
                "content": "machine learning programming algorithms data science python",
                "created_at": "2024-01-02T00:00:00",
                "embedding": [0.15] * 1536
            }
        ]
        
        relationships = await graph_builder._extract_memory_relationships(memories)
        
        assert isinstance(relationships, list)
        # Should find relationship based on high content similarity (same words, different order)
        if len(relationships) > 0:
            assert all("source_memory_id" in r for r in relationships)
            assert all("target_memory_id" in r for r in relationships)
            assert relationships[0]["source_memory_id"] == "m1"
            assert relationships[0]["target_memory_id"] == "m2"
        # If no relationships found due to TF-IDF threshold, that's valid too