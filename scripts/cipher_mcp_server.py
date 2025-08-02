#!/usr/bin/env python3
"""
Cipher MCP Server for Warp Terminal
Provides MCP protocol interface for Cipher integration
"""

import json
import sys
import os
import subprocess
import logging
from typing import Dict, Any, Optional

# Setup logging
logging.basicConfig(
    filename=os.path.expanduser("~/.cipher/warp-mcp.log"),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class CipherMCPServer:
    """MCP Server implementation for Cipher"""
    
    def __init__(self):
        self.setup_environment()
        logging.info("Cipher MCP Server started")
        
    def setup_environment(self):
        """Setup environment variables for Cipher"""
        os.environ['CIPHER_CONFIG_PATH'] = os.path.expanduser("~/.cipher/config.yaml")
        os.environ['VECTOR_STORE_PROVIDER'] = 'qdrant'
        os.environ['VECTOR_STORE_URL'] = 'http://localhost:6333'
        os.environ['MCP_TRANSPORT'] = 'stdio'
        
    def send_response(self, request_id: Optional[int], result: Any):
        """Send JSON-RPC response"""
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
        print(json.dumps(response))
        sys.stdout.flush()
        
    def send_error(self, request_id: Optional[int], error_message: str):
        """Send JSON-RPC error"""
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32000,
                "message": error_message
            }
        }
        print(json.dumps(response))
        sys.stdout.flush()
        
    def handle_initialize(self, request_id: int):
        """Handle initialization request"""
        self.send_response(request_id, {
            "capabilities": {
                "tools": {
                    "listChanged": False
                },
                "prompts": {
                    "listChanged": False
                }
            },
            "serverInfo": {
                "name": "cipher-mcp",
                "version": "1.0.0"
            }
        })
        
    def handle_tools_list(self, request_id: int):
        """Return available tools"""
        tools = [
            {
                "name": "search_memory",
                "description": "Search through AI coding memories",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "add_memory",
                "description": "Store a new memory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Memory content"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags for categorization"
                        }
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "analyze_code",
                "description": "Analyze code and extract patterns",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Code to analyze"
                        },
                        "language": {
                            "type": "string",
                            "description": "Programming language",
                            "default": "auto"
                        }
                    },
                    "required": ["code"]
                }
            },
            {
                "name": "get_context",
                "description": "Get current project context",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Project path",
                            "default": "."
                        }
                    }
                }
            }
        ]
        
        self.send_response(request_id, {"tools": tools})
        
    def handle_tool_call(self, request_id: int, params: Dict[str, Any]):
        """Execute a tool call"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        try:
            if tool_name == "search_memory":
                result = self.search_memory(
                    arguments.get("query"),
                    arguments.get("limit", 5)
                )
            elif tool_name == "add_memory":
                result = self.add_memory(
                    arguments.get("content"),
                    arguments.get("tags", [])
                )
            elif tool_name == "analyze_code":
                result = self.analyze_code(
                    arguments.get("code"),
                    arguments.get("language", "auto")
                )
            elif tool_name == "get_context":
                result = self.get_context(
                    arguments.get("path", ".")
                )
            else:
                self.send_error(request_id, f"Unknown tool: {tool_name}")
                return
                
            self.send_response(request_id, {
                "content": [
                    {
                        "type": "text",
                        "text": result
                    }
                ]
            })
            
        except Exception as e:
            logging.error(f"Tool execution error: {e}")
            self.send_error(request_id, str(e))
            
    def search_memory(self, query: str, limit: int) -> str:
        """Search Cipher memories"""
        try:
            cmd = ["cipher", "memory", "search", query, "--limit", str(limit)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return result.stdout if result.returncode == 0 else f"Search failed: {result.stderr}"
        except Exception as e:
            return f"Error searching memories: {e}"
            
    def add_memory(self, content: str, tags: list) -> str:
        """Add a new memory"""
        try:
            cmd = ["cipher", "memory", "add", content]
            if tags:
                cmd.extend(["--tags", ",".join(tags)])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return "Memory added successfully" if result.returncode == 0 else f"Failed: {result.stderr}"
        except Exception as e:
            return f"Error adding memory: {e}"
            
    def analyze_code(self, code: str, language: str) -> str:
        """Analyze code patterns"""
        try:
            # Use echo to pipe code to cipher
            process = subprocess.Popen(
                ["cipher", "analyze", "--language", language],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(input=code, timeout=10)
            return stdout if process.returncode == 0 else f"Analysis failed: {stderr}"
        except Exception as e:
            return f"Error analyzing code: {e}"
            
    def get_context(self, path: str) -> str:
        """Get project context"""
        try:
            cmd = ["cipher", "context", "analyze", path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return result.stdout if result.returncode == 0 else f"Context failed: {result.stderr}"
        except Exception as e:
            return f"Error getting context: {e}"
            
    def handle_prompts_list(self, request_id: int):
        """Return available prompts"""
        prompts = [
            {
                "name": "debug_error",
                "description": "Get debugging help for an error",
                "arguments": [
                    {
                        "name": "error",
                        "description": "Error message or stack trace",
                        "required": True
                    }
                ]
            },
            {
                "name": "explain_code",
                "description": "Explain how code works",
                "arguments": [
                    {
                        "name": "code",
                        "description": "Code to explain",
                        "required": True
                    }
                ]
            },
            {
                "name": "suggest_improvement",
                "description": "Suggest code improvements",
                "arguments": [
                    {
                        "name": "code",
                        "description": "Code to improve",
                        "required": True
                    }
                ]
            }
        ]
        
        self.send_response(request_id, {"prompts": prompts})
        
    def handle_prompt_get(self, request_id: int, params: Dict[str, Any]):
        """Get a specific prompt"""
        prompt_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if prompt_name == "debug_error":
            prompt = f"Help me debug this error:\n\n{arguments.get('error', '')}\n\nUse context from similar past issues."
        elif prompt_name == "explain_code":
            prompt = f"Explain this code:\n\n{arguments.get('code', '')}\n\nInclude relevant patterns from memory."
        elif prompt_name == "suggest_improvement":
            prompt = f"Suggest improvements for:\n\n{arguments.get('code', '')}\n\nBased on best practices in memory."
        else:
            self.send_error(request_id, f"Unknown prompt: {prompt_name}")
            return
            
        self.send_response(request_id, {
            "description": f"Prompt: {prompt_name}",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": prompt
                    }
                }
            ]
        })
        
    def process_request(self, request: Dict[str, Any]):
        """Process incoming JSON-RPC request"""
        method = request.get("method")
        request_id = request.get("id")
        params = request.get("params", {})
        
        logging.info(f"Processing request: {method}")
        
        try:
            if method == "initialize":
                self.handle_initialize(request_id)
            elif method == "initialized":
                # No response needed
                pass
            elif method == "tools/list":
                self.handle_tools_list(request_id)
            elif method == "tools/call":
                self.handle_tool_call(request_id, params)
            elif method == "prompts/list":
                self.handle_prompts_list(request_id)
            elif method == "prompts/get":
                self.handle_prompt_get(request_id, params)
            else:
                self.send_error(request_id, f"Unknown method: {method}")
                
        except Exception as e:
            logging.error(f"Request processing error: {e}")
            self.send_error(request_id, str(e))
            
    def run(self):
        """Main server loop"""
        logging.info("Starting MCP server loop")
        
        for line in sys.stdin:
            try:
                request = json.loads(line.strip())
                self.process_request(request)
            except json.JSONDecodeError as e:
                logging.error(f"Invalid JSON: {e}")
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                
        logging.info("MCP server shutting down")

if __name__ == "__main__":
    server = CipherMCPServer()
    server.run()