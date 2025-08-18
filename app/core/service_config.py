"""
Centralized service configuration for Second Brain v5.0
ALL service URLs and configurations MUST come from here.
"""
import os


class ServiceConfig:
    """Single source of truth for all service configurations"""

    # External Service URLs - These MUST be consistent everywhere
    CLIP_SERVICE_URL: str = os.getenv("CLIP_SERVICE_URL", "http://localhost:8002")
    LLAVA_SERVICE_URL: str = os.getenv("LLAVA_SERVICE_URL", "http://localhost:1234")

    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://secondbrain:changeme@localhost/secondbrain",
    )
    USE_MOCK_DATABASE: bool = os.getenv("USE_MOCK_DATABASE", "false").lower() == "true"

    # Redis Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Google Drive Configuration
    GDRIVE_MOUNT_PATH: str = os.getenv("GDRIVE_MOUNT_PATH", "G:/My Drive")
    TAKEOUT_PATH: str = os.getenv("TAKEOUT_PATH", "G:/My Drive/Takeout")

    # Application Settings
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # Photo Processing Settings
    PHOTO_BATCH_SIZE: int = int(os.getenv("PHOTO_BATCH_SIZE", "20"))
    ENABLE_LLAVA_DESCRIPTIONS: bool = os.getenv("ENABLE_LLAVA_DESCRIPTIONS", "true").lower() == "true"

    # Embedding Settings
    EMBEDDING_DIMENSION: int = 768  # CLIP dimension - DO NOT CHANGE
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "10"))

    @classmethod
    def get_clip_url(cls) -> str:
        """Get CLIP service URL - use this everywhere"""
        return cls.CLIP_SERVICE_URL

    @classmethod
    def get_llava_url(cls) -> str:
        """Get LLaVA service URL - use this everywhere"""
        return cls.LLAVA_SERVICE_URL

    @classmethod
    def get_database_url(cls) -> str:
        """Get database URL - use this everywhere"""
        return cls.DATABASE_URL

    @classmethod
    def should_use_mock_database(cls) -> bool:
        """Check if mock database should be used"""
        return cls.USE_MOCK_DATABASE

    @classmethod
    def validate_configuration(cls) -> bool:
        """Validate that all required configuration is present"""
        errors = []

        # Check service availability
        import requests
        try:
            response = requests.get(f"{cls.CLIP_SERVICE_URL}/", timeout=2)
            if response.status_code != 200:
                errors.append(f"CLIP service not responding at {cls.CLIP_SERVICE_URL}")
        except:
            errors.append(f"Cannot connect to CLIP service at {cls.CLIP_SERVICE_URL}")

        if cls.ENABLE_LLAVA_DESCRIPTIONS:
            try:
                response = requests.get(f"{cls.LLAVA_SERVICE_URL}/v1/models", timeout=2)
                if response.status_code != 200:
                    errors.append(f"LLaVA service not responding at {cls.LLAVA_SERVICE_URL}")
            except:
                errors.append(f"Cannot connect to LLaVA service at {cls.LLAVA_SERVICE_URL}")

        # Check paths
        from pathlib import Path
        if not Path(cls.GDRIVE_MOUNT_PATH).exists():
            errors.append(f"Google Drive not mounted at {cls.GDRIVE_MOUNT_PATH}")

        if not Path(cls.TAKEOUT_PATH).exists():
            errors.append(f"Takeout path not found at {cls.TAKEOUT_PATH}")

        if errors:
            print("⚠️ Configuration Errors:")
            for error in errors:
                print(f"  ❌ {error}")
            return False

        print("✅ Configuration validated successfully")
        return True

# Create singleton instance
config = ServiceConfig()
