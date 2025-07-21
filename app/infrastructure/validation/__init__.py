"""
Advanced validation system
"""

from app.infrastructure.validation.schema import (
    INGESTION_REQUEST_SCHEMA,
    JSONSchema,
    MEMORY_SCHEMA,
    Schema,
    USER_SCHEMA,
    create_model_validator,
    validate_ingestion_request,
    validate_memory,
    validate_user,
    validate_with_schema,
)
from app.infrastructure.validation.validators import (
    ChoiceValidator,
    CompositeValidator,
    ConditionalValidator,
    ContextualValidator,
    CustomValidator,
    DictValidator,
    EmailValidator,
    LengthValidator,
    ListValidator,
    PatternValidator,
    RangeValidator,
    RequiredValidator,
    TypeValidator,
    URLValidator,
    ValidationContext,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    Validator,
)

__all__ = [
    # Core validation
    "Validator",
    "ValidationResult",
    "ValidationIssue",
    "ValidationSeverity",
    "ValidationContext",
    # Basic validators
    "RequiredValidator",
    "TypeValidator",
    "RangeValidator",
    "LengthValidator",
    "PatternValidator",
    "EmailValidator",
    "URLValidator",
    "ChoiceValidator",
    "CustomValidator",
    # Complex validators
    "CompositeValidator",
    "DictValidator",
    "ListValidator",
    "ConditionalValidator",
    "ContextualValidator",
    # Schema validation
    "Schema",
    "JSONSchema",
    "create_model_validator",
    "validate_with_schema",
    # Common schemas
    "MEMORY_SCHEMA",
    "INGESTION_REQUEST_SCHEMA",
    "USER_SCHEMA",
    # Helper functions
    "validate_memory",
    "validate_ingestion_request",
    "validate_user",
]