"""
Schema-based validation system
"""

import json
import logging
from typing import Any, Optional, Type, Union

from app.infrastructure.validation.validators import (
    ChoiceValidator,
    DictValidator,
    EmailValidator,
    LengthValidator,
    ListValidator,
    PatternValidator,
    RangeValidator,
    RequiredValidator,
    TypeValidator,
    URLValidator,
    ValidationResult,
    Validator,
)

logger = logging.getLogger(__name__)


class Schema:
    """
    Schema definition for validation
    """
    
    def __init__(self, definition: dict[str, Any]):
        self.definition = definition
        self._validators_cache: dict[str, Validator] = {}
        
    def create_validator(self) -> Validator:
        """Create validator from schema"""
        return self._create_validator_from_def(self.definition)
        
    def _create_validator_from_def(self, definition: dict[str, Any]) -> Validator:
        """Create validator from definition"""
        # Check cache
        def_str = json.dumps(definition, sort_keys=True)
        if def_str in self._validators_cache:
            return self._validators_cache[def_str]
            
        # Create validator
        validator = self._build_validator(definition)
        
        # Cache it
        self._validators_cache[def_str] = validator
        
        return validator
        
    def _build_validator(self, definition: dict[str, Any]) -> Validator:
        """Build validator from definition"""
        val_type = definition.get("type", "any")
        
        if val_type == "object":
            return self._build_object_validator(definition)
        elif val_type == "array":
            return self._build_array_validator(definition)
        elif val_type == "string":
            return self._build_string_validator(definition)
        elif val_type == "number":
            return self._build_number_validator(definition)
        elif val_type == "integer":
            return self._build_integer_validator(definition)
        elif val_type == "boolean":
            return TypeValidator(bool)
        elif val_type == "null":
            return TypeValidator(type(None))
        elif val_type == "any":
            # Always valid
            return Validator()
        else:
            raise ValueError(f"Unknown type: {val_type}")
            
    def _build_object_validator(self, definition: dict[str, Any]) -> Validator:
        """Build object validator"""
        properties = definition.get("properties", {})
        required = definition.get("required", [])
        additional_properties = definition.get("additionalProperties", True)
        
        # Build field validators
        field_validators = {}
        
        for field_name, field_def in properties.items():
            field_validator = self._create_validator_from_def(field_def)
            
            # Add required validator if needed
            if field_name in required:
                field_validator = RequiredValidator() & field_validator
                
            field_validators[field_name] = field_validator
            
        return DictValidator(field_validators, allow_extra=additional_properties)
        
    def _build_array_validator(self, definition: dict[str, Any]) -> Validator:
        """Build array validator"""
        items = definition.get("items", {"type": "any"})
        min_items = definition.get("minItems")
        max_items = definition.get("maxItems")
        
        item_validator = self._create_validator_from_def(items)
        
        return ListValidator(item_validator, min_items=min_items, max_items=max_items)
        
    def _build_string_validator(self, definition: dict[str, Any]) -> Validator:
        """Build string validator"""
        validators = [TypeValidator(str)]
        
        # Length constraints
        min_length = definition.get("minLength")
        max_length = definition.get("maxLength")
        if min_length is not None or max_length is not None:
            validators.append(LengthValidator(min_length=min_length, max_length=max_length))
            
        # Pattern
        pattern = definition.get("pattern")
        if pattern:
            validators.append(PatternValidator(pattern))
            
        # Format
        format_type = definition.get("format")
        if format_type == "email":
            validators.append(EmailValidator())
        elif format_type == "uri" or format_type == "url":
            validators.append(URLValidator())
            
        # Enum
        enum = definition.get("enum")
        if enum:
            validators.append(ChoiceValidator(enum))
            
        # Combine validators
        if len(validators) == 1:
            return validators[0]
        else:
            result = validators[0]
            for validator in validators[1:]:
                result = result & validator
            return result
            
    def _build_number_validator(self, definition: dict[str, Any]) -> Validator:
        """Build number validator"""
        validators = [TypeValidator(float)]
        
        # Range constraints
        minimum = definition.get("minimum")
        maximum = definition.get("maximum")
        exclusive_minimum = definition.get("exclusiveMinimum")
        exclusive_maximum = definition.get("exclusiveMaximum")
        
        if minimum is not None:
            validators.append(RangeValidator(min_value=minimum))
        if maximum is not None:
            validators.append(RangeValidator(max_value=maximum))
        if exclusive_minimum is not None:
            validators.append(RangeValidator(min_value=exclusive_minimum + 0.000001))
        if exclusive_maximum is not None:
            validators.append(RangeValidator(max_value=exclusive_maximum - 0.000001))
            
        # Combine validators
        if len(validators) == 1:
            return validators[0]
        else:
            result = validators[0]
            for validator in validators[1:]:
                result = result & validator
            return result
            
    def _build_integer_validator(self, definition: dict[str, Any]) -> Validator:
        """Build integer validator"""
        validators = [TypeValidator(int)]
        
        # Range constraints
        minimum = definition.get("minimum")
        maximum = definition.get("maximum")
        
        if minimum is not None or maximum is not None:
            validators.append(RangeValidator(min_value=minimum, max_value=maximum))
            
        # Combine validators
        if len(validators) == 1:
            return validators[0]
        else:
            return validators[0] & validators[1]


# JSON Schema validation

class JSONSchema(Schema):
    """JSON Schema based validation"""
    
    @classmethod
    def from_file(cls, filepath: str) -> 'JSONSchema':
        """Load schema from JSON file"""
        with open(filepath, 'r') as f:
            definition = json.load(f)
        return cls(definition)
        
    @classmethod
    def from_json(cls, json_str: str) -> 'JSONSchema':
        """Load schema from JSON string"""
        definition = json.loads(json_str)
        return cls(definition)


# Pydantic-style validation

def create_model_validator(model_class: Type) -> Validator:
    """
    Create validator from a Pydantic-style model class
    """
    from pydantic import BaseModel
    
    if not issubclass(model_class, BaseModel):
        raise ValueError("Model must be a Pydantic BaseModel")
        
    schema = model_class.schema()
    json_schema = JSONSchema(schema)
    return json_schema.create_validator()


# Common schemas

MEMORY_SCHEMA = {
    "type": "object",
    "properties": {
        "content": {
            "type": "string",
            "minLength": 1,
            "maxLength": 10000
        },
        "memory_type": {
            "type": "string",
            "enum": ["general", "task", "insight", "question", "decision", "reference", "knowledge", "technical"]
        },
        "importance": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0
        },
        "tags": {
            "type": "array",
            "items": {
                "type": "string",
                "minLength": 1,
                "maxLength": 50
            },
            "maxItems": 20
        },
        "metadata": {
            "type": "object",
            "additionalProperties": True
        }
    },
    "required": ["content", "memory_type"]
}

INGESTION_REQUEST_SCHEMA = {
    "type": "object",
    "properties": {
        "content": {
            "type": "string",
            "minLength": 1
        },
        "user_context": {
            "type": "object",
            "additionalProperties": True
        },
        "domain_hint": {
            "type": "string"
        },
        "language": {
            "type": "string",
            "pattern": "^[a-z]{2}$"
        },
        "extract_entities": {
            "type": "boolean"
        },
        "extract_relationships": {
            "type": "boolean"
        },
        "extract_topics": {
            "type": "boolean"
        },
        "detect_intent": {
            "type": "boolean"
        },
        "extract_structured": {
            "type": "boolean"
        },
        "generate_embeddings": {
            "type": "boolean"
        },
        "fast_mode": {
            "type": "boolean"
        },
        "max_processing_time": {
            "type": "integer",
            "minimum": 100,
            "maximum": 60000
        }
    },
    "required": ["content"]
}

USER_SCHEMA = {
    "type": "object",
    "properties": {
        "username": {
            "type": "string",
            "minLength": 3,
            "maxLength": 50,
            "pattern": "^[a-zA-Z0-9_-]+$"
        },
        "email": {
            "type": "string",
            "format": "email"
        },
        "full_name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100
        },
        "password": {
            "type": "string",
            "minLength": 8,
            "maxLength": 128
        },
        "is_active": {
            "type": "boolean"
        },
        "roles": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["user", "admin", "moderator"]
            }
        }
    },
    "required": ["username", "email", "password"]
}


# Helper functions

async def validate_with_schema(data: Any, schema: dict[str, Any]) -> ValidationResult:
    """Validate data against a schema"""
    json_schema = JSONSchema(schema)
    validator = json_schema.create_validator()
    return await validator.validate(data)


async def validate_memory(memory_data: dict) -> ValidationResult:
    """Validate memory data"""
    return await validate_with_schema(memory_data, MEMORY_SCHEMA)


async def validate_ingestion_request(request_data: dict) -> ValidationResult:
    """Validate ingestion request"""
    return await validate_with_schema(request_data, INGESTION_REQUEST_SCHEMA)


async def validate_user(user_data: dict) -> ValidationResult:
    """Validate user data"""
    return await validate_with_schema(user_data, USER_SCHEMA)