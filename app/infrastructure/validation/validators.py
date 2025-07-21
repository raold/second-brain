"""
Advanced validation system with composable validators
"""

import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Generic, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a validation issue"""
    field: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    code: Optional[str] = None
    context: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "field": self.field,
            "message": self.message,
            "severity": self.severity.value,
            "code": self.code,
            "context": self.context
        }


@dataclass
class ValidationResult:
    """Result of validation"""
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def add_issue(self, issue: ValidationIssue):
        """Add validation issue"""
        self.issues.append(issue)
        if issue.severity == ValidationSeverity.ERROR:
            self.is_valid = False
            
    def merge(self, other: 'ValidationResult'):
        """Merge another validation result"""
        self.is_valid = self.is_valid and other.is_valid
        self.issues.extend(other.issues)
        self.metadata.update(other.metadata)
        
    @property
    def error_count(self) -> int:
        """Count of errors"""
        return sum(1 for issue in self.issues if issue.severity == ValidationSeverity.ERROR)
        
    @property
    def warning_count(self) -> int:
        """Count of warnings"""
        return sum(1 for issue in self.issues if issue.severity == ValidationSeverity.WARNING)
        
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "is_valid": self.is_valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [issue.to_dict() for issue in self.issues],
            "metadata": self.metadata
        }


class Validator(ABC, Generic[T]):
    """Abstract base class for validators"""
    
    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        
    @abstractmethod
    async def validate(self, value: T, field: str = "") -> ValidationResult:
        """Validate a value"""
        pass
        
    def __and__(self, other: 'Validator[T]') -> 'CompositeValidator[T]':
        """Combine validators with AND logic"""
        return CompositeValidator([self, other], mode="and")
        
    def __or__(self, other: 'Validator[T]') -> 'CompositeValidator[T]':
        """Combine validators with OR logic"""
        return CompositeValidator([self, other], mode="or")


class CompositeValidator(Validator[T]):
    """Composite validator that combines multiple validators"""
    
    def __init__(self, validators: list[Validator[T]], mode: str = "and"):
        super().__init__(f"composite_{mode}")
        self.validators = validators
        self.mode = mode  # "and" or "or"
        
    async def validate(self, value: T, field: str = "") -> ValidationResult:
        """Validate using all validators"""
        if self.mode == "and":
            # All validators must pass
            result = ValidationResult(is_valid=True)
            for validator in self.validators:
                sub_result = await validator.validate(value, field)
                result.merge(sub_result)
                if not sub_result.is_valid:
                    break
            return result
        else:
            # At least one validator must pass
            all_issues = []
            for validator in self.validators:
                sub_result = await validator.validate(value, field)
                if sub_result.is_valid:
                    return sub_result
                all_issues.extend(sub_result.issues)
                
            # None passed
            result = ValidationResult(is_valid=False)
            result.issues = all_issues
            return result


# Basic validators

class RequiredValidator(Validator[Any]):
    """Validates that value is not None or empty"""
    
    def __init__(self, message: str = "This field is required"):
        super().__init__("required")
        self.message = message
        
    async def validate(self, value: Any, field: str = "") -> ValidationResult:
        """Check if value exists"""
        result = ValidationResult(is_valid=True)
        
        if value is None:
            result.add_issue(ValidationIssue(
                field=field,
                message=self.message,
                code="required"
            ))
        elif isinstance(value, (str, list, dict)) and len(value) == 0:
            result.add_issue(ValidationIssue(
                field=field,
                message=self.message,
                code="required_empty"
            ))
            
        return result


class TypeValidator(Validator[Any]):
    """Validates value type"""
    
    def __init__(self, expected_type: type, message: str = None):
        super().__init__(f"type_{expected_type.__name__}")
        self.expected_type = expected_type
        self.message = message or f"Expected type {expected_type.__name__}"
        
    async def validate(self, value: Any, field: str = "") -> ValidationResult:
        """Check value type"""
        result = ValidationResult(is_valid=True)
        
        if value is not None and not isinstance(value, self.expected_type):
            result.add_issue(ValidationIssue(
                field=field,
                message=f"{self.message}, got {type(value).__name__}",
                code="type_error",
                context={"expected": self.expected_type.__name__, "actual": type(value).__name__}
            ))
            
        return result


class RangeValidator(Validator[Union[int, float]]):
    """Validates numeric range"""
    
    def __init__(self, min_value: Optional[float] = None, max_value: Optional[float] = None):
        super().__init__("range")
        self.min_value = min_value
        self.max_value = max_value
        
    async def validate(self, value: Union[int, float], field: str = "") -> ValidationResult:
        """Check numeric range"""
        result = ValidationResult(is_valid=True)
        
        if value is None:
            return result
            
        if self.min_value is not None and value < self.min_value:
            result.add_issue(ValidationIssue(
                field=field,
                message=f"Value must be at least {self.min_value}",
                code="min_value",
                context={"min": self.min_value, "actual": value}
            ))
            
        if self.max_value is not None and value > self.max_value:
            result.add_issue(ValidationIssue(
                field=field,
                message=f"Value must be at most {self.max_value}",
                code="max_value",
                context={"max": self.max_value, "actual": value}
            ))
            
        return result


class LengthValidator(Validator[Union[str, list, dict]]):
    """Validates length of strings, lists, or dicts"""
    
    def __init__(self, min_length: Optional[int] = None, max_length: Optional[int] = None):
        super().__init__("length")
        self.min_length = min_length
        self.max_length = max_length
        
    async def validate(self, value: Union[str, list, dict], field: str = "") -> ValidationResult:
        """Check length"""
        result = ValidationResult(is_valid=True)
        
        if value is None:
            return result
            
        length = len(value)
        
        if self.min_length is not None and length < self.min_length:
            result.add_issue(ValidationIssue(
                field=field,
                message=f"Length must be at least {self.min_length}",
                code="min_length",
                context={"min": self.min_length, "actual": length}
            ))
            
        if self.max_length is not None and length > self.max_length:
            result.add_issue(ValidationIssue(
                field=field,
                message=f"Length must be at most {self.max_length}",
                code="max_length",
                context={"max": self.max_length, "actual": length}
            ))
            
        return result


class PatternValidator(Validator[str]):
    """Validates string against regex pattern"""
    
    def __init__(self, pattern: str, message: str = "Invalid format", flags: int = 0):
        super().__init__("pattern")
        self.pattern = re.compile(pattern, flags)
        self.message = message
        
    async def validate(self, value: str, field: str = "") -> ValidationResult:
        """Check pattern match"""
        result = ValidationResult(is_valid=True)
        
        if value is None:
            return result
            
        if not self.pattern.match(value):
            result.add_issue(ValidationIssue(
                field=field,
                message=self.message,
                code="pattern",
                context={"pattern": self.pattern.pattern}
            ))
            
        return result


class EmailValidator(PatternValidator):
    """Validates email addresses"""
    
    def __init__(self):
        super().__init__(
            pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            message="Invalid email address"
        )
        self.name = "email"


class URLValidator(PatternValidator):
    """Validates URLs"""
    
    def __init__(self):
        super().__init__(
            pattern=r'^https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)$',
            message="Invalid URL"
        )
        self.name = "url"


class ChoiceValidator(Validator[Any]):
    """Validates value is in allowed choices"""
    
    def __init__(self, choices: list[Any], message: str = None):
        super().__init__("choice")
        self.choices = choices
        self.message = message or f"Value must be one of: {choices}"
        
    async def validate(self, value: Any, field: str = "") -> ValidationResult:
        """Check if value in choices"""
        result = ValidationResult(is_valid=True)
        
        if value is not None and value not in self.choices:
            result.add_issue(ValidationIssue(
                field=field,
                message=self.message,
                code="choice",
                context={"choices": self.choices, "actual": value}
            ))
            
        return result


class CustomValidator(Validator[T]):
    """Custom validator using a function"""
    
    def __init__(self, validate_func: Callable[[T], tuple[bool, Optional[str]]], name: str = "custom"):
        super().__init__(name)
        self.validate_func = validate_func
        
    async def validate(self, value: T, field: str = "") -> ValidationResult:
        """Run custom validation"""
        result = ValidationResult(is_valid=True)
        
        try:
            is_valid, message = self.validate_func(value)
            if not is_valid:
                result.add_issue(ValidationIssue(
                    field=field,
                    message=message or "Validation failed",
                    code="custom"
                ))
        except Exception as e:
            result.add_issue(ValidationIssue(
                field=field,
                message=f"Validation error: {str(e)}",
                code="custom_error"
            ))
            
        return result


# Complex validators

class DictValidator(Validator[dict]):
    """Validates dictionary structure"""
    
    def __init__(self, schema: dict[str, Validator], allow_extra: bool = True):
        super().__init__("dict")
        self.schema = schema
        self.allow_extra = allow_extra
        
    async def validate(self, value: dict, field: str = "") -> ValidationResult:
        """Validate dictionary"""
        result = ValidationResult(is_valid=True)
        
        if not isinstance(value, dict):
            result.add_issue(ValidationIssue(
                field=field,
                message="Expected dictionary",
                code="type_error"
            ))
            return result
            
        # Check required fields
        for key, validator in self.schema.items():
            field_name = f"{field}.{key}" if field else key
            
            if key in value:
                # Validate field
                field_result = await validator.validate(value[key], field_name)
                result.merge(field_result)
            elif isinstance(validator, RequiredValidator):
                # Required field missing
                field_result = await validator.validate(None, field_name)
                result.merge(field_result)
                
        # Check for extra fields
        if not self.allow_extra:
            extra_fields = set(value.keys()) - set(self.schema.keys())
            for extra in extra_fields:
                result.add_issue(ValidationIssue(
                    field=f"{field}.{extra}" if field else extra,
                    message="Unknown field",
                    code="unknown_field",
                    severity=ValidationSeverity.WARNING
                ))
                
        return result


class ListValidator(Validator[list]):
    """Validates list items"""
    
    def __init__(self, item_validator: Validator, min_items: Optional[int] = None, max_items: Optional[int] = None):
        super().__init__("list")
        self.item_validator = item_validator
        self.min_items = min_items
        self.max_items = max_items
        
    async def validate(self, value: list, field: str = "") -> ValidationResult:
        """Validate list"""
        result = ValidationResult(is_valid=True)
        
        if not isinstance(value, list):
            result.add_issue(ValidationIssue(
                field=field,
                message="Expected list",
                code="type_error"
            ))
            return result
            
        # Check length
        if self.min_items is not None and len(value) < self.min_items:
            result.add_issue(ValidationIssue(
                field=field,
                message=f"List must have at least {self.min_items} items",
                code="min_items"
            ))
            
        if self.max_items is not None and len(value) > self.max_items:
            result.add_issue(ValidationIssue(
                field=field,
                message=f"List must have at most {self.max_items} items",
                code="max_items"
            ))
            
        # Validate each item
        for i, item in enumerate(value):
            item_field = f"{field}[{i}]" if field else f"[{i}]"
            item_result = await self.item_validator.validate(item, item_field)
            result.merge(item_result)
            
        return result


class ConditionalValidator(Validator[T]):
    """Validates based on condition"""
    
    def __init__(self, condition: Callable[[T], bool], then_validator: Validator[T], else_validator: Optional[Validator[T]] = None):
        super().__init__("conditional")
        self.condition = condition
        self.then_validator = then_validator
        self.else_validator = else_validator
        
    async def validate(self, value: T, field: str = "") -> ValidationResult:
        """Conditional validation"""
        if self.condition(value):
            return await self.then_validator.validate(value, field)
        elif self.else_validator:
            return await self.else_validator.validate(value, field)
        else:
            return ValidationResult(is_valid=True)


# Validation context for complex scenarios

class ValidationContext:
    """Context for validation with access to related data"""
    
    def __init__(self, root_data: Any = None, metadata: dict[str, Any] = None):
        self.root_data = root_data
        self.metadata = metadata or {}
        self._cache: dict[str, Any] = {}
        
    def get(self, path: str, default: Any = None) -> Any:
        """Get value by path (e.g., 'user.email')"""
        try:
            value = self.root_data
            for part in path.split('.'):
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = getattr(value, part, None)
                if value is None:
                    return default
            return value
        except:
            return default
            
    def cache(self, key: str, value: Any):
        """Cache a value"""
        self._cache[key] = value
        
    def get_cached(self, key: str, default: Any = None) -> Any:
        """Get cached value"""
        return self._cache.get(key, default)


class ContextualValidator(Validator[T]):
    """Validator that uses context"""
    
    def __init__(self, validate_func: Callable[[T, ValidationContext], ValidationResult], name: str = "contextual"):
        super().__init__(name)
        self.validate_func = validate_func
        self._context: Optional[ValidationContext] = None
        
    def with_context(self, context: ValidationContext) -> 'ContextualValidator[T]':
        """Set validation context"""
        self._context = context
        return self
        
    async def validate(self, value: T, field: str = "") -> ValidationResult:
        """Validate with context"""
        if self._context is None:
            self._context = ValidationContext()
            
        result = self.validate_func(value, self._context)
        if asyncio.iscoroutine(result):
            result = await result
            
        return result