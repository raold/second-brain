#!/usr/bin/env python3
"""
Directory Cleanup Script
Maintains clean directory structure according to DIRECTORY_STRUCTURE.md
"""

import os
import shutil
from pathlib import Path
import argparse

def cleanup_cache_dirs(dry_run=False):
    """Remove all cache directories"""
    cache_patterns = [
        "__pycache__",
        ".pytest_cache", 
        ".mypy_cache",
        ".ruff_cache",
        ".hypothesis"
    ]
    
    removed = []
    for pattern in cache_patterns:
        for path in Path(".").rglob(pattern):
            if path.is_dir():
                if not dry_run:
                    shutil.rmtree(path)
                removed.append(str(path))
                print(f"{'Would remove' if dry_run else 'Removed'}: {path}")
    
    return removed

def cleanup_temp_files(dry_run=False):
    """Remove temporary and backup files"""
    temp_patterns = [
        "*.tmp",
        "*.bak",
        "*.backup",
        "*.old",
        "*_backup*",
        "*_old*",
        "*.orig",
        "*~",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".DS_Store",
        "Thumbs.db"
    ]
    
    removed = []
    for pattern in temp_patterns:
        for path in Path(".").rglob(pattern):
            if path.is_file():
                if not dry_run:
                    path.unlink()
                removed.append(str(path))
                print(f"{'Would remove' if dry_run else 'Removed'}: {path}")
    
    return removed

def cleanup_empty_dirs(dry_run=False):
    """Remove empty directories"""
    removed = []
    
    # Get all directories, sorted by depth (deepest first)
    all_dirs = sorted(
        [p for p in Path(".").rglob("*") if p.is_dir()],
        key=lambda p: len(p.parts),
        reverse=True
    )
    
    for path in all_dirs:
        # Skip .git and .venv directories
        if ".git" in path.parts or ".venv" in path.parts:
            continue
            
        try:
            if not any(path.iterdir()):
                if not dry_run:
                    path.rmdir()
                removed.append(str(path))
                print(f"{'Would remove' if dry_run else 'Removed'} empty dir: {path}")
        except (OSError, PermissionError):
            pass
    
    return removed

def find_duplicates():
    """Find potential duplicate files"""
    # Common duplicate patterns
    duplicates = []
    
    # Check for multiple LICENSE files
    licenses = list(Path(".").glob("LICENSE*"))
    if len(licenses) > 1:
        duplicates.append(f"Multiple LICENSE files: {licenses}")
    
    # Check for backup files
    for pattern in ["*_backup*", "*_old*", "*.bak"]:
        backups = list(Path(".").rglob(pattern))
        if backups:
            duplicates.append(f"Backup files found: {backups}")
    
    # Check for test files in wrong location
    app_tests = list(Path("app").rglob("test_*.py")) + list(Path("app").rglob("*_test.py"))
    if app_tests:
        duplicates.append(f"Test files in app directory: {app_tests}")
    
    return duplicates

def verify_structure():
    """Verify directory structure matches guidelines"""
    required_dirs = [
        "app",
        "tests",
        "docs", 
        "scripts",
        "static",
        "docker",
        "config"
    ]
    
    missing = []
    for dir_name in required_dirs:
        if not Path(dir_name).exists():
            missing.append(dir_name)
    
    return missing

def main():
    parser = argparse.ArgumentParser(description="Clean up project directory structure")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be removed without removing")
    parser.add_argument("--check", action="store_true", help="Check structure without cleaning")
    args = parser.parse_args()
    
    print("Second Brain Directory Cleanup")
    print("=" * 50)
    
    if args.check:
        # Just check structure
        print("\nChecking directory structure...")
        missing = verify_structure()
        if missing:
            print(f"  WARNING: Missing directories: {', '.join(missing)}")
        else:
            print("  OK: All required directories present")
        
        print("\nChecking for duplicates...")
        duplicates = find_duplicates()
        if duplicates:
            for dup in duplicates:
                print(f"  WARNING: {dup}")
        else:
            print("  OK: No duplicates found")
    else:
        # Perform cleanup
        print(f"\n{'DRY RUN - ' if args.dry_run else ''}Starting cleanup...")
        
        print("\nRemoving cache directories...")
        cache_removed = cleanup_cache_dirs(args.dry_run)
        print(f"   {len(cache_removed)} cache directories {'would be' if args.dry_run else ''} removed")
        
        print("\nRemoving temporary files...")
        temp_removed = cleanup_temp_files(args.dry_run)
        print(f"   {len(temp_removed)} temporary files {'would be' if args.dry_run else ''} removed")
        
        print("\nRemoving empty directories...")
        empty_removed = cleanup_empty_dirs(args.dry_run)
        print(f"   {len(empty_removed)} empty directories {'would be' if args.dry_run else ''} removed")
        
        total = len(cache_removed) + len(temp_removed) + len(empty_removed)
        print(f"\nTotal items {'would be' if args.dry_run else ''} removed: {total}")
        
        if args.dry_run:
            print("\nRun without --dry-run to actually remove files")

if __name__ == "__main__":
    main()