#!/usr/bin/env python3
"""Add common missing imports to files."""

import os
import re
from pathlib import Path

# Common imports that are missing
COMMON_IMPORTS = {
    're': 'import re',
    'time': 'import time',
    'np': 'import numpy as np',
    'nx': 'import networkx as nx',
    'spacy': 'import spacy',
    'field': 'from dataclasses import field',
    'abstractmethod': 'from abc import abstractmethod',
    'ABC': 'from abc import ABC',
    'List': 'from typing import List',
    'Dict': 'from typing import Dict',
    'Optional': 'from typing import Optional',
    'Any': 'from typing import Any',
    'Union': 'from typing import Union',
    'Tuple': 'from typing import Tuple',
    'Set': 'from typing import Set',
}

def add_missing_imports(file_path):
    """Add missing imports to a file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find which imports are needed
    needed_imports = []
    for name, import_stmt in COMMON_IMPORTS.items():
        # Check if the name is used but not imported
        if re.search(rf'\b{name}\b', content) and import_stmt not in content:
            # Special check for 'from typing import' to avoid duplicates
            if 'from typing import' in import_stmt:
                # Check if we already have a typing import
                if 'from typing import' in content:
                    continue
            needed_imports.append(import_stmt)
    
    if not needed_imports:
        return False
    
    # Find where to insert imports (after docstring and existing imports)
    lines = content.split('\n')
    insert_pos = 0
    in_docstring = False
    
    for i, line in enumerate(lines):
        if i == 0 and (line.strip().startswith('"""') or line.strip().startswith("'''")):
            in_docstring = True
        if in_docstring and ('"""' in line or "'''" in line):
            in_docstring = False
            insert_pos = i + 1
            continue
        if not in_docstring and line.strip() and not line.startswith('import') and not line.startswith('from'):
            if insert_pos == 0:
                insert_pos = i
            break
        if line.startswith('import') or line.startswith('from'):
            insert_pos = i + 1
    
    # Insert the imports
    for imp in needed_imports:
        lines.insert(insert_pos, imp)
        insert_pos += 1
    
    # Write back
    with open(file_path, 'w') as f:
        f.write('\n'.join(lines))
    
    return True

def main():
    """Fix common imports in all Python files."""
    root = Path('app')
    fixed_count = 0
    
    for file_path in root.rglob('*.py'):
        if add_missing_imports(file_path):
            print(f"Fixed: {file_path}")
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} files with missing imports.")

if __name__ == "__main__":
    main()