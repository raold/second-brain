#!/usr/bin/env python3
"""
Script to remove mock database dependencies from the Second Brain codebase.
This will update all files to use the real PostgreSQL database.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

# Files to completely remove
FILES_TO_REMOVE = [
    "app/database_mock.py",
    "tests/unit/test_database_mock.py",
]

# Patterns to search and replace
REPLACEMENTS = [
    # Remove     (
        r'use_mock\s*=\s*os\.getenv\("        'use_mock = False  # Mock database removed - always use real database'
    ),
    (
        r'if\s+use_mock:\s*\n\s*logger\.info\("Using mock database[^"]*"\)\s*\n\s*#.*\n\s*from app\.database_mock import MockDatabase\s*\n\s*\n\s*db = MockDatabase\(\)\s*\n\s*await db\.initialize\(\)\s*\n\s*logger\.info\("Mock database initialized"\)\s*\n\s*else:',
        '# Mock database removed - always use real database'
    ),
    (
        r'if\s+use_mock:\s*\n\s*logger\.info\("Mock database cleanup[^"]*"\)\s*\n\s*else:',
        '# Mock database removed - always cleanup real database'
    ),
    # Remove imports
    (r'from app\.database_mock import.*\n', ''),
    (r'import app\.database_mock.*\n', ''),
    # Remove environment variable settings
    (r'os\.environ\["    (r'    (r'    # Update environment variable documentation
    (r']

# Files to update specifically
SPECIFIC_FILE_UPDATES = {
    ".env.development": [
        (r'    ],
    ".env.example": [
        (r'    ],
    "pytest.ini": [
        (r'    ],
    ".github/workflows/ci.yml": [
        (r"        (r'echo "    ],
}


def remove_files(files: List[str]) -> List[str]:
    """Remove specified files."""
    removed = []
    for file_path in files:
        if os.path.exists(file_path):
            os.remove(file_path)
            removed.append(file_path)
            print(f"✅ Removed: {file_path}")
        else:
            print(f"⚠️  File not found: {file_path}")
    return removed


def update_file(file_path: str, replacements: List[Tuple[str, str]]) -> bool:
    """Update a file with the given replacements."""
    if not os.path.exists(file_path):
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def find_and_update_files(root_dir: str, extensions: List[str], replacements: List[Tuple[str, str]]) -> List[str]:
    """Find and update all files with given extensions."""
    updated_files = []
    root_path = Path(root_dir)
    
    for ext in extensions:
        for file_path in root_path.rglob(f"*{ext}"):
            # Skip hidden directories and test files for now
            if any(part.startswith('.') for part in file_path.parts):
                continue
            if 'node_modules' in file_path.parts or 'venv' in file_path.parts:
                continue
                
            if update_file(str(file_path), replacements):
                updated_files.append(str(file_path))
                print(f"✅ Updated: {file_path}")
    
    return updated_files


def update_app_py():
    """Special handling for app.py to remove mock database logic."""
    app_py_path = "app/app.py"
    
    with open(app_py_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    skip_until_else = False
    in_mock_block = False
    
    for i, line in enumerate(lines):
        # Skip mock database initialization block
        if "use_mock = os.getenv" in line and "            new_lines.append("    # Mock database removed - always use real database\n")
            continue
            
        if "if use_mock:" in line:
            skip_until_else = True
            in_mock_block = True
            continue
            
        if skip_until_else and line.strip() == "else:":
            skip_until_else = False
            in_mock_block = False
            continue
            
        if skip_until_else:
            continue
            
        # Remove mock database import
        if "            continue
            
        new_lines.append(line)
    
    with open(app_py_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"✅ Special update completed: {app_py_path}")


def main():
    """Main function to remove mock database dependencies."""
    print("🔧 Removing mock database dependencies from Second Brain...")
    print("=" * 60)
    
    # Change to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    # 1. Remove mock database files
    print("\n1. Removing mock database files...")
    removed_files = remove_files(FILES_TO_REMOVE)
    print(f"   Removed {len(removed_files)} files")
    
    # 2. Update Python files
    print("\n2. Updating Python files...")
    updated_py_files = find_and_update_files(".", [".py"], REPLACEMENTS)
    print(f"   Updated {len(updated_py_files)} Python files")
    
    # 3. Update configuration files
    print("\n3. Updating configuration files...")
    config_updates = 0
    for file_path, replacements in SPECIFIC_FILE_UPDATES.items():
        if update_file(file_path, replacements):
            config_updates += 1
            print(f"✅ Updated: {file_path}")
    print(f"   Updated {config_updates} configuration files")
    
    # 4. Special handling for app.py
    print("\n4. Special handling for app.py...")
    update_app_py()
    
    # 5. Update test files to use real test database
    print("\n5. Updating test files...")
    test_replacements = [
        (r'mock_db = MockDatabase\(\)', 'db = await get_database()  # Use real test database'),
        (r'from app\.database_mock import.*\n', 'from app.database import get_database\n'),
    ]
    updated_test_files = find_and_update_files("tests", [".py"], test_replacements)
    print(f"   Updated {len(updated_test_files)} test files")
    
    print("\n" + "=" * 60)
    print("✅ Mock database removal complete!")
    print("\n⚠️  Next steps:")
    print("1. Review the changes carefully")
    print("2. Ensure PostgreSQL is running for development")
    print("3. Update test database configuration")
    print("4. Run tests to verify everything works")
    print("5. Commit the changes")


if __name__ == "__main__":
    main()