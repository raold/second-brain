#!/usr/bin/env python3
"""
Test script for the newly implemented services.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.domain_classifier import DomainClassifier
from app.services.topic_classifier import TopicClassifier
from app.services.structured_data_extractor import StructuredDataExtractor
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


async def test_domain_classifier():
    """Test the DomainClassifier service"""
    logger.info("Testing DomainClassifier...")
    
    classifier = DomainClassifier(use_ai=False)  # Start without AI
    
    # Test content
    test_content = """
    Python Programming Tutorial
    
    In this tutorial, we'll learn about Python programming language and its key features.
    Python is a high-level, interpreted programming language known for its simplicity.
    
    Key concepts we'll cover:
    - Variables and data types
    - Functions and classes
    - Object-oriented programming
    - Working with APIs and databases
    
    Let's start with a simple example:
    
    def hello_world():
        print("Hello, World!")
    
    Python is widely used in web development, data science, machine learning, and automation.
    The language has a vast ecosystem of libraries and frameworks like Django, Flask, NumPy, and TensorFlow.
    """
    
    # Test topic extraction
    topics = classifier.extract_topics(test_content)
    logger.info(f"Extracted {len(topics)} topics:")
    for topic in topics[:5]:
        logger.info(f"  - {topic.name} (confidence: {topic.confidence:.2f})")
    
    # Test advanced topic extraction
    advanced_topics = classifier.extract_advanced_topics(test_content)
    logger.info(f"\nExtracted {len(advanced_topics)} advanced topics")
    
    # Test topic statistics
    stats = classifier.get_topic_statistics(topics)
    logger.info(f"\nTopic statistics: {stats}")
    
    # Test domain classification
    domain_result = classifier.classify_domain(test_content)
    logger.info(f"\nDomain classification: {domain_result}")
    
    # Test structured data extraction
    structured_data = classifier.extract_structured_data(test_content)
    logger.info(f"\nStructured data extracted:")
    logger.info(f"  - Key-value pairs: {len(structured_data.key_value_pairs)}")
    logger.info(f"  - Lists: {len(structured_data.lists)}")
    logger.info(f"  - Code snippets: {len(structured_data.code_snippets)}")


async def test_topic_classifier():
    """Test the TopicClassifier service"""
    logger.info("\n\nTesting TopicClassifier...")
    
    classifier = TopicClassifier(use_ai=False, n_topics=5)
    
    # Test content with multiple paragraphs for LDA
    test_content = """
    Machine Learning Fundamentals
    
    Machine learning is a subset of artificial intelligence that focuses on building systems
    that learn from data. Instead of being explicitly programmed, these systems improve
    their performance through experience.
    
    Supervised Learning
    
    In supervised learning, algorithms learn from labeled training data. Common algorithms
    include linear regression, decision trees, and neural networks. Applications include
    spam detection, image classification, and predictive analytics.
    
    Unsupervised Learning
    
    Unsupervised learning deals with unlabeled data. Algorithms like k-means clustering,
    hierarchical clustering, and PCA help discover hidden patterns. Use cases include
    customer segmentation, anomaly detection, and dimensionality reduction.
    
    Deep Learning
    
    Deep learning uses neural networks with multiple layers. Convolutional neural networks
    excel at image processing, while recurrent neural networks handle sequential data.
    Transformers have revolutionized natural language processing tasks.
    
    Practical Applications
    
    Machine learning powers recommendation systems, autonomous vehicles, medical diagnosis,
    and financial fraud detection. The field continues to evolve with advances in
    hardware acceleration and algorithm efficiency.
    """
    
    # Test basic topic extraction
    topics = classifier.extract_topics(test_content)
    logger.info(f"Extracted {len(topics)} topics using LDA")
    
    for topic in topics[:3]:
        logger.info(f"\nTopic: {topic.name}")
        logger.info(f"  Prevalence: {topic.prevalence:.3f}")
        logger.info(f"  Coherence: {topic.coherence_score:.3f}")
        logger.info(f"  Top keywords: {[kw[0] for kw in topic.keywords[:5]]}")
    
    # Test advanced topics with hierarchy
    advanced_topics = classifier.extract_advanced_topics(test_content)
    logger.info(f"\nAdvanced topics with hierarchy: {len(advanced_topics)} topics")
    
    # Test topic statistics
    stats = classifier.get_topic_statistics(advanced_topics)
    logger.info(f"\nTopic statistics:")
    logger.info(f"  - Average coherence: {stats.get('average_coherence', 0):.3f}")
    logger.info(f"  - Topic diversity: {stats.get('topic_diversity', 0):.3f}")
    logger.info(f"  - Hierarchical depth: {stats.get('hierarchical_depth', 0)}")
    
    # Test structured data extraction
    structured = classifier.extract_structured_data(test_content)
    logger.info(f"\nStructured topic data:")
    logger.info(f"  - Topic models: {len(structured.get('topic_models', []))}")
    logger.info(f"  - Keyword index entries: {len(structured.get('keyword_index', {}))}")
    
    # Test domain classification
    domains = classifier.classify_domain(test_content)
    logger.info(f"\nDomain classification: {domains}")


async def test_structured_data_extractor():
    """Test the StructuredDataExtractor service"""
    logger.info("\n\nTesting StructuredDataExtractor...")
    
    extractor = StructuredDataExtractor(use_ai=False)
    
    # Test content with various structured elements
    test_content = """
    # Project Documentation
    
    Project Name: Second Brain AI System
    Version: 3.0.0
    Author: AI Team
    Created: 2024-01-15
    Status: In Development
    
    ## Overview
    
    The Second Brain system provides:
    - Intelligent memory management
    - Content analysis and classification
    - Knowledge graph construction
    - Semantic search capabilities
    
    ## Technical Specifications
    
    | Component | Technology | Version |
    |-----------|------------|---------|
    | Backend | FastAPI | 0.104.1 |
    | Database | PostgreSQL | 15.0 |
    | ML Framework | PyTorch | 2.0.1 |
    | Vector Store | pgvector | 0.5.0 |
    
    ## Code Example
    
    ```python
    from app.services.memory_service import MemoryService
    
    class MemoryManager:
        def __init__(self):
            self.service = MemoryService()
        
        async def create_memory(self, content: str):
            return await self.service.create(content)
    ```
    
    ## Configuration
    
    Database URL: postgresql://user:pass@localhost/secondbrain
    Redis URL: redis://localhost:6379
    API Port: 8000
    
    ## TODO List
    
    1. Implement real-time synchronization
    2. Add multi-user support
    3. Enhance security features
    4. Optimize query performance
    
    Contact: team@example.com
    Website: https://secondbrain.ai
    """
    
    # Test basic extraction
    data = extractor.extract_structured_data(test_content)
    
    logger.info("Extracted structured data:")
    logger.info(f"\nKey-value pairs ({len(data.key_value_pairs)}):")
    for key, value in list(data.key_value_pairs.items())[:5]:
        logger.info(f"  - {key}: {value}")
    
    logger.info(f"\nLists ({len(data.lists)}):")
    for lst in data.lists[:2]:
        logger.info(f"  - {lst.list_type} list ({len(lst.items)} items)")
        if lst.title:
            logger.info(f"    Title: {lst.title}")
        for item in lst.items[:3]:
            logger.info(f"    • {item}")
    
    logger.info(f"\nTables ({len(data.tables)}):")
    for table in data.tables:
        logger.info(f"  - Table type: {table.table_type}")
        logger.info(f"    Headers: {table.headers}")
        logger.info(f"    Rows: {len(table.rows)}")
    
    logger.info(f"\nCode snippets ({len(data.code_snippets)}):")
    for snippet in data.code_snippets:
        logger.info(f"  - Language: {snippet.language}")
        logger.info(f"    Lines: {snippet.line_count}")
        logger.info(f"    Functions: {snippet.functions}")
        logger.info(f"    Classes: {snippet.classes}")
    
    logger.info(f"\nEntities ({len(data.entities)}):")
    entity_types = {}
    for entity in data.entities:
        entity_types[entity.entity_type] = entity_types.get(entity.entity_type, 0) + 1
    for etype, count in entity_types.items():
        logger.info(f"  - {etype}: {count}")
    
    # Test statistics
    stats = extractor.get_extraction_statistics(data)
    logger.info(f"\nExtraction statistics:")
    logger.info(f"  - Total elements: {stats.get('total_structured_elements', 0)}")
    logger.info(f"  - Has structured data: {any([data.key_value_pairs, data.lists, data.tables, data.code_snippets])}")
    
    # Test topic extraction
    topics = extractor.extract_topics(test_content)
    logger.info(f"\nExtracted topics: {len(topics)}")
    for topic in topics[:3]:
        logger.info(f"  - {topic.get('type')}: {topic.get('title', topic.get('term', 'Unknown'))}")


async def main():
    """Run all tests"""
    logger.info("Starting service tests...\n")
    
    try:
        # Test each service
        await test_domain_classifier()
        await test_topic_classifier()
        await test_structured_data_extractor()
        
        logger.info("\n\nAll tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    # Run the tests
    exit_code = asyncio.run(main())
    sys.exit(exit_code)