"""
Memory Sync Provider Interface

This module defines the abstract interface for memory synchronization providers
like Cipher, allowing Second Brain to integrate with external memory systems
while maintaining architectural independence.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Protocol
from pydantic import BaseModel


class SyncStatus(str, Enum):
    """Status of a sync operation"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    PENDING = "pending"


class ConflictResolution(str, Enum):
    """How to resolve sync conflicts"""
    LOCAL_WINS = "local"
    REMOTE_WINS = "remote"
    NEWEST_WINS = "newest"
    MANUAL = "manual"


class SyncDirection(str, Enum):
    """Direction of synchronization"""
    PUSH = "push"
    PULL = "pull"
    BIDIRECTIONAL = "bidirectional"


class HealthStatus(BaseModel):
    """Health check status for a sync provider"""
    healthy: bool
    latency_ms: Optional[float] = None
    last_sync: Optional[datetime] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = {}


class SyncFilter(BaseModel):
    """Filter criteria for selective synchronization"""
    include_tags: Optional[List[str]] = None
    exclude_tags: Optional[List[str]] = None
    include_types: Optional[List[str]] = None
    exclude_types: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    
    def matches(self, memory: Dict[str, Any]) -> bool:
        """Check if a memory matches this filter"""
        # Tag filtering
        memory_tags = set(memory.get("tags", []))
        if self.include_tags and not memory_tags.intersection(self.include_tags):
            return False
        if self.exclude_tags and memory_tags.intersection(self.exclude_tags):
            return False
            
        # Type filtering
        memory_type = memory.get("type")
        if self.include_types and memory_type not in self.include_types:
            return False
        if self.exclude_types and memory_type in self.exclude_types:
            return False
            
        # Date filtering
        created_at = memory.get("created_at")
        if created_at and isinstance(created_at, (str, datetime)):
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            if self.date_from and created_at < self.date_from:
                return False
            if self.date_to and created_at > self.date_to:
                return False
                
        return True


class SyncProviderConfig(BaseModel):
    """Configuration for a sync provider"""
    enabled: bool = False
    name: str
    sync_interval: int = 300  # seconds
    conflict_resolution: ConflictResolution = ConflictResolution.NEWEST_WINS
    direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    filters: List[SyncFilter] = []
    batch_size: int = 100
    retry_attempts: int = 3
    timeout: int = 30  # seconds
    custom_settings: Dict[str, Any] = {}


class SyncResult(BaseModel):
    """Result of a sync operation"""
    status: SyncStatus
    pushed: int = 0
    pulled: int = 0
    conflicts: int = 0
    errors: List[str] = []
    duration_ms: float = 0
    details: Dict[str, Any] = {}


class ISyncProvider(ABC):
    """
    Abstract interface for memory synchronization providers.
    
    Implementations of this interface enable Second Brain to sync
    with external memory systems like Cipher, Mem0, or custom solutions.
    """
    
    def __init__(self, config: SyncProviderConfig):
        self.config = config
        self._connected = False
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of this sync provider"""
        pass
    
    @property
    def is_enabled(self) -> bool:
        """Check if this provider is enabled"""
        return self.config.enabled
    
    @property
    def is_connected(self) -> bool:
        """Check if provider is currently connected"""
        return self._connected
    
    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection to the external memory system.
        
        Raises:
            ConnectionError: If connection cannot be established
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully disconnect from the external system"""
        pass
    
    @abstractmethod
    async def push_memory(self, memory: Dict[str, Any]) -> bool:
        """
        Push a single memory to the external system.
        
        Args:
            memory: Memory object to sync
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def push_batch(self, memories: List[Dict[str, Any]]) -> SyncResult:
        """
        Push multiple memories to the external system.
        
        Args:
            memories: List of memories to sync
            
        Returns:
            SyncResult with operation details
        """
        pass
    
    @abstractmethod
    async def pull_changes(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Pull changes from the external system.
        
        Args:
            since: Only get changes after this timestamp
            
        Returns:
            List of updated memories
        """
        pass
    
    @abstractmethod
    async def resolve_conflict(
        self, 
        local: Dict[str, Any], 
        remote: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Resolve a conflict between local and remote versions.
        
        Args:
            local: Local version of the memory
            remote: Remote version of the memory
            
        Returns:
            Resolved memory object
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """
        Check health and connectivity of the sync provider.
        
        Returns:
            HealthStatus object with provider health details
        """
        pass
    
    async def sync(self) -> SyncResult:
        """
        Perform a full synchronization cycle.
        
        This is the main method that orchestrates push/pull operations
        based on the configured sync direction.
        """
        if not self.is_enabled:
            return SyncResult(
                status=SyncStatus.FAILED,
                errors=["Provider is not enabled"]
            )
            
        if not self.is_connected:
            try:
                await self.connect()
            except Exception as e:
                return SyncResult(
                    status=SyncStatus.FAILED,
                    errors=[f"Connection failed: {str(e)}"]
                )
        
        # Implementation would handle full sync logic
        # This is a template that specific providers would override
        return SyncResult(status=SyncStatus.PENDING)
    
    def should_sync(self, memory: Dict[str, Any]) -> bool:
        """Check if a memory should be synced based on filters"""
        if not self.config.filters:
            return True
            
        return any(f.matches(memory) for f in self.config.filters)


class ISyncManager(Protocol):
    """Protocol for the sync manager that coordinates multiple providers"""
    
    async def register_provider(self, provider: ISyncProvider) -> None:
        """Register a new sync provider"""
        ...
    
    async def unregister_provider(self, name: str) -> None:
        """Unregister a sync provider"""
        ...
    
    async def sync_all(self) -> Dict[str, SyncResult]:
        """Run sync for all enabled providers"""
        ...
    
    async def sync_provider(self, name: str) -> SyncResult:
        """Run sync for a specific provider"""
        ...
    
    async def get_provider_status(self, name: str) -> HealthStatus:
        """Get status of a specific provider"""
        ...