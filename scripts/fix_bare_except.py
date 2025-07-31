#!/usr/bin/env python3
"""Fix all bare except clauses in the codebase."""

import re
from pathlib import Path


def fix_bare_except(file_path):
    """Fix bare except clauses in a file."""
    with open(file_path) as f:
        content = f.read()

    # Replace bare except Exception: with except Exception:
    # This regex handles both "except Exception:" and "except Exception: # comment"
    modified = re.sub(r'\bexcept\s*:', 'except Exception:', content)

    if modified != content:
        with open(file_path, 'w') as f:
            f.write(modified)
        return True
    return False

def main():
    """Find and fix all Python files with bare except clauses."""
    # Get all Python files
    root = Path('.')
    python_files = list(root.rglob('*.py'))

    fixed_count = 0
    for file_path in python_files:
        # Skip venv and other directories
        if any(part in str(file_path).split('/') for part in ['.venv', 'venv', '__pycache__', '.git']):
            continue

        if fix_bare_except(file_path):
            print(f"Fixed: {file_path}")
            fixed_count += 1

    print(f"\nFixed {fixed_count} files with bare except clauses.")

if __name__ == "__main__":
    main()
