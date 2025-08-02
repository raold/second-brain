#!/bin/bash
# Cipher MCP Server wrapper for Warp Terminal
# This script launches Cipher in MCP mode for Warp integration

# Set environment variables
export CIPHER_CONFIG_PATH="$HOME/.cipher/config.yaml"
export OPENAI_API_KEY="${OPENAI_API_KEY}"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}"
export VECTOR_STORE_PROVIDER="qdrant"
export VECTOR_STORE_URL="http://localhost:6333"
export CIPHER_MODE="mcp"
export MCP_TRANSPORT="stdio"

# Log startup
echo "[$(date)] Starting Cipher MCP server for Warp" >> ~/.cipher/warp.log

# Launch Cipher in MCP mode with stdio transport
exec cipher mcp 2>> ~/.cipher/warp-error.log