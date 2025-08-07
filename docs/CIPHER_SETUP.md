# Cipher Installation & Configuration Guide

## Installation Steps

### 1. Prerequisites
```bash
# Ensure Node.js is installed (v18+)
node --version

# Install pnpm if not already installed
npm install -g pnpm
```

### 2. Install Cipher via NPM
```bash
# Global installation for system-wide access
npm install -g @campfire/cipher

# Or use pnpm
pnpm add -g @campfire/cipher
```

### 3. Alternative: Docker Installation
```bash
# Pull the Cipher Docker image
docker pull campfirein/cipher:latest

# Run with persistent storage
docker run -d \
  --name cipher-memory \
  -p 3000:3000 \
  -v ~/cipher-data:/data \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  campfirein/cipher:latest
```

## Configuration

### 1. Create Configuration File
Create `~/.cipher/config.yaml`:

```yaml
# LLM Providers Configuration
llm:
  providers:
    - name: openai
      api_key: ${OPENAI_API_KEY}
      model: gpt-4-turbo-preview
      enabled: true
    
    - name: anthropic
      api_key: ${ANTHROPIC_API_KEY}
      model: claude-3-opus-20240229
      enabled: true
    
    - name: ollama
      base_url: http://localhost:11434
      model: llama3:latest
      enabled: false

# Vector Database Configuration
vector_store:
  provider: qdrant  # or milvus, postgres
  qdrant:
    url: http://localhost:6333
    collection: cipher_memories
  
  # Fallback to SQLite if Qdrant is unavailable
  fallback:
    provider: sqlite
    path: ~/.cipher/memories.db

# Embedding Configuration
embeddings:
  provider: openai  # or sentence-transformers, ollama
  model: text-embedding-3-small
  dimensions: 1536
  batch_size: 100

# Memory Layer Settings
memory:
  system1:
    max_memories: 10000
    retention_days: 90
    auto_summarize: true
  
  system2:
    max_chains: 5000
    chain_depth: 10
    prune_threshold: 0.3

# MCP Server Configuration
mcp:
  mode: aggregator  # or default
  transport: stdio  # or sse, http
  port: 3000
  
  # IDE-specific settings
  ides:
    vscode:
      enabled: true
      workspace_trust: true
    
    cursor:
      enabled: true
      auto_sync: true
    
    claude_desktop:
      enabled: true
      context_window: 200000

# Team Collaboration
collaboration:
  enabled: true
  sync_interval: 300  # seconds
  share_with_team: true
  team_id: ${TEAM_ID}

# Logging
logging:
  level: info
  file: ~/.cipher/cipher.log
  rotate: daily
```

### 2. Set Environment Variables
Add to `~/.zshrc` or `~/.bash_profile`:

```bash
# Cipher Environment Variables
export CIPHER_CONFIG_PATH="$HOME/.cipher/config.yaml"
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export CIPHER_TEAM_ID="your-team-id"

# Optional: Qdrant configuration
export QDRANT_URL="http://localhost:6333"
export QDRANT_API_KEY="your-qdrant-key"
```

## IDE Integration

### VS Code
1. Install MCP extension from marketplace
2. Add to `settings.json`:
```json
{
  "mcp.server.path": "cipher",
  "mcp.server.args": ["--mode", "aggregator"],
  "mcp.autoStart": true
}
```

### Cursor
1. Open Cursor Settings
2. Navigate to "AI" → "Model Context Protocol"
3. Add Cipher server:
```json
{
  "mcp_servers": {
    "cipher": {
      "command": "cipher",
      "args": ["serve", "--mode", "aggregator"]
    }
  }
}
```

### Claude Desktop
1. Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "cipher": {
      "command": "cipher",
      "args": ["serve", "--transport", "stdio"],
      "env": {
        "CIPHER_CONFIG_PATH": "~/.cipher/config.yaml"
      }
    }
  }
}
```

## Quick Start Commands

```bash
# Start Cipher server
cipher serve

# Interactive mode
cipher chat

# Check configuration
cipher config validate

# View stored memories
cipher memory list

# Search memories
cipher memory search "authentication patterns"

# Sync with team
cipher sync

# Export memories
cipher export --format json > memories.json
```

## Testing Installation

```bash
# Test basic functionality
cipher --version
cipher config test

# Test LLM connections
cipher test llm --provider openai
cipher test llm --provider anthropic

# Test vector store
cipher test vector --provider qdrant

# Test MCP server
cipher serve --test
```

## Troubleshooting

### Common Issues

1. **Port conflicts**: Change MCP port in config.yaml
2. **API key errors**: Verify environment variables are set
3. **Vector DB connection**: Ensure Qdrant/Milvus is running
4. **IDE not connecting**: Restart IDE after configuration

### Debug Mode
```bash
# Run with debug logging
CIPHER_LOG_LEVEL=debug cipher serve
```

## Integration with Second-Brain

### 1. Shared Memory Pool
Configure both systems to use the same vector database:
```yaml
# In second-brain config
vector_db:
  provider: qdrant
  url: http://localhost:6333
  collection: shared_memories
```

### 2. API Integration
```python
# In second-brain code
import requests

class CipherMemoryClient:
    def __init__(self, base_url="http://localhost:3000"):
        self.base_url = base_url
    
    def get_memories(self, query):
        return requests.get(f"{self.base_url}/api/memories/search", 
                           params={"q": query})
    
    def add_memory(self, content, metadata):
        return requests.post(f"{self.base_url}/api/memories",
                            json={"content": content, "metadata": metadata})
```

### 3. Event Stream Integration
```javascript
// Subscribe to Cipher memory updates
const eventSource = new EventSource('http://localhost:3000/api/events');
eventSource.onmessage = (event) => {
    const memory = JSON.parse(event.data);
    updateDashboard(memory);
};
```

## Next Steps

1. Start Cipher server: `cipher serve`
2. Open your IDE (VS Code, Cursor, or Claude Desktop)
3. Start coding - memories will be automatically captured
4. Access dashboard at http://localhost:3000/dashboard
5. Monitor memories via CLI: `cipher memory watch`