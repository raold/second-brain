#!/usr/bin/env python3
"""
Fix all common import issues across the codebase
"""

import os
import re
import subprocess

def add_missing_import(filepath, missing_name, import_line):
    """Add a missing import to a file"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Check if already imported
        if missing_name in content.split('\n')[0:50]:  # Check first 50 lines
            return False
            
        lines = content.split('\n')
        
        # Find where to insert import
        last_import_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                last_import_idx = i
        
        # Insert after last import
        lines.insert(last_import_idx + 1, import_line)
        
        with open(filepath, 'w') as f:
            f.write('\n'.join(lines))
        
        print(f"Fixed {filepath}: Added {missing_name}")
        return True
    except Exception as e:
        print(f"Error fixing {filepath}: {e}")
        return False

def fix_common_imports():
    """Fix common missing imports"""
    fixes = [
        # Common typing imports
        {
            'pattern': r'\bProtocol\b',
            'import': 'from typing import Protocol',
            'name': 'Protocol'
        },
        {
            'pattern': r'\bCallable\b',
            'import': 'from typing import Callable',
            'name': 'Callable'
        },
        {
            'pattern': r'\bTypeVar\b',
            'import': 'from typing import TypeVar',
            'name': 'TypeVar'
        },
        {
            'pattern': r'\bOptional\b',
            'import': 'from typing import Optional',
            'name': 'Optional'
        },
        {
            'pattern': r'\bDict\b',
            'import': 'from typing import Dict',
            'name': 'Dict'
        },
        {
            'pattern': r'\bList\b',
            'import': 'from typing import List',
            'name': 'List'
        },
        {
            'pattern': r'\bAny\b',
            'import': 'from typing import Any',
            'name': 'Any'
        },
        {
            'pattern': r'\bUnion\b',
            'import': 'from typing import Union',
            'name': 'Union'
        },
        {
            'pattern': r'\bTuple\b',
            'import': 'from typing import Tuple',
            'name': 'Tuple'
        },
        # FastAPI imports
        {
            'pattern': r'\bQuery\b',
            'import': 'from fastapi import Query',
            'name': 'Query'
        },
        {
            'pattern': r'\bDepends\b',
            'import': 'from fastapi import Depends',
            'name': 'Depends'
        },
        {
            'pattern': r'\bHTTPException\b',
            'import': 'from fastapi import HTTPException',
            'name': 'HTTPException'
        },
        {
            'pattern': r'\bAPIRouter\b',
            'import': 'from fastapi import APIRouter',
            'name': 'APIRouter'
        },
        # Common standard library
        {
            'pattern': r'\bdatetime\b',
            'import': 'from datetime import datetime',
            'name': 'datetime'
        },
        {
            'pattern': r'\btimedelta\b',
            'import': 'from datetime import timedelta',
            'name': 'timedelta'
        },
        {
            'pattern': r'\bEnum\b',
            'import': 'from enum import Enum',
            'name': 'Enum'
        },
        {
            'pattern': r'\bdataclass\b',
            'import': 'from dataclasses import dataclass',
            'name': 'dataclass'
        },
        {
            'pattern': r'\bCounter\b',
            'import': 'from collections import Counter',
            'name': 'Counter'
        },
        {
            'pattern': r'\bdefaultdict\b',
            'import': 'from collections import defaultdict',
            'name': 'defaultdict'
        },
        # Pydantic
        {
            'pattern': r'\bBaseModel\b',
            'import': 'from pydantic import BaseModel',
            'name': 'BaseModel'
        },
        {
            'pattern': r'\bField\b',
            'import': 'from pydantic import Field',
            'name': 'Field'
        }
    ]
    
    # Find all Python files
    python_files = []
    for root, dirs, files in os.walk('/Users/dro/Documents/second-brain/app'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    print(f"Found {len(python_files)} Python files to check")
    
    # Check each file for missing imports
    fixed_count = 0
    for filepath in python_files:
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            for fix in fixes:
                if re.search(fix['pattern'], content):
                    # Check if import is missing
                    if fix['name'] not in content.split('\n')[0:50]:
                        if add_missing_import(filepath, fix['name'], fix['import']):
                            fixed_count += 1
        except Exception as e:
            print(f"Error checking {filepath}: {e}")
    
    print(f"\nFixed {fixed_count} import issues")

if __name__ == "__main__":
    fix_common_imports()