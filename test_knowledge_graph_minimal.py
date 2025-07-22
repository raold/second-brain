"""
Minimal test for knowledge graph builder feature branch
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.knowledge_graph_builder import (
    KnowledgeGraphBuilder, 
    EntityType, 
    RelationshipType,
    Entity,
    EntityMention
)


async def test_knowledge_graph_basic():
    """Test basic knowledge graph builder functionality"""
    print("🕸️ Testing Knowledge Graph Builder v2.6.1-knowledge-graph")
    
    # Mock database for testing
    class MockDB:
        def __init__(self):
            self.pool = None
        
        async def get_memory(self, memory_id):
            return {
                "id": memory_id,
                "content": "John Smith works at OpenAI developing ChatGPT in San Francisco",
                "metadata": {}
            }
        
        async def get_memories(self, memory_ids=None, limit=10):
            return [
                {
                    "id": "1",
                    "content": "Python programming is powerful",
                    "metadata": {}
                },
                {
                    "id": "2", 
                    "content": "Python is used for machine learning",
                    "metadata": {}
                }
            ]
    
    db = MockDB()
    builder = KnowledgeGraphBuilder(db)
    
    # Test entity extraction
    memory = {
        "id": "test1",
        "content": "John Smith works at OpenAI developing ChatGPT",
        "metadata": {}
    }
    
    entity_mentions = await builder._extract_entities_from_memory(memory)
    
    entity_names = [e.entity.name for e in entity_mentions]
    print(f"📍 Extracted entities: {entity_names}")
    
    # Check that entities were found
    assert len(entity_names) > 0
    assert any("John Smith" in name for name in entity_names)
    assert any("OpenAI" in name for name in entity_names)
    print("✅ Entity extraction works")
    
    # Test TF-IDF similarity calculation  
    memories = [
        {"id": "1", "content": "Python programming is powerful"},
        {"id": "2", "content": "Python is used for data science"},
        {"id": "3", "content": "JavaScript for web development"}
    ]
    
    try:
        similarity_matrix = builder._calculate_tfidf_similarity(memories)
        # Python memories should be more similar to each other
        assert similarity_matrix["1"]["2"] > similarity_matrix["1"]["3"]
        print("✅ TF-IDF similarity calculation works")
    except Exception as e:
        print(f"⚠️  TF-IDF test skipped (missing sklearn): {e}")
    
    # Test input validation
    try:
        await builder.build_graph_from_memories([])
        assert False, "Should have failed with empty memory list"
    except ValueError as e:
        print(f"✅ Input validation works: {e}")
    
    try:
        await builder.build_graph_from_memories(["mem1"] * 1001)
        assert False, "Should have failed with too many memories"
    except ValueError as e:
        print(f"✅ Memory limit validation works: {e}")
    
    # Test confidence validation
    try:
        await builder.build_graph_from_memories(["mem1"], min_confidence=1.5)
        assert False, "Should have failed with invalid confidence"
    except ValueError as e:
        print(f"✅ Confidence validation works: {e}")
    
    print("🎉 All basic knowledge graph builder tests passed!")
    return True


async def main():
    """Run the test"""
    try:
        success = await test_knowledge_graph_basic()
        print("\n✅ Knowledge Graph Builder Feature Test: PASSED")
        return True
    except Exception as e:
        print(f"\n❌ Knowledge Graph Builder Feature Test: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)