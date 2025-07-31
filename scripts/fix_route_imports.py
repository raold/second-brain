#!/usr/bin/env python3
"""
Fix missing imports in route files
"""

import os
import re

# Common imports needed for route files
COMMON_IMPORTS = """from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
"""

def fix_route_file(filepath):
    """Fix imports in a single route file"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check if APIRouter is used but not imported
    if 'APIRouter' in content and 'from fastapi import' not in content:
        print(f"Fixing {filepath}")
        
        # Find the first import or start of file
        lines = content.split('\n')
        insert_pos = 0
        
        # Find position after docstring
        in_docstring = False
        for i, line in enumerate(lines):
            if '"""' in line:
                in_docstring = not in_docstring
                if not in_docstring:
                    insert_pos = i + 1
                    break
        
        # Insert common imports
        lines.insert(insert_pos, '')
        lines.insert(insert_pos + 1, COMMON_IMPORTS)
        
        # Write back
        with open(filepath, 'w') as f:
            f.write('\n'.join(lines))
        
        print(f"Fixed {filepath}")
        return True
    return False

def main():
    routes_dir = "/Users/dro/Documents/second-brain/app/routes"
    fixed_count = 0
    
    for filename in os.listdir(routes_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            filepath = os.path.join(routes_dir, filename)
            if fix_route_file(filepath):
                fixed_count += 1
    
    print(f"\nFixed {fixed_count} files")

if __name__ == "__main__":
    main()