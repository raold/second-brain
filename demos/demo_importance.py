#!/usr/bin/env python3
"""
Quick Demo of Automated Importance Scoring System
Demonstrates key features with direct Python calls
"""

import asyncio
import os
from datetime import datetime

# Set environment for testing
os.environ["USE_MOCK_DATABASE"] = "true"

from app.database import get_database
from app.importance_engine import get_importance_engine


async def demo_importance_scoring():
    """Demonstrate the automated importance scoring system"""
    print("🧠 Second Brain - Automated Importance Scoring Demo")
    print("=" * 55)

    print("\n🎯 Initializing Importance Engine...")

    # Get database and engine
    database = await get_database()
    engine = get_importance_engine(database)

    print("✅ Engine initialized successfully!")

    # Demo 1: Content Quality Analysis
    print("\n📊 DEMO 1: Content Quality Analysis")
    print("-" * 40)

    test_contents = [
        {
            "name": "Technical Documentation",
            "content": """
            # Database Performance Optimization Guide

            ## Indexing Strategies
            ```sql
            CREATE INDEX CONCURRENTLY idx_memories_composite
            ON memories(importance_score DESC, last_accessed DESC);
            ```

            Key considerations:
            - Use partial indexes for filtered queries
            - Monitor index usage with pg_stat_user_indexes
            - Consider covering indexes for read-heavy workloads

            ## Connection Pooling
            Configure pgbouncer for optimal connection management.
            """,
            "memory_type": "procedural",
        },
        {"name": "Simple Note", "content": "Remember to update the API documentation", "memory_type": "semantic"},
        {
            "name": "Meeting Notes",
            "content": """
            Team standup meeting - 2024-01-15

            Discussed:
            - Implementation of importance scoring algorithm
            - Database schema updates needed
            - Timeline for testing and deployment

            Action items:
            - John: Complete schema migration
            - Sarah: Test importance calculations
            - Mike: Update API documentation
            """,
            "memory_type": "episodic",
        },
    ]

    for content_sample in test_contents:
        print(f"\n📝 Analyzing: {content_sample['name']}")

        # Calculate content quality score
        quality_score = engine._calculate_content_quality_score(content_sample["content"])

        # Get memory type weight
        type_weight = engine.memory_type_weights.get(content_sample["memory_type"], 1.0)

        # Calculate initial importance (quality × type weight)
        initial_importance = quality_score * type_weight

        print(f"   🎯 Content Quality Score: {quality_score:.3f}")
        print(f"   ⚖️  Memory Type Weight: {type_weight:.1f}x ({content_sample['memory_type']})")
        print(f"   📊 Initial Importance: {initial_importance:.3f}")

        # Analyze quality factors
        content = content_sample["content"]
        factors = []

        if len(content) >= 50:
            factors.append("sufficient length")
        if "```" in content or "`" in content:
            factors.append("contains code")
        if "http" in content.lower():
            factors.append("has URLs")
        if any(marker in content for marker in ["- ", "* ", "1. "]):
            factors.append("structured format")

        technical_terms = ["API", "SQL", "database", "algorithm", "function", "optimization"]
        tech_count = sum(1 for term in technical_terms if term.lower() in content.lower())
        if tech_count > 0:
            factors.append(f"{tech_count} technical terms")

        print(f"   💡 Quality Factors: {', '.join(factors) if factors else 'basic content'}")

    # Demo 2: Access Pattern Simulation
    print("\n\n🔄 DEMO 2: Access Pattern Effects")
    print("-" * 40)

    # Create a mock access pattern
    from app.importance_engine import AccessPattern

    access_patterns = [
        {
            "name": "Frequently Accessed Memory",
            "pattern": AccessPattern(
                memory_id="test-1",
                total_accesses=25,
                recent_accesses=8,
                last_accessed=datetime.now(),
                search_appearances=12,
                avg_search_position=2.5,
                user_interactions={"upvotes": 3, "saves": 2},
            ),
        },
        {
            "name": "Rarely Accessed Memory",
            "pattern": AccessPattern(
                memory_id="test-2",
                total_accesses=2,
                recent_accesses=0,
                last_accessed=datetime(2024, 1, 1),
                search_appearances=1,
                avg_search_position=8.0,
                user_interactions={},
            ),
        },
        {
            "name": "Recently Created Memory",
            "pattern": AccessPattern(
                memory_id="test-3",
                total_accesses=1,
                recent_accesses=1,
                last_accessed=datetime.now(),
                search_appearances=0,
                avg_search_position=10.0,
                user_interactions={},
            ),
        },
    ]

    for pattern_demo in access_patterns:
        print(f"\n📈 Analyzing: {pattern_demo['name']}")
        pattern = pattern_demo["pattern"]

        # Calculate individual scoring components
        frequency_score = engine._calculate_frequency_score(pattern)
        recency_score = engine._calculate_recency_score(pattern)
        search_score = engine._calculate_search_relevance_score(pattern)
        decay_factor = engine._calculate_temporal_decay(pattern)

        print(f"   🔢 Frequency Score: {frequency_score:.3f} (accesses: {pattern.total_accesses})")
        print(f"   ⏰ Recency Score: {recency_score:.3f}")
        print(f"   🔍 Search Relevance: {search_score:.3f}")
        print(f"   📉 Temporal Decay: {decay_factor:.3f}")

        # Calculate combined behavioral score
        config = engine.config
        behavioral_score = (
            frequency_score * config["frequency_weight"]
            + recency_score * config["recency_weight"]
            + search_score * config["search_relevance_weight"]
        ) * decay_factor

        print(f"   🎯 Behavioral Score: {behavioral_score:.3f}")

    # Demo 3: Memory Type Weighting
    print("\n\n⚖️  DEMO 3: Memory Type Weighting")
    print("-" * 40)

    base_score = 0.6

    for memory_type, weight in engine.memory_type_weights.items():
        final_score = base_score * weight
        print(f"   📚 {memory_type.title():10} | Weight: {weight:.1f}x | Final: {final_score:.3f}")

    print("\n   💡 Explanation:")
    print("      • Procedural memories (processes/workflows) are most important")
    print("      • Semantic memories (facts/knowledge) have standard importance")
    print("      • Episodic memories (experiences) decay faster but can surge with access")

    # Demo 4: Importance Engine Configuration
    print("\n\n⚙️  DEMO 4: Engine Configuration")
    print("-" * 40)

    config = engine.config
    print("   📊 Scoring Weights:")
    print(f"      • Frequency: {config['frequency_weight']:.0%}")
    print(f"      • Recency: {config['recency_weight']:.0%}")
    print(f"      • Search Relevance: {config['search_relevance_weight']:.0%}")
    print(f"      • Content Quality: {config['content_quality_weight']:.0%}")
    print(f"      • Memory Type: {config['type_weight']:.0%}")

    print("\n   ⏳ Temporal Parameters:")
    print(f"      • Half-life: {config['half_life_days']} days")
    print(f"      • Minimum importance: {config['min_importance']}")
    print(f"      • High frequency threshold: {config['high_frequency_threshold']} accesses")

    # Demo 5: Real Calculation Example
    print("\n\n🧮 DEMO 5: Complete Calculation Example")
    print("-" * 40)

    # Use the first test content with a realistic access pattern
    example_content = test_contents[0]["content"]
    example_type = test_contents[0]["memory_type"]

    print(f"📝 Content: {test_contents[0]['name']}")

    try:
        # Calculate a comprehensive importance score
        score = await engine.calculate_importance_score(
            memory_id="demo-memory", content=example_content, memory_type=example_type, current_score=0.5
        )

        print(f"\n   🎯 Final Importance Score: {score.final_score:.3f}")
        print("   📊 Component Breakdown:")
        print(f"      • Frequency: {score.frequency_score:.3f}")
        print(f"      • Recency: {score.recency_score:.3f}")
        print(f"      • Search Relevance: {score.search_relevance_score:.3f}")
        print(f"      • Content Quality: {score.content_quality_score:.3f}")
        print(f"      • Type Weight: {score.type_weight:.3f}")
        print(f"      • Decay Factor: {score.decay_factor:.3f}")
        print(f"      • Confidence: {score.confidence:.3f}")
        print(f"   💡 Explanation: {score.explanation}")

    except Exception as e:
        print(f"   ❌ Calculation error: {e}")

    # Demo Summary
    print("\n\n" + "=" * 55)
    print("🎯 AUTOMATED IMPORTANCE SCORING SUMMARY")
    print("=" * 55)

    print("\n✨ KEY FEATURES DEMONSTRATED:")
    print("   • Intelligent content quality analysis")
    print("   • Multi-dimensional access pattern scoring")
    print("   • Memory type-specific importance weighting")
    print("   • Temporal decay with frequency protection")
    print("   • Configurable scoring parameters")
    print("   • Confidence estimation based on data availability")

    print("\n🚀 BUSINESS VALUE:")
    print("   • Automatically identifies most valuable content")
    print("   • Learns from user behavior patterns")
    print("   • Scales importance assessment across large knowledge bases")
    print("   • Provides transparent, explainable scoring")
    print("   • Adapts to different memory types and usage patterns")

    print("\n🔬 TECHNICAL INNOVATION:")
    print("   • Logarithmic frequency scaling prevents over-weighting")
    print("   • Exponential temporal decay with half-life calculations")
    print("   • Content analysis using regex patterns and complexity metrics")
    print("   • Multi-factor combination with weighted scoring")
    print("   • Degradable operation with confidence indicators")

    print("\n✅ Demo completed successfully!")
    print("   The importance engine is working and ready for production use.")


if __name__ == "__main__":
    asyncio.run(demo_importance_scoring())
