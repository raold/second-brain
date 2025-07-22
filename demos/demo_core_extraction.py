"""
Demo script for the enhanced core extraction pipeline with transformers
"""

import asyncio
import json
import logging
from datetime import datetime

from app.ingestion.core_extraction_pipeline import CoreExtractionPipeline
from app.ingestion.models import IngestionConfig, IngestionRequest

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def demo_extraction():
    """Demonstrate the core extraction pipeline capabilities"""

    # Initialize pipeline with transformer models
    print("🚀 Initializing Core Extraction Pipeline with Transformers...")
    config = IngestionConfig(
        entity_model="en_core_web_trf",  # Use transformer model
        min_entity_confidence=0.7,
        min_relationship_confidence=0.6,
        enable_custom_entities=True,
        enable_coreference_resolution=True,
        enable_dependency_parsing=True,
        enable_sentiment_analysis=True
    )

    pipeline = CoreExtractionPipeline(config=config, use_gpu=False)
    print("✅ Pipeline initialized\n")

    # Example texts to process
    test_texts = [
        {
            "name": "Technical Discussion",
            "content": """
            I'm working on integrating PyTorch with our machine learning pipeline at DataCorp. 
            The main challenge is optimizing the transformer models for real-time inference. 
            John Smith from the AI team suggested using ONNX for model optimization, which could 
            reduce latency by 40%. We need to complete this by next Friday for the product launch.
            
            TODO: Benchmark the current model performance
            TODO: Implement ONNX conversion pipeline
            TODO: Set up A/B testing framework
            
            The project repository is at https://github.com/datacorp/ml-pipeline
            """
        },
        {
            "name": "Meeting Notes",
            "content": """
            Meeting with Sarah Johnson (CEO) and Michael Chen (CTO) about Q4 roadmap.
            
            Key decisions:
            1. We will prioritize the mobile app development over the web platform
            2. The budget for cloud infrastructure will be increased by $50,000
            3. New hiring freeze until January 2024
            
            Sarah emphasized that customer retention is critical. Our current churn rate 
            of 15% needs to drop below 10% by year end. Michael will lead the technical 
            initiatives to improve app performance.
            
            Next meeting scheduled for December 15th at 2:00 PM PST.
            """
        },
        {
            "name": "Research Notes",
            "content": """
            Exploring the relationship between deep learning and cognitive science. Recent papers 
            by Dr. Emma Watson at MIT show promising connections between transformer attention 
            mechanisms and human visual attention patterns. This could revolutionize how we 
            design neural architectures.
            
            Key insights:
            - Attention weights correlate with eye-tracking data (r=0.82)
            - Multi-head attention mirrors parallel processing in the brain
            - Self-attention resembles working memory mechanisms
            
            I think this research opens new possibilities for explainable AI. What if we could 
            design models that not only perform well but also process information in ways that 
            align with human cognition?
            """
        }
    ]

    # Process each text
    for test_case in test_texts:
        print(f"{'='*80}")
        print(f"📝 Processing: {test_case['name']}")
        print(f"{'='*80}\n")

        # Create ingestion request
        request = IngestionRequest(
            content=test_case['content'],
            extract_entities=True,
            extract_relationships=True,
            extract_topics=True,
            detect_intent=True,
            extract_structured=True,
            generate_embeddings=True
        )

        # Process the content
        response = await pipeline.process(request)

        # Display results
        if response.status == "completed" and response.processed_content:
            content = response.processed_content

            # Entities
            print(f"🔍 Extracted Entities ({len(content.entities)}):")
            for entity in content.entities[:10]:  # Show first 10
                print(f"  - {entity.text} ({entity.type.value}) [confidence: {entity.confidence:.2f}]")
            if len(content.entities) > 10:
                print(f"  ... and {len(content.entities) - 10} more entities")
            print()

            # Relationships
            print(f"🔗 Detected Relationships ({len(content.relationships)}):")
            for rel in content.relationships[:5]:  # Show first 5
                print(f"  - {rel.source.text} --[{rel.type.value}]--> {rel.target.text} [confidence: {rel.confidence:.2f}]")
            if len(content.relationships) > 5:
                print(f"  ... and {len(content.relationships) - 5} more relationships")
            print()

            # Intent
            if content.intent:
                print(f"🎯 Intent: {content.intent.type.value} [confidence: {content.intent.confidence:.2f}]")
                if content.intent.urgency:
                    print(f"  - Urgency: {content.intent.urgency:.2f}")
                if content.intent.sentiment is not None:
                    print(f"  - Sentiment: {content.intent.sentiment:.2f}")
                if content.intent.action_items:
                    print("  - Action Items:")
                    for item in content.intent.action_items:
                        print(f"    • {item}")
            print()

            # Topics
            if content.topics:
                print(f"📊 Topics ({len(content.topics)}):")
                for topic in content.topics:
                    print(f"  - {topic.name} [relevance: {topic.relevance:.2f}]")
                    if topic.keywords:
                        print(f"    Keywords: {', '.join(topic.keywords[:5])}")
            print()

            # Quality Assessment
            print("✨ Quality Assessment:")
            print(f"  - Content Quality: {content.quality.value}")
            print(f"  - Completeness: {content.completeness_score:.2f}")
            print(f"  - Suggested Importance: {content.suggested_importance:.2f}")
            print(f"  - Suggested Memory Type: {content.suggested_memory_type}")
            print()

            # Embeddings
            if content.embeddings:
                print("🧮 Embeddings Generated:")
                for emb_type in content.embeddings:
                    print(f"  - {emb_type}: {len(content.embeddings[emb_type])} dimensions")
            print()

            # Processing Stats
            print("⚡ Processing Stats:")
            for key, value in response.processing_stats.items():
                if isinstance(value, dict):
                    print(f"  - {key}:")
                    for k, v in value.items():
                        print(f"    • {k}: {v}")
                else:
                    print(f"  - {key}: {value}")
            print()

        else:
            print(f"❌ Processing failed: {response.errors}")
            print()

    # Show pipeline info
    print(f"\n{'='*80}")
    print("🔧 Pipeline Configuration:")
    print(f"{'='*80}")
    pipeline_info = pipeline.get_pipeline_info()
    print(json.dumps(pipeline_info, indent=2))


async def demo_batch_processing():
    """Demonstrate batch processing capabilities"""
    print("\n" + "="*80)
    print("📦 Batch Processing Demo")
    print("="*80 + "\n")

    # Initialize pipeline
    pipeline = CoreExtractionPipeline()

    # Create multiple requests
    requests = [
        IngestionRequest(
            content="Apple Inc. announced new iPhone 15 with advanced AI features.",
            extract_entities=True,
            extract_relationships=True
        ),
        IngestionRequest(
            content="TODO: Review the quarterly report before the meeting tomorrow at 3 PM.",
            detect_intent=True,
            extract_entities=True
        ),
        IngestionRequest(
            content="The research paper by Dr. Smith explores quantum computing applications in cryptography.",
            extract_topics=True,
            extract_entities=True
        )
    ]

    # Process in batch
    start_time = datetime.now()
    responses = await pipeline.batch_process(requests)
    batch_time = (datetime.now() - start_time).total_seconds()

    print(f"⏱️  Batch processed {len(requests)} requests in {batch_time:.2f} seconds")
    print(f"📊 Average time per request: {batch_time/len(requests):.2f} seconds\n")

    # Show summary
    for i, response in enumerate(responses):
        if response.status == "completed" and response.processed_content:
            content = response.processed_content
            print(f"Request {i+1}: {response.status}")
            print(f"  - Entities: {len(content.entities)}")
            print(f"  - Intent: {content.intent.type.value if content.intent else 'N/A'}")
            print(f"  - Topics: {len(content.topics)}")
        else:
            print(f"Request {i+1}: {response.status} - {response.errors}")


async def main():
    """Run all demos"""
    print("\n🎯 Enhanced Core Extraction Pipeline Demo with Transformers\n")

    # Run extraction demo
    await demo_extraction()

    # Run batch processing demo
    await demo_batch_processing()

    print("\n✅ Demo completed!")


if __name__ == "__main__":
    # Note: Download required models first:
    # python -m spacy download en_core_web_sm
    # python -m spacy download en_core_web_lg
    # python -m spacy download en_core_web_trf

    asyncio.run(main())
