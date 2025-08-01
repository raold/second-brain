"""
Data models for the sophisticated ingestion engine
"""

from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum
from pydantic import field_validator

class EntityType(str, Enum):
    """Types of entities that can be extracted"""

    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    DATE = "date"
    TIME = "time"
    PROJECT = "project"
    TECHNOLOGY = "technology"
    CONCEPT = "concept"
    URL = "url"
    EMAIL = "email"
    PHONE = "phone"
    CUSTOM = "custom"

class RelationshipType(str, Enum):
    """Types of relationships between entities"""

    RELATED_TO = "related_to"
    PART_OF = "part_of"
    LOCATED_IN = "located_in"
    WORKS_FOR = "works_for"
    CREATED_BY = "created_by"
    MENTIONED_WITH = "mentioned_with"
    TEMPORAL_BEFORE = "temporal_before"
    TEMPORAL_AFTER = "temporal_after"
    TEMPORAL_DURING = "temporal_during"
    CAUSAL = "causal"
    DEPENDS_ON = "depends_on"
    SIMILAR_TO = "similar_to"

class IntentType(str, Enum):
    """Types of user intent in content"""

    QUESTION = "question"
    STATEMENT = "statement"
    TODO = "todo"
    IDEA = "idea"
    DECISION = "decision"
    LEARNING = "learning"
    REFERENCE = "reference"
    REFLECTION = "reflection"
    PLANNING = "planning"
    PROBLEM = "problem"
    SOLUTION = "solution"

class ContentQuality(str, Enum):
    """Quality assessment of content"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INCOMPLETE = "incomplete"

class Entity(BaseModel):
    """Represents an extracted entity"""

    text: str = Field(..., description="The entity text as it appears")
    type: EntityType = Field(..., description="Type of entity")
    normalized: str | None = Field(None, description="Normalized form of entity")
    start_pos: int = Field(..., description="Start position in text")
    end_pos: int = Field(..., description="End position in text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional entity metadata")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))

class Relationship(BaseModel):
    """Represents a relationship between entities"""

    source: Entity = Field(..., description="Source entity")
    target: Entity = Field(..., description="Target entity")
    type: RelationshipType = Field(..., description="Type of relationship")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Relationship confidence")
    evidence: str | None = Field(None, description="Text evidence for relationship")
    metadata: dict[str, Any] = Field(default_factory=dict)

class Topic(BaseModel):
    """Represents an extracted topic"""

    name: str = Field(..., description="Topic name")
    keywords: list[str] = Field(..., description="Associated keywords")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Topic confidence")
    relevance: float = Field(..., ge=0.0, le=1.0, description="Relevance to content")
    hierarchy: list[str] | None = Field(None, description="Topic hierarchy path")

class Intent(BaseModel):
    """Represents extracted user intent"""

    type: IntentType = Field(..., description="Primary intent type")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Intent confidence")
    action_items: list[str] = Field(default_factory=list, description="Extracted action items")
    urgency: float | None = Field(None, ge=0.0, le=1.0, description="Urgency score")
    sentiment: float | None = Field(None, ge=-1.0, le=1.0, description="Sentiment score")

class StructuredData(BaseModel):
    """Represents extracted structured data"""

    key_value_pairs: dict[str, Any] = Field(default_factory=dict)
    lists: dict[str, list[str]] = Field(default_factory=dict)
    tables: list[dict[str, Any]] = Field(default_factory=list)
    code_snippets: list[dict[str, str]] = Field(default_factory=list)
    metadata_fields: dict[str, Any] = Field(default_factory=dict)

class EmbeddingMetadata(BaseModel):
    """Metadata for generated embeddings"""

    model: str = Field(..., description="Model used for embedding")
    dimensions: int = Field(..., description="Embedding dimensions")
    chunk_id: int | None = Field(None, description="Chunk ID if content was chunked")
    chunk_overlap: int | None = Field(None, description="Overlap between chunks")
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class ProcessedContent(BaseModel):
    """Complete processed content with all extractions"""

    # Original content
    original_content: str = Field(..., description="Original input content")
    content_hash: str = Field(..., description="Hash of original content")

    # Extracted entities and relationships
    entities: list[Entity] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)

    # Topics and classification
    topics: list[Topic] = Field(default_factory=list)
    primary_topic: Topic | None = None
    domain: str | None = Field(None, description="Content domain")

    # Intent and metadata
    intent: Intent | None = None
    quality: ContentQuality = Field(default=ContentQuality.MEDIUM)
    completeness_score: float = Field(default=0.5, ge=0.0, le=1.0)

    # Structured data
    structured_data: StructuredData | None = None

    # Embeddings
    embeddings: dict[str, list[float]] = Field(default_factory=dict)
    embedding_metadata: EmbeddingMetadata | None = None

    # Processing metadata
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: int | None = None
    processor_version: str = Field(default="1.0.0")

    # Suggested metadata for storage
    suggested_tags: list[str] = Field(default_factory=list)
    suggested_memory_type: str | None = None
    suggested_importance: float = Field(default=0.5, ge=0.0, le=1.0)

class IngestionRequest(BaseModel):
    """Request model for content ingestion"""

    content: str = Field(..., description="Content to ingest", min_length=1)

    # Optional context
    user_context: dict[str, Any] | None = Field(
        None, description="User context for personalization"
    )
    domain_hint: str | None = Field(None, description="Hint about content domain")
    language: str | None = Field(default="en", description="Content language")

    # Processing options
    extract_entities: bool = Field(default=True)
    extract_relationships: bool = Field(default=True)
    extract_topics: bool = Field(default=True)
    detect_intent: bool = Field(default=True)
    extract_structured: bool = Field(default=True)
    generate_embeddings: bool = Field(default=True)

    # Performance options
    fast_mode: bool = Field(default=False, description="Use faster, less accurate models")
    max_processing_time: int | None = Field(None, description="Max processing time in ms")

class IngestionResponse(BaseModel):
    """Response model for content ingestion"""

    request_id: UUID = Field(..., description="Unique request ID")
    status: str = Field(..., description="Processing status")
    processed_content: ProcessedContent | None = None
    memory_id: str | None = Field(None, description="ID of created memory if stored")
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    processing_stats: dict[str, Any] = Field(default_factory=dict)

class IngestionConfig(BaseModel):
    """Configuration for the ingestion engine"""

    # Model configurations
    entity_model: str = Field(default="en_core_web_sm", description="SpaCy model for NER")
    embedding_model: str = Field(
        default="text-embedding-ada-002", description="OpenAI embedding model"
    )
    classification_model: str = Field(
        default="bert-base-uncased", description="Classification model"
    )

    # Processing thresholds
    min_entity_confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    min_relationship_confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    min_topic_relevance: float = Field(default=0.5, ge=0.0, le=1.0)

    # Performance settings
    max_entities_per_content: int = Field(default=100, ge=1)
    max_relationships_per_content: int = Field(default=50, ge=1)
    max_topics_per_content: int = Field(default=10, ge=1)

    # Chunking settings
    chunk_size: int = Field(default=1000, ge=100)
    chunk_overlap: int = Field(default=200, ge=0)

    # Feature flags
    enable_coreference_resolution: bool = Field(default=True)
    enable_dependency_parsing: bool = Field(default=True)
    enable_sentiment_analysis: bool = Field(default=True)
    enable_custom_entities: bool = Field(default=True)
