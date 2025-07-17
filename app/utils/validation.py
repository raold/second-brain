"""
Validation utilities for Second Brain application.
"""
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

def _validate_stats(stats: Dict, required_fields: List[str]) -> bool:
    """
    Validate that stats contain required fields.
    
    Args:
        stats (Dict): Statistics dictionary to validate
        required_fields (List[str]): List of required field names
        
    Returns:
        bool: True if all required fields are present, False otherwise
        
    Example:
        >>> stats = {"requests": 100, "errors": 5, "latency": 0.25}
        >>> required = ["requests", "errors", "latency", "uptime"]
        >>> _validate_stats(stats, required)
        False  # Missing 'uptime' field
    """
    missing_fields = []
    
    for field in required_fields:
        if field not in stats:
            missing_fields.append(field)
            logger.warning(f"Missing required field: {field}")
    
    if missing_fields:
        logger.error(f"Validation failed. Missing fields: {missing_fields}")
        return False
    
    logger.debug(f"Validation passed for fields: {required_fields}")
    return True

def validate_memory_input(content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Validate memory input data before processing.
    
    Args:
        content (str): Text content to validate
        metadata (Dict, optional): Additional metadata
        
    Returns:
        Dict[str, Any]: Validation result with success status and errors
    """
    errors = []
    warnings = []
    
    # Content validation
    if not content or not content.strip():
        errors.append("Content cannot be empty")
    elif len(content.strip()) < 10:
        warnings.append("Content is very short, consider adding more detail")
    elif len(content) > 100000:  # 100KB limit
        errors.append("Content exceeds maximum length (100KB)")
    
    # Metadata validation
    if metadata:
        required_meta_fields = ["source", "timestamp"]
        if not _validate_stats(metadata, required_meta_fields):
            warnings.append("Some metadata fields are missing")
    
    # Character encoding validation
    try:
        content.encode('utf-8')
    except UnicodeEncodeError:
        errors.append("Content contains invalid characters")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "content_length": len(content),
        "word_count": len(content.split()) if content else 0
    }

def validate_search_params(query: str, limit: int = 10, threshold: float = 0.7) -> Dict[str, Any]:
    """
    Validate search API parameters.
    
    Args:
        query (str): Search query string
        limit (int): Number of results to return
        threshold (float): Similarity threshold
        
    Returns:
        Dict[str, Any]: Validation result
    """
    errors = []
    
    # Query validation
    if not query or not query.strip():
        errors.append("Query cannot be empty")
    elif len(query) > 1000:
        errors.append("Query too long (max 1000 characters)")
    
    # Limit validation
    if not isinstance(limit, int) or limit < 1:
        errors.append("Limit must be a positive integer")
    elif limit > 100:
        errors.append("Limit cannot exceed 100")
    
    # Threshold validation
    if not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
        errors.append("Threshold must be between 0 and 1")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "sanitized_query": query.strip() if query else "",
        "validated_limit": min(max(limit, 1), 100),
        "validated_threshold": max(min(threshold, 1.0), 0.0)
    }

def validate_monitoring_data(metrics: Dict) -> bool:
    """Validate monitoring metrics data."""
    required_monitoring_fields = [
        "response_time_ms",
        "requests_per_second", 
        "error_rate",
        "memory_usage_mb",
        "cpu_usage_percent",
        "active_connections"
    ]
    
    return _validate_stats(metrics, required_monitoring_fields)
