"""
Advanced validation framework for ingestion pipeline
"""

import logging
import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from app.ingestion.models import (
    ContentQuality,
    EntityType,
    ProcessedContent,
)

logger = logging.getLogger(__name__)


class ValidationLevel(str, Enum):
    """Validation severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationType(str, Enum):
    """Types of validation"""
    SCHEMA = "schema"
    CONTENT = "content"
    EXTRACTION = "extraction"
    QUALITY = "quality"
    CONSISTENCY = "consistency"
    BUSINESS = "business"


@dataclass
class ValidationIssue:
    """Represents a validation issue"""
    level: ValidationLevel
    type: ValidationType
    field: str
    message: str
    details: dict[str, Any] | None = None
    suggestion: str | None = None


@dataclass
class ValidationResult:
    """Result of validation"""
    is_valid: bool
    issues: list[ValidationIssue]
    score: float  # 0-1 validation score
    metadata: dict[str, Any]

    def get_issues_by_level(self, level: ValidationLevel) -> list[ValidationIssue]:
        """Get issues of specific level"""
        return [issue for issue in self.issues if issue.level == level]

    def get_issues_by_type(self, type: ValidationType) -> list[ValidationIssue]:
        """Get issues of specific type"""
        return [issue for issue in self.issues if issue.type == type]


class ValidationRule:
    """Base class for validation rules"""

    def __init__(self, name: str, level: ValidationLevel = ValidationLevel.WARNING):
        self.name = name
        self.level = level

    def validate(self, content: ProcessedContent) -> list[ValidationIssue]:
        """Validate content and return issues"""
        raise NotImplementedError


class AdvancedValidator:
    """Advanced validation framework for processed content"""

    def __init__(self):
        """Initialize validator"""
        # Initialize validation rules
        self.schema_rules = self._initialize_schema_rules()
        self.content_rules = self._initialize_content_rules()
        self.extraction_rules = self._initialize_extraction_rules()
        self.quality_rules = self._initialize_quality_rules()
        self.consistency_rules = self._initialize_consistency_rules()
        self.business_rules = self._initialize_business_rules()

        # Custom rules
        self.custom_rules: list[ValidationRule] = []

        # Validation thresholds
        self.thresholds = {
            "min_content_length": 10,
            "max_content_length": 1000000,
            "min_entities": 0,
            "max_entities": 1000,
            "min_confidence": 0.3,
            "min_quality_score": 0.5
        }

    def validate(self, content: ProcessedContent) -> ValidationResult:
        """
        Perform comprehensive validation

        Args:
            content: Processed content to validate

        Returns:
            Validation result with issues and score
        """
        issues = []

        # Schema validation
        schema_issues = self._validate_schema(content)
        issues.extend(schema_issues)

        # Content validation
        content_issues = self._validate_content(content)
        issues.extend(content_issues)

        # Extraction validation
        extraction_issues = self._validate_extractions(content)
        issues.extend(extraction_issues)

        # Quality validation
        quality_issues = self._validate_quality(content)
        issues.extend(quality_issues)

        # Consistency validation
        consistency_issues = self._validate_consistency(content)
        issues.extend(consistency_issues)

        # Business rules validation
        business_issues = self._validate_business_rules(content)
        issues.extend(business_issues)

        # Custom rules
        for rule in self.custom_rules:
            rule_issues = rule.validate(content)
            issues.extend(rule_issues)

        # Calculate validation score
        score = self._calculate_validation_score(issues)

        # Determine if valid
        critical_errors = [i for i in issues if i.level == ValidationLevel.CRITICAL]
        error_count = len([i for i in issues if i.level == ValidationLevel.ERROR])

        is_valid = len(critical_errors) == 0 and error_count < 5

        # Create metadata
        metadata = {
            "total_issues": len(issues),
            "critical_count": len(critical_errors),
            "error_count": error_count,
            "warning_count": len([i for i in issues if i.level == ValidationLevel.WARNING]),
            "info_count": len([i for i in issues if i.level == ValidationLevel.INFO]),
            "validation_timestamp": datetime.utcnow().isoformat()
        }

        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            score=score,
            metadata=metadata
        )

    def _validate_schema(self, content: ProcessedContent) -> list[ValidationIssue]:
        """Validate content schema"""
        issues = []

        # Check required fields
        if not content.original_content:
            issues.append(ValidationIssue(
                level=ValidationLevel.CRITICAL,
                type=ValidationType.SCHEMA,
                field="original_content",
                message="Original content is missing",
                suggestion="Ensure content is provided before processing"
            ))

        if not content.content_hash:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                type=ValidationType.SCHEMA,
                field="content_hash",
                message="Content hash is missing",
                suggestion="Generate content hash during preprocessing"
            ))

        # Check data types
        if content.completeness_score is not None:
            if not 0 <= content.completeness_score <= 1:
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    type=ValidationType.SCHEMA,
                    field="completeness_score",
                    message=f"Completeness score {content.completeness_score} out of range [0,1]",
                    details={"value": content.completeness_score}
                ))

        if content.suggested_importance is not None:
            if not 0 <= content.suggested_importance <= 10:
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    type=ValidationType.SCHEMA,
                    field="suggested_importance",
                    message=f"Importance {content.suggested_importance} out of range [0,10]",
                    details={"value": content.suggested_importance}
                ))

        return issues

    def _validate_content(self, content: ProcessedContent) -> list[ValidationIssue]:
        """Validate content itself"""
        issues = []

        text = content.original_content

        # Length validation
        if len(text) < self.thresholds["min_content_length"]:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                type=ValidationType.CONTENT,
                field="original_content",
                message="Content is too short",
                details={"length": len(text), "min_length": self.thresholds["min_content_length"]},
                suggestion="Provide more substantial content"
            ))

        if len(text) > self.thresholds["max_content_length"]:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                type=ValidationType.CONTENT,
                field="original_content",
                message="Content is very long",
                details={"length": len(text), "max_length": self.thresholds["max_content_length"]},
                suggestion="Consider splitting into smaller chunks"
            ))

        # Character validation
        if not text.strip():
            issues.append(ValidationIssue(
                level=ValidationLevel.CRITICAL,
                type=ValidationType.CONTENT,
                field="original_content",
                message="Content is empty or only whitespace"
            ))

        # Check for binary content
        if '\x00' in text or '\xff' in text:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                type=ValidationType.CONTENT,
                field="original_content",
                message="Content appears to contain binary data",
                suggestion="Ensure content is properly decoded text"
            ))

        # Check for repetitive content
        if self._is_repetitive(text):
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                type=ValidationType.CONTENT,
                field="original_content",
                message="Content appears to be highly repetitive",
                suggestion="Check for data corruption or processing errors"
            ))

        # Check encoding
        try:
            text.encode('utf-8')
        except UnicodeEncodeError:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                type=ValidationType.CONTENT,
                field="original_content",
                message="Content contains invalid Unicode characters",
                suggestion="Fix encoding issues in preprocessing"
            ))

        return issues

    def _validate_extractions(self, content: ProcessedContent) -> list[ValidationIssue]:
        """Validate extracted data"""
        issues = []

        # Entity validation
        if len(content.entities) > self.thresholds["max_entities"]:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                type=ValidationType.EXTRACTION,
                field="entities",
                message=f"Excessive number of entities extracted ({len(content.entities)})",
                details={"count": len(content.entities), "max": self.thresholds["max_entities"]},
                suggestion="Review entity extraction parameters"
            ))

        # Check entity confidence
        low_confidence_entities = [
            e for e in content.entities
            if e.confidence < self.thresholds["min_confidence"]
        ]

        if low_confidence_entities:
            issues.append(ValidationIssue(
                level=ValidationLevel.INFO,
                type=ValidationType.EXTRACTION,
                field="entities",
                message=f"{len(low_confidence_entities)} entities have low confidence",
                details={"count": len(low_confidence_entities)},
                suggestion="Consider filtering low-confidence entities"
            ))

        # Validate entity positions
        for entity in content.entities:
            if entity.start_pos >= entity.end_pos:
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    type=ValidationType.EXTRACTION,
                    field="entities",
                    message=f"Invalid entity position for '{entity.text}'",
                    details={"start": entity.start_pos, "end": entity.end_pos}
                ))

            if entity.end_pos > len(content.original_content):
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    type=ValidationType.EXTRACTION,
                    field="entities",
                    message=f"Entity position exceeds content length for '{entity.text}'",
                    details={"position": entity.end_pos, "content_length": len(content.original_content)}
                ))

        # Relationship validation
        for rel in content.relationships:
            # Check if entities exist
            entity_texts = {e.text for e in content.entities}
            if rel.source.text not in entity_texts or rel.target.text not in entity_texts:
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    type=ValidationType.EXTRACTION,
                    field="relationships",
                    message="Relationship references non-existent entity",
                    details={"source": rel.source.text, "target": rel.target.text}
                ))

        # Topic validation
        if content.topics:
            # Check for duplicate topics
            topic_names = [t.name for t in content.topics]
            if len(topic_names) != len(set(topic_names)):
                issues.append(ValidationIssue(
                    level=ValidationLevel.INFO,
                    type=ValidationType.EXTRACTION,
                    field="topics",
                    message="Duplicate topics detected",
                    suggestion="Merge similar topics"
                ))

        # Embedding validation
        if content.embeddings:
            for key, embedding in content.embeddings.items():
                if not isinstance(embedding, list) or not all(isinstance(x, (int, float)) for x in embedding):
                    issues.append(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        type=ValidationType.EXTRACTION,
                        field="embeddings",
                        message=f"Invalid embedding format for key '{key}'",
                        suggestion="Ensure embeddings are lists of numbers"
                    ))

        return issues

    def _validate_quality(self, content: ProcessedContent) -> list[ValidationIssue]:
        """Validate content quality"""
        issues = []

        # Check quality assessment
        if content.quality == ContentQuality.INCOMPLETE:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                type=ValidationType.QUALITY,
                field="quality",
                message="Content marked as incomplete",
                suggestion="Review content for missing information"
            ))

        # Check completeness score
        if content.completeness_score < self.thresholds["min_quality_score"]:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                type=ValidationType.QUALITY,
                field="completeness_score",
                message=f"Low completeness score ({content.completeness_score:.2f})",
                details={"score": content.completeness_score},
                suggestion="Improve extraction coverage"
            ))

        # Check extraction coverage
        content_words = len(content.original_content.split())
        entity_coverage = len(content.entities) / max(content_words / 50, 1)  # Rough estimate

        if entity_coverage < 0.1:
            issues.append(ValidationIssue(
                level=ValidationLevel.INFO,
                type=ValidationType.QUALITY,
                field="entities",
                message="Low entity extraction coverage",
                details={"coverage": entity_coverage},
                suggestion="Content may need richer entity extraction"
            ))

        return issues

    def _validate_consistency(self, content: ProcessedContent) -> list[ValidationIssue]:
        """Validate data consistency"""
        issues = []

        # Check entity-relationship consistency
        entity_set = {(e.text, e.type) for e in content.entities}

        for rel in content.relationships:
            source_key = (rel.source.text, rel.source.type)
            target_key = (rel.target.text, rel.target.type)

            if source_key not in entity_set:
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    type=ValidationType.CONSISTENCY,
                    field="relationships",
                    message=f"Relationship source entity not found: {rel.source.text}",
                    details={"entity": rel.source.text, "type": rel.source.type}
                ))

            if target_key not in entity_set:
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    type=ValidationType.CONSISTENCY,
                    field="relationships",
                    message=f"Relationship target entity not found: {rel.target.text}",
                    details={"entity": rel.target.text, "type": rel.target.type}
                ))

        # Check metadata consistency
        if content.suggested_tags:
            # Check if suggested tags match extracted topics
            topic_keywords = set()
            for topic in content.topics:
                topic_keywords.update(topic.keywords)

            unrelated_tags = [
                tag for tag in content.suggested_tags
                if not any(keyword in tag for keyword in topic_keywords)
            ]

            if len(unrelated_tags) > len(content.suggested_tags) * 0.5:
                issues.append(ValidationIssue(
                    level=ValidationLevel.INFO,
                    type=ValidationType.CONSISTENCY,
                    field="suggested_tags",
                    message="Many tags don't match extracted topics",
                    details={"unrelated_count": len(unrelated_tags)},
                    suggestion="Review tag generation logic"
                ))

        # Check timestamp consistency
        if content.processed_at and content.embedding_metadata:
            if content.embedding_metadata.generated_at < content.processed_at:
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    type=ValidationType.CONSISTENCY,
                    field="timestamps",
                    message="Embedding generated before processing timestamp",
                    details={
                        "processed_at": content.processed_at.isoformat(),
                        "embedding_at": content.embedding_metadata.generated_at.isoformat()
                    }
                ))

        return issues

    def _validate_business_rules(self, content: ProcessedContent) -> list[ValidationIssue]:
        """Validate business-specific rules"""
        issues = []

        # Example business rules

        # Rule: Important content should have high quality
        if content.suggested_importance and content.suggested_importance > 7:
            if content.quality in [ContentQuality.LOW, ContentQuality.INCOMPLETE]:
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    type=ValidationType.BUSINESS,
                    field="quality",
                    message="High importance content has low quality",
                    details={
                        "importance": content.suggested_importance,
                        "quality": content.quality
                    },
                    suggestion="Improve processing for important content"
                ))

        # Rule: Action items should have deadlines
        if content.intent and content.intent.type.value == "todo":
            if content.intent.action_items and not self._has_temporal_reference(content):
                issues.append(ValidationIssue(
                    level=ValidationLevel.INFO,
                    type=ValidationType.BUSINESS,
                    field="intent",
                    message="TODO items without temporal reference",
                    suggestion="Consider extracting or adding deadlines"
                ))

        # Rule: Code snippets should have language detection
        if content.structured_data and content.structured_data.code_snippets:
            unknown_lang_count = sum(
                1 for snippet in content.structured_data.code_snippets
                if snippet.get("language") == "unknown"
            )

            if unknown_lang_count > 0:
                issues.append(ValidationIssue(
                    level=ValidationLevel.INFO,
                    type=ValidationType.BUSINESS,
                    field="structured_data",
                    message=f"{unknown_lang_count} code snippets with unknown language",
                    suggestion="Improve language detection for code"
                ))

        return issues

    def add_custom_rule(self, rule: ValidationRule):
        """Add a custom validation rule"""
        self.custom_rules.append(rule)

    def set_threshold(self, name: str, value: Any):
        """Set a validation threshold"""
        self.thresholds[name] = value

    def _is_repetitive(self, text: str) -> bool:
        """Check if text is highly repetitive"""
        # Simple check for repetitive patterns
        words = text.split()
        if len(words) < 10:
            return False

        # Check for repeated words
        word_counts = defaultdict(int)
        for word in words:
            word_counts[word.lower()] += 1

        # If any word appears more than 30% of the time
        max_count = max(word_counts.values())
        if max_count > len(words) * 0.3:
            return True

        # Check for repeated phrases
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
        bigram_counts = defaultdict(int)
        for bigram in bigrams:
            bigram_counts[bigram] += 1

        max_bigram_count = max(bigram_counts.values()) if bigram_counts else 0
        if max_bigram_count > len(bigrams) * 0.2:
            return True

        return False

    def _has_temporal_reference(self, content: ProcessedContent) -> bool:
        """Check if content has temporal references"""
        # Check entities for date/time types
        for entity in content.entities:
            if entity.type in [EntityType.DATE, EntityType.TIME]:
                return True

        # Check for temporal patterns in text
        temporal_patterns = [
            r'\b(?:today|tomorrow|yesterday|next|last)\b',
            r'\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b',
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
        ]

        text_lower = content.original_content.lower()
        for pattern in temporal_patterns:
            if re.search(pattern, text_lower):
                return True

        return False

    def _calculate_validation_score(self, issues: list[ValidationIssue]) -> float:
        """Calculate overall validation score"""
        if not issues:
            return 1.0

        # Weight issues by severity
        weights = {
            ValidationLevel.CRITICAL: 10.0,
            ValidationLevel.ERROR: 5.0,
            ValidationLevel.WARNING: 2.0,
            ValidationLevel.INFO: 0.5
        }

        total_weight = sum(weights.get(issue.level, 1.0) for issue in issues)

        # Score decreases with issue weight
        score = max(0.0, 1.0 - (total_weight / 100.0))

        return score

    def _initialize_schema_rules(self) -> list[Callable]:
        """Initialize schema validation rules"""
        return []

    def _initialize_content_rules(self) -> list[Callable]:
        """Initialize content validation rules"""
        return []

    def _initialize_extraction_rules(self) -> list[Callable]:
        """Initialize extraction validation rules"""
        return []

    def _initialize_quality_rules(self) -> list[Callable]:
        """Initialize quality validation rules"""
        return []

    def _initialize_consistency_rules(self) -> list[Callable]:
        """Initialize consistency validation rules"""
        return []

    def _initialize_business_rules(self) -> list[Callable]:
        """Initialize business validation rules"""
        return []

    def get_validation_report(self, result: ValidationResult) -> str:
        """Generate human-readable validation report"""
        report = []
        report.append("Validation Report")
        report.append("=" * 50)
        report.append(f"Valid: {result.is_valid}")
        report.append(f"Score: {result.score:.2f}")
        report.append(f"Total Issues: {result.metadata['total_issues']}")
        report.append("")

        # Group issues by level
        for level in ValidationLevel:
            level_issues = result.get_issues_by_level(level)
            if level_issues:
                report.append(f"{level.value.upper()} ({len(level_issues)} issues):")
                for issue in level_issues:
                    report.append(f"  - [{issue.type.value}] {issue.field}: {issue.message}")
                    if issue.suggestion:
                        report.append(f"    Suggestion: {issue.suggestion}")
                report.append("")

        return "\n".join(report)
