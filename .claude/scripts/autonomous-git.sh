#!/bin/bash
# Autonomous Git Operations Helper
# This script handles git operations without any prompts

# Function to auto-commit with smart message generation
auto_commit() {
    # Check if there are changes
    if [[ -z $(git status -s) ]]; then
        return 0
    fi
    
    # Stage all changes
    git add -A
    
    # Generate commit message based on changes
    CHANGES=$(git diff --cached --name-status | head -5)
    FILE_COUNT=$(git diff --cached --name-only | wc -l | tr -d ' ')
    
    if [[ $FILE_COUNT -eq 1 ]]; then
        FILE=$(git diff --cached --name-only)
        ACTION=$(git diff --cached --name-status | cut -f1)
        case $ACTION in
            A) MSG="Add $FILE" ;;
            M) MSG="Update $FILE" ;;
            D) MSG="Remove $FILE" ;;
            *) MSG="Modify $FILE" ;;
        esac
    else
        MSG="Update $FILE_COUNT files"
    fi
    
    # Commit without any prompts
    git commit -m "$MSG" --no-verify --quiet
    echo "✓ Auto-committed: $MSG"
}

# Function to auto-push without prompts
auto_push() {
    BRANCH=$(git branch --show-current)
    git push origin $BRANCH --quiet 2>/dev/null || git push -u origin $BRANCH --quiet
    echo "✓ Auto-pushed to origin/$BRANCH"
}

# Export functions for use in Claude
export -f auto_commit
export -f auto_push

# If called directly, run both
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    auto_commit
    auto_push
fi