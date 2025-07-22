"""
Tests for the knowledge graph builder
"""

from unittest.mock import AsyncMock

import pytest

from app.services.knowledge_graph_builder import (
    Entity,
    EntityType,
    KnowledgeGraph,
    KnowledgeGraphBuilder,
    RelationshipType,
)


class TestKnowledgeGraphBuilder:
    """Test the knowledge graph builder functionality"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database"""
        db = AsyncMock()
        return db

    @pytest.fixture
    def graph_builder(self, mock_db):
        """Create a knowledge graph builder instance"""
        return KnowledgeGraphBuilder(mock_db)

    @pytest.mark.asyncio
    async def test_extract_entities(self, graph_builder):
        """Test entity extraction from text"""
        text = "John Smith works at OpenAI developing ChatGPT in San Francisco"

        entities = await graph_builder._extract_entities(text)

        assert len(entities) > 0

        # Check for expected entities
        entity_texts = [e.text for e in entities]
        assert "John Smith" in entity_texts
        assert "OpenAI" in entity_texts
        assert "ChatGPT" in entity_texts
        assert "San Francisco" in entity_texts

        # Check entity types
        person_entities = [e for e in entities if e.type == EntityType.PERSON]
        assert len(person_entities) >= 1
        assert person_entities[0].text == "John Smith"

        org_entities = [e for e in entities if e.type == EntityType.ORGANIZATION]
        assert len(org_entities) >= 1

        tech_entities = [e for e in entities if e.type == EntityType.TECHNOLOGY]
        assert len(tech_entities) >= 1

    @pytest.mark.asyncio
    async def test_extract_entities_with_patterns(self, graph_builder):
        """Test pattern-based entity extraction"""
        text = """
        I learned Python and JavaScript for web development.
        Machine learning and deep learning are fascinating topics.
        The conference was held in New York City.
        """

        entities = await graph_builder._extract_entities(text)

        # Check technology entities
        tech_entities = [e for e in entities if e.type == EntityType.TECHNOLOGY]
        tech_names = [e.text for e in tech_entities]
        assert "Python" in tech_names
        assert "JavaScript" in tech_names

        # Check concept entities
        concept_entities = [e for e in entities if e.type == EntityType.CONCEPT]
        concept_names = [e.text for e in concept_entities]
        assert "machine learning" in concept_names or "Machine learning" in concept_names
        assert "deep learning" in concept_names

        # Check location entities
        location_entities = [e for e in entities if e.type == EntityType.LOCATION]
        location_names = [e.text for e in location_entities]
        assert "New York City" in location_names

    @pytest.mark.asyncio
    async def test_deduplicate_entities(self, graph_builder):
        """Test entity deduplication"""
        entities = [
            Entity(text="Python", type=EntityType.TECHNOLOGY, confidence=0.9),
            Entity(text="python", type=EntityType.TECHNOLOGY, confidence=0.8),
            Entity(text="PYTHON", type=EntityType.TECHNOLOGY, confidence=0.7),
            Entity(text="JavaScript", type=EntityType.TECHNOLOGY, confidence=0.85),
            Entity(text="Python", type=EntityType.SKILL, confidence=0.6),  # Different type
        ]

        deduplicated = graph_builder._deduplicate_entities(entities)

        # Should keep highest confidence version
        assert len(deduplicated) == 3  # Python (tech), JavaScript, Python (skill)

        python_tech = [e for e in deduplicated if e.text == "Python" and e.type == EntityType.TECHNOLOGY]
        assert len(python_tech) == 1
        assert python_tech[0].confidence == 0.9  # Highest confidence kept

    @pytest.mark.asyncio
    async def test_detect_relationships(self, graph_builder, mock_db):
        """Test relationship detection between memories"""
        memories = [
            {
                "id": "mem1",
                "content": "Started learning Python programming",
                "metadata": {"entities": ["Python"], "topics": ["programming"]}
            },
            {
                "id": "mem2",
                "content": "Python led me to explore machine learning",
                "metadata": {"entities": ["Python", "machine learning"]}
            },
            {
                "id": "mem3",
                "content": "Machine learning requires understanding of statistics",
                "metadata": {"entities": ["machine learning", "statistics"]}
            }
        ]

        relationships = await graph_builder._detect_relationships(memories)

        assert len(relationships) > 0

        # Check for causal relationship
        causal_rels = [r for r in relationships if r.type == RelationshipType.CAUSED_BY]
        assert len(causal_rels) >= 1

        # Check for dependency relationship
        depends_rels = [r for r in relationships if r.type == RelationshipType.DEPENDS_ON]
        assert len(depends_rels) >= 1

    @pytest.mark.asyncio
    async def test_calculate_tfidf_similarity(self, graph_builder):
        """Test TF-IDF similarity calculation"""
        memories = [
            {"id": "1", "content": "Python programming is powerful"},
            {"id": "2", "content": "Python is a great language for programming"},
            {"id": "3", "content": "JavaScript is used for web development"},
            {"id": "4", "content": "Machine learning uses Python extensively"}
        ]

        similarity_matrix = graph_builder._calculate_tfidf_similarity(memories)

        # Similar memories should have higher scores
        assert similarity_matrix["1"]["2"] > similarity_matrix["1"]["3"]
        assert similarity_matrix["2"]["4"] > similarity_matrix["2"]["3"]  # Both mention Python

        # Similarity should be symmetric
        assert similarity_matrix["1"]["2"] == similarity_matrix["2"]["1"]

    @pytest.mark.asyncio
    async def test_build_graph_from_memories(self, graph_builder, mock_db):
        """Test building a complete knowledge graph"""
        # Mock database responses
        mock_db.get_memories.return_value = [
            {
                "id": "mem1",
                "content": "John Smith started learning Python at Stanford University",
                "metadata": {},
                "created_at": "2024-01-01"
            },
            {
                "id": "mem2",
                "content": "Python helped John build machine learning models",
                "metadata": {},
                "created_at": "2024-01-02"
            }
        ]

        # Mock entity storage
        mock_db.store_entities = AsyncMock()
        mock_db.store_entity_mentions = AsyncMock()
        mock_db.store_relationships = AsyncMock()

        graph = await graph_builder.build_graph_from_memories(
            memory_ids=["mem1", "mem2"],
            include_entities=True,
            include_relationships=True
        )

        assert isinstance(graph, KnowledgeGraph)
        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0

        # Check that entities were stored
        assert mock_db.store_entities.called
        assert mock_db.store_entity_mentions.called
        assert mock_db.store_relationships.called

    @pytest.mark.asyncio
    async def test_incremental_update(self, graph_builder, mock_db):
        """Test incremental graph updates"""
        # Mock existing graph
        mock_db.get_graph_metadata.return_value = {
            "id": "graph1",
            "memory_ids": ["mem1", "mem2"],
            "entity_count": 5,
            "relationship_count": 3
        }

        # Mock new memory
        new_memory = {
            "id": "mem3",
            "content": "Deep learning extends machine learning concepts",
            "metadata": {}
        }

        mock_db.get_memory.return_value = new_memory
        mock_db.get_memories.return_value = [
            {"id": "mem1", "content": "Introduction to machine learning"},
            {"id": "mem2", "content": "Python for data science"}
        ]

        # Mock storage operations
        mock_db.store_entities = AsyncMock()
        mock_db.store_relationships = AsyncMock()
        mock_db.update_graph_metadata = AsyncMock()

        updated_graph = await graph_builder.update_graph_incrementally(
            graph_id="graph1",
            new_memory_id="mem3"
        )

        assert updated_graph is not None
        assert "mem3" in updated_graph.metadata.get("memory_ids", [])
        assert mock_db.update_graph_metadata.called

    @pytest.mark.asyncio
    async def test_analyze_graph_structure(self, graph_builder):
        """Test graph structure analysis"""
        # Create a simple graph
        graph = KnowledgeGraph(
            nodes=[
                {"id": "A", "label": "Node A", "type": "concept"},
                {"id": "B", "label": "Node B", "type": "concept"},
                {"id": "C", "label": "Node C", "type": "concept"},
                {"id": "D", "label": "Node D", "type": "concept"}
            ],
            edges=[
                {"source": "A", "target": "B", "weight": 0.8},
                {"source": "A", "target": "C", "weight": 0.6},
                {"source": "B", "target": "C", "weight": 0.7},
                {"source": "C", "target": "D", "weight": 0.5}
            ],
            metadata={}
        )

        analysis = graph_builder._analyze_graph_structure(graph)

        assert "density" in analysis
        assert "connected_components" in analysis
        assert "degree_distribution" in analysis
        assert "average_degree" in analysis

        # Check specific values
        assert analysis["node_count"] == 4
        assert analysis["edge_count"] == 4
        assert analysis["density"] > 0  # Should be positive for connected graph
        assert analysis["connected_components"] == 1  # All connected

    @pytest.mark.asyncio
    async def test_get_entity_subgraph(self, graph_builder, mock_db):
        """Test extracting entity-centered subgraph"""
        # Mock entity and related data
        mock_db.get_entity.return_value = {
            "id": "ent1",
            "text": "Python",
            "type": "technology"
        }

        mock_db.get_entity_relationships.return_value = [
            {
                "source_id": "ent1",
                "target_id": "ent2",
                "type": "used_in",
                "weight": 0.8
            },
            {
                "source_id": "ent3",
                "target_id": "ent1",
                "type": "related_to",
                "weight": 0.6
            }
        ]

        mock_db.get_entities_by_ids.return_value = [
            {"id": "ent2", "text": "Machine Learning", "type": "concept"},
            {"id": "ent3", "text": "Programming", "type": "skill"}
        ]

        subgraph = await graph_builder.get_entity_subgraph(
            entity_id="ent1",
            max_depth=1
        )

        assert len(subgraph.nodes) == 3  # Central node + 2 connected
        assert len(subgraph.edges) == 2

        # Check central node is included
        node_ids = [n["id"] for n in subgraph.nodes]
        assert "ent1" in node_ids
        assert "ent2" in node_ids
        assert "ent3" in node_ids

    @pytest.mark.asyncio
    async def test_memory_relationship_detection(self, graph_builder):
        """Test detection of relationships between memories"""
        memory1 = {
            "id": "1",
            "content": "The bug in the system caused data loss",
            "metadata": {}
        }

        memory2 = {
            "id": "2",
            "content": "Data loss led to implementing better backups",
            "metadata": {}
        }

        relationship = graph_builder._detect_memory_relationship(memory1, memory2)

        assert relationship is not None
        assert relationship.type in [RelationshipType.CAUSED_BY, RelationshipType.LEADS_TO]
        assert relationship.confidence > 0.5

    @pytest.mark.asyncio
    async def test_entity_confidence_scoring(self, graph_builder):
        """Test entity extraction confidence scoring"""
        # Test known patterns with high confidence
        text = "Dr. Jane Smith presented at MIT"
        entities = await graph_builder._extract_entities(text)

        jane_entities = [e for e in entities if "Jane Smith" in e.text]
        assert len(jane_entities) > 0
        assert jane_entities[0].confidence >= 0.8  # High confidence for title pattern

        mit_entities = [e for e in entities if "MIT" in e.text]
        assert len(mit_entities) > 0
        assert mit_entities[0].confidence >= 0.8  # High confidence for known org

    @pytest.mark.asyncio
    async def test_parallel_entity_extraction(self, graph_builder, mock_db):
        """Test parallel processing of entity extraction"""
        # Create many memories
        memories = [
            {
                "id": f"mem{i}",
                "content": f"Memory {i} about Python and AI",
                "metadata": {}
            }
            for i in range(100)
        ]

        mock_db.get_memories.return_value = memories
        mock_db.store_entities = AsyncMock()
        mock_db.store_entity_mentions = AsyncMock()

        # Should handle large batches efficiently
        graph = await graph_builder.build_graph_from_memories(
            memory_ids=[m["id"] for m in memories],
            include_entities=True,
            include_relationships=False  # Skip relationships for speed
        )

        assert len(graph.nodes) > 0
        # Should have extracted entities from all memories
        assert mock_db.store_entity_mentions.call_count > 0

    @pytest.mark.asyncio
    async def test_graph_caching_integration(self, graph_builder, mock_db):
        """Test integration with graph cache"""
        # First call - should hit database
        mock_db.get_memories.return_value = [
            {"id": "1", "content": "Test memory"}
        ]

        graph1 = await graph_builder.build_graph_from_memories(["1"])

        # Second call - should potentially use cached data
        graph2 = await graph_builder.build_graph_from_memories(["1"])

        # Graphs should be equivalent
        assert len(graph1.nodes) == len(graph2.nodes)
        assert len(graph1.edges) == len(graph2.edges)

    @pytest.mark.asyncio
    async def test_error_handling(self, graph_builder, mock_db):
        """Test error handling in graph builder"""
        # Test with database error
        mock_db.get_memories.side_effect = Exception("Database error")

        # Should handle gracefully
        graph = await graph_builder.build_graph_from_memories(["1", "2"])
        assert graph is not None
        assert len(graph.nodes) == 0  # Empty graph on error

        # Test with invalid memory ID
        mock_db.get_memory.return_value = None
        result = await graph_builder.update_graph_incrementally("graph1", "invalid_id")
        assert result is None  # Should return None for invalid memory

    @pytest.mark.asyncio
    async def test_relationship_type_detection(self, graph_builder):
        """Test accurate detection of different relationship types"""
        test_cases = [
            ("This caused that to happen", "that to happen", RelationshipType.CAUSED_BY),
            ("A is part of B", "B", RelationshipType.PART_OF),
            ("X is similar to Y", "Y", RelationshipType.SIMILAR_TO),
            ("The project depends on funding", "funding", RelationshipType.DEPENDS_ON),
            ("This contradicts the previous statement", "previous statement", RelationshipType.CONTRADICTS),
            ("Learning evolved into mastery", "mastery", RelationshipType.EVOLVED_INTO),
            ("Before the meeting started", "meeting started", RelationshipType.TEMPORAL_BEFORE),
            ("After completing the task", "completing the task", RelationshipType.TEMPORAL_AFTER)
        ]

        for content1, content2, expected_type in test_cases:
            memory1 = {"id": "1", "content": content1, "metadata": {}}
            memory2 = {"id": "2", "content": content2, "metadata": {}}

            relationship = graph_builder._detect_memory_relationship(memory1, memory2)
            assert relationship is not None, f"Should detect relationship in: {content1}"
            assert relationship.type == expected_type, f"Expected {expected_type} for: {content1}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
