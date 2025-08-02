# Cipher Practical Usage Guide

## 🎯 Quick Start - What You Can Do RIGHT NOW

### 1. Start Interactive Chat (Easiest Way)
```bash
# Open a terminal and start Cipher's interactive mode
cipher cli

# Now you can chat with Cipher and it will remember everything
> Help me implement user authentication
> Show me how I did database migrations before
> What's the best pattern for error handling in Python?
```

### 2. Store Current Work Session
```bash
# After solving a problem or implementing a feature
cipher memory add "Implemented JWT authentication using PyJWT library with refresh tokens. Key pattern: separate access and refresh token endpoints"

# Add with tags for better organization
cipher memory add "Fixed CORS issue in FastAPI by adding middleware" --tags bug,fastapi,cors
```

### 3. Search Your Past Solutions
```bash
# When you encounter a familiar problem
cipher memory search "authentication"
cipher memory search "docker compose postgres"
cipher memory search "pytest fixtures"
```

## 💻 Real-World Usage Scenarios

### Scenario 1: "I Know I've Done This Before"
```bash
# You're setting up PostgreSQL again
cipher memory search "postgres connection"

# Cipher returns your past setups:
# - "Used asyncpg with connection pooling, max_connections=50"
# - "PostgreSQL Docker setup with custom init script"
# - "Fixed connection timeout by adding keepalive settings"
```

### Scenario 2: Debugging Complex Issues
```bash
# You hit an error
echo "TypeError: 'NoneType' object is not subscriptable" | cipher analyze

# Cipher analyzes and suggests based on your past debugging:
# "You encountered this in project X when API returned null
#  Solution: Add null check before accessing dictionary"
```

### Scenario 3: Code Review Patterns
```bash
# Before committing code
cat app/routes/auth.py | cipher analyze --language python

# Cipher identifies patterns and issues:
# - "Missing error handling in login endpoint"
# - "Similar to your user_service.py - consider same structure"
# - "Password should use bcrypt like in previous projects"
```

## 🔧 Warp Terminal Integration

### Configure Warp (If Not Done)
1. Open Warp Settings (Cmd + ,)
2. Go to "AI" → "MCP Servers"
3. Add this configuration:

```json
{
  "cipher-memory": {
    "command": "/usr/bin/python3",
    "args": ["/Users/dro/Library/CloudStorage/GoogleDrive-dro@lynchburgsmiles.com/My Drive/projects/second-brain/scripts/cipher_mcp_server.py"],
    "env": {
      "OPENAI_API_KEY": "your-key-here"
    }
  }
}
```

### Use in Warp
```bash
# Type # to activate Warp AI, then:
#find the docker command I used for Redis
#show me similar error handling patterns
#how did I configure pytest last time
```

## 📝 Daily Workflow Integration

### Morning Routine
```bash
# Start your day by checking context
cipher context show

# See what you were working on
cipher memory list --limit 5 --recent

# Set context for today
cipher context set "Working on API authentication endpoints"
```

### During Development
```bash
# Store important decisions
cipher memory add "Decided to use Redis for session storage instead of JWT"

# Save error solutions
cipher memory add "Fixed circular import by moving models to separate file"

# Document complex commands
cipher memory add "Deploy command: docker-compose -f prod.yml up -d --build"
```

### End of Day
```bash
# Summarize what you learned
cipher memory add "Today: Implemented complete auth flow with 2FA"

# Export memories for backup
cipher memory export --format json > memories-backup.json
```

## 🤖 Automation Scripts

### Auto-capture Git Commits
Create `~/.gitconfig`:
```ini
[alias]
    cipher-commit = !git commit -m \"$1\" && cipher memory add \"Git commit: $1\" && :
```

Usage:
```bash
git cipher-commit "feat: Add user authentication"
```

### Capture Error Solutions
Create `~/bin/debug-with-cipher`:
```bash
#!/bin/bash
ERROR="$1"
SOLUTION="$2"
cipher memory add "Error: $ERROR | Solution: $SOLUTION" --tags debug,solved
```

### Project Context Switcher
Create `~/bin/project-context`:
```bash
#!/bin/bash
PROJECT=$(basename $PWD)
cipher context set "Working on $PROJECT"
cipher memory search $PROJECT --limit 5
```

## 🧠 Advanced Features

### 1. Pattern Analysis
```bash
# Analyze your coding patterns
cipher analyze patterns --language python

# Output:
# Most used: FastAPI (45%), SQLAlchemy (30%), Pytest (25%)
# Common patterns: Repository pattern, Dependency injection
# Frequent issues: Async context managers, Type hints
```

### 2. Team Knowledge Sharing (If Configured)
```bash
# Share a solution with team
cipher memory add "Optimized query by adding index on user_id" --share

# Search team knowledge
cipher memory search "optimization" --team
```

### 3. Context-Aware Suggestions
```bash
# Get suggestions for current directory
cd /path/to/project
cipher suggest

# Output:
# Based on this project structure, consider:
# - Adding pytest.ini (you usually configure pytest)
# - Your typical folder structure has /tests/unit/
# - Missing .env.example (you always create one)
```

## 🎨 VS Code / Cursor Integration

### Quick Setup
1. Install MCP extension from marketplace
2. Open Command Palette (Cmd+Shift+P)
3. Type "MCP: Connect to Server"
4. Select "cipher"

### Usage in VS Code
- **Hover over code**: Get memories about similar patterns
- **Right-click**: "Search Cipher for similar code"
- **Problems panel**: Cipher suggests fixes from past solutions

## 📊 Monitor Your Memory Usage

### Check Statistics
```bash
# See how much you've stored
cipher stats

# Output:
# Total memories: 847
# System 1 (concepts): 612
# System 2 (reasoning): 235
# Most active topics: Python (234), Docker (123), API (98)
# Memory growth: +47 this week
```

### Clean Up Old Memories
```bash
# Remove outdated memories
cipher memory prune --older-than 90d

# Remove by tag
cipher memory delete --tag deprecated
```

## 🚨 Real Examples from Your Project

### Example 1: Remember Complex Configurations
```bash
# After setting up Qdrant
cipher memory add "Qdrant setup: Docker on port 6333, collections: cipher_knowledge, cipher_reflection, 1536 dimensions for OpenAI embeddings"
```

### Example 2: Document Workarounds
```bash
# After fixing an issue
cipher memory add "Fixed 'Module not found' in tests by adding __init__.py to all test directories"
```

### Example 3: Save Useful Commands
```bash
cipher memory add "Clean Python cache: find . -type d -name __pycache__ -exec rm -r {} +"
cipher memory add "Test specific file: pytest tests/unit/test_auth.py -v"
```

## 🔄 Daily Practical Commands

```bash
# Morning
cipher cli  # Start interactive session
> What was I working on yesterday?
> Show me my recent Docker commands

# During coding
cipher memory add "Useful regex for email: ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

# When stuck
cipher memory search "similar error"
cipher memory search "pagination implementation"

# Before closing
cipher context save  # Save current session context
```

## 💡 Pro Tips

1. **Be Specific**: Instead of "fixed bug", write "fixed KeyError in user_routes.py by checking if 'email' exists in request"

2. **Tag Everything**: Use tags like `bug`, `feature`, `config`, `docker`, `sql`

3. **Store Commands**: Every complex command you run, store it

4. **Document Decisions**: "Chose PostgreSQL over MongoDB because of ACID compliance needs"

5. **Error-Solution Pairs**: Always store both the error and how you fixed it

## 🎯 Start Now - Your First 5 Memories

Run these commands right now to get started:

```bash
# 1. Store your project setup
cipher memory add "Second-brain project: FastAPI + PostgreSQL + Redis + Qdrant vector DB"

# 2. Document your development environment
cipher memory add "Dev setup: macOS, Python 3.13.5, Docker Desktop, Warp terminal"

# 3. Save a useful command
cipher memory add "Start all services: docker-compose up -d && cipher api && make dev"

# 4. Document a recent solution
cipher memory add "Used Pydantic v2 BaseModel for API validation with field validators"

# 5. Store a decision
cipher memory add "Using Qdrant over Pinecone for vector storage - self-hosted and free"
```

Now search for them:
```bash
cipher memory search "second-brain"
cipher memory search "docker"
```

## 🔗 Integrate with Your Workflow

### Git Hook for Auto-Memory
Create `.git/hooks/post-commit`:
```bash
#!/bin/bash
MESSAGE=$(git log -1 --pretty=%B)
cipher memory add "Git commit: $MESSAGE" --tags git,commit
```

### Terminal Alias
Add to `~/.zshrc`:
```bash
alias cmem="cipher memory add"
alias csearch="cipher memory search"
alias cchat="cipher cli"
```

Now you can:
```bash
cmem "PostgreSQL connection string format: postgresql://user:pass@localhost/db"
csearch "postgresql"
cchat  # Start chatting
```

## Start Using Cipher NOW!

1. Open a new terminal
2. Run: `cipher cli`
3. Ask: "Help me organize my second-brain project better"
4. Watch as Cipher uses your context to provide personalized help!

Remember: The more you use Cipher, the smarter it gets about YOUR coding patterns!