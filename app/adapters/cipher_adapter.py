"""
Cipher Memory Adapter

This adapter enables optional integration with Cipher (https://github.com/campfirein/cipher),
an AI memory layer for coding agents. It implements the ISyncProvider interface to allow
Second Brain users to sync their memories with Cipher for IDE integration.

Note: This is an OPTIONAL component. Second Brain works perfectly without Cipher.
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import httpx
from pathlib import Path

from app.interfaces.sync_provider import (
    ISyncProvider, 
    SyncProviderConfig, 
    SyncResult, 
    SyncStatus,
    HealthStatus,
    ConflictResolution
)
from app.core.logging import get_logger
from app.models.memory import Memory

logger = get_logger(__name__)


class CipherAdapter(ISyncProvider):
    """
    Adapter for syncing with Cipher memory layer.
    
    Cipher provides:
    - MCP (Model Context Protocol) server for IDE integration
    - Dual memory system (System 1: concepts, System 2: reasoning)
    - Cross-IDE memory persistence
    - Team knowledge sharing
    
    This adapter enables bi-directional sync between Second Brain and Cipher.
    """
    
    def __init__(self, config: SyncProviderConfig):
        super().__init__(config)
        self.client: Optional[httpx.AsyncClient] = None
        self.mcp_socket: Optional[Any] = None  # MCP WebSocket connection
        
        # Cipher-specific settings
        self.cipher_url = config.custom_settings.get(
            "cipher_url", 
            "http://localhost:3000"  # Default Cipher server
        )
        self.api_key = config.custom_settings.get("api_key")
        self.workspace_id = config.custom_settings.get("workspace_id")
        self.enable_mcp = config.custom_settings.get("enable_mcp", True)
    
    @property
    def name(self) -> str:
        return "cipher"
    
    async def connect(self) -> None:
        """Connect to Cipher server"""
        try:
            # Create HTTP client
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
                
            self.client = httpx.AsyncClient(
                base_url=self.cipher_url,
                headers=headers,
                timeout=self.config.timeout
            )
            
            # Test connection
            response = await self.client.get("/health")
            response.raise_for_status()
            
            # Connect to MCP WebSocket if enabled
            if self.enable_mcp:
                await self._connect_mcp()
            
            self._connected = True
            logger.info(f"Connected to Cipher at {self.cipher_url}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Cipher: {e}")
            raise ConnectionError(f"Cannot connect to Cipher: {e}")
    
    async def _connect_mcp(self) -> None:
        """Connect to Cipher's MCP WebSocket for real-time sync"""
        # MCP connection implementation would go here
        # This is a placeholder for the actual MCP protocol implementation
        logger.info("MCP connection initialized (placeholder)")
    
    async def disconnect(self) -> None:
        """Disconnect from Cipher"""
        if self.client:
            await self.client.aclose()
            self.client = None
            
        if self.mcp_socket:
            # Close MCP WebSocket
            pass
            
        self._connected = False
        logger.info("Disconnected from Cipher")
    
    async def push_memory(self, memory: Dict[str, Any]) -> bool:
        """Push a single memory to Cipher"""
        if not self.should_sync(memory):
            return True
            
        try:
            # Transform to Cipher format
            cipher_memory = self._to_cipher_format(memory)
            
            # Determine which system (1 or 2) based on memory type
            endpoint = "/api/memories"
            if memory.get("type") == "reasoning":
                endpoint = "/api/reasoning"
            
            response = await self.client.post(
                endpoint,
                json=cipher_memory
            )
            response.raise_for_status()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to push memory to Cipher: {e}")
            return False
    
    async def push_batch(self, memories: List[Dict[str, Any]]) -> SyncResult:
        """Push multiple memories to Cipher"""
        result = SyncResult(status=SyncStatus.SUCCESS)
        
        # Filter memories
        memories_to_sync = [m for m in memories if self.should_sync(m)]
        
        # Split into batches
        for i in range(0, len(memories_to_sync), self.config.batch_size):
            batch = memories_to_sync[i:i + self.config.batch_size]
            
            try:
                # Transform batch
                cipher_batch = [self._to_cipher_format(m) for m in batch]
                
                # Bulk upload
                response = await self.client.post(
                    "/api/memories/bulk",
                    json={"memories": cipher_batch}
                )
                response.raise_for_status()
                
                result.pushed += len(batch)
                
            except Exception as e:
                logger.error(f"Failed to push batch to Cipher: {e}")
                result.errors.append(str(e))
                result.status = SyncStatus.PARTIAL
        
        return result
    
    async def pull_changes(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Pull changes from Cipher"""
        try:
            params = {}
            if since:
                params["since"] = since.isoformat()
            if self.workspace_id:
                params["workspace_id"] = self.workspace_id
            
            response = await self.client.get(
                "/api/memories/changes",
                params=params
            )
            response.raise_for_status()
            
            cipher_memories = response.json().get("memories", [])
            
            # Transform from Cipher format
            return [self._from_cipher_format(m) for m in cipher_memories]
            
        except Exception as e:
            logger.error(f"Failed to pull changes from Cipher: {e}")
            return []
    
    async def resolve_conflict(
        self, 
        local: Dict[str, Any], 
        remote: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve conflicts between local and remote memories"""
        strategy = self.config.conflict_resolution
        
        if strategy == ConflictResolution.LOCAL_WINS:
            return local
        elif strategy == ConflictResolution.REMOTE_WINS:
            return remote
        elif strategy == ConflictResolution.NEWEST_WINS:
            local_updated = datetime.fromisoformat(
                local.get("updated_at", local.get("created_at", ""))
            )
            remote_updated = datetime.fromisoformat(
                remote.get("updated_at", remote.get("created_at", ""))
            )
            return local if local_updated >= remote_updated else remote
        else:
            # Manual resolution - for now, default to local
            logger.warning(f"Manual conflict resolution not implemented, using local")
            return local
    
    async def health_check(self) -> HealthStatus:
        """Check Cipher connection health"""
        if not self._connected:
            return HealthStatus(
                healthy=False,
                error_message="Not connected"
            )
        
        try:
            start = datetime.now()
            response = await self.client.get("/health")
            latency_ms = (datetime.now() - start).total_seconds() * 1000
            
            if response.status_code == 200:
                data = response.json()
                return HealthStatus(
                    healthy=True,
                    latency_ms=latency_ms,
                    last_sync=datetime.now(),
                    details=data
                )
            else:
                return HealthStatus(
                    healthy=False,
                    error_message=f"Health check failed: {response.status_code}"
                )
                
        except Exception as e:
            return HealthStatus(
                healthy=False,
                error_message=f"Health check error: {str(e)}"
            )
    
    def _to_cipher_format(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Second Brain memory to Cipher format"""
        # Map our format to Cipher's expected format
        cipher_memory = {
            "id": memory.get("id"),
            "content": memory.get("content"),
            "type": memory.get("type", "concept"),  # Default to System 1
            "metadata": {
                "tags": memory.get("tags", []),
                "source": "second-brain",
                "original_id": memory.get("id"),
                "created_at": memory.get("created_at"),
                "updated_at": memory.get("updated_at"),
            }
        }
        
        # Add embedding if available
        if "embedding" in memory:
            cipher_memory["embedding"] = memory["embedding"]
        
        # Add workspace ID if configured
        if self.workspace_id:
            cipher_memory["workspace_id"] = self.workspace_id
        
        # Map specific fields based on memory type
        if memory.get("type") == "code":
            cipher_memory["language"] = memory.get("metadata", {}).get("language", "unknown")
            cipher_memory["file_path"] = memory.get("metadata", {}).get("file_path")
        
        return cipher_memory
    
    def _from_cipher_format(self, cipher_memory: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Cipher memory to Second Brain format"""
        # Map Cipher format to our format
        memory = {
            "content": cipher_memory.get("content"),
            "type": cipher_memory.get("type", "general"),
            "tags": cipher_memory.get("metadata", {}).get("tags", []),
            "metadata": {
                "cipher_id": cipher_memory.get("id"),
                "cipher_workspace": cipher_memory.get("workspace_id"),
                "synced_at": datetime.now().isoformat(),
            }
        }
        
        # Preserve timestamps if available
        if "created_at" in cipher_memory:
            memory["created_at"] = cipher_memory["created_at"]
        if "updated_at" in cipher_memory:
            memory["updated_at"] = cipher_memory["updated_at"]
        
        # Add embedding if available
        if "embedding" in cipher_memory:
            memory["embedding"] = cipher_memory["embedding"]
        
        return memory


def create_cipher_config(
    enabled: bool = False,
    cipher_url: str = "http://localhost:3000",
    api_key: Optional[str] = None,
    workspace_id: Optional[str] = None,
    sync_interval: int = 300,
    enable_mcp: bool = True
) -> SyncProviderConfig:
    """
    Factory function to create Cipher configuration.
    
    Args:
        enabled: Whether to enable Cipher sync
        cipher_url: URL of Cipher server
        api_key: Optional API key for authentication
        workspace_id: Optional workspace ID for team sync
        sync_interval: Seconds between sync operations
        enable_mcp: Whether to enable MCP real-time sync
    
    Returns:
        SyncProviderConfig for Cipher
    """
    return SyncProviderConfig(
        name="cipher",
        enabled=enabled,
        sync_interval=sync_interval,
        custom_settings={
            "cipher_url": cipher_url,
            "api_key": api_key,
            "workspace_id": workspace_id,
            "enable_mcp": enable_mcp
        }
    )