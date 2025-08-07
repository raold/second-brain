"""
Graceful Degradation Manager
Handles service failures and provides fallback functionality
"""

from enum import IntEnum
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DegradationLevel(IntEnum):
    """Service degradation levels (lower is better)"""
    FULL = 0           # All features available
    NO_VECTOR = 1      # Qdrant down, keyword search only
    NO_PERSISTENCE = 2 # Storage issues, memory-only mode
    READONLY = 3       # Critical issues, read-only mode
    MAINTENANCE = 4    # Maintenance mode, minimal functionality


class ServiceStatus:
    """Track individual service status"""
    
    def __init__(self, name: str):
        self.name = name
        self.is_healthy = True
        self.last_check = datetime.now()
        self.consecutive_failures = 0
        self.error_message: Optional[str] = None
        self.retry_after: Optional[datetime] = None
    
    def mark_healthy(self):
        """Mark service as healthy"""
        self.is_healthy = True
        self.consecutive_failures = 0
        self.error_message = None
        self.retry_after = None
        self.last_check = datetime.now()
    
    def mark_unhealthy(self, error: str):
        """Mark service as unhealthy with exponential backoff"""
        self.is_healthy = False
        self.consecutive_failures += 1
        self.error_message = error
        self.last_check = datetime.now()
        
        # Exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s, max 60s
        backoff_seconds = min(2 ** self.consecutive_failures, 60)
        self.retry_after = datetime.now() + timedelta(seconds=backoff_seconds)
    
    def should_retry(self) -> bool:
        """Check if we should retry this service"""
        if self.is_healthy:
            return False
        if self.retry_after and datetime.now() < self.retry_after:
            return False
        return True


class DegradationManager:
    """Manages graceful degradation of services"""
    
    def __init__(self):
        self.services: Dict[str, ServiceStatus] = {
            "qdrant": ServiceStatus("qdrant"),
            "persistence": ServiceStatus("persistence"),
            "openai": ServiceStatus("openai"),
            "anthropic": ServiceStatus("anthropic"),
        }
        self.current_level = DegradationLevel.FULL
        self.features_disabled: List[str] = []
    
    def check_service(self, name: str, check_func) -> bool:
        """
        Check if a service is available
        
        Args:
            name: Service name
            check_func: Function that returns True if healthy, raises exception if not
        
        Returns:
            True if service is healthy
        """
        if name not in self.services:
            logger.warning(f"Unknown service: {name}")
            return False
        
        service = self.services[name]
        
        # Skip if in backoff period
        if not service.should_retry():
            return service.is_healthy
        
        try:
            # Attempt health check
            if check_func():
                service.mark_healthy()
                logger.info(f"Service {name} is healthy")
                return True
            else:
                raise Exception("Health check returned False")
        except Exception as e:
            service.mark_unhealthy(str(e))
            logger.warning(
                f"Service {name} unhealthy (attempt {service.consecutive_failures}): {e}"
            )
            return False
    
    def update_degradation_level(self):
        """Update the current degradation level based on service status"""
        old_level = self.current_level
        
        # Determine new level based on service availability
        if not self.services["persistence"].is_healthy:
            self.current_level = DegradationLevel.NO_PERSISTENCE
            self.features_disabled = ["persistence", "export", "import"]
        
        elif not self.services["qdrant"].is_healthy:
            self.current_level = DegradationLevel.NO_VECTOR
            self.features_disabled = ["semantic_search", "embeddings"]
        
        elif not (self.services["openai"].is_healthy or 
                  self.services["anthropic"].is_healthy):
            self.current_level = DegradationLevel.READONLY
            self.features_disabled = ["ai_features", "auto_tagging", "importance_scoring"]
        
        else:
            self.current_level = DegradationLevel.FULL
            self.features_disabled = []
        
        # Log level changes
        if old_level != self.current_level:
            if self.current_level > old_level:
                logger.warning(
                    f"Degradation level increased: {old_level.name} -> {self.current_level.name}"
                )
            else:
                logger.info(
                    f"Degradation level improved: {old_level.name} -> {self.current_level.name}"
                )
    
    def is_feature_available(self, feature: str) -> bool:
        """Check if a feature is available at current degradation level"""
        return feature not in self.features_disabled
    
    def get_status(self) -> Dict[str, Any]:
        """Get current degradation status"""
        return {
            "level": self.current_level.name,
            "level_value": self.current_level.value,
            "services": {
                name: {
                    "healthy": service.is_healthy,
                    "last_check": service.last_check.isoformat(),
                    "consecutive_failures": service.consecutive_failures,
                    "error": service.error_message,
                    "retry_after": service.retry_after.isoformat() if service.retry_after else None
                }
                for name, service in self.services.items()
            },
            "features_disabled": self.features_disabled,
            "can_write": self.current_level < DegradationLevel.READONLY,
            "can_persist": self.current_level < DegradationLevel.NO_PERSISTENCE,
            "can_use_ai": self.current_level < DegradationLevel.READONLY,
            "can_vector_search": self.current_level == DegradationLevel.FULL
        }
    
    async def perform_health_checks(self):
        """Perform health checks on all services"""
        # Check persistence
        self.check_service("persistence", self._check_persistence)
        
        # Check Qdrant (if configured)
        if self._is_qdrant_configured():
            self.check_service("qdrant", self._check_qdrant)
        
        # Check AI services
        self.check_service("openai", self._check_openai)
        self.check_service("anthropic", self._check_anthropic)
        
        # Update degradation level
        self.update_degradation_level()
    
    def _check_persistence(self) -> bool:
        """Check if persistence is available"""
        import os
        persist_path = os.getenv("MEMORY_PERSIST_PATH", "/data")
        
        # Check if path exists and is writable
        if os.path.exists(persist_path):
            test_file = os.path.join(persist_path, ".write_test")
            try:
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
                return True
            except:
                return False
        else:
            # Try to create directory
            try:
                os.makedirs(persist_path, exist_ok=True)
                return True
            except:
                return False
    
    def _is_qdrant_configured(self) -> bool:
        """Check if Qdrant is configured"""
        import os
        return bool(os.getenv("QDRANT_URL"))
    
    def _check_qdrant(self) -> bool:
        """Check if Qdrant is available"""
        import os
        import requests
        
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        try:
            response = requests.get(f"{qdrant_url}/collections", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _check_openai(self) -> bool:
        """Check if OpenAI API is available"""
        import os
        return bool(os.getenv("OPENAI_API_KEY"))
    
    def _check_anthropic(self) -> bool:
        """Check if Anthropic API is available"""
        import os
        return bool(os.getenv("ANTHROPIC_API_KEY"))


# Global degradation manager instance
_degradation_manager: Optional[DegradationManager] = None


def get_degradation_manager() -> DegradationManager:
    """Get or create the global degradation manager"""
    global _degradation_manager
    if _degradation_manager is None:
        _degradation_manager = DegradationManager()
    return _degradation_manager