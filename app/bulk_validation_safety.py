"""
Bulk Operations Validation and Safety System

Provides comprehensive safety mechanisms for bulk memory operations:
- Multi-level data validation
- Automatic rollback and recovery
- Error handling and reporting
- Safety limits and constraints
- Audit logging and compliance
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Set, Callable
from dataclasses import dataclass, asdict
import re
import hashlib
from collections import defaultdict

from .bulk_memory_operations import BulkMemoryItem, ValidationLevel

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class SafetyViolation(Exception):
    """Custom exception for safety violations."""
    pass


class RollbackType(Enum):
    """Types of rollback operations."""
    NONE = "none"
    PARTIAL = "partial"
    FULL = "full"
    CHECKPOINT = "checkpoint"


class SafetyLevel(Enum):
    """Safety enforcement levels."""
    PERMISSIVE = "permissive"   # Minimal safety checks
    STANDARD = "standard"       # Normal safety enforcement
    STRICT = "strict"           # High safety enforcement
    MAXIMUM = "maximum"         # Maximum safety enforcement


@dataclass
class ValidationResult:
    """Result of validation operations."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]
    severity: str = "info"  # info, warning, error, critical


@dataclass
class SafetyCheck:
    """Individual safety check configuration."""
    name: str
    description: str
    enabled: bool = True
    threshold: Optional[float] = None
    action: str = "warn"  # warn, block, rollback


@dataclass
class RollbackPoint:
    """Checkpoint for rollback operations."""
    checkpoint_id: str
    operation_id: str
    timestamp: datetime
    state_snapshot: Dict[str, Any]
    affected_records: List[str]
    rollback_type: RollbackType


@dataclass
class SafetyConfiguration:
    """Configuration for safety mechanisms."""
    safety_level: SafetyLevel = SafetyLevel.STANDARD
    max_items_per_operation: int = 50000
    max_operations_per_hour: int = 100
    enable_duplicate_detection: bool = True
    enable_content_analysis: bool = True
    enable_rate_limiting: bool = True
    enable_audit_logging: bool = True
    rollback_retention_days: int = 7
    validation_timeout_seconds: int = 300
    
    # Content safety thresholds
    max_content_length: int = 100000
    min_content_length: int = 1
    max_embedding_dimension: int = 2048
    
    # Performance limits
    max_concurrent_validations: int = 10
    validation_batch_size: int = 1000
    
    # Security settings
    blocked_patterns: List[str] = None
    required_fields: List[str] = None
    
    def __post_init__(self):
        if self.blocked_patterns is None:
            self.blocked_patterns = [
                r"(?i)drop\s+table",
                r"(?i)delete\s+from",
                r"(?i)<script[^>]*>",
                r"(?i)javascript:",
                r"(?i)eval\s*\(",
                r"(?i)exec\s*\(",
                r"(?i)system\s*\(",
                r"(?i)\.\.\/",
                r"(?i)file:\/\/",
                r"(?i)ftp:\/\/"
            ]
        
        if self.required_fields is None:
            self.required_fields = ["content", "memory_type"]


class ContentValidator:
    """
    Advanced content validation with security scanning.
    
    Provides multiple validation levels and security checks.
    """
    
    def __init__(self, config: SafetyConfiguration):
        self.config = config
        self.compiled_patterns = [re.compile(pattern) for pattern in config.blocked_patterns]
        self.word_count_cache = {}
        
    async def validate_item(self, item: BulkMemoryItem, level: ValidationLevel) -> ValidationResult:
        """Validate a single memory item."""
        errors = []
        warnings = []
        metadata = {}
        
        try:
            # Basic validation
            basic_result = await self._basic_validation(item)
            errors.extend(basic_result.errors)
            warnings.extend(basic_result.warnings)
            metadata.update(basic_result.metadata)
            
            # Level-specific validation
            if level in [ValidationLevel.STANDARD, ValidationLevel.STRICT, ValidationLevel.PARANOID]:
                standard_result = await self._standard_validation(item)
                errors.extend(standard_result.errors)
                warnings.extend(standard_result.warnings)
                metadata.update(standard_result.metadata)
            
            if level in [ValidationLevel.STRICT, ValidationLevel.PARANOID]:
                strict_result = await self._strict_validation(item)
                errors.extend(strict_result.errors)
                warnings.extend(strict_result.warnings)
                metadata.update(strict_result.metadata)
            
            if level == ValidationLevel.PARANOID:
                paranoid_result = await self._paranoid_validation(item)
                errors.extend(paranoid_result.errors)
                warnings.extend(paranoid_result.warnings)
                metadata.update(paranoid_result.metadata)
            
            # Security validation (always performed)
            security_result = await self._security_validation(item)
            errors.extend(security_result.errors)
            warnings.extend(security_result.warnings)
            metadata.update(security_result.metadata)
            
            # Determine severity
            severity = "critical" if any("security" in error.lower() for error in errors) else \
                      "error" if errors else \
                      "warning" if warnings else "info"
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                metadata=metadata,
                severity=severity
            )
            
        except Exception as e:
            logger.error(f"Validation failed for item: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                metadata={},
                severity="critical"
            )
    
    async def _basic_validation(self, item: BulkMemoryItem) -> ValidationResult:
        """Basic validation checks."""
        errors = []
        warnings = []
        metadata = {}
        
        # Required fields
        for field in self.config.required_fields:
            if not hasattr(item, field) or getattr(item, field) is None:
                errors.append(f"Missing required field: {field}")
        
        # Content validation
        if item.content:
            content_len = len(item.content)
            metadata["content_length"] = content_len
            
            if content_len < self.config.min_content_length:
                errors.append(f"Content too short: {content_len} chars (min: {self.config.min_content_length})")
            
            if content_len > self.config.max_content_length:
                errors.append(f"Content too long: {content_len} chars (max: {self.config.max_content_length})")
        else:
            errors.append("Content is empty or null")
        
        # Memory type validation
        valid_types = ["semantic", "episodic", "procedural"]
        if item.memory_type not in valid_types:
            errors.append(f"Invalid memory type: {item.memory_type} (valid: {valid_types})")
        
        # Importance score validation
        if not 0 <= item.importance_score <= 1:
            errors.append(f"Invalid importance score: {item.importance_score} (must be 0-1)")
        
        return ValidationResult(True, errors, warnings, metadata)
    
    async def _standard_validation(self, item: BulkMemoryItem) -> ValidationResult:
        """Standard validation checks."""
        errors = []
        warnings = []
        metadata = {}
        
        # Content quality analysis
        if item.content:
            # Word count analysis
            words = item.content.split()
            word_count = len(words)
            metadata["word_count"] = word_count
            
            if word_count < 3:
                warnings.append("Content has very few words")
            
            # Character encoding validation
            try:
                item.content.encode('utf-8')
            except UnicodeEncodeError:
                errors.append("Content contains invalid UTF-8 characters")
            
            # Basic structure analysis
            lines = item.content.split('\n')
            metadata["line_count"] = len(lines)
            
            if len(lines) > 1000:
                warnings.append("Content has many lines - consider splitting")
        
        # Metadata validation
        for metadata_field in [item.semantic_metadata, item.episodic_metadata, 
                              item.procedural_metadata, item.metadata]:
            if metadata_field:
                if not isinstance(metadata_field, dict):
                    errors.append("Metadata must be a dictionary")
                else:
                    # Check for nested depth
                    depth = self._get_dict_depth(metadata_field)
                    if depth > 5:
                        warnings.append("Metadata structure is deeply nested")
        
        return ValidationResult(True, errors, warnings, metadata)
    
    async def _strict_validation(self, item: BulkMemoryItem) -> ValidationResult:
        """Strict validation checks."""
        errors = []
        warnings = []
        metadata = {}
        
        # Content complexity analysis
        if item.content:
            # Entropy calculation for randomness detection
            entropy = self._calculate_entropy(item.content)
            metadata["content_entropy"] = entropy
            
            if entropy < 2.0:
                warnings.append("Content has low entropy - may be repetitive")
            elif entropy > 7.0:
                warnings.append("Content has high entropy - may be random")
            
            # Language detection patterns
            if self._detect_code_content(item.content):
                metadata["contains_code"] = True
                warnings.append("Content appears to contain code")
            
            # URL detection
            url_count = len(re.findall(r'https?://\S+', item.content))
            metadata["url_count"] = url_count
            if url_count > 10:
                warnings.append("Content contains many URLs")
        
        # Memory type specific validation
        if item.memory_type == "semantic":
            if not item.semantic_metadata:
                warnings.append("Semantic memory should have semantic_metadata")
        elif item.memory_type == "episodic":
            if not item.episodic_metadata:
                warnings.append("Episodic memory should have episodic_metadata")
        elif item.memory_type == "procedural":
            if not item.procedural_metadata:
                warnings.append("Procedural memory should have procedural_metadata")
        
        return ValidationResult(True, errors, warnings, metadata)
    
    async def _paranoid_validation(self, item: BulkMemoryItem) -> ValidationResult:
        """Paranoid validation checks."""
        errors = []
        warnings = []
        metadata = {}
        
        # Advanced content analysis
        if item.content:
            # Sensitive data detection
            if self._detect_sensitive_data(item.content):
                errors.append("Content may contain sensitive data")
                metadata["sensitive_data_detected"] = True
            
            # Profanity/inappropriate content detection
            if self._detect_inappropriate_content(item.content):
                warnings.append("Content may contain inappropriate material")
                metadata["inappropriate_content_detected"] = True
            
            # Duplicate content hash
            content_hash = hashlib.sha256(item.content.encode()).hexdigest()
            metadata["content_hash"] = content_hash
            
            # Check for potential injection attacks
            if self._detect_injection_patterns(item.content):
                errors.append("Content contains potential injection patterns")
                metadata["injection_risk"] = True
        
        # Metadata security analysis
        for field_name, metadata_field in [
            ("semantic_metadata", item.semantic_metadata),
            ("episodic_metadata", item.episodic_metadata),
            ("procedural_metadata", item.procedural_metadata),
            ("metadata", item.metadata)
        ]:
            if metadata_field:
                # Check for executable content in metadata
                if self._contains_executable_content(metadata_field):
                    errors.append(f"Metadata field {field_name} contains executable content")
                
                # Size validation
                metadata_size = len(json.dumps(metadata_field))
                if metadata_size > 50000:  # 50KB limit
                    warnings.append(f"Metadata field {field_name} is very large")
        
        return ValidationResult(True, errors, warnings, metadata)
    
    async def _security_validation(self, item: BulkMemoryItem) -> ValidationResult:
        """Security-focused validation."""
        errors = []
        warnings = []
        metadata = {}
        
        if item.content:
            # Check against blocked patterns
            for i, pattern in enumerate(self.compiled_patterns):
                if pattern.search(item.content):
                    errors.append(f"Content matches blocked pattern {i+1}")
                    metadata["security_violation"] = True
                    break
            
            # SQL injection detection
            sql_patterns = [
                r"(?i)union\s+select",
                r"(?i)insert\s+into",
                r"(?i)update\s+.*\s+set",
                r"(?i)delete\s+from",
                r"(?i);.*--",
                r"(?i)'.*or.*'.*=.*'"
            ]
            
            for pattern in sql_patterns:
                if re.search(pattern, item.content):
                    errors.append("Content contains potential SQL injection")
                    metadata["sql_injection_risk"] = True
                    break
            
            # XSS detection
            xss_patterns = [
                r"(?i)<script[^>]*>",
                r"(?i)javascript:",
                r"(?i)on\w+\s*=",
                r"(?i)alert\s*\(",
                r"(?i)document\.cookie",
                r"(?i)eval\s*\("
            ]
            
            for pattern in xss_patterns:
                if re.search(pattern, item.content):
                    errors.append("Content contains potential XSS")
                    metadata["xss_risk"] = True
                    break
        
        return ValidationResult(True, errors, warnings, metadata)
    
    def _get_dict_depth(self, d: dict, current_depth: int = 0) -> int:
        """Calculate the maximum depth of a nested dictionary."""
        if not isinstance(d, dict):
            return current_depth
        
        max_depth = current_depth
        for value in d.values():
            if isinstance(value, dict):
                depth = self._get_dict_depth(value, current_depth + 1)
                max_depth = max(max_depth, depth)
        
        return max_depth
    
    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of text."""
        if not text:
            return 0.0
        
        char_counts = defaultdict(int)
        for char in text:
            char_counts[char] += 1
        
        length = len(text)
        entropy = 0.0
        
        for count in char_counts.values():
            probability = count / length
            entropy -= probability * (probability).bit_length()
        
        return entropy
    
    def _detect_code_content(self, text: str) -> bool:
        """Detect if content contains code."""
        code_indicators = [
            r'function\s+\w+\s*\(',
            r'class\s+\w+\s*:',
            r'def\s+\w+\s*\(',
            r'import\s+\w+',
            r'#include\s*<',
            r'public\s+class\s+\w+',
            r'if\s*\([^)]+\)\s*{',
            r'for\s*\([^)]*\)\s*{',
            r'while\s*\([^)]+\)\s*{'
        ]
        
        for pattern in code_indicators:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _detect_sensitive_data(self, text: str) -> bool:
        """Detect potentially sensitive data."""
        sensitive_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # Credit card
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b',  # IP address
            r'(?i)password\s*[:=]\s*\S+',  # Password
            r'(?i)api[_-]?key\s*[:=]\s*\S+',  # API key
            r'(?i)secret\s*[:=]\s*\S+',  # Secret
            r'(?i)token\s*[:=]\s*\S+'  # Token
        ]
        
        for pattern in sensitive_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _detect_inappropriate_content(self, text: str) -> bool:
        """Detect inappropriate content (simplified)."""
        # This would typically use a more sophisticated content filtering system
        inappropriate_words = [
            "hate", "violence", "illegal", "fraud", "scam",
            "phishing", "malware", "virus", "exploit"
        ]
        
        text_lower = text.lower()
        for word in inappropriate_words:
            if word in text_lower:
                return True
        
        return False
    
    def _detect_injection_patterns(self, text: str) -> bool:
        """Detect potential injection attack patterns."""
        injection_patterns = [
            r'(?i)exec\s*\(',
            r'(?i)system\s*\(',
            r'(?i)eval\s*\(',
            r'(?i)subprocess\.',
            r'(?i)os\.',
            r'(?i)__import__',
            r'(?i)file_get_contents',
            r'(?i)include\s*\(',
            r'(?i)require\s*\(',
            r'\.\./|\.\.\\'
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _contains_executable_content(self, metadata: dict) -> bool:
        """Check if metadata contains executable content."""
        metadata_str = json.dumps(metadata).lower()
        
        executable_indicators = [
            "javascript:", "data:text/html", "eval(", "function(",
            "exec(", "system(", "__import__", "subprocess"
        ]
        
        for indicator in executable_indicators:
            if indicator in metadata_str:
                return True
        
        return False


class SafetyEnforcer:
    """
    Safety enforcement system for bulk operations.
    
    Provides safety limits, rollback mechanisms, and audit logging.
    """
    
    def __init__(self, config: SafetyConfiguration):
        self.config = config
        self.operation_history = {}
        self.rollback_points = {}
        self.rate_limit_tracker = defaultdict(list)
        self.content_hashes = set()
    
    async def check_operation_safety(
        self, 
        operation_type: str, 
        item_count: int,
        user_id: Optional[str] = None
    ) -> ValidationResult:
        """Check if operation meets safety requirements."""
        errors = []
        warnings = []
        metadata = {}
        
        # Item count limits
        if item_count > self.config.max_items_per_operation:
            errors.append(f"Operation exceeds maximum items: {item_count} > {self.config.max_items_per_operation}")
        
        # Rate limiting
        if self.config.enable_rate_limiting and user_id:
            current_time = datetime.now()
            hour_ago = current_time - timedelta(hours=1)
            
            # Clean old entries
            self.rate_limit_tracker[user_id] = [
                op_time for op_time in self.rate_limit_tracker[user_id]
                if op_time > hour_ago
            ]
            
            recent_operations = len(self.rate_limit_tracker[user_id])
            if recent_operations >= self.config.max_operations_per_hour:
                errors.append(f"Rate limit exceeded: {recent_operations} operations in last hour")
            
            # Track this operation
            self.rate_limit_tracker[user_id].append(current_time)
        
        # Safety level specific checks
        if self.config.safety_level == SafetyLevel.STRICT:
            if operation_type == "delete" and item_count > 1000:
                warnings.append("Large delete operation - consider smaller batches")
        
        elif self.config.safety_level == SafetyLevel.MAXIMUM:
            if operation_type == "delete" and item_count > 100:
                errors.append("Delete operations limited to 100 items in maximum safety mode")
            
            if operation_type in ["update", "delete"] and item_count > 5000:
                errors.append("Bulk modifications limited to 5000 items in maximum safety mode")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metadata=metadata
        )
    
    async def create_rollback_point(
        self, 
        operation_id: str, 
        affected_records: List[str]
    ) -> str:
        """Create a rollback checkpoint."""
        checkpoint_id = str(uuid.uuid4())
        
        # Create state snapshot (simplified)
        state_snapshot = {
            "operation_id": operation_id,
            "timestamp": datetime.now().isoformat(),
            "affected_records": affected_records,
            "record_count": len(affected_records)
        }
        
        rollback_point = RollbackPoint(
            checkpoint_id=checkpoint_id,
            operation_id=operation_id,
            timestamp=datetime.now(),
            state_snapshot=state_snapshot,
            affected_records=affected_records,
            rollback_type=RollbackType.CHECKPOINT
        )
        
        self.rollback_points[checkpoint_id] = rollback_point
        
        logger.info(f"Created rollback point: {checkpoint_id} for operation: {operation_id}")
        return checkpoint_id
    
    async def execute_rollback(self, checkpoint_id: str) -> bool:
        """Execute rollback to a specific checkpoint."""
        if checkpoint_id not in self.rollback_points:
            logger.error(f"Rollback point not found: {checkpoint_id}")
            return False
        
        rollback_point = self.rollback_points[checkpoint_id]
        
        try:
            # In a real implementation, this would restore the database state
            # For now, we'll just log the rollback
            logger.info(f"Executing rollback for checkpoint: {checkpoint_id}")
            logger.info(f"Affected records: {len(rollback_point.affected_records)}")
            
            # Mark rollback as executed
            rollback_point.rollback_type = RollbackType.FULL
            
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed for checkpoint {checkpoint_id}: {e}")
            return False
    
    async def detect_duplicates(self, items: List[BulkMemoryItem]) -> Tuple[List[BulkMemoryItem], List[BulkMemoryItem]]:
        """Detect duplicate content in items."""
        if not self.config.enable_duplicate_detection:
            return items, []
        
        unique_items = []
        duplicate_items = []
        seen_hashes = set()
        
        for item in items:
            # Create content hash
            content_hash = hashlib.sha256(item.content.encode()).hexdigest()
            
            if content_hash in seen_hashes or content_hash in self.content_hashes:
                duplicate_items.append(item)
            else:
                unique_items.append(item)
                seen_hashes.add(content_hash)
                self.content_hashes.add(content_hash)
        
        return unique_items, duplicate_items
    
    async def cleanup_rollback_points(self):
        """Clean up old rollback points."""
        cutoff_date = datetime.now() - timedelta(days=self.config.rollback_retention_days)
        
        to_remove = []
        for checkpoint_id, rollback_point in self.rollback_points.items():
            if rollback_point.timestamp < cutoff_date:
                to_remove.append(checkpoint_id)
        
        for checkpoint_id in to_remove:
            del self.rollback_points[checkpoint_id]
        
        logger.info(f"Cleaned up {len(to_remove)} old rollback points")


class BulkValidationOrchestrator:
    """
    Orchestrates validation and safety for bulk operations.
    
    Coordinates between content validation, safety enforcement, and error handling.
    """
    
    def __init__(self, safety_config: Optional[SafetyConfiguration] = None):
        self.safety_config = safety_config or SafetyConfiguration()
        self.content_validator = ContentValidator(self.safety_config)
        self.safety_enforcer = SafetyEnforcer(self.safety_config)
        self.validation_semaphore = asyncio.Semaphore(self.safety_config.max_concurrent_validations)
    
    async def validate_bulk_operation(
        self,
        items: List[BulkMemoryItem],
        operation_type: str,
        validation_level: ValidationLevel = ValidationLevel.STANDARD,
        user_id: Optional[str] = None
    ) -> Tuple[List[BulkMemoryItem], List[BulkMemoryItem], Dict[str, Any]]:
        """
        Comprehensive validation for bulk operations.
        
        Returns:
            Tuple of (valid_items, invalid_items, validation_summary)
        """
        start_time = time.time()
        
        # Operation-level safety check
        operation_safety = await self.safety_enforcer.check_operation_safety(
            operation_type, len(items), user_id
        )
        
        if not operation_safety.is_valid:
            raise SafetyViolation(f"Operation safety check failed: {operation_safety.errors}")
        
        # Duplicate detection
        unique_items, duplicate_items = await self.safety_enforcer.detect_duplicates(items)
        
        # Validate items in batches
        valid_items = []
        invalid_items = []
        validation_errors = []
        validation_warnings = []
        
        batch_size = self.safety_config.validation_batch_size
        
        for i in range(0, len(unique_items), batch_size):
            batch = unique_items[i:i + batch_size]
            
            # Validate batch with concurrency control
            async with self.validation_semaphore:
                batch_results = await self._validate_batch(batch, validation_level)
            
            for item, result in zip(batch, batch_results):
                if result.is_valid:
                    valid_items.append(item)
                else:
                    invalid_items.append(item)
                    item.validation_errors = result.errors
                
                validation_errors.extend(result.errors)
                validation_warnings.extend(result.warnings)
        
        # Add duplicate items to invalid items
        for dup_item in duplicate_items:
            dup_item.validation_errors = ["Duplicate content detected"]
            invalid_items.append(dup_item)
        
        # Create validation summary
        validation_time = time.time() - start_time
        validation_summary = {
            "total_items": len(items),
            "valid_items": len(valid_items),
            "invalid_items": len(invalid_items),
            "duplicate_items": len(duplicate_items),
            "validation_time_seconds": validation_time,
            "validation_level": validation_level.value,
            "safety_level": self.safety_config.safety_level.value,
            "operation_safety_warnings": operation_safety.warnings,
            "total_errors": len(validation_errors),
            "total_warnings": len(validation_warnings),
            "error_categories": self._categorize_errors(validation_errors),
            "performance_metrics": {
                "items_per_second": len(items) / validation_time if validation_time > 0 else 0,
                "concurrent_validations": self.safety_config.max_concurrent_validations,
                "batch_size": batch_size
            }
        }
        
        logger.info(f"Bulk validation completed: {len(valid_items)}/{len(items)} items valid")
        
        return valid_items, invalid_items, validation_summary
    
    async def _validate_batch(
        self, 
        batch: List[BulkMemoryItem], 
        level: ValidationLevel
    ) -> List[ValidationResult]:
        """Validate a batch of items concurrently."""
        tasks = [
            self.content_validator.validate_item(item, level)
            for item in batch
        ]
        
        return await asyncio.gather(*tasks, return_exceptions=False)
    
    def _categorize_errors(self, errors: List[str]) -> Dict[str, int]:
        """Categorize validation errors for reporting."""
        categories = defaultdict(int)
        
        for error in errors:
            error_lower = error.lower()
            
            if "security" in error_lower or "injection" in error_lower:
                categories["security"] += 1
            elif "content" in error_lower:
                categories["content"] += 1
            elif "metadata" in error_lower:
                categories["metadata"] += 1
            elif "type" in error_lower:
                categories["type"] += 1
            elif "duplicate" in error_lower:
                categories["duplicate"] += 1
            else:
                categories["other"] += 1
        
        return dict(categories)
    
    async def create_operation_checkpoint(
        self, 
        operation_id: str, 
        affected_records: List[str]
    ) -> str:
        """Create a rollback checkpoint for the operation."""
        return await self.safety_enforcer.create_rollback_point(operation_id, affected_records)
    
    async def rollback_operation(self, checkpoint_id: str) -> bool:
        """Rollback operation to checkpoint."""
        return await self.safety_enforcer.execute_rollback(checkpoint_id)


# Global instances
_validation_orchestrator_instance: Optional[BulkValidationOrchestrator] = None


async def get_validation_orchestrator(
    safety_config: Optional[SafetyConfiguration] = None
) -> BulkValidationOrchestrator:
    """Get or create the global validation orchestrator instance."""
    global _validation_orchestrator_instance
    
    if _validation_orchestrator_instance is None:
        _validation_orchestrator_instance = BulkValidationOrchestrator(safety_config)
    
    return _validation_orchestrator_instance 