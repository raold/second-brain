"""
Example demonstrating granular error handling for async operations.
Shows how the new error handling system provides better visibility and control.
"""

import asyncio

from app.utils.exceptions import (
    CircuitBreakerError,
    DatabaseConnectionError,
    DatabaseIntegrityError,
    DatabaseTimeoutError,
    EmbeddingDimensionError,
    OpenAIAuthError,
    OpenAIQuotaError,
    OpenAIRateLimitError,
    SecondBrainError,
    VectorStoreConnectionError,
    get_retry_delay,
    is_retryable_error,
    map_external_exception,
)
from app.utils.retry import (
    _circuit_breakers,
    api_retry,
    async_timeout,
    async_with_semaphore,
    database_retry,
    vector_store_retry,
)


# Example 1: Database operation with granular error handling
@database_retry(circuit_breaker_name="example_db")
@async_timeout(10.0, "database_query")
async def example_database_operation():
    """Example database operation with comprehensive error handling."""
    try:
        # Simulate database operation
        await asyncio.sleep(0.1)  # Simulate work
        
        # Simulate different types of failures
        import random
        failure_type = random.choice([None, "connection", "timeout", "integrity"])
        
        if failure_type == "connection":
            raise DatabaseConnectionError("Connection to database lost")
        elif failure_type == "timeout":
            raise DatabaseTimeoutError("Query timed out", "SELECT", 30.0)
        elif failure_type == "integrity":
            raise DatabaseIntegrityError("Foreign key constraint violation", "fk_user_id")
        
        return {"status": "success", "data": "example_data"}
        
    except DatabaseConnectionError:
        # This will be retried automatically by @database_retry
        raise
    except DatabaseTimeoutError:
        # This will be retried with exponential backoff
        raise
    except DatabaseIntegrityError:
        # This won't be retried (business logic error)
        raise
    except Exception as e:
        # Map unknown exceptions to our hierarchy
        mapped_exc = map_external_exception(e)
        raise mapped_exc


# Example 2: API operation with circuit breaker
@api_retry(circuit_breaker_name="openai_api")
@async_with_semaphore(5, "openai_request")
async def example_api_operation():
    """Example API operation with rate limiting and circuit breaker."""
    try:
        # Simulate API call
        await asyncio.sleep(0.2)
        
        # Simulate API failures
        import random
        failure_type = random.choice([None, "rate_limit", "quota", "auth"])
        
        if failure_type == "rate_limit":
            raise OpenAIRateLimitError("Rate limit exceeded", retry_after=60)
        elif failure_type == "quota":
            raise OpenAIQuotaError("API quota exceeded")
        elif failure_type == "auth":
            raise OpenAIAuthError("Invalid API key")
        
        return {"embedding": [0.1, 0.2, 0.3]}
        
    except OpenAIRateLimitError as e:
        # Will be retried after the specified delay
        print(f"Rate limited, retrying after {e.retry_after} seconds")
        raise
    except OpenAIQuotaError:
        # Won't be retried (permanent failure)
        raise
    except OpenAIAuthError:
        # Critical error, won't be retried
        raise


# Example 3: Vector store operation
@vector_store_retry(circuit_breaker_name="qdrant")
async def example_vector_store_operation():
    """Example vector store operation with specific error handling."""
    try:
        # Simulate vector store operation
        await asyncio.sleep(0.1)
        
        # Simulate vector store failures
        import random
        failure_type = random.choice([None, "connection", "dimension_mismatch"])
        
        if failure_type == "connection":
            raise VectorStoreConnectionError("Cannot connect to Qdrant", "localhost", 6333)
        elif failure_type == "dimension_mismatch":
            raise EmbeddingDimensionError(expected=1536, actual=512)
        
        return {"points_inserted": 1, "status": "success"}
        
    except VectorStoreConnectionError:
        # Will be retried with exponential backoff
        raise
    except EmbeddingDimensionError:
        # Won't be retried (data validation error)
        raise


# Example 4: Complex operation combining multiple services
async def complex_memory_storage_operation(text: str):
    """
    Example of a complex operation that combines multiple services
    with comprehensive error handling.
    """
    try:
        # Step 1: Generate embedding (with API retry)
        embedding_result = await example_api_operation()
        
        # Step 2: Store in vector database (with vector store retry)
        vector_result = await example_vector_store_operation()
        
        # Step 3: Store metadata in SQL database (with database retry)
        db_result = await example_database_operation()
        
        return {
            "success": True,
            "embedding": embedding_result,
            "vector_store": vector_result,
            "database": db_result
        }
        
    except OpenAIAuthError as e:
        # Critical error - can't proceed
        return {
            "success": False,
            "error": f"Authentication failed: {e}",
            "severity": e.severity.value,
            "retryable": False
        }
        
    except CircuitBreakerError as e:
        # Service is down - temporary failure
        return {
            "success": False,
            "error": f"Service unavailable: {e.service}",
            "severity": e.severity.value,
            "retryable": True,
            "retry_after": 60
        }
        
    except (DatabaseConnectionError, VectorStoreConnectionError) as e:
        # Connection issues - retryable
        return {
            "success": False,
            "error": f"Connection failed: {e}",
            "severity": e.severity.value,
            "retryable": is_retryable_error(e),
            "retry_after": get_retry_delay(e)
        }
        
    except (DatabaseIntegrityError, EmbeddingDimensionError) as e:
        # Data validation errors - not retryable
        return {
            "success": False,
            "error": f"Data validation failed: {e}",
            "severity": e.severity.value,
            "retryable": False
        }
        
    except SecondBrainError as e:
        # Any other application error
        return {
            "success": False,
            "error": str(e),
            "severity": e.severity.value,
            "retryable": is_retryable_error(e),
            "context": e.context
        }


# Example usage
async def main():
    """Demonstrate the error handling system."""
    print("=== Granular Error Handling Demo ===\n")
    
    # Test multiple operations
    for i in range(5):
        print(f"Attempt {i + 1}:")
        try:
            result = await complex_memory_storage_operation(f"Test text {i}")
            print(f"Result: {result}")
        except Exception as e:
            print(f"Unhandled error: {e}")
        print()
    
    # Check circuit breaker states
    print("Circuit Breaker States:")
    for name, breaker in _circuit_breakers.items():
        print(f"  {name}: {breaker.state.value} (failures: {breaker.failure_count})")


if __name__ == "__main__":
    asyncio.run(main()) 