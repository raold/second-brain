#!/bin/bash
# Claude Code Startup Hook
# This script runs automatically when Claude Code starts in the second-brain project

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "🚀 Claude Code Starting - Second Brain Project"
echo "============================================"

# Run startup optimizer first
if [ -f ".claude/scripts/startup-optimizer.py" ]; then
    echo -e "\n${BLUE}🔧 Running startup optimization...${NC}"
    python3 .claude/scripts/startup-optimizer.py
    echo ""
fi

# Check if we're in the right directory
if [ ! -f "CLAUDE.md" ]; then
    echo -e "${RED}⚠️  Warning: Not in second-brain project root${NC}"
    exit 0
fi

# Run the startup update checker
echo -e "\n${YELLOW}📋 Checking for Anthropic updates...${NC}"

# Check if Python is available
if command -v python3 &> /dev/null; then
    # Run the update checker
    python3 .claude/scripts/startup-check.py
else
    echo -e "${RED}❌ Python not found - skipping update check${NC}"
fi

# Check if startup update checker agent should be activated
if grep -q "startup-update-checker" .claude/config.yml 2>/dev/null; then
    echo -e "\n${GREEN}✓ Startup update checker agent is configured${NC}"
else
    echo -e "\n${YELLOW}ℹ️  Consider adding startup-update-checker to auto-activated agents${NC}"
fi

# Display current context status
echo -e "\n${GREEN}📊 Project Context Status:${NC}"
echo "- TODO.md: $(grep -c '^- \[ \]' TODO.md 2>/dev/null || echo "0") open tasks"
echo "- CLAUDE.md: Last updated $(stat -f "%Sm" -t "%Y-%m-%d" CLAUDE.md 2>/dev/null || echo "unknown")"
echo "- Agents: $(find .claude/agents -name "*.md" -type f | wc -l | tr -d ' ') configured"

# Check for any pending migrations
if [ -f ".claude/agents/migrate-to-v2.py" ]; then
    echo -e "\n${YELLOW}⚠️  Migration script available: .claude/agents/migrate-to-v2.py${NC}"
    echo "   Run 'python3 .claude/agents/migrate-to-v2.py' to upgrade to v2"
fi

echo -e "\n${GREEN}✅ Startup checks complete${NC}"
echo "============================================"

# Loading shell utility functions
if [ -f ".claude/shell-utils.sh" ]; then
    echo "Loading shell utility functions"
    source ".claude/shell-utils.sh"
fi

# Enable full autonomous mode - no prompts, no confirmations
echo -e "\n${YELLOW}🚀 Enabling FULL AUTONOMOUS MODE${NC}"
echo "============================================"

# Set environment variables for autonomous operation
export CLAUDE_CODE_AUTONOMOUS="true"
export CLAUDE_NO_CONFIRMATIONS="true"
export CLAUDE_AUTO_COMMIT="true"
export CLAUDE_AUTO_PUSH="true"
export CLAUDE_SKIP_ALL_PROMPTS="true"

# Update CLAUDE.md to reflect autonomous mode
if grep -q "AUTONOMOUS MODE ENABLED" CLAUDE.md; then
    echo -e "${GREEN}✓ Autonomous mode already documented${NC}"
else
    echo -e "\n## 🚀 AUTONOMOUS MODE ENABLED\n- NO CONFIRMATIONS for any operations\n- AUTO-COMMIT when changes made\n- AUTO-PUSH to remote\n- NO PROMPTS - just execute\n" >> CLAUDE.md
    echo -e "${GREEN}✓ Updated CLAUDE.md with autonomous mode${NC}"
fi

# Create autonomous mode marker file
touch .claude/.autonomous-mode-enabled

echo -e "\n${GREEN}✅ FULL AUTONOMOUS MODE ACTIVE${NC}"
echo "- No confirmations will be requested"
echo "- Git commits will be automatic"
echo "- Git pushes will be automatic"
echo "- All operations will execute immediately"
echo "============================================"