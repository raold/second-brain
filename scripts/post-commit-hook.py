#!/usr/bin/env python3
"""
Git Commit Hook for Automated Version Bumping
Analyzes commit messages and automatically bumps version
"""

import re
import subprocess
import sys
from pathlib import Path


def get_commit_message():
    """Get the commit message from git"""
    try:
        result = subprocess.run(["git", "log", "-1", "--pretty=%B"], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def analyze_commit_message(message):
    """Analyze commit message to determine version bump type"""
    lines = message.split("\n")
    first_line = lines[0] if lines else ""

    # Check for BREAKING CHANGE
    if any("BREAKING CHANGE" in line for line in lines):
        return "major"

    # Check for major version triggers
    if re.match(r"^(feat|feature)!:", first_line):
        return "major"

    # Check for minor version triggers
    if re.match(r"^(feat|feature|perf|performance):", first_line):
        return "minor"

    # Check for patch version triggers (combined patterns)
    patch_patterns = [
        r"^(fix|bug):",
        r"^(docs|doc):",
        r"^(style|format):",
        r"^(refactor|refac):",
        r"^(test|tests):",
        r"^(chore|maint):",
    ]

    if any(re.match(pattern, first_line) for pattern in patch_patterns):
        return "patch"

    # Default to patch for any other changes
    return "patch"


def should_bump_version(message):
    """Determine if version should be bumped based on commit message"""
    # Skip version bumping for version bump commits
    if "bump version" in message.lower():
        return False

    # Skip for merge commits
    if message.startswith("Merge "):
        return False

    # Skip for revert commits
    if message.startswith("Revert "):
        return False

    return True


def check_version_manager():
    """Check if version manager is available"""
    try:
        script_path = Path("scripts/version_manager.py")
        if script_path.exists():
            subprocess.run([sys.executable, str(script_path), "status"], check=True, capture_output=True)
            return True
    except subprocess.CalledProcessError as e:
        print(f"Version manager not available: {e}")
        return False

    return False


def main():
    """Main post-commit hook execution"""
    print("🔍 Post-commit hook checking version management...")

    commit_message = get_commit_message()

    if not commit_message:
        print("No commit message found")
        return

    if not should_bump_version(commit_message):
        print("Skipping automatic version management")
        return

    bump_type = analyze_commit_message(commit_message)
    print(f"📝 Commit: {commit_message.split()[0]}")
    print(f"🔄 Detected change type: {bump_type}")

    if check_version_manager():
        print("✅ Version manager available")
        print("💡 Use 'python scripts/version_manager.py prepare X.Y.Z' for releases")
    else:
        print("❌ Version manager not available")


if __name__ == "__main__":
    main()
