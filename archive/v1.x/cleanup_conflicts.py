#!/usr/bin/env python3
"""Clean up merge conflicts in all Python files."""

import os
import re

def clean_merge_conflicts(filepath):
    """Remove merge conflict markers from a file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Count conflicts
        conflicts = content.count('<<<<<<< HEAD')
        if conflicts == 0:
            return 0
        
        # Pattern to match merge conflicts
        # This will keep the content from the remote branch (after =======)
        pattern = r'<<<<<<< HEAD.*?=======(.*?)>>>>>>> [a-f0-9]+'
        
        # Replace conflicts with remote version
        cleaned = re.sub(pattern, r'\1', content, flags=re.DOTALL)
        
        # Write back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(cleaned)
        
        print(f"Cleaned {conflicts} conflicts in {filepath}")
        return conflicts
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return 0

def main():
    """Clean all Python files."""
    total_conflicts = 0
    
    # Find all Python files
    for root, dirs, files in os.walk('.'):
        # Skip hidden directories and virtual environments
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['venv', '__pycache__']]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                total_conflicts += clean_merge_conflicts(filepath)
    
    print(f"\nTotal conflicts cleaned: {total_conflicts}")

if __name__ == "__main__":
    main() 