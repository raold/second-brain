# Warp Terminal + Cipher MCP Integration

## Configuration for Warp MCP Servers

Copy and paste this JSON configuration into Warp's MCP server settings:

### Option 1: Direct Cipher Command
```json
{
  "cipher": {
    "command": "cipher",
    "args": ["mcp"],
    "env": {
      "CIPHER_CONFIG_PATH": "~/.cipher/config.yaml",
      "OPENAI_API_KEY": "YOUR_OPENAI_KEY",
      "VECTOR_STORE_PROVIDER": "qdrant",
      "VECTOR_STORE_URL": "http://localhost:6333",
      "MCP_TRANSPORT": "stdio"
    },
    "working_directory": null
  }
}
```

### Option 2: Using Wrapper Script (Recommended)
```json
{
  "cipher-memory": {
    "command": "/Users/dro/Library/CloudStorage/GoogleDrive-dro@lynchburgsmiles.com/My Drive/projects/second-brain/scripts/cipher-mcp-warp.sh",
    "args": [],
    "env": {
      "OPENAI_API_KEY": "YOUR_OPENAI_KEY"
    },
    "working_directory": "/Users/dro/Library/CloudStorage/GoogleDrive-dro@lynchburgsmiles.com/My Drive/projects/second-brain"
  }
}
```

### Option 3: Full-Featured Configuration
```json
{
  "cipher-ai-memory": {
    "command": "/opt/homebrew/bin/cipher",
    "args": ["mcp", "--transport", "stdio"],
    "env": {
      "CIPHER_CONFIG_PATH": "/Users/dro/.cipher/config.yaml",
      "OPENAI_API_KEY": "YOUR_OPENAI_KEY",
      "VECTOR_STORE_PROVIDER": "qdrant",
      "VECTOR_STORE_URL": "http://localhost:6333",
      "CIPHER_LOG_LEVEL": "info",
      "CIPHER_MEMORY_MODE": "dual",
      "MCP_AGGREGATOR_MODE": "true"
    },
    "working_directory": null
  }
}
```

## Setup Instructions

1. **Open Warp Preferences**
   - Press `Cmd + ,` or go to Settings
   - Navigate to "AI" or "MCP Servers" section

2. **Add Cipher MCP Server**
   - Click the "+" button
   - Replace the default JSON with one of the options above
   - Update `YOUR_OPENAI_KEY` with your actual API key

3. **Save and Restart Warp**
   - Save the configuration
   - Restart Warp for changes to take effect

4. **Verify Integration**
   - In Warp, try semantic commands like:
     - "Show me recent authentication patterns"
     - "What was the last database query I wrote?"
     - "Find similar code to this function"

## Warp-Specific Features with Cipher

### 1. Semantic Command Enhancement
Cipher will enhance Warp's semantic understanding with:
- **Context Memory**: Remember previous commands and their outputs
- **Pattern Recognition**: Identify coding patterns from your history
- **Smart Suggestions**: Provide contextual command suggestions

### 2. Terminal Workflows
```bash
# Example workflow commands that leverage Cipher

# Search memories from terminal
cipher memory search "docker compose"

# Add a memory about current task
cipher memory add "Configured PostgreSQL with custom settings"

# Get context for current directory
cipher context analyze .

# Find similar past solutions
cipher similar "authentication middleware"
```

### 3. Warp AI + Cipher Integration
When using Warp AI features, Cipher provides:
- Historical context from past terminal sessions
- Code patterns from your repositories
- Team knowledge if collaboration is enabled
- Reasoning chains for complex debugging

### 4. Custom Warp Workflows
Create custom workflows that combine Warp and Cipher:

```bash
# Create a Warp workflow file: ~/.warp/workflows/cipher.yaml
workflows:
  - name: "Remember This"
    description: "Store current context in Cipher"
    command: |
      cipher memory add "$(pwd): $1"
    
  - name: "Find Similar"
    description: "Find similar past solutions"
    command: |
      cipher memory search "$1" --limit 5
    
  - name: "Debug With Context"
    description: "Get debugging help with full context"
    command: |
      cipher analyze --error "$1" --context "$(history -10)"
```

## Troubleshooting

### MCP Server Not Connecting
1. Check Cipher is installed: `which cipher`
2. Verify MCP mode works: `cipher mcp --test`
3. Check logs: `tail -f ~/.cipher/warp-error.log`

### No Responses from Cipher
1. Ensure Qdrant is running: `docker ps | grep qdrant`
2. Check API key is set correctly
3. Test direct command: `cipher cli`

### Performance Issues
1. Reduce memory limits in config.yaml
2. Use SQLite instead of Qdrant for faster local access
3. Disable reflection memories if not needed

## Advanced Integration

### Terminal Context Capture
Cipher automatically captures:
- Command history and outputs
- Error messages and stack traces
- File modifications and git operations
- Environment variables and configurations

### Semantic Search in Terminal
```bash
# Use Warp's AI with Cipher context
# Type '#' in Warp to activate AI, then:
"#find the command I used to setup docker last week"
"#show me similar database migration patterns"
"#what was that regex I used for email validation?"
```

### Team Collaboration
If team features are enabled:
- Share terminal workflows with team
- Access team member's command patterns
- Collaborative debugging with shared context

## Benefits of Warp + Cipher

1. **Persistent Memory**: Never lose track of complex commands
2. **Context-Aware AI**: Warp AI enhanced with your coding history
3. **Smart Autocomplete**: Predictions based on your patterns
4. **Cross-Project Knowledge**: Apply learnings across repositories
5. **Team Knowledge Sharing**: Learn from team's terminal usage

## Next Steps

1. Configure Cipher in Warp preferences
2. Test with semantic commands
3. Create custom workflows
4. Enable team features if desired
5. Monitor memory growth in Qdrant dashboard