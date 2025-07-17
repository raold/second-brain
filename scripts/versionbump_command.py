#!/usr/bin/env python3
"""
Version Bump Command Handler
Simple interface for executing version bumps with the VERSIONBUMP command
"""

import sys
from pathlib import Path

# Add the scripts directory to the path so we can import version_bump
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

# Import after path modification (required for local module)
from version_bump import VersionBumper  # noqa: E402


def handle_versionbump_command(args):
    """Handle VERSIONBUMP command with arguments"""
    if not args:
        print("Usage: VERSIONBUMP [major|minor|patch]")
        print("Example: VERSIONBUMP patch")
        return

    bump_type = args[0].lower()
    if bump_type not in ["major", "minor", "patch"]:
        print("Error: bump_type must be 'major', 'minor', or 'patch'")
        return

    try:
        # Initialize version bumper
        bumper = VersionBumper()

        # Execute version bump
        bumper.execute_version_bump(bump_type)

        print("\n" + "=" * 60)
        print("🎉 VERSIONBUMP COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"✅ Version bumped: {bump_type}")
        print("✅ All files updated")
        print("✅ Git operations completed")
        print("✅ Release notes generated")
        print("\n🚀 Ready to create GitHub release!")

    except Exception as e:
        print(f"❌ VERSIONBUMP failed: {e}")
        sys.exit(1)


def main():
    """Main entry point"""
    # Check if this is being called as VERSIONBUMP
    script_name = Path(sys.argv[0]).name

    if script_name.upper() == "VERSIONBUMP" or "versionbump" in script_name.lower():
        # Called as VERSIONBUMP command
        handle_versionbump_command(sys.argv[1:])
    else:
        # Called directly - show usage
        print("Version Bump Command Handler")
        print("Usage: python versionbump_command.py [major|minor|patch]")
        print("Or create alias: alias VERSIONBUMP='python scripts/versionbump_command.py'")


if __name__ == "__main__":
    main()
