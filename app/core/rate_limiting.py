"""
Rate Limiting Middleware for Second Brain v3.0.0
Enterprise-grade rate limiting with Redis backend and configurable limits
"""

import asyncio
import json
import time
from typing import Optional, Dict, Callable, Any
from datetime import datetime, timedelta

import redis.asyncio as redis
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimitConfig:
    """Rate limiting configuration"""
    
    # Default limits (requests per window)
    DEFAULT_LIMITS = {
        "default": {"requests": 1000, "window": 3600},      # 1000/hour
        "health": {"requests": 10000, "window": 3600},      # 10000/hour (health checks)
        "search": {"requests": 100, "window": 3600},        # 100/hour (expensive operations)
        "upload": {"requests": 50, "window": 3600},         # 50/hour (file uploads)
        "memories": {"requests": 500, "window": 3600},      # 500/hour (CRUD operations)
        "auth": {"requests": 50, "window": 3600},           # 50/hour (authentication)
    }
    
    # Burst limits (requests per minute)
    BURST_LIMITS = {
        "default": {"requests": 100, "window": 60},
        "health": {"requests": 1000, "window": 60},
        "search": {"requests": 10, "window": 60},
        "upload": {"requests": 5, "window": 60},
        "memories": {"requests": 50, "window": 60},
        "auth": {"requests": 10, "window": 60},
    }
    
    # Rate limit by user role/tier
    USER_TIER_MULTIPLIERS = {
        "free": 1.0,
        "premium": 2.0,
        "enterprise": 5.0,
        "admin": 10.0
    }


class RateLimiter:
    """Redis-based distributed rate limiter"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.config = RateLimitConfig()
    
    async def is_allowed(self, key: str, limit: Dict[str, int], 
                        user_tier: str = "free") -> Dict[str, Any]:
        """
        Check if request is allowed under rate limit
        
        Returns:
            dict: {
                "allowed": bool,
                "remaining": int,
                "reset_time": int,
                "retry_after": int
            }
        """
        # Apply user tier multiplier
        multiplier = self.config.USER_TIER_MULTIPLIERS.get(user_tier, 1.0)
        adjusted_limit = int(limit["requests"] * multiplier)
        window = limit["window"]
        
        current_time = int(time.time())
        window_start = current_time - (current_time % window)
        
        # Use sliding window with Redis pipeline
        pipe = self.redis.pipeline()
        
        try:
            # Get current count in window
            pipe.get(f"rate_limit:{key}:{window_start}")
            
            # Increment counter with expiration
            pipe.incr(f"rate_limit:{key}:{window_start}")
            pipe.expire(f"rate_limit:{key}:{window_start}", window + 10)  # Extra buffer
            
            results = await pipe.execute()
            
            current_count = int(results[0] or 0)
            new_count = int(results[1])
            
            # Check if limit exceeded
            if current_count >= adjusted_limit:
                remaining = 0
                reset_time = window_start + window
                retry_after = reset_time - current_time
                
                # Log rate limit hit
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "key": key,
                        "limit": adjusted_limit,
                        "current": current_count,
                        "user_tier": user_tier,
                        "window": window
                    }
                )
                
                return {
                    "allowed": False,
                    "remaining": remaining,
                    "reset_time": reset_time,
                    "retry_after": retry_after
                }
            
            # Request allowed
            remaining = max(0, adjusted_limit - new_count)
            reset_time = window_start + window
            
            return {
                "allowed": True,
                "remaining": remaining,
                "reset_time": reset_time,
                "retry_after": 0
            }
            
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # Fail open - allow request if Redis is down
            return {
                "allowed": True,
                "remaining": adjusted_limit,
                "reset_time": current_time + window,
                "retry_after": 0
            }
    
    async def get_rate_limit_status(self, key: str, limit: Dict[str, int], 
                                  user_tier: str = "free") -> Dict[str, Any]:
        """Get current rate limit status without incrementing"""
        multiplier = self.config.USER_TIER_MULTIPLIERS.get(user_tier, 1.0)
        adjusted_limit = int(limit["requests"] * multiplier)
        window = limit["window"]
        
        current_time = int(time.time())
        window_start = current_time - (current_time % window)
        
        try:
            current_count = await self.redis.get(f"rate_limit:{key}:{window_start}")
            current_count = int(current_count or 0)
            
            remaining = max(0, adjusted_limit - current_count)
            reset_time = window_start + window
            
            return {
                "limit": adjusted_limit,
                "remaining": remaining,
                "reset_time": reset_time,
                "used": current_count,
                "window": window
            }
            
        except Exception as e:
            logger.error(f"Rate limit status error: {e}")
            return {
                "limit": adjusted_limit,
                "remaining": adjusted_limit,
                "reset_time": current_time + window,
                "used": 0,
                "window": window
            }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting"""
    
    def __init__(self, app, redis_client: redis.Redis):
        super().__init__(app)
        self.rate_limiter = RateLimiter(redis_client)
        self.config = RateLimitConfig()
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process request with rate limiting"""
        # Skip rate limiting for certain paths
        if self._should_skip_rate_limiting(request):
            return await call_next(request)
        
        # Determine rate limit category and user info
        category = self._get_rate_limit_category(request)
        user_info = await self._get_user_info(request)
        user_id = user_info.get("user_id", "anonymous")
        user_tier = user_info.get("tier", "free")
        
        # Create rate limit key
        client_ip = self._get_client_ip(request)
        rate_limit_key = f"{user_id}:{client_ip}:{category}"
        
        # Check both hourly and burst limits
        hourly_limit = self.config.DEFAULT_LIMITS[category]
        burst_limit = self.config.BURST_LIMITS[category]
        
        # Check hourly limit
        hourly_result = await self.rate_limiter.is_allowed(
            f"hourly:{rate_limit_key}", hourly_limit, user_tier
        )
        
        # Check burst limit  
        burst_result = await self.rate_limiter.is_allowed(
            f"burst:{rate_limit_key}", burst_limit, user_tier
        )
        
        # Determine if request should be blocked
        if not hourly_result["allowed"]:
            return self._create_rate_limit_response(hourly_result, "hourly")
        
        if not burst_result["allowed"]:
            return self._create_rate_limit_response(burst_result, "burst")
        
        # Add rate limit headers to response
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit-Hourly"] = str(hourly_limit["requests"])
        response.headers["X-RateLimit-Remaining-Hourly"] = str(hourly_result["remaining"])
        response.headers["X-RateLimit-Reset-Hourly"] = str(hourly_result["reset_time"])
        
        response.headers["X-RateLimit-Limit-Burst"] = str(burst_limit["requests"])
        response.headers["X-RateLimit-Remaining-Burst"] = str(burst_result["remaining"])
        response.headers["X-RateLimit-Reset-Burst"] = str(burst_result["reset_time"])
        
        response.headers["X-RateLimit-Category"] = category
        response.headers["X-RateLimit-User-Tier"] = user_tier
        
        return response
    
    def _should_skip_rate_limiting(self, request: Request) -> bool:
        """Determine if rate limiting should be skipped"""
        path = request.url.path
        
        # Skip for internal health checks
        if path in ["/health", "/ready", "/metrics"]:
            return False  # Still rate limit, but with higher limits
        
        # Skip for static files
        if path.startswith("/static/"):
            return True
        
        # Skip for admin endpoints (if properly authenticated)
        if path.startswith("/admin/") and self._is_admin_request(request):
            return True
        
        return False
    
    def _get_rate_limit_category(self, request: Request) -> str:
        """Determine rate limit category based on request"""
        path = request.url.path
        method = request.method
        
        # Health endpoints
        if path in ["/health", "/ready", "/metrics"]:
            return "health"
        
        # Authentication endpoints
        if path.startswith("/auth/") or path.startswith("/api/v1/auth/"):
            return "auth"
        
        # Search endpoints (expensive)
        if "search" in path:
            return "search"
        
        # Upload endpoints
        if "upload" in path or method == "POST" and any(
            upload_path in path for upload_path in ["/ingest/", "/attachments/", "/files/"]
        ):
            return "upload"
        
        # Memory operations
        if "/memories" in path:
            return "memories"
        
        # Default category
        return "default"
    
    async def _get_user_info(self, request: Request) -> Dict[str, str]:
        """Extract user information from request"""
        # Try to get user from request state (set by auth middleware)
        user = getattr(request.state, "user", None)
        if user:
            return {
                "user_id": str(user.get("id", "anonymous")),
                "tier": user.get("tier", "free")
            }
        
        # Try to get API key from request
        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        if api_key:
            # In a real implementation, you'd look up the user by API key
            # For now, use the API key as user identifier
            return {
                "user_id": f"api:{api_key[:8]}",  # Use first 8 chars for privacy
                "tier": "free"  # Default tier for API key users
            }
        
        # Anonymous user
        return {
            "user_id": "anonymous",
            "tier": "free"
        }
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Try X-Forwarded-For first (for load balancers)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Try X-Real-IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to client host
        return request.client.host if request.client else "unknown"
    
    def _is_admin_request(self, request: Request) -> bool:
        """Check if request is from admin user"""
        user = getattr(request.state, "user", None)
        return user and user.get("role") == "admin"
    
    def _create_rate_limit_response(self, result: Dict[str, Any], 
                                  limit_type: str) -> JSONResponse:
        """Create rate limit exceeded response"""
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit exceeded ({limit_type})",
                    "details": {
                        "limit_type": limit_type,
                        "retry_after": result["retry_after"],
                        "reset_time": result["reset_time"]
                    }
                }
            },
            headers={
                "Retry-After": str(result["retry_after"]),
                "X-RateLimit-Reset": str(result["reset_time"]),
                "X-RateLimit-Remaining": "0"
            }
        )


# Rate limiting decorators for specific endpoints
def rate_limit(category: str = "default", custom_limit: Optional[Dict[str, int]] = None):
    """Decorator for additional endpoint-specific rate limiting"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # This would be implemented with dependency injection in FastAPI
            # For now, it's a placeholder for future enhancement
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Utility functions for rate limit management
async def get_user_rate_limit_status(redis_client: redis.Redis, user_id: str, 
                                   category: str = "default") -> Dict[str, Any]:
    """Get rate limit status for a user"""
    rate_limiter = RateLimiter(redis_client)
    config = RateLimitConfig()
    
    limit = config.DEFAULT_LIMITS[category]
    key = f"hourly:{user_id}:rate_limit:{category}"
    
    return await rate_limiter.get_rate_limit_status(key, limit)


async def reset_user_rate_limit(redis_client: redis.Redis, user_id: str, 
                               category: str = "default"):
    """Reset rate limit for a user (admin function)"""
    current_time = int(time.time())
    window = RateLimitConfig.DEFAULT_LIMITS[category]["window"]
    window_start = current_time - (current_time % window)
    
    key = f"rate_limit:hourly:{user_id}:rate_limit:{category}:{window_start}"
    await redis_client.delete(key)
    
    logger.info(f"Rate limit reset for user {user_id}, category {category}")


# Integration with FastAPI app
def setup_rate_limiting(app, redis_client: redis.Redis):
    """Setup rate limiting middleware for FastAPI app"""
    app.add_middleware(RateLimitMiddleware, redis_client=redis_client)
    
    # Add rate limit status endpoint
    @app.get("/api/v1/rate-limit/status")
    async def get_rate_limit_status(request: Request):
        """Get current user's rate limit status"""
        middleware = RateLimitMiddleware(app, redis_client)
        user_info = await middleware._get_user_info(request)
        user_id = user_info["user_id"]
        
        status = {}
        for category in RateLimitConfig.DEFAULT_LIMITS.keys():
            status[category] = await get_user_rate_limit_status(
                redis_client, user_id, category
            )
        
        return {
            "user_id": user_id,
            "user_tier": user_info["tier"],
            "rate_limits": status,
            "timestamp": datetime.now().isoformat()
        }
    
    logger.info("Rate limiting middleware configured")
