"""
Cipher Integration Service for Second-Brain
Connects to Cipher's memory layer for enhanced AI context management
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import aiohttp
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CipherMemory(BaseModel):
    """Represents a memory from Cipher"""
    id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    system: int = 1  # System 1 or System 2
    created_at: datetime
    source_ide: Optional[str] = None
    relevance_score: Optional[float] = None


class CipherReasoningChain(BaseModel):
    """Represents a reasoning chain from System 2"""
    id: str
    steps: List[Dict[str, str]]
    decision: str
    confidence: float
    context: Dict[str, Any]
    created_at: datetime


class CipherIntegrationService:
    """Service for integrating with Cipher memory layer"""
    
    def __init__(self, base_url: str = "http://localhost:3000", api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        self._memories_cache = {}
        self._event_stream = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
        
    async def connect(self):
        """Initialize connection to Cipher"""
        if not self.session:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self.session = aiohttp.ClientSession(headers=headers)
            logger.info(f"Connected to Cipher at {self.base_url}")
            
    async def disconnect(self):
        """Close connection to Cipher"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Disconnected from Cipher")
            
    async def search_memories(self, query: str, limit: int = 10, 
                            system: Optional[int] = None) -> List[CipherMemory]:
        """
        Search memories using semantic search
        
        Args:
            query: Search query
            limit: Maximum number of results
            system: Filter by system (1 or 2)
        """
        if not self.session:
            await self.connect()
            
        params = {
            "q": query,
            "limit": limit
        }
        
        if system:
            params["system"] = system
            
        try:
            async with self.session.get(
                f"{self.base_url}/api/memories/search",
                params=params
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                memories = [
                    CipherMemory(**memory) for memory in data.get("memories", [])
                ]
                
                # Cache results
                for memory in memories:
                    self._memories_cache[memory.id] = memory
                    
                return memories
                
        except aiohttp.ClientError as e:
            logger.error(f"Failed to search memories: {e}")
            return []
            
    async def add_memory(self, content: str, metadata: Dict[str, Any], 
                        system: int = 1) -> Optional[CipherMemory]:
        """
        Add a new memory to Cipher
        
        Args:
            content: Memory content
            metadata: Additional metadata
            system: System 1 (concepts) or System 2 (reasoning)
        """
        if not self.session:
            await self.connect()
            
        payload = {
            "content": content,
            "metadata": metadata,
            "system": system,
            "source": "second-brain",
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/memories",
                json=payload
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                memory = CipherMemory(**data)
                self._memories_cache[memory.id] = memory
                
                logger.info(f"Added memory: {memory.id}")
                return memory
                
        except aiohttp.ClientError as e:
            logger.error(f"Failed to add memory: {e}")
            return None
            
    async def get_reasoning_chains(self, context: str) -> List[CipherReasoningChain]:
        """
        Get reasoning chains for a given context
        
        Args:
            context: Context to get reasoning chains for
        """
        if not self.session:
            await self.connect()
            
        try:
            async with self.session.get(
                f"{self.base_url}/api/reasoning/chains",
                params={"context": context}
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                return [
                    CipherReasoningChain(**chain) 
                    for chain in data.get("chains", [])
                ]
                
        except aiohttp.ClientError as e:
            logger.error(f"Failed to get reasoning chains: {e}")
            return []
            
    async def sync_with_second_brain(self, knowledge_graph_data: Dict[str, Any]) -> bool:
        """
        Sync Second-Brain knowledge graph with Cipher
        
        Args:
            knowledge_graph_data: Knowledge graph data to sync
        """
        if not self.session:
            await self.connect()
            
        payload = {
            "source": "second-brain",
            "data": knowledge_graph_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/sync",
                json=payload
            ) as response:
                response.raise_for_status()
                logger.info("Successfully synced with Cipher")
                return True
                
        except aiohttp.ClientError as e:
            logger.error(f"Failed to sync with Cipher: {e}")
            return False
            
    async def get_team_memories(self, team_id: Optional[str] = None) -> List[CipherMemory]:
        """
        Get memories shared by team members
        
        Args:
            team_id: Optional team ID filter
        """
        if not self.session:
            await self.connect()
            
        params = {}
        if team_id:
            params["team_id"] = team_id
            
        try:
            async with self.session.get(
                f"{self.base_url}/api/team/memories",
                params=params
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                return [
                    CipherMemory(**memory) 
                    for memory in data.get("memories", [])
                ]
                
        except aiohttp.ClientError as e:
            logger.error(f"Failed to get team memories: {e}")
            return []
            
    async def get_context_for_ide(self, ide: str) -> Dict[str, Any]:
        """
        Get current context for a specific IDE
        
        Args:
            ide: IDE name (vscode, cursor, claude_desktop)
        """
        if not self.session:
            await self.connect()
            
        try:
            async with self.session.get(
                f"{self.base_url}/api/ide/{ide}/context"
            ) as response:
                response.raise_for_status()
                return await response.json()
                
        except aiohttp.ClientError as e:
            logger.error(f"Failed to get IDE context: {e}")
            return {}
            
    async def subscribe_to_events(self, callback):
        """
        Subscribe to Cipher memory events via SSE
        
        Args:
            callback: Async function to call with event data
        """
        if not self.session:
            await self.connect()
            
        try:
            async with self.session.get(
                f"{self.base_url}/api/events/stream",
                timeout=aiohttp.ClientTimeout(total=None)
            ) as response:
                async for line in response.content:
                    if line.startswith(b"data: "):
                        data = json.loads(line[6:])
                        await callback(data)
                        
        except asyncio.CancelledError:
            logger.info("Event subscription cancelled")
        except Exception as e:
            logger.error(f"Event stream error: {e}")
            
    async def analyze_code_context(self, code: str, language: str = "python") -> Dict[str, Any]:
        """
        Analyze code context and extract relevant memories
        
        Args:
            code: Code to analyze
            language: Programming language
        """
        if not self.session:
            await self.connect()
            
        payload = {
            "code": code,
            "language": language,
            "extract_patterns": True,
            "find_similar": True
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/analyze/code",
                json=payload
            ) as response:
                response.raise_for_status()
                return await response.json()
                
        except aiohttp.ClientError as e:
            logger.error(f"Failed to analyze code: {e}")
            return {}
            
    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about stored memories"""
        if not self.session:
            await self.connect()
            
        try:
            async with self.session.get(
                f"{self.base_url}/api/stats"
            ) as response:
                response.raise_for_status()
                return await response.json()
                
        except aiohttp.ClientError as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
            
    async def export_memories(self, format: str = "json") -> Optional[str]:
        """
        Export all memories
        
        Args:
            format: Export format (json, csv, markdown)
        """
        if not self.session:
            await self.connect()
            
        try:
            async with self.session.get(
                f"{self.base_url}/api/export",
                params={"format": format}
            ) as response:
                response.raise_for_status()
                
                if format == "json":
                    return json.dumps(await response.json(), indent=2)
                else:
                    return await response.text()
                    
        except aiohttp.ClientError as e:
            logger.error(f"Failed to export memories: {e}")
            return None


# Dashboard integration components
class CipherDashboardWidget:
    """Widget for displaying Cipher status in dashboard"""
    
    def __init__(self, cipher_service: CipherIntegrationService):
        self.cipher = cipher_service
        
    async def get_widget_data(self) -> Dict[str, Any]:
        """Get data for dashboard widget"""
        stats = await self.cipher.get_memory_stats()
        
        return {
            "title": "AI Memory Status",
            "system1_count": stats.get("system1_count", 0),
            "system2_count": stats.get("system2_count", 0),
            "active_context": stats.get("active_context", "None"),
            "team_members": stats.get("team_members", 0),
            "last_sync": stats.get("last_sync", "Never"),
            "status": "connected" if self.cipher.session else "disconnected"
        }
        
    async def render_html(self) -> str:
        """Render widget as HTML"""
        data = await self.get_widget_data()
        
        return f"""
        <div class="cipher-widget">
            <h3>🧠 {data['title']}</h3>
            <div class="stats">
                <div>System 1 (Concepts): {data['system1_count']} memories</div>
                <div>System 2 (Reasoning): {data['system2_count']} chains</div>
                <div>Active Context: {data['active_context']}</div>
                <div>Team Members: {data['team_members']}</div>
                <div>Last Sync: {data['last_sync']}</div>
            </div>
            <div class="status {data['status']}">{data['status'].upper()}</div>
        </div>
        """


# Example usage
async def main():
    """Example of using Cipher integration"""
    
    # Initialize service
    async with CipherIntegrationService() as cipher:
        
        # Search for memories
        memories = await cipher.search_memories("authentication patterns")
        for memory in memories:
            print(f"Found: {memory.content[:100]}...")
            
        # Add a memory
        new_memory = await cipher.add_memory(
            content="Implemented JWT authentication with refresh tokens",
            metadata={
                "project": "second-brain",
                "type": "implementation",
                "tags": ["auth", "jwt", "security"]
            }
        )
        
        # Get reasoning chains
        chains = await cipher.get_reasoning_chains("optimize database queries")
        for chain in chains:
            print(f"Reasoning: {chain.decision} (confidence: {chain.confidence})")
            
        # Get team memories
        team_memories = await cipher.get_team_memories()
        print(f"Team has shared {len(team_memories)} memories")
        
        # Subscribe to events
        async def handle_event(event):
            print(f"Event: {event.get('type')} - {event.get('data')}")
            
        # Start event subscription in background
        event_task = asyncio.create_task(
            cipher.subscribe_to_events(handle_event)
        )
        
        # Do other work...
        await asyncio.sleep(5)
        
        # Cancel event subscription
        event_task.cancel()
        
        
if __name__ == "__main__":
    asyncio.run(main())