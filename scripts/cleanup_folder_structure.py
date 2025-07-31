#!/usr/bin/env python3
"""
Automated folder structure cleanup script for Second Brain project.
Ensures files are in their proper directories.
"""

import os
import shutil
from pathlib import Path
from typing import List, Tuple

# Define file patterns and their destinations
FILE_PATTERNS = {
    # Test files
    'tests/manual/import_tests/': [
        'test_*.py',
        'quick_*.py',
        'final_*.py',
        '*_test.py'
    ],
    # Development scripts
    'scripts/development/': [
        'check_*.py',
        'auto_fix_*.py',
        'fix_*.py'
    ],
    # Documentation
    'docs/project/': [
        'CODE_OF_CONDUCT.md',
        'CONTRIBUTING.md',
        'SECURITY.md'
    ],
    'docs/development/': [
        '*_SETUP.md',
        'QUICK_REFERENCE.md',
        '*_FIXES_SUMMARY.md'
    ],
    'docs/releases/': [
        'RELEASE_NOTES_*.md'
    ]
}

# Files that should stay in root
ROOT_FILES = {
    'README.md',
    'README-ACTUAL-STATE.md',
    'TODO.md',
    'CLAUDE.md',
    'DEVELOPMENT_CONTEXT.md',
    'DEVELOPMENT_ROADMAP.md',
    'IMPLEMENTATION_CHECKLIST.md',
    'NEXT_SESSION_GUIDE.md',
    'FOLDER_STRUCTURE_CLEANUP.md',
    'COMPREHENSIVE_STUB_ANALYSIS.md',
    'COMPREHENSIVE_CODE_REVIEW_RESULTS.md',
    'LICENSE',
    'pyproject.toml',
    'pytest.ini',
    'ruff.toml',
    'docker-compose.yml',
    'Dockerfile',
    'Makefile',
    '.gitignore',
    'alembic.ini',
    'main.py',
    'requirements.txt'
}


def find_misplaced_files() -> List[Tuple[str, str]]:
    """Find files that are in the wrong location."""
    misplaced = []
    
    # Check root directory
    for file in os.listdir('.'):
        if not os.path.isfile(file):
            continue
            
        # Skip if it should be in root
        if file in ROOT_FILES:
            continue
            
        # Check if it matches any pattern
        for dest_dir, patterns in FILE_PATTERNS.items():
            for pattern in patterns:
                if pattern.startswith('*') and pattern.endswith('*'):
                    # Contains pattern
                    if pattern[1:-1] in file:
                        misplaced.append((file, dest_dir))
                        break
                elif pattern.startswith('*'):
                    # Ends with pattern
                    if file.endswith(pattern[1:]):
                        misplaced.append((file, dest_dir))
                        break
                elif pattern.endswith('*'):
                    # Starts with pattern
                    if file.startswith(pattern[:-1]):
                        misplaced.append((file, dest_dir))
                        break
                elif file == pattern:
                    # Exact match
                    misplaced.append((file, dest_dir))
                    break
    
    return misplaced


def cleanup_structure(dry_run: bool = True, pre_commit: bool = False):
    """Clean up the folder structure."""
    misplaced = find_misplaced_files()
    
    if not misplaced:
        if not pre_commit:
            print("✅ All files are in their correct locations!")
        return 0
    
    print(f"Found {len(misplaced)} misplaced files:")
    print()
    
    for file, dest_dir in misplaced:
        print(f"  {file} → {dest_dir}")
    
    if dry_run and not pre_commit:
        print("\nThis is a dry run. Use --execute to actually move files.")
        return 1
    
    if pre_commit:
        print("\n⚠️  Pre-commit hook found misplaced files!")
        print("Please run the following command to fix:")
        print("  python scripts/cleanup_folder_structure.py --execute")
        print("\nThen stage the changes and commit again.")
        return 1
    
    print("\nMoving files...")
    for file, dest_dir in misplaced:
        # Create destination directory if needed
        Path(dest_dir).mkdir(parents=True, exist_ok=True)
        
        # Move the file
        dest_path = os.path.join(dest_dir, file)
        shutil.move(file, dest_path)
        print(f"  ✓ Moved {file} to {dest_path}")
    
    print("\n✅ Cleanup complete!")
    return 0


if __name__ == "__main__":
    import sys
    
    if "--help" in sys.argv:
        print("Usage: python scripts/cleanup_folder_structure.py [--execute] [--pre-commit]")
        print("  --execute: Actually move files (default is dry run)")
        print("  --pre-commit: Run in pre-commit mode (exits with error if files need moving)")
        sys.exit(0)
    
    dry_run = "--execute" not in sys.argv
    pre_commit = "--pre-commit" in sys.argv or os.environ.get("PRE_COMMIT", "0") == "1"
    
    exit_code = cleanup_structure(dry_run, pre_commit)
    sys.exit(exit_code)