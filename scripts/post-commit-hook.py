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


def bump_version(bump_type):
    """Execute version bump script"""
    try:
        script_path = Path("scripts/version_bump.py")
        if script_path.exists():
            subprocess.run([sys.executable, str(script_path), bump_type], check=True)
            return True
    except subprocess.CalledProcessError as e:
        print(f"Error bumping version: {e}")
        return False

    return False


def main():
    """Main post-commit hook logic"""
    commit_message = get_commit_message()

    if not commit_message:
        print("No commit message found")
        return

    if not should_bump_version(commit_message):
        print("Skipping version bump")
        return

    bump_type = analyze_commit_message(commit_message)
    print(f"📝 Commit: {commit_message.split()[0]}")
    print(f"🔄 Detected bump type: {bump_type}")

    if bump_version(bump_type):
        print("✅ Version bumped successfully")

        # Stage and commit the version changes
        try:
            subprocess.run(["git", "add", "-A"], check=True)
            subprocess.run(["git", "commit", "-m", f"chore: bump version ({bump_type})"], check=True)
            print("✅ Version bump committed")
        except subprocess.CalledProcessError as e:
            print(f"Error committing version bump: {e}")
    else:
        print("❌ Version bump failed")


if __name__ == "__main__":
    main()
