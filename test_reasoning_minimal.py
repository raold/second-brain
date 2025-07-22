"""
Minimal test for reasoning engine feature branch
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.reasoning_engine import ReasoningEngine, ReasoningType


async def test_reasoning_basic():
    """Test basic reasoning engine functionality"""
    print("🧠 Testing Reasoning Engine v2.6.0-reasoning")

    # Mock database for testing
    class MockDB:
        async def contextual_search(self, query, limit=10, importance_threshold=0.0):
            return [
                {
                    "id": "mem1",
                    "content": "Started learning Python programming",
                    "contextual_score": 0.9,
                    "memory_type": "episodic",
                    "importance_score": 0.8,
                    "created_at": "2024-01-01"
                }
            ]

    db = MockDB()
    engine = ReasoningEngine(db)

    # Test reasoning type detection
    assert engine._detect_reasoning_type("What caused this?") == ReasoningType.CAUSAL
    assert engine._detect_reasoning_type("What happened before?") == ReasoningType.TEMPORAL
    assert engine._detect_reasoning_type("How has this evolved?") == ReasoningType.EVOLUTIONARY
    print("✅ Reasoning type detection works")

    # Test query parsing
    query = await engine._parse_query("What caused me to learn Python?", max_hops=3, reasoning_type=None)
    assert query.reasoning_type == ReasoningType.CAUSAL
    assert query.max_hops == 3
    print("✅ Query parsing works")

    # Test input validation
    try:
        await engine.multi_hop_query("", max_hops=3)
        assert False, "Should have failed with empty query"
    except ValueError:
        print("✅ Input validation works")

    try:
        await engine.multi_hop_query("test", max_hops=20)
        assert False, "Should have failed with too many hops"
    except ValueError:
        print("✅ Hop limit validation works")

    print("🎉 All basic reasoning engine tests passed!")
    return True


async def main():
    """Run the test"""
    try:
        success = await test_reasoning_basic()
        print("\n✅ Reasoning Engine Feature Test: PASSED")
        return True
    except Exception as e:
        print(f"\n❌ Reasoning Engine Feature Test: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
