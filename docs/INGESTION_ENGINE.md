# Sophisticated Ingestion Engine Documentation

## Overview

The Second Brain v2.5.2-RC introduces a sophisticated content ingestion engine that automatically extracts rich metadata, entities, relationships, and insights from unstructured text. This NLP-powered pipeline transforms raw content into structured, searchable knowledge.

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Ingestion Pipeline                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Raw Content → Preprocessing → Entity Extraction           │
│                      ↓              ↓                       │
│                Topic Modeling → Relationship Detection      │
│                      ↓              ↓                       │
│               Intent Recognition → Embedding Generation     │
│                      ↓              ↓                       │
│              Structured Data → Content Classification       │
│                      ↓              ↓                       │
│                 Validation → Processed Content              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Basic Usage

```python
from app.ingestion.models import IngestionRequest
from app.ingestion.engine import IngestionEngine

# Initialize engine
engine = IngestionEngine()

# Process content
request = IngestionRequest(
    content="Your text content here",
    extract_entities=True,
    extract_topics=True,
    generate_embeddings=True
)

response = await engine.process(request)
```

### Streaming Usage

```python
from app.ingestion.streaming_ingestion import StreamingIngestionBuilder

# Build streaming pipeline
pipeline = (
    StreamingIngestionBuilder()
    .with_workers(4)
    .with_batch_config(size=10, timeout=5.0)
    .add_preprocessor(preprocess_function)
    .add_processor(process_function)
    .build()
)

# Start pipeline
await pipeline.start()

# Ingest content
message_id = await pipeline.ingest("Your content here")
```

## Component Details

### 1. Entity Extraction (`entity_extractor.py`)

Extracts named entities from text using both SpaCy NER and custom patterns.

**Features:**
- Standard NER: Person, Organization, Location, Date, Time
- Custom entities: Email, URL, Phone, Project, Technology
- Confidence scoring for each entity
- Position tracking (start/end character positions)
- Entity deduplication and normalization

**Example:**
```python
from app.ingestion.entity_extractor import EntityExtractor

extractor = EntityExtractor()
entities = extractor.extract_entities(
    "John Smith works at OpenAI in San Francisco.",
    min_confidence=0.7
)
```

### 2. Topic Modeling (`topic_classifier.py`)

Identifies topics and themes using multiple approaches.

**Features:**
- LDA (Latent Dirichlet Allocation) for unsupervised topic discovery
- Keyword-based classification with predefined topics
- Domain detection (Technology, Business, Science, etc.)
- Hierarchical topic structures
- Topic relevance and confidence scoring

**Example:**
```python
from app.ingestion.topic_classifier import TopicClassifier

classifier = TopicClassifier(n_topics=10)
topics = classifier.extract_topics(
    text,
    min_relevance=0.5,
    max_topics=5
)
```

### 3. Relationship Detection (`relationship_detector.py`)

Discovers connections between entities.

**Features:**
- Dependency parsing using SpaCy
- Pattern-based relationship extraction
- Proximity-based relationships
- Coreference resolution
- Supported types: WORKS_FOR, LOCATED_IN, CREATED_BY, etc.

**Example:**
```python
from app.ingestion.relationship_detector import RelationshipDetector

detector = RelationshipDetector()
relationships = detector.detect_relationships(
    text,
    entities,
    min_confidence=0.6
)
```

### 4. Intent Recognition (`intent_recognizer.py`)

Understands the purpose and urgency of content.

**Features:**
- Intent types: Question, TODO, Idea, Decision, Learning, etc.
- Action item extraction
- Urgency scoring (0-1)
- Sentiment analysis (optional)
- Pattern-based and structural analysis

**Example:**
```python
from app.ingestion.intent_recognizer import IntentRecognizer

recognizer = IntentRecognizer(enable_sentiment=True)
intent = recognizer.recognize_intent(text)
```

### 5. Embedding Generation (`embedding_generator.py`)

Creates vector embeddings for semantic search.

**Features:**
- Multiple model support (Sentence Transformers, OpenAI)
- Document chunking with overlap
- Chunk-level and document-level embeddings
- Similarity calculation
- Embedding caching

**Example:**
```python
from app.ingestion.embedding_generator import EmbeddingGenerator

generator = EmbeddingGenerator(
    model_name="all-MiniLM-L6-v2",
    chunk_size=1000
)
embeddings, metadata = await generator.generate_embeddings(text)
```

### 6. Content Classification (`content_classifier.py`)

Intelligently categorizes and assesses content.

**Features:**
- Quality assessment (HIGH/MEDIUM/LOW/INCOMPLETE)
- Domain classification
- Memory type suggestions
- Importance scoring (0-10)
- Automatic tag generation
- Completeness evaluation

**Example:**
```python
from app.ingestion.content_classifier import ContentClassifier

classifier = ContentClassifier()
classification = classifier.classify_content(processed_content)
```

### 7. Structured Data Extraction (`structured_extractor.py`)

Extracts structured elements from unstructured text.

**Features:**
- Key-value pair extraction
- List detection (bullet, numbered, comma-separated)
- Table extraction (Markdown, ASCII)
- Code snippet detection with language identification
- Metadata field extraction

**Example:**
```python
from app.ingestion.structured_extractor import StructuredDataExtractor

extractor = StructuredDataExtractor()
structured_data = extractor.extract_structured_data(text)
```

### 8. Preprocessing (`preprocessor.py`)

Prepares content for processing.

**Features:**
- Encoding fixes (using ftfy)
- HTML tag removal
- Unicode normalization
- Contraction expansion
- URL/email extraction
- Smart truncation
- Content validation

**Example:**
```python
from app.ingestion.preprocessor import ContentPreprocessor

preprocessor = ContentPreprocessor(
    fix_encoding=True,
    normalize_whitespace=True
)
cleaned_text, metadata = preprocessor.preprocess(text)
```

### 9. Validation Framework (`validator.py`)

Ensures data quality and consistency.

**Features:**
- Multi-level validation (schema, content, extraction, quality)
- Issue severity levels (INFO, WARNING, ERROR, CRITICAL)
- Business rule validation
- Custom validation rules
- Detailed validation reports

**Example:**
```python
from app.ingestion.validator import AdvancedValidator

validator = AdvancedValidator()
result = validator.validate(processed_content)
print(validator.get_validation_report(result))
```

## Configuration

### Engine Configuration

```python
from app.ingestion.models import IngestionConfig

config = IngestionConfig(
    # Model configurations
    entity_model="en_core_web_sm",
    embedding_model="all-MiniLM-L6-v2",
    classification_model="bert-base-uncased",
    
    # Processing thresholds
    min_entity_confidence=0.7,
    min_relationship_confidence=0.6,
    min_topic_relevance=0.5,
    
    # Performance settings
    max_entities_per_content=100,
    max_relationships_per_content=50,
    max_topics_per_content=10,
    
    # Chunking settings
    chunk_size=1000,
    chunk_overlap=200,
    
    # Feature flags
    enable_coreference_resolution=True,
    enable_dependency_parsing=True,
    enable_sentiment_analysis=True
)
```

### Processing Options

```python
request = IngestionRequest(
    content="Your text here",
    
    # Optional context
    user_context={"user_id": "123"},
    domain_hint="technology",
    language="en",
    
    # Processing options
    extract_entities=True,
    extract_relationships=True,
    extract_topics=True,
    detect_intent=True,
    extract_structured=True,
    generate_embeddings=True,
    
    # Performance options
    fast_mode=False,
    max_processing_time=5000  # milliseconds
)
```

## Best Practices

### 1. Content Preparation
- Ensure text is properly encoded (UTF-8)
- Remove or clean HTML if present
- Consider content length for optimal processing

### 2. Model Selection
- Use lightweight models for fast processing
- Use advanced models for better accuracy
- Balance based on your requirements

### 3. Confidence Thresholds
- Higher thresholds = fewer but more accurate results
- Lower thresholds = more results but potential noise
- Adjust based on use case

### 4. Performance Optimization
- Enable caching for repeated content
- Use streaming for large volumes
- Configure appropriate batch sizes
- Monitor processing times

### 5. Error Handling
- Always validate content before processing
- Handle extraction failures gracefully
- Log issues for debugging
- Use validation framework

## Integration with Second Brain

### Memory Creation with Ingestion

```python
# Process content
response = await engine.process(request)
content = response.processed_content

# Create memory with extracted metadata
memory = {
    "content": content.original_content,
    "embeddings": content.embeddings.get("full", []),
    "metadata": {
        "entities": [e.dict() for e in content.entities],
        "topics": [t.dict() for t in content.topics],
        "domain": content.domain,
        "quality": content.quality,
        "importance": content.suggested_importance
    },
    "tags": content.suggested_tags,
    "memory_type": content.suggested_memory_type
}
```

### Search Enhancement

Use extracted entities and topics to enhance search:

```python
# Search by entity
results = await search_by_entity("John Smith", entity_type="person")

# Search by topic
results = await search_by_topic("machine learning")

# Search by relationship
results = await search_by_relationship(
    source="OpenAI",
    relationship_type="CREATED_BY"
)
```

## Troubleshooting

### Common Issues

1. **SpaCy Model Not Found**
   ```bash
   python -m spacy download en_core_web_sm
   ```

2. **High Memory Usage**
   - Reduce batch sizes
   - Enable fast_mode
   - Limit max entities/topics

3. **Slow Processing**
   - Use streaming pipeline
   - Enable parallel processing
   - Consider lighter models

4. **Poor Extraction Quality**
   - Adjust confidence thresholds
   - Provide domain hints
   - Ensure content quality

## Dependencies

### Required
- `pydantic>=2.0`
- `fastapi`
- Python 3.11+

### Optional (for enhanced features)
```bash
pip install spacy
python -m spacy download en_core_web_sm
pip install scikit-learn
pip install sentence-transformers
pip install textblob
pip install beautifulsoup4
pip install ftfy
pip install numpy
```

## API Reference

See the full API documentation in the code files:
- `/app/ingestion/models.py` - Data models
- `/app/ingestion/engine.py` - Main engine (to be implemented)
- Individual component files for specific functionality

## Examples

### Complete Processing Example

```python
import asyncio
from app.ingestion.entity_extractor import EntityExtractor
from app.ingestion.topic_classifier import TopicClassifier
from app.ingestion.relationship_detector import RelationshipDetector
from app.ingestion.intent_recognizer import IntentRecognizer
from app.ingestion.embedding_generator import EmbeddingGenerator
from app.ingestion.content_classifier import ContentClassifier
from app.ingestion.models import ProcessedContent

async def process_content(text: str) -> ProcessedContent:
    # Initialize components
    entity_extractor = EntityExtractor()
    topic_classifier = TopicClassifier()
    relationship_detector = RelationshipDetector()
    intent_recognizer = IntentRecognizer()
    embedding_generator = EmbeddingGenerator()
    content_classifier = ContentClassifier()
    
    # Extract entities
    entities = entity_extractor.extract_entities(text)
    
    # Extract topics
    topics = topic_classifier.extract_topics(text)
    
    # Detect relationships
    relationships = relationship_detector.detect_relationships(text, entities)
    
    # Recognize intent
    intent = intent_recognizer.recognize_intent(text)
    
    # Generate embeddings
    embeddings, embedding_metadata = await embedding_generator.generate_embeddings(text)
    
    # Create processed content
    processed_content = ProcessedContent(
        original_content=text,
        content_hash=hashlib.md5(text.encode()).hexdigest(),
        entities=entities,
        relationships=relationships,
        topics=topics,
        intent=intent,
        embeddings=embeddings,
        embedding_metadata=embedding_metadata
    )
    
    # Classify content
    classification = content_classifier.classify_content(processed_content)
    
    return processed_content

# Run the processing
text = "John Smith, CEO of TechCorp, announced a new AI product today in San Francisco."
result = asyncio.run(process_content(text))
```

---

For more examples and advanced usage, see the test files in `/tests/unit/test_ingestion/`.