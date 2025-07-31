#!/usr/bin/env python3
"""
Find and restore all missing dependencies by parsing import errors
"""
import os
import re
import shutil
import subprocess
from pathlib import Path


def run_pytest_and_get_error():
    """Run pytest and capture import errors"""
    cmd = [
        r"C:\Users\dro\second-brain\.venv\Scripts\python.exe",
        "-m", "pytest",
        "tests/unit/test_advanced_synthesis.py",
        "-v", "--tb=short", "-x"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stderr

def extract_missing_module(error_text):
    """Extract missing module name from error text"""
    # Pattern for: ModuleNotFoundError: No module named 'app.something'
    pattern = r"ModuleNotFoundError: No module named '(app\.[^']+)'"
    match = re.search(pattern, error_text)
    if match:
        return match.group(1)

    # Pattern for: ImportError: cannot import name 'something' from 'app.module'
    pattern = r"ImportError: cannot import name '[^']+' from '(app\.[^']+)'"
    match = re.search(pattern, error_text)
    if match:
        return match.group(1)

    return None

def find_file_in_archive(module_path):
    """Find file in archive based on module path"""
    # Convert module path to file path
    file_path = module_path.replace(".", "/") + ".py"
    file_path = file_path.replace("app/", "")

    archive_dir = Path("archive/pre-v3")

    # Search for the file
    for root, _dirs, files in os.walk(archive_dir):
        for file in files:
            if file_path.endswith(file) and file_path in os.path.join(root, file):
                return Path(root) / file

    # Also search by just filename
    filename = Path(file_path).name
    for root, _dirs, files in os.walk(archive_dir):
        if filename in files:
            full_path = Path(root) / filename
            # Verify it's in the right module structure
            if file_path.replace("\\", "/") in str(full_path).replace("\\", "/"):
                return full_path

    return None

def restore_file(src_path, module_path):
    """Restore file from archive to app directory"""
    # Convert module path to destination path
    dst_path = Path(module_path.replace(".", "/") + ".py")

    # Ensure directory exists
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    # Copy file
    shutil.copy2(src_path, dst_path)
    print(f"[RESTORED] {dst_path} from {src_path}")
    return True

def main():
    max_iterations = 20
    restored_files = []

    for i in range(max_iterations):
        print(f"\n[ITERATION {i+1}] Running tests...")

        # Run pytest and get error
        error_text = run_pytest_and_get_error()

        # Extract missing module
        missing_module = extract_missing_module(error_text)

        if not missing_module:
            print("[SUCCESS] No import errors found!")
            break

        print(f"[MISSING] {missing_module}")

        # Find file in archive
        src_file = find_file_in_archive(missing_module)

        if not src_file:
            print(f"[ERROR] Could not find {missing_module} in archive")
            print("Error text:", error_text[:500])
            break

        # Restore file
        if restore_file(src_file, missing_module):
            restored_files.append(missing_module)
        else:
            print(f"[ERROR] Failed to restore {missing_module}")
            break

    print(f"\n[SUMMARY] Restored {len(restored_files)} files:")
    for file in restored_files:
        print(f"  - {file}")

if __name__ == "__main__":
    main()
