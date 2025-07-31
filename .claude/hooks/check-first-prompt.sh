#!/bin/bash
# Claude Code First Prompt Hook
# This script runs on the first user prompt to trigger startup behaviors

# Check if this is the first prompt of the session
SESSION_FILE="/tmp/claude-session-$(basename "$CLAUDE_PROJECT_DIR")"

if [ ! -f "$SESSION_FILE" ]; then
    # Mark this session as started
    touch "$SESSION_FILE"
    
    # Run the startup script
    if [ -f "$CLAUDE_PROJECT_DIR/.claude/hooks/on-startup.sh" ]; then
        "$CLAUDE_PROJECT_DIR/.claude/hooks/on-startup.sh"
    fi
fi