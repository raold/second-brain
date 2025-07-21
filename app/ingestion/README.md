# Enhanced Ingestion System with Transformers

This directory contains the sophisticated ingestion engine that powers content extraction, entity recognition, relationship detection, and semantic understanding using state-of-the-art transformer models.

## 🚀 Features

### Entity Extraction with spaCy Transformers
- **Transformer-based NER**: Uses `en_core_web_trf` for superior entity recognition
- **Custom Entity Patterns**: Domain-specific patterns for technology, projects, etc.
- **GPU Acceleration**: Optional GPU support for faster processing
- **Fallback Models**: Gracefully degrades to smaller models if transformers unavailable
- **Entity Context**: Extract entities with surrounding context for better understanding

### Relationship Detection
- **Dependency Parsing**: Advanced syntax analysis for relationship extraction
- **Transformer Similarity**: Semantic similarity using transformer embeddings
- **Pattern Matching**: Rule-based patterns for common relationships
- **Contextual Analysis**: Understands relationships based on surrounding text
- **Multiple Detection Methods**: Combines multiple approaches for better accuracy

### Automatic Embedding Generation
- **Multiple Models**: Support for OpenAI, Sentence-Transformers, and more
- **Auto Model Selection**: Automatically chooses best available model
- **Chunking Support**: Handles long documents with overlapping chunks
- **Caching**: Efficient embedding reuse for repeated content
- **Dimension Reduction**: Can reduce embedding dimensions when needed

### Intent Classification
- **Zero-Shot Classification**: Uses BART for intent recognition without training
- **Pattern-Based Fallback**: Rule-based detection when transformers unavailable
- **Action Item Extraction**: Automatically identifies TODOs and action items
- **Urgency Detection**: Assesses content urgency based on linguistic cues
- **Sentiment Analysis**: Optional sentiment scoring using TextBlob

## 📦 Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

2. Download spaCy models:
```bash
# Transformer model (best quality, ~500MB)
python -m spacy download en_core_web_trf

# Large model (good quality, ~800MB) 
python -m spacy download en_core_web_lg

# Small model (fast, ~50MB)
python -m spacy download en_core_web_sm
```

3. Optional: Install CUDA for GPU acceleration
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

## 🔧 Usage

### Basic Usage

```python
from app.ingestion.core_extraction_pipeline import CoreExtractionPipeline
from app.ingestion.models import IngestionRequest

# Initialize pipeline
pipeline = CoreExtractionPipeline(use_gpu=False)

# Create request
request = IngestionRequest(
    content="Apple Inc. announced the iPhone 15 with AI features.",
    extract_entities=True,
    extract_relationships=True,
    detect_intent=True,
    generate_embeddings=True
)

# Process content
response = await pipeline.process(request)

# Access results
if response.status == "completed":
    content = response.processed_content
    print(f"Entities: {[e.text for e in content.entities]}")
    print(f"Intent: {content.intent.type.value}")
```

### Advanced Configuration

```python
from app.ingestion.models import IngestionConfig

# Custom configuration
config = IngestionConfig(
    entity_model="en_core_web_trf",
    embedding_model="all-mpnet-base-v2",
    min_entity_confidence=0.8,
    min_relationship_confidence=0.7,
    enable_custom_entities=True,
    chunk_size=1000,
    chunk_overlap=200
)

pipeline = CoreExtractionPipeline(config=config, use_gpu=True)
```

### Batch Processing

```python
# Process multiple documents efficiently
requests = [
    IngestionRequest(content=doc) for doc in documents
]

responses = await pipeline.batch_process(requests)
```

## 🏗️ Architecture

### Core Components

1. **EntityExtractor** (`entity_extractor.py`)
   - SpaCy transformer models
   - Custom entity patterns
   - Confidence scoring
   - Entity normalization

2. **RelationshipDetector** (`relationship_detector.py`)
   - Dependency parsing
   - Transformer embeddings
   - Pattern matching
   - Proximity analysis

3. **EmbeddingGenerator** (`embedding_generator.py`)
   - Multiple model support
   - Async generation
   - Chunking strategies
   - Similarity calculations

4. **IntentRecognizer** (`intent_recognizer.py`)
   - Zero-shot classification
   - Pattern matching
   - Action item extraction
   - Urgency assessment

5. **CoreExtractionPipeline** (`core_extraction_pipeline.py`)
   - Orchestrates all components
   - Quality assessment
   - Batch processing
   - Error handling

### Data Models

All data models are defined in `models.py`:
- `Entity`: Extracted entity with type, position, and confidence
- `Relationship`: Connection between entities
- `Intent`: User intent with urgency and action items
- `ProcessedContent`: Complete extraction results
- `IngestionConfig`: Pipeline configuration

## 🎯 Use Cases

1. **Knowledge Management**
   - Extract key concepts and relationships from documents
   - Build knowledge graphs automatically
   - Identify important information

2. **Task Management**
   - Extract action items from meeting notes
   - Identify deadlines and urgency
   - Track decisions and problems

3. **Content Analysis**
   - Understand document topics and themes
   - Assess content quality
   - Generate tags and categories

4. **Search Enhancement**
   - Generate semantic embeddings
   - Enable similarity search
   - Improve retrieval accuracy

## 🔍 Demo

Run the demo to see all features in action:

```bash
python demos/demo_core_extraction.py
```

This will demonstrate:
- Entity extraction from technical discussions
- Relationship detection in meeting notes
- Intent recognition with action items
- Topic classification
- Batch processing performance

## 🚦 Performance Tips

1. **Model Selection**
   - Use transformer models for best quality
   - Use large models for good balance
   - Use small models for speed

2. **GPU Acceleration**
   - Enable GPU for 2-5x speedup
   - Batch process documents
   - Use async processing

3. **Caching**
   - Enable embedding cache
   - Reuse pipeline instances
   - Process similar content together

## 📊 Metrics

Typical performance on modern hardware:
- Entity extraction: 50-200ms per document
- Relationship detection: 100-300ms per document  
- Embedding generation: 50-150ms per document
- Full pipeline: 200-500ms per document

With GPU acceleration:
- 2-5x faster processing
- Better for batch processing
- Handles longer documents efficiently