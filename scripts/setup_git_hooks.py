#!/usr/bin/env python3
"""
Setup git hooks for the Second Brain project.
This ensures folder structure is maintained across all commits.
"""

import subprocess
import sys
import os


def install_pre_commit():
    """Install pre-commit hooks."""
    print("📦 Installing pre-commit framework...")
    
    # Check if pre-commit is installed
    try:
        subprocess.run(["pre-commit", "--version"], check=True, capture_output=True)
        print("✅ pre-commit is already installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Installing pre-commit...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pre-commit"], check=True)
        print("✅ pre-commit installed successfully")
    
    # Install the pre-commit hooks
    print("\n🔧 Installing pre-commit hooks...")
    subprocess.run(["pre-commit", "install"], check=True)
    print("✅ Pre-commit hooks installed")
    
    # Run against all files to check current state
    print("\n🧹 Checking current repository state...")
    try:
        subprocess.run(["pre-commit", "run", "--all-files"], check=True)
        print("✅ All checks passed!")
    except subprocess.CalledProcessError:
        print("⚠️  Some checks failed. Please fix the issues and commit again.")
        print("   Run 'pre-commit run --all-files' to see details.")


def main():
    """Main setup function."""
    print("🚀 Setting up git hooks for Second Brain project\n")
    
    # Check if we're in the right directory
    if not os.path.exists(".git"):
        print("❌ Error: Not in a git repository. Please run from project root.")
        sys.exit(1)
    
    if not os.path.exists("scripts/cleanup_folder_structure.py"):
        print("❌ Error: Cannot find cleanup script. Please run from project root.")
        sys.exit(1)
    
    install_pre_commit()
    
    print("\n✨ Setup complete!")
    print("\nThe following hooks are now active:")
    print("  - Trailing whitespace removal")
    print("  - End of file fixer")
    print("  - YAML/JSON validation")
    print("  - Python formatting (ruff)")
    print("  - Import validation")
    print("  - 🧹 Folder structure cleanup")
    print("\nThese will run automatically before each commit.")


if __name__ == "__main__":
    main()