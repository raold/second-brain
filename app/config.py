import os

from dotenv import load_dotenv

# Load .env file if present (useful in local dev)
load_dotenv()

class Config:
    # === OpenAI Settings ===
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    # === API Authentication ===
    API_TOKENS = os.getenv("API_TOKENS", "").split(",")

    # === Qdrant Settings ===
    QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
    QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "second_brain")
    QDRANT_VECTOR_SIZE = int(os.getenv("QDRANT_VECTOR_SIZE", 1536))
    QDRANT_DISTANCE = os.getenv("QDRANT_DISTANCE", "Cosine")

    # === PostgreSQL Settings ===
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))
    POSTGRES_DB = os.getenv("POSTGRES_DB", "brain")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "brain")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "brainpw")
    POSTGRES_POOL_SIZE = int(os.getenv("POSTGRES_POOL_SIZE", 20))
    POSTGRES_MAX_OVERFLOW = int(os.getenv("POSTGRES_MAX_OVERFLOW", 30))

    # === Application Settings ===
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

    # === Logging ===
    LOG_PATH = os.getenv("LOG_PATH", "tests/logs/processor.log")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # === OpenAI Retry Settings ===
    OPENAI_RETRY_ATTEMPTS = int(os.getenv("OPENAI_RETRY_ATTEMPTS", 3))
    OPENAI_RETRY_MULTIPLIER = int(os.getenv("OPENAI_RETRY_MULTIPLIER", 1))
    OPENAI_RETRY_MIN_WAIT = int(os.getenv("OPENAI_RETRY_MIN_WAIT", 2))
    OPENAI_RETRY_MAX_WAIT = int(os.getenv("OPENAI_RETRY_MAX_WAIT", 10))

    # === Model Version Tracking ===
    MODEL_VERSIONS = {
        "llm": os.getenv("MODEL_VERSION_LLM", "gpt-4o"),
        "embedding": os.getenv("MODEL_VERSION_EMBEDDING", "text-embedding-3-small")
    }

    # === Performance Optimization Settings ===
    
    # Cache Configuration
    CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    
    # Embedding Cache Settings
    EMBEDDING_CACHE_SIZE = int(os.getenv("EMBEDDING_CACHE_SIZE", 2000))
    EMBEDDING_CACHE_TTL = int(os.getenv("EMBEDDING_CACHE_TTL", 3600))  # 1 hour
    
    # Search Cache Settings
    SEARCH_CACHE_SIZE = int(os.getenv("SEARCH_CACHE_SIZE", 1000))
    SEARCH_CACHE_TTL = int(os.getenv("SEARCH_CACHE_TTL", 300))  # 5 minutes
    
    # Query Cache Settings
    QUERY_CACHE_SIZE = int(os.getenv("QUERY_CACHE_SIZE", 500))
    QUERY_CACHE_TTL = int(os.getenv("QUERY_CACHE_TTL", 300))  # 5 minutes
    
    # Memory Access Cache Settings
    MEMORY_ACCESS_CACHE_SIZE = int(os.getenv("MEMORY_ACCESS_CACHE_SIZE", 5000))
    MEMORY_ACCESS_CACHE_TTL = int(os.getenv("MEMORY_ACCESS_CACHE_TTL", 1800))  # 30 minutes
    
    # Analytics Cache Settings
    ANALYTICS_CACHE_SIZE = int(os.getenv("ANALYTICS_CACHE_SIZE", 100))
    ANALYTICS_CACHE_TTL = int(os.getenv("ANALYTICS_CACHE_TTL", 60))  # 1 minute
    
    # Intent Detection Cache Settings
    INTENT_CACHE_SIZE = int(os.getenv("INTENT_CACHE_SIZE", 500))
    INTENT_CACHE_TTL = int(os.getenv("INTENT_CACHE_TTL", 3600))  # 1 hour
    
    # Dual Storage Cache Settings
    DUAL_STORAGE_CACHE_SIZE = int(os.getenv("DUAL_STORAGE_CACHE_SIZE", 1000))
    DUAL_STORAGE_CACHE_TTL = int(os.getenv("DUAL_STORAGE_CACHE_TTL", 600))  # 10 minutes
    
    # Performance Monitoring
    PERFORMANCE_MONITORING_ENABLED = os.getenv("PERFORMANCE_MONITORING_ENABLED", "true").lower() == "true"
    METRICS_ENABLED = os.getenv("METRICS_ENABLED", "true").lower() == "true"
    
    # Connection Pool Optimization
    CONNECTION_POOL_MONITORING = os.getenv("CONNECTION_POOL_MONITORING", "true").lower() == "true"
    
    # Smart Eviction Settings
    SMART_EVICTION_ENABLED = os.getenv("SMART_EVICTION_ENABLED", "true").lower() == "true"
    CACHE_CLEANUP_INTERVAL = int(os.getenv("CACHE_CLEANUP_INTERVAL", 300))  # 5 minutes
    
    # Async Operations
    ASYNC_STORAGE_ENABLED = os.getenv("ASYNC_STORAGE_ENABLED", "true").lower() == "true"
    
    # Health Check Configuration
    HEALTH_CHECK_CACHE_TTL = int(os.getenv("HEALTH_CHECK_CACHE_TTL", 30))  # 30 seconds
    
    @classmethod
    def summary(cls) -> dict:
        """Get configuration summary for logging."""
        return {
            "environment": cls.ENVIRONMENT,
            "debug": cls.DEBUG,
            "qdrant_host": cls.QDRANT_HOST,
            "postgres_host": cls.POSTGRES_HOST,
            "cache_enabled": cls.CACHE_ENABLED,
            "performance_monitoring": cls.PERFORMANCE_MONITORING_ENABLED,
            "metrics_enabled": cls.METRICS_ENABLED,
            "embedding_model": cls.OPENAI_EMBEDDING_MODEL,
            "connection_pools": {
                "postgres_pool_size": cls.POSTGRES_POOL_SIZE,
                "postgres_max_overflow": cls.POSTGRES_MAX_OVERFLOW
            },
            "cache_configurations": {
                "embedding_cache": {"size": cls.EMBEDDING_CACHE_SIZE, "ttl": cls.EMBEDDING_CACHE_TTL},
                "search_cache": {"size": cls.SEARCH_CACHE_SIZE, "ttl": cls.SEARCH_CACHE_TTL},
                "memory_cache": {"size": cls.MEMORY_ACCESS_CACHE_SIZE, "ttl": cls.MEMORY_ACCESS_CACHE_TTL},
                "analytics_cache": {"size": cls.ANALYTICS_CACHE_SIZE, "ttl": cls.ANALYTICS_CACHE_TTL}
            },
            "optimizations": {
                "smart_eviction": cls.SMART_EVICTION_ENABLED,
                "async_storage": cls.ASYNC_STORAGE_ENABLED,
                "connection_monitoring": cls.CONNECTION_POOL_MONITORING
            }
        }
