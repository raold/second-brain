"""
Test the sophisticated ingestion engine components
"""


import pytest

from app.ingestion.content_classifier import ContentClassifier
from app.ingestion.embedding_generator import EmbeddingGenerator
from app.ingestion.entity_extractor import EntityExtractor
from app.ingestion.intent_recognizer import IntentRecognizer
from app.ingestion.models import (
    ContentQuality,
    Entity,
    EntityType,
    IntentType,
    ProcessedContent,
    RelationshipType,
    Topic,
)
from app.ingestion.preprocessor import ContentPreprocessor
from app.ingestion.relationship_detector import RelationshipDetector
from app.ingestion.structured_extractor import StructuredDataExtractor
from app.ingestion.topic_classifier import TopicClassifier
from app.ingestion.validator import AdvancedValidator, ValidationLevel


class TestEntityExtractor:
    """Test entity extraction"""

    def setup_method(self):
        self.extractor = EntityExtractor(enable_custom=True)

    def test_extract_custom_entities(self):
        """Test custom pattern extraction"""
        text = "Contact john@example.com or visit https://example.com"
        entities = self.extractor.extract_entities(text, min_confidence=0.5)

        # Should find email and URL
        entity_types = {e.type for e in entities}
        assert EntityType.EMAIL in entity_types
        assert EntityType.URL in entity_types

        # Check specific entities
        emails = [e for e in entities if e.type == EntityType.EMAIL]
        assert len(emails) == 1
        assert emails[0].text == "john@example.com"

    def test_extract_dates(self):
        """Test date extraction"""
        text = "The meeting is on 2024-12-25 and the deadline is January 15, 2025"
        entities = self.extractor.extract_entities(text)

        dates = [e for e in entities if e.type == EntityType.DATE]
        assert len(dates) >= 2

    def test_entity_deduplication(self):
        """Test entity deduplication"""
        text = "John works at OpenAI. John is the CEO."
        entities = self.extractor.extract_entities(text)

        # Should deduplicate overlapping entities
        john_entities = [e for e in entities if e.text == "John"]
        assert len(john_entities) <= 2  # One per occurrence, not duplicated


class TestTopicClassifier:
    """Test topic classification"""

    def setup_method(self):
        self.classifier = TopicClassifier(enable_lda=False)  # Disable LDA for unit tests

    def test_keyword_topic_extraction(self):
        """Test keyword-based topic extraction"""
        text = "This project involves software development using Python and machine learning"
        topics = self.classifier.extract_topics(text, min_relevance=0.3)

        topic_names = {t.name for t in topics}
        assert any("Software Development" in name for name in topic_names)

    def test_domain_detection(self):
        """Test domain detection"""
        text = "The latest research in artificial intelligence and neural networks"
        topics = self.classifier.extract_topics(text)

        # Should detect technology domain
        assert any("Technology" in t.name or "technology" in t.keywords for t in topics)

    def test_topic_merging(self):
        """Test similar topic merging"""
        text = "Python programming and software development with Python"
        topics = self.classifier.extract_topics(text)

        # Should merge similar topics
        assert len(topics) < 5  # Not too many duplicate topics


class TestRelationshipDetector:
    """Test relationship detection"""

    def setup_method(self):
        self.detector = RelationshipDetector(enable_patterns=True)

    def test_pattern_based_relationships(self):
        """Test pattern-based relationship detection"""
        text = "John Smith works for OpenAI"
        entities = [
            Entity(text="John Smith", type=EntityType.PERSON, normalized="john smith",
                  start_pos=0, end_pos=10, confidence=0.9),
            Entity(text="OpenAI", type=EntityType.ORGANIZATION, normalized="openai",
                  start_pos=20, end_pos=26, confidence=0.9)
        ]

        relationships = self.detector.detect_relationships(text, entities)

        assert len(relationships) > 0
        assert any(r.type == RelationshipType.WORKS_FOR for r in relationships)

    def test_proximity_relationships(self):
        """Test proximity-based relationships"""
        text = "Apple and Microsoft are technology companies"
        entities = [
            Entity(text="Apple", type=EntityType.ORGANIZATION, normalized="apple",
                  start_pos=0, end_pos=5, confidence=0.9),
            Entity(text="Microsoft", type=EntityType.ORGANIZATION, normalized="microsoft",
                  start_pos=10, end_pos=19, confidence=0.9)
        ]

        relationships = self.detector.detect_relationships(text, entities)

        # Should detect proximity relationship
        assert len(relationships) > 0
        assert any(r.type == RelationshipType.MENTIONED_WITH for r in relationships)


class TestIntentRecognizer:
    """Test intent recognition"""

    def setup_method(self):
        self.recognizer = IntentRecognizer(enable_sentiment=False)

    def test_question_intent(self):
        """Test question intent detection"""
        text = "What is the best way to implement this feature?"
        intent = self.recognizer.recognize_intent(text)

        assert intent.type == IntentType.QUESTION
        assert intent.confidence > 0.7

    def test_todo_intent(self):
        """Test TODO intent detection"""
        text = "TODO: Need to fix the bug in the authentication system"
        intent = self.recognizer.recognize_intent(text)

        assert intent.type == IntentType.TODO
        assert len(intent.action_items) > 0

    def test_urgency_detection(self):
        """Test urgency detection"""
        text = "This is urgent and needs to be done ASAP by tomorrow"
        intent = self.recognizer.recognize_intent(text)

        assert intent.urgency > 0.7


class TestContentClassifier:
    """Test content classification"""

    def setup_method(self):
        self.classifier = ContentClassifier()

    def test_quality_assessment(self):
        """Test content quality assessment"""
        # High quality content
        content = ProcessedContent(
            original_content="A" * 500,  # Long content
            content_hash="test_hash",
            entities=[Entity(text="test", type=EntityType.CONCEPT, normalized="test",
                           start_pos=0, end_pos=4, confidence=0.9)] * 5,
            topics=[Topic(name="Test", keywords=["test"], confidence=0.9, relevance=0.8)],
            relationships=[]
        )

        result = self.classifier.classify_content(content)
        assert content.quality in [ContentQuality.HIGH, ContentQuality.MEDIUM]

    def test_domain_classification(self):
        """Test domain classification"""
        content = ProcessedContent(
            original_content="Machine learning and artificial intelligence research",
            content_hash="test_hash",
            entities=[Entity(text="AI", type=EntityType.TECHNOLOGY, normalized="ai",
                           start_pos=0, end_pos=2, confidence=0.9)],
            topics=[Topic(name="AI Topic", keywords=["ai", "ml"], confidence=0.9, relevance=0.8)]
        )

        result = self.classifier.classify_content(content)
        assert content.domain == "Technology"

    def test_tag_generation(self):
        """Test automatic tag generation"""
        content = ProcessedContent(
            original_content="Python programming tutorial",
            content_hash="test_hash",
            entities=[],
            topics=[Topic(name="Programming", keywords=["python", "code"], confidence=0.9, relevance=0.8)]
        )

        result = self.classifier.classify_content(content)
        assert len(content.suggested_tags) > 0
        assert any("python" in tag.lower() for tag in content.suggested_tags)


class TestStructuredDataExtractor:
    """Test structured data extraction"""

    def setup_method(self):
        self.extractor = StructuredDataExtractor()

    def test_key_value_extraction(self):
        """Test key-value pair extraction"""
        text = """
        Name: John Doe
        Email: john@example.com
        Age: 30
        """

        data = self.extractor.extract_structured_data(text)

        assert "name" in data.key_value_pairs
        assert data.key_value_pairs["name"] == "John Doe"
        assert "email" in data.key_value_pairs
        assert data.key_value_pairs["age"] == 30

    def test_list_extraction(self):
        """Test list extraction"""
        text = """
        TODO List:
        - Fix bug in authentication
        - Update documentation
        - Write tests
        """

        data = self.extractor.extract_structured_data(text)

        assert len(data.lists) > 0
        bullet_list = next(iter(data.lists.values()))
        assert len(bullet_list) == 3

    def test_code_extraction(self):
        """Test code snippet extraction"""
        text = """
        Here's a Python example:
        ```python
        def hello_world():
            print("Hello, World!")
        ```
        """

        data = self.extractor.extract_structured_data(text)

        assert len(data.code_snippets) == 1
        assert data.code_snippets[0]["language"] == "python"
        assert "def hello_world" in data.code_snippets[0]["code"]


class TestPreprocessor:
    """Test content preprocessing"""

    def setup_method(self):
        self.preprocessor = ContentPreprocessor(
            normalize_whitespace=True,
            expand_contractions=True
        )

    def test_whitespace_normalization(self):
        """Test whitespace normalization"""
        text = "This   has    multiple    spaces"
        cleaned, metadata = self.preprocessor.preprocess(text)

        assert "  " not in cleaned
        assert cleaned == "This has multiple spaces"

    def test_contraction_expansion(self):
        """Test contraction expansion"""
        text = "Don't worry, it's fine"
        cleaned, metadata = self.preprocessor.preprocess(text)

        assert "do not" in cleaned.lower()
        assert "it is" in cleaned.lower()

    def test_content_validation(self):
        """Test content validation"""
        # Empty content
        result = self.preprocessor.validate_content("")
        assert not result["is_valid"]

        # Valid content
        result = self.preprocessor.validate_content("This is valid content")
        assert result["is_valid"]


class TestEmbeddingGenerator:
    """Test embedding generation"""

    @pytest.mark.asyncio
    async def test_mock_embedding_generation(self):
        """Test mock embedding generation"""
        generator = EmbeddingGenerator(model_type="mock")

        text = "Test content for embedding"
        embeddings, metadata = await generator.generate_embeddings(text, generate_chunks=False)

        assert "full" in embeddings
        assert len(embeddings["full"]) == generator.dimensions
        assert all(isinstance(x, float) for x in embeddings["full"])

    @pytest.mark.asyncio
    async def test_chunking(self):
        """Test text chunking"""
        generator = EmbeddingGenerator(chunk_size=50, chunk_overlap=10)

        # Long text that will be chunked
        text = " ".join(["word"] * 200)
        embeddings, metadata = await generator.generate_embeddings(text, generate_chunks=True)

        # Should have multiple chunk embeddings
        chunk_keys = [k for k in embeddings.keys() if k.startswith("chunk_")]
        assert len(chunk_keys) > 1

        # Should have average embedding
        assert "average" in embeddings


class TestValidator:
    """Test validation framework"""

    def setup_method(self):
        self.validator = AdvancedValidator()

    def test_schema_validation(self):
        """Test schema validation"""
        # Invalid content
        content = ProcessedContent(
            original_content="",  # Empty content
            content_hash="",  # Empty hash
            entities=[],
            topics=[],
            relationships=[]
        )

        result = self.validator.validate(content)

        assert not result.is_valid
        assert any(i.level == ValidationLevel.CRITICAL for i in result.issues)

    def test_extraction_validation(self):
        """Test extraction validation"""
        # Entity with invalid position
        content = ProcessedContent(
            original_content="Test",
            content_hash="test_hash",
            entities=[Entity(text="Invalid", type=EntityType.CONCEPT, normalized="invalid",
                           start_pos=10, end_pos=5, confidence=0.9)],  # Invalid positions
            topics=[],
            relationships=[]
        )

        result = self.validator.validate(content)

        error_issues = result.get_issues_by_level(ValidationLevel.ERROR)
        assert len(error_issues) > 0
        assert any("position" in i.message for i in error_issues)

    def test_validation_score(self):
        """Test validation scoring"""
        # Good content
        content = ProcessedContent(
            original_content="This is valid test content with sufficient length",
            content_hash="valid_hash",
            entities=[],
            topics=[],
            relationships=[],
            quality=ContentQuality.HIGH,
            completeness_score=0.9
        )

        result = self.validator.validate(content)

        assert result.score > 0.7  # Good score for valid content


# Integration test for the full pipeline
class TestIngestionPipeline:
    """Test the complete ingestion pipeline"""

    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """Test processing content through all components"""
        # Sample content
        text = """
        John Smith, CEO of TechCorp, announced today that they will be launching
        a new AI product next month. The product uses machine learning to analyze
        customer behavior. Contact: john@techcorp.com
        
        TODO: Prepare marketing materials for the launch
        """

        # Process through each component
        entity_extractor = EntityExtractor()
        topic_classifier = TopicClassifier(enable_lda=False)
        relationship_detector = RelationshipDetector()
        intent_recognizer = IntentRecognizer()
        embedding_generator = EmbeddingGenerator(model_type="mock")
        content_classifier = ContentClassifier()
        structured_extractor = StructuredDataExtractor()
        preprocessor = ContentPreprocessor()
        validator = AdvancedValidator()

        # Preprocess
        cleaned_text, metadata = preprocessor.preprocess(text)

        # Extract components
        entities = entity_extractor.extract_entities(cleaned_text)
        topics = topic_classifier.extract_topics(cleaned_text)
        relationships = relationship_detector.detect_relationships(cleaned_text, entities)
        intent = intent_recognizer.recognize_intent(cleaned_text)
        structured_data = structured_extractor.extract_structured_data(cleaned_text)
        embeddings, emb_metadata = await embedding_generator.generate_embeddings(cleaned_text)

        # Create processed content
        content = ProcessedContent(
            original_content=cleaned_text,
            content_hash="test_hash",
            entities=entities,
            relationships=relationships,
            topics=topics,
            intent=intent,
            structured_data=structured_data,
            embeddings=embeddings,
            embedding_metadata=emb_metadata
        )

        # Classify
        classification = content_classifier.classify_content(content)

        # Validate
        validation_result = validator.validate(content)

        # Assertions
        assert len(entities) > 0  # Should find entities
        assert any(e.type == EntityType.PERSON for e in entities)  # John Smith
        assert any(e.type == EntityType.ORGANIZATION for e in entities)  # TechCorp
        assert any(e.type == EntityType.EMAIL for e in entities)  # Email

        assert len(topics) > 0  # Should find topics
        assert len(relationships) > 0  # Should find relationships

        assert intent is not None
        assert intent.type == IntentType.TODO  # Should detect TODO
        assert len(intent.action_items) > 0

        assert content.domain is not None
        assert content.quality is not None
        assert len(content.suggested_tags) > 0

        assert validation_result.is_valid  # Should be valid content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
