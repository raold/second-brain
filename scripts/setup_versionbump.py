#!/usr/bin/env python3
"""
Setup VERSIONBUMP Command
Creates aliases and shortcuts for the VERSIONBUMP command across different platforms
"""

import platform
import sys
from pathlib import Path


def setup_versionbump_command():
    """Setup VERSIONBUMP command for the current platform"""

    # Get paths
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent

    system = platform.system().lower()

    print(f"🔧 Setting up VERSIONBUMP command for {system}")
    print(f"📁 Root directory: {root_dir}")

    if system == "windows":
        setup_windows_command(script_dir, root_dir)
    elif system in ["linux", "darwin"]:  # Linux or macOS
        setup_unix_command(script_dir, root_dir)
    else:
        print(f"❌ Unsupported platform: {system}")
        return False

    return True


def setup_windows_command(script_dir, root_dir):
    """Setup VERSIONBUMP command for Windows"""

    # Create a batch file in the scripts directory
    batch_content = f"""@echo off
REM VERSIONBUMP Command - Auto-generated
cd /d "{root_dir}"
python scripts\\version_bump.py %*
"""

    batch_file = script_dir / "versionbump.bat"
    batch_file.write_text(batch_content)

    print(f"✅ Created batch file: {batch_file}")

    # Instructions for adding to PATH
    print("\n📋 To make VERSIONBUMP available system-wide:")
    print(f"1. Add this directory to your PATH: {script_dir}")
    print("2. Or run from project root: scripts\\VERSIONBUMP.bat [major|minor|patch]")
    print("3. Or use PowerShell: scripts\\VERSIONBUMP.ps1 [major|minor|patch]")

    # Create PowerShell profile entry
    powershell_alias = f"""
# VERSIONBUMP alias for Second Brain
function VERSIONBUMP {{
    param([string]$BumpType)
    if (-not $BumpType) {{
        Write-Host "Usage: VERSIONBUMP [major|minor|patch]" -ForegroundColor Yellow
        return
    }}
    & "{script_dir / 'VERSIONBUMP.ps1'}" $BumpType
}}
"""

    print("\n📝 PowerShell alias (add to your profile):")
    print(powershell_alias)


def setup_unix_command(script_dir, root_dir):
    """Setup VERSIONBUMP command for Unix-like systems"""

    # Create a shell script
    shell_script = f"""#!/bin/bash
# VERSIONBUMP Command - Auto-generated
cd "{root_dir}"
python3 scripts/version_bump.py "$@"
"""

    script_file = script_dir / "versionbump"
    script_file.write_text(shell_script)
    script_file.chmod(0o755)  # Make executable

    print(f"✅ Created shell script: {script_file}")

    # Create alias for common shells
    bash_alias = f"""
# VERSIONBUMP alias for Second Brain
alias VERSIONBUMP='cd "{root_dir}" && python3 scripts/version_bump.py'
"""

    print("\n📝 Bash/Zsh alias (add to your ~/.bashrc or ~/.zshrc):")
    print(bash_alias)

    print("\n📋 To make VERSIONBUMP available system-wide:")
    print(f"1. Add this directory to your PATH: {script_dir}")
    print("2. Or run from project root: scripts/versionbump [major|minor|patch]")
    print("3. Or add the alias above to your shell configuration")


def main():
    """Main entry point"""
    print("🚀 Second Brain Version Bump Command Setup")
    print("=" * 50)

    if setup_versionbump_command():
        print("\n🎉 VERSIONBUMP command setup completed!")
        print("\n📚 Usage:")
        print("  VERSIONBUMP major   - Major version bump (1.0.0 → 2.0.0)")
        print("  VERSIONBUMP minor   - Minor version bump (1.0.0 → 1.1.0)")
        print("  VERSIONBUMP patch   - Patch version bump (1.0.0 → 1.0.1)")
        print("\n🔧 The command will:")
        print("  ✅ Update app/version.py")
        print("  ✅ Update README.md")
        print("  ✅ Update CHANGELOG.md")
        print("  ✅ Update docs/ files recursively")
        print("  ✅ Git add, commit, and push")
        print("  ✅ Create and push Git tag")
        print("  ✅ Generate release notes for GitHub")
    else:
        print("\n❌ Setup failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
