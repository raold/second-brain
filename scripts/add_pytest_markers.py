#!/usr/bin/env python3
"""
Add pytest markers to test files that are missing them.
"""

import os
import sys
from pathlib import Path

def add_pytest_marker_to_file(file_path: Path, marker_type: str):
    """Add pytest marker to a test file if it doesn't already have it."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check if pytestmark already exists
        if f"pytestmark = pytest.mark.{marker_type}" in content:
            print(f"✓ {file_path.name} already has {marker_type} marker")
            return False
        
        # Find the position after imports
        lines = content.split('\n')
        insert_position = 0
        
        # Find where to insert the marker (after imports, before first class/function)
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('import ') or stripped.startswith('from '):
                continue
            elif stripped == '':
                continue
            elif stripped.startswith('#'):
                continue
            elif stripped.startswith('"""') or stripped.startswith("'''"):
                # Skip docstrings
                continue
            else:
                # This is where we want to insert
                insert_position = i
                break
        
        # Find a good insertion point after imports
        for i in range(len(lines)):
            line = lines[i].strip()
            if line.startswith('import pytest'):
                # Insert after pytest import
                insert_position = i + 1
                break
            elif line.startswith('import ') and 'pytest' not in line:
                continue
            elif line.startswith('from ') and 'pytest' not in line:
                continue
            elif line == '':
                continue
        
        # Insert the marker
        marker_line = f"pytestmark = pytest.mark.{marker_type}"
        
        # Make sure we have pytest imported
        if 'import pytest' not in content:
            lines.insert(insert_position, 'import pytest')
            insert_position += 1
        
        # Add a blank line before the marker if needed
        if insert_position < len(lines) and lines[insert_position].strip() != '':
            lines.insert(insert_position, '')
            insert_position += 1
        
        lines.insert(insert_position, marker_line)
        
        # Add a blank line after the marker if needed
        if insert_position + 1 < len(lines) and lines[insert_position + 1].strip() != '':
            lines.insert(insert_position + 1, '')
        
        # Write back the file
        with open(file_path, 'w') as f:
            f.write('\n'.join(lines))
        
        print(f"✓ Added {marker_type} marker to {file_path.name}")
        return True
        
    except Exception as e:
        print(f"✗ Failed to process {file_path.name}: {e}")
        return False

def main():
    """Add pytest markers to test files."""
    project_root = Path(__file__).parent.parent
    tests_dir = project_root / "tests"
    
    # Define marker mappings
    marker_mappings = {
        "unit": ["tests/unit"],
        "integration": ["tests/integration"], 
        "validation": ["tests/validation"],
        "performance": ["tests/performance"],
        "comprehensive": ["tests/comprehensive"]
    }
    
    total_updated = 0
    
    for marker_type, directories in marker_mappings.items():
        for directory in directories:
            test_dir = project_root / directory
            if not test_dir.exists():
                print(f"Directory {test_dir} does not exist, skipping...")
                continue
            
            print(f"\nProcessing {marker_type} tests in {directory}...")
            
            # Find all test files
            test_files = list(test_dir.glob("test_*.py"))
            if not test_files:
                test_files = list(test_dir.rglob("test_*.py"))
            
            for test_file in test_files:
                if add_pytest_marker_to_file(test_file, marker_type):
                    total_updated += 1
    
    print(f"\n✅ Updated {total_updated} test files with pytest markers")

if __name__ == "__main__":
    main()