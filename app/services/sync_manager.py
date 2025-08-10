"""
Memory Sync Manager

Central service that coordinates synchronization between Second Brain and
external memory providers like Cipher. Handles scheduling, conflict resolution,
and monitoring of sync operations.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from collections import defaultdict

from app.interfaces.sync_provider import (
    ISyncProvider,
    ISyncManager,
    SyncResult,
    SyncStatus,
    HealthStatus
)
from app.core.logging import get_logger
from app.models.memory import Memory
from app.database import get_db
from sqlalchemy.orm import Session

logger = get_logger(__name__)


class SyncManager:
    """
    Manages multiple sync providers and coordinates synchronization.
    
    Features:
    - Provider registration and lifecycle management
    - Scheduled synchronization
    - Conflict detection and resolution
    - Sync status monitoring
    - Error recovery and retry logic
    """
    
    def __init__(self):
        self.providers: Dict[str, ISyncProvider] = {}
        self.sync_tasks: Dict[str, asyncio.Task] = {}
        self.last_sync: Dict[str, datetime] = {}
        self.sync_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._running = False
    
    async def start(self) -> None:
        """Start the sync manager and all enabled providers"""
        logger.info("Starting sync manager")
        self._running = True
        
        # Connect all enabled providers
        for name, provider in self.providers.items():
            if provider.is_enabled:
                try:
                    await provider.connect()
                    # Schedule periodic sync
                    task = asyncio.create_task(
                        self._sync_loop(name, provider)
                    )
                    self.sync_tasks[name] = task
                except Exception as e:
                    logger.error(f"Failed to start provider {name}: {e}")
    
    async def stop(self) -> None:
        """Stop the sync manager and all providers"""
        logger.info("Stopping sync manager")
        self._running = False
        
        # Cancel all sync tasks
        for task in self.sync_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.sync_tasks.values(), return_exceptions=True)
        
        # Disconnect all providers
        for provider in self.providers.values():
            try:
                await provider.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting provider: {e}")
    
    async def register_provider(self, provider: ISyncProvider) -> None:
        """Register a new sync provider"""
        name = provider.name
        
        if name in self.providers:
            logger.warning(f"Provider {name} already registered, replacing")
            # Stop existing provider
            if name in self.sync_tasks:
                self.sync_tasks[name].cancel()
        
        self.providers[name] = provider
        logger.info(f"Registered sync provider: {name}")
        
        # Start if manager is running and provider is enabled
        if self._running and provider.is_enabled:
            try:
                await provider.connect()
                task = asyncio.create_task(
                    self._sync_loop(name, provider)
                )
                self.sync_tasks[name] = task
            except Exception as e:
                logger.error(f"Failed to start provider {name}: {e}")
    
    async def unregister_provider(self, name: str) -> None:
        """Unregister a sync provider"""
        if name not in self.providers:
            logger.warning(f"Provider {name} not found")
            return
        
        # Stop sync task
        if name in self.sync_tasks:
            self.sync_tasks[name].cancel()
            await self.sync_tasks[name]
        
        # Disconnect provider
        provider = self.providers[name]
        await provider.disconnect()
        
        # Remove from registry
        del self.providers[name]
        logger.info(f"Unregistered sync provider: {name}")
    
    async def sync_all(self) -> Dict[str, SyncResult]:
        """Manually trigger sync for all enabled providers"""
        results = {}
        
        tasks = []
        for name, provider in self.providers.items():
            if provider.is_enabled:
                tasks.append(self.sync_provider(name))
        
        if tasks:
            sync_results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, (name, _) in enumerate(
                [(n, p) for n, p in self.providers.items() if p.is_enabled]
            ):
                if isinstance(sync_results[i], Exception):
                    results[name] = SyncResult(
                        status=SyncStatus.FAILED,
                        errors=[str(sync_results[i])]
                    )
                else:
                    results[name] = sync_results[i]
        
        return results
    
    async def sync_provider(self, name: str) -> SyncResult:
        """Manually trigger sync for a specific provider"""
        if name not in self.providers:
            return SyncResult(
                status=SyncStatus.FAILED,
                errors=[f"Provider {name} not found"]
            )
        
        provider = self.providers[name]
        if not provider.is_enabled:
            return SyncResult(
                status=SyncStatus.FAILED,
                errors=[f"Provider {name} is not enabled"]
            )
        
        # Use lock to prevent concurrent syncs
        async with self.sync_locks[name]:
            return await self._perform_sync(name, provider)
    
    async def get_provider_status(self, name: str) -> HealthStatus:
        """Get health status of a specific provider"""
        if name not in self.providers:
            return HealthStatus(
                healthy=False,
                error_message=f"Provider {name} not found"
            )
        
        provider = self.providers[name]
        return await provider.health_check()
    
    async def get_all_statuses(self) -> Dict[str, HealthStatus]:
        """Get health status of all providers"""
        statuses = {}
        
        for name, provider in self.providers.items():
            statuses[name] = await provider.health_check()
        
        return statuses
    
    async def _sync_loop(self, name: str, provider: ISyncProvider) -> None:
        """Background sync loop for a provider"""
        logger.info(f"Starting sync loop for {name}")
        
        while self._running and provider.is_enabled:
            try:
                # Wait for sync interval
                await asyncio.sleep(provider.config.sync_interval)
                
                # Perform sync
                async with self.sync_locks[name]:
                    result = await self._perform_sync(name, provider)
                    
                    if result.status == SyncStatus.FAILED:
                        logger.error(
                            f"Sync failed for {name}: {result.errors}"
                        )
                    else:
                        logger.info(
                            f"Sync completed for {name}: "
                            f"pushed={result.pushed}, pulled={result.pulled}"
                        )
                
            except asyncio.CancelledError:
                logger.info(f"Sync loop cancelled for {name}")
                break
            except Exception as e:
                logger.error(f"Error in sync loop for {name}: {e}")
                # Wait before retrying
                await asyncio.sleep(60)
    
    async def _perform_sync(
        self, 
        name: str, 
        provider: ISyncProvider
    ) -> SyncResult:
        """Perform actual sync operation"""
        start_time = datetime.now()
        result = SyncResult(status=SyncStatus.SUCCESS)
        
        try:
            # Ensure provider is connected
            if not provider.is_connected:
                await provider.connect()
            
            # Get last sync time
            last_sync = self.last_sync.get(name)
            
            # Pull changes from remote
            if provider.config.direction in ["pull", "bidirectional"]:
                remote_memories = await provider.pull_changes(since=last_sync)
                result.pulled = len(remote_memories)
                
                # Process pulled memories
                if remote_memories:
                    await self._process_pulled_memories(
                        provider, 
                        remote_memories
                    )
            
            # Push local changes
            if provider.config.direction in ["push", "bidirectional"]:
                local_memories = await self._get_local_changes(since=last_sync)
                
                if local_memories:
                    push_result = await provider.push_batch(local_memories)
                    result.pushed = push_result.pushed
                    result.errors.extend(push_result.errors)
                    
                    if push_result.status == SyncStatus.FAILED:
                        result.status = SyncStatus.FAILED
                    elif push_result.status == SyncStatus.PARTIAL:
                        result.status = SyncStatus.PARTIAL
            
            # Update last sync time
            self.last_sync[name] = datetime.now()
            
        except Exception as e:
            logger.error(f"Sync error for {name}: {e}")
            result.status = SyncStatus.FAILED
            result.errors.append(str(e))
        
        finally:
            result.duration_ms = (
                datetime.now() - start_time
            ).total_seconds() * 1000
        
        return result
    
    async def _get_local_changes(
        self, 
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get local memories that need to be synced"""
        # This would query the database for memories
        # modified since the last sync
        # For now, return empty list as placeholder
        return []
    
    async def _process_pulled_memories(
        self, 
        provider: ISyncProvider,
        memories: List[Dict[str, Any]]
    ) -> None:
        """Process memories pulled from remote provider"""
        # This would:
        # 1. Check for conflicts with local memories
        # 2. Resolve conflicts using provider's strategy
        # 3. Update local database
        # For now, just log
        logger.info(
            f"Processing {len(memories)} pulled memories from {provider.name}"
        )


# Global sync manager instance
_sync_manager: Optional[SyncManager] = None


async def get_sync_manager() -> SyncManager:
    """Get or create the global sync manager instance"""
    global _sync_manager
    
    if _sync_manager is None:
        _sync_manager = SyncManager()
        
        # Register configured providers
        await _register_configured_providers(_sync_manager)
    
    return _sync_manager


async def _register_configured_providers(manager: SyncManager) -> None:
    """Register providers based on configuration"""
    from app.config import Config
    
    # Check if Cipher is configured
    if Config.CIPHER_ENABLED:
        from app.adapters.cipher_adapter import CipherAdapter, create_cipher_config
        
        cipher_config = create_cipher_config(
            enabled=True,
            cipher_url=Config.CIPHER_URL,
            api_key=Config.CIPHER_API_KEY,
            workspace_id=Config.CIPHER_WORKSPACE_ID,
            sync_interval=Config.CIPHER_SYNC_INTERVAL,
            enable_mcp=Config.CIPHER_ENABLE_MCP
        )
        
        cipher_adapter = CipherAdapter(cipher_config)
        await manager.register_provider(cipher_adapter)
    
    # Future: Register other providers here