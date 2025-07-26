"""
Test exception handling system
"""

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from datetime import datetime
import json

from app.core.exceptions import (
    ErrorCode,
    ErrorResponse,
    SecondBrainException,
    UnauthorizedException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
    DatabaseException,
    RateLimitExceededException,
    second_brain_exception_handler,
    generic_exception_handler,
    validation_exception_handler
)


class TestErrorResponse:
    """Test ErrorResponse model"""
    
    def test_error_response_creation(self):
        """Test creating an error response"""
        response = ErrorResponse(
            error_code=ErrorCode.NOT_FOUND,
            message="Resource not found",
            details={"resource": "Memory", "id": "123"}
        )
        
        assert response.error_code == ErrorCode.NOT_FOUND
        assert response.message == "Resource not found"
        assert response.details["resource"] == "Memory"
        assert response.timestamp is not None
    
    def test_error_response_with_request_id(self):
        """Test error response with request ID"""
        response = ErrorResponse(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Something went wrong",
            request_id="req-123"
        )
        
        assert response.request_id == "req-123"


class TestExceptions:
    """Test custom exception classes"""
    
    def test_second_brain_exception(self):
        """Test base SecondBrainException"""
        exc = SecondBrainException(
            message="Test error",
            error_code=ErrorCode.INTERNAL_ERROR,
            status_code=500,
            details={"info": "test"}
        )
        
        assert exc.message == "Test error"
        assert exc.error_code == ErrorCode.INTERNAL_ERROR
        assert exc.status_code == 500
        assert exc.details["info"] == "test"
    
    def test_unauthorized_exception(self):
        """Test UnauthorizedException"""
        exc = UnauthorizedException()
        
        assert exc.message == "Authentication required"
        assert exc.error_code == ErrorCode.UNAUTHORIZED
        assert exc.status_code == 401
    
    def test_not_found_exception(self):
        """Test NotFoundException"""
        exc = NotFoundException(resource="Memory", identifier="mem-123")
        
        assert exc.message == "Memory with id 'mem-123' not found"
        assert exc.error_code == ErrorCode.NOT_FOUND
        assert exc.status_code == 404
        assert exc.details["resource"] == "Memory"
        assert exc.details["identifier"] == "mem-123"
    
    def test_validation_exception(self):
        """Test ValidationException"""
        exc = ValidationException(
            message="Invalid input",
            field="content",
            details={"min_length": 10}
        )
        
        assert exc.message == "Invalid input"
        assert exc.error_code == ErrorCode.VALIDATION_ERROR
        assert exc.status_code == 422
        assert exc.details["field"] == "content"
        assert exc.details["min_length"] == 10
    
    def test_database_exception(self):
        """Test DatabaseException"""
        exc = DatabaseException(message="Connection failed")
        
        assert exc.message == "Connection failed"
        assert exc.error_code == ErrorCode.DATABASE_ERROR
        assert exc.status_code == 500
    
    def test_rate_limit_exception(self):
        """Test RateLimitExceededException"""
        exc = RateLimitExceededException(
            limit=100,
            window="minute",
            retry_after=30
        )
        
        assert exc.message == "Rate limit exceeded: 100 requests per minute"
        assert exc.error_code == ErrorCode.RATE_LIMIT_EXCEEDED
        assert exc.status_code == 429
        assert exc.details["limit"] == 100
        assert exc.details["window"] == "minute"
        assert exc.details["retry_after_seconds"] == 30


class TestExceptionHandlers:
    """Test exception handlers"""
    
    @pytest.mark.asyncio
    async def test_second_brain_exception_handler(self):
        """Test SecondBrainException handler"""
        # Create mock request with proper structure
        request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/test",
                "headers": [(b"x-request-id", b"test-123")],
                "query_string": b"",
                "root_path": "",
                "scheme": "http",
                "server": ("testserver", 80)
            }
        )
        
        # Create exception
        exc = NotFoundException(resource="Memory", identifier="123")
        
        # Handle exception
        response = await second_brain_exception_handler(request, exc)
        
        # Check response
        assert response.status_code == 404
        content = json.loads(response.body)
        assert content["error_code"] == "NOT_FOUND"
        assert content["message"] == "Memory with id '123' not found"
        assert content["request_id"] == "test-123"
        assert "X-Request-ID" in response.headers
    
    @pytest.mark.asyncio
    async def test_generic_exception_handler(self):
        """Test generic exception handler"""
        # Create mock request with proper structure
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/test",
                "headers": [],
                "query_string": b"",
                "root_path": "",
                "scheme": "http",
                "server": ("testserver", 80)
            }
        )
        
        # Create generic exception
        exc = RuntimeError("Something unexpected happened")
        
        # Handle exception
        response = await generic_exception_handler(request, exc)
        
        # Check response
        assert response.status_code == 500
        content = json.loads(response.body)
        assert content["error_code"] == "INTERNAL_ERROR"
        assert content["message"] == "An unexpected error occurred"
        assert content["details"]["type"] == "RuntimeError"
        assert "request_id" in content


class TestExceptionIntegration:
    """Test exception handling in the app"""
    
    def test_app_exception_handling(self):
        """Test that exceptions are properly handled in the app"""
        from app.app import app
        
        # Create test client
        client = TestClient(app)
        
        # Test 404 error
        response = client.get("/nonexistent")
        assert response.status_code == 404
        
        # Test unauthorized (using invalid API key)
        response = client.get("/memories/test-id?api_key=invalid")
        assert response.status_code == 401
    
    def test_custom_exception_in_route(self):
        """Test custom exception raised in route"""
        from app.app import app
        from fastapi import APIRouter
        
        # Create test router with custom exception
        test_router = APIRouter()
        
        @test_router.get("/test-exception")
        async def test_exception_route():
            raise NotFoundException(resource="TestResource", identifier="test-123")
        
        # Add router to app
        app.include_router(test_router)
        
        # Create test client
        client = TestClient(app)
        
        # Test the route
        response = client.get("/test-exception")
        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "NOT_FOUND"
        assert "TestResource" in data["message"]
        assert data["details"]["resource"] == "TestResource"