#!/usr/bin/env python3
"""
Setup Cipher MCP Integration for Second Brain
This creates a lightweight integration that preserves context locally
"""

import json
import os
import sys
import io
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def setup_cipher_mcp():
    """
    Setup MCP configuration for IDE integration with Second Brain
    Since standard Cipher might have issues, we'll use Second Brain directly
    """
    
    print("\n🔧 Setting up Cipher/MCP Integration for Second Brain\n")
    print("=" * 60)
    
    # Create MCP config directory if needed
    mcp_config_dir = Path.home() / ".config" / "mcp"
    mcp_config_dir.mkdir(parents=True, exist_ok=True)
    
    # MCP Server configuration for IDEs (VS Code, Cursor, etc.)
    mcp_config = {
        "mcpServers": {
            "second-brain": {
                "description": "Second Brain memory persistence",
                "command": "python",
                "args": [
                    str(Path(__file__).parent / "mcp_server.py")
                ],
                "env": {
                    "SECOND_BRAIN_URL": "http://localhost:8001",
                    "API_KEY": os.getenv("API_KEY", ""),
                }
            }
        }
    }
    
    # Save MCP config
    config_file = mcp_config_dir / "servers.json"
    with open(config_file, 'w') as f:
        json.dump(mcp_config, f, indent=2)
    
    print(f"✅ Created MCP config at: {config_file}")
    
    # Create VS Code settings
    vscode_settings = {
        "cipher.enabled": True,
        "cipher.serverUrl": "http://localhost:8001",
        "cipher.syncInterval": 300,
        "mcp.servers": {
            "second-brain": {
                "enabled": True,
                "url": "http://localhost:8001"
            }
        }
    }
    
    # Save VS Code workspace settings
    workspace_dir = Path.cwd() / ".vscode"
    workspace_dir.mkdir(exist_ok=True)
    
    settings_file = workspace_dir / "settings.json"
    existing_settings = {}
    
    if settings_file.exists():
        with open(settings_file, 'r') as f:
            existing_settings = json.load(f)
    
    existing_settings.update(vscode_settings)
    
    with open(settings_file, 'w') as f:
        json.dump(existing_settings, f, indent=2)
    
    print(f"✅ Created VS Code settings at: {settings_file}")
    
    # Instructions for different IDEs
    print("\n📝 IDE Configuration Instructions:\n")
    
    print("For VS Code/Cursor:")
    print("  1. Install MCP extension (if available)")
    print("  2. Settings already configured in .vscode/settings.json")
    print("  3. Restart VS Code/Cursor")
    
    print("\nFor Claude Desktop:")
    print("  1. Open Claude Desktop settings")
    print("  2. Add MCP server configuration:")
    print(f"     - Server URL: http://localhost:8001")
    print(f"     - Config path: {config_file}")
    
    print("\nFor other IDEs:")
    print("  1. Point to Second Brain API: http://localhost:8001")
    print("  2. Use API key from .env file")
    print("  3. Enable auto-sync if available")
    
    print("\n✅ Setup Complete!")
    print("\nNext steps:")
    print("1. Start Second Brain: make dev")
    print("2. Open your IDE and verify MCP connection")
    print("3. Your memories will now persist across sessions!")
    
    return True

if __name__ == "__main__":
    setup_cipher_mcp()