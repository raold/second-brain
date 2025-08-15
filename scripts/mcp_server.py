#!/usr/bin/env python3
"""
MCP Server for Second Brain
Provides Model Context Protocol interface for IDE integration
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import httpx

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class SecondBrainMCP:
    """
    MCP Server that connects IDEs to Second Brain
    """
    
    def __init__(self):
        self.base_url = os.getenv("SECOND_BRAIN_URL", "http://localhost:8001")
        self.api_key = os.getenv("API_KEY", "")
        self.client = None
        
    async def connect(self):
        """Connect to Second Brain API"""
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
            
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=30.0
        )
        
    async def store_context(self, content: str, context_type: str = "code"):
        """Store context in Second Brain"""
        if not self.client:
            await self.connect()
            
        memory = {
            "content": content,
            "type": context_type,
            "tags": ["mcp", "ide-context"],
            "metadata": {
                "source": "mcp-server",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        response = await self.client.post("/api/v2/memories", json=memory)
        return response.json()
    
    async def retrieve_context(self, query: str):
        """Retrieve relevant context from Second Brain"""
        if not self.client:
            await self.connect()
            
        response = await self.client.post(
            "/api/v2/search",
            json={"query": query, "limit": 10}
        )
        return response.json()
    
    async def handle_mcp_request(self, request):
        """Handle MCP protocol requests"""
        method = request.get("method")
        params = request.get("params", {})
        
        if method == "store":
            return await self.store_context(
                params.get("content"),
                params.get("type", "code")
            )
        elif method == "retrieve":
            return await self.retrieve_context(params.get("query"))
        elif method == "health":
            return {"status": "healthy", "service": "second-brain-mcp"}
        else:
            return {"error": f"Unknown method: {method}"}
    
    async def run_server(self):
        """Run the MCP server"""
        print(f"🚀 Second Brain MCP Server starting...")
        print(f"   Connecting to: {self.base_url}")
        
        await self.connect()
        print("✅ Connected to Second Brain")
        
        # Simple stdin/stdout protocol for MCP
        while True:
            try:
                # Read request from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                
                if not line:
                    break
                    
                request = json.loads(line)
                response = await self.handle_mcp_request(request)
                
                # Write response to stdout
                print(json.dumps(response))
                sys.stdout.flush()
                
            except json.JSONDecodeError:
                print(json.dumps({"error": "Invalid JSON"}))
                sys.stdout.flush()
            except Exception as e:
                print(json.dumps({"error": str(e)}))
                sys.stdout.flush()

if __name__ == "__main__":
    server = SecondBrainMCP()
    asyncio.run(server.run_server())