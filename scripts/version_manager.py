#!/usr/bin/env python3
"""
Second Brain Version Manager
Centralized version management system for releases

This script manages all aspects of versioning including:
- Version number updates
- Release notes generation
- Commit messages
- Git workflows
- Documentation updates
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_RELEASES = PROJECT_ROOT / "docs" / "releases"
APP_VERSION_FILE = PROJECT_ROOT / "app" / "version.py"
README_FILE = PROJECT_ROOT / "README.md"
CHANGELOG_FILE = PROJECT_ROOT / "CHANGELOG.md"
PROJECT_STATUS_FILE = PROJECT_ROOT / "PROJECT_STATUS.md"


class VersionManager:
    """Central version management system"""

    def __init__(self):
        self.versions_config = self.load_versions_config()
        self.current_version = self.get_current_version()

    def load_versions_config(self) -> dict:
        """Load version configuration from centralized file"""
        config_file = DOCS_RELEASES / "version_config.json"

        # Create default config if it doesn't exist
        if not config_file.exists():
            default_config = {
                "current_stable": "2.4.1",
                "current_development": "2.4.2",
                "branch_strategy": "develop->testing->main",
                "supported_workflows": [
                    "develop->testing->main->release",
                    "testing->main->release",
                    "develop->main->release",
                    "direct->main",
                ],
                "versions": {
                    "2.4.2": {
                        "status": "development",
                        "title": "Architecture Cleanup & Optimization",
                        "focus": "Cleanup",
                        "release_date": "2025-07-18",
                        "changes": [
                            "Complete Qdrant dependency removal",
                            "Project organization cleanup",
                            "Documentation consistency improvements",
                            "Configuration optimization",
                        ],
                        "commit_message": "Release v2.4.2: Architecture cleanup and dependency optimization",
                        "pr_testing": True,
                        "git_workflow": "testing->main->release",
                    },
                    "2.4.1": {
                        "status": "stable",
                        "title": "Documentation & Quality Improvements",
                        "focus": "Quality",
                        "release_date": "2025-07-18",
                        "changes": [
                            "Documentation improvements",
                            "Quality enhancements",
                            "Licensing fixes",
                            "Badge accuracy",
                        ],
                        "commit_message": "Release v2.4.1: Documentation and quality improvements",
                        "pr_testing": False,
                        "git_workflow": "direct->main",
                    },
                },
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2)

            return default_config

        with open(config_file, encoding="utf-8") as f:
            return json.load(f)

    def save_versions_config(self):
        """Save version configuration"""
        config_file = DOCS_RELEASES / "version_config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(self.versions_config, f, indent=2)

    def get_current_version(self) -> str:
        """Get current version from app/version.py"""
        with open(APP_VERSION_FILE, encoding="utf-8") as f:
            content = f.read()

        match = re.search(r'__version__ = ["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)
        raise ValueError("Could not find version in app/version.py")

    def update_version(self, new_version: str, version_info: dict):
        """Update version across all files"""
        print(f"🔄 Updating version to {new_version}...")

        # Update app/version.py
        self._update_app_version(new_version, version_info)

        # Update README.md
        self._update_readme_version(new_version)

        # Update CHANGELOG.md
        self._update_changelog(new_version, version_info)

        # Update PROJECT_STATUS.md
        self._update_project_status(new_version, version_info)

        # Update version config
        self.versions_config["current_development"] = new_version
        self.versions_config["versions"][new_version] = version_info
        self.save_versions_config()

        print(f"✅ Version updated to {new_version}")

    def _update_app_version(self, version: str, info: dict):
        """Update app/version.py"""
        with open(APP_VERSION_FILE, encoding="utf-8") as f:
            content = f.read()

        # Update version string
        content = re.sub(r'__version__ = ["\'][^"\']+["\']', f'__version__ = "{version}"', content)

        # Update version info tuple
        major, minor, patch = version.split(".")
        content = re.sub(r"__version_info__ = \([^)]+\)", f"__version_info__ = ({major}, {minor}, {patch})", content)

        # Update release date
        content = re.sub(
            r'__release_date__ = ["\'][^"\']+["\']', f'__release_date__ = "{info["release_date"]}"', content
        )

        with open(APP_VERSION_FILE, "w", encoding="utf-8") as f:
            f.write(content)

    def _update_readme_version(self, version: str):
        """Update README.md version"""
        with open(README_FILE, encoding="utf-8") as f:
            content = f.read()

        # Update title
        content = re.sub(r"# Second Brain v[\d.]+", f"# Second Brain v{version}", content)

        # Update architecture overview
        content = re.sub(r"Second Brain v[\d.]+ represents", f"Second Brain v{version} represents", content)

        with open(README_FILE, "w", encoding="utf-8") as f:
            f.write(content)

    def _update_changelog(self, version: str, info: dict):
        """Update CHANGELOG.md"""
        with open(CHANGELOG_FILE, encoding="utf-8") as f:
            content = f.read()

        # Create new changelog entry
        changes_text = "\n".join([f"- **{change}**" for change in info["changes"]])

        new_entry = f"""## [{version}] - {info["release_date"]}

### 🧹 {info["title"]}

{changes_text}

"""

        # Insert after the header
        lines = content.split("\n")
        header_end = 0
        for i, line in enumerate(lines):
            if line.startswith("## ["):
                header_end = i
                break

        if header_end > 0:
            lines.insert(header_end, new_entry)
            content = "\n".join(lines)
        else:
            # If no previous entries, add after header
            content += f"\n{new_entry}"

        with open(CHANGELOG_FILE, "w", encoding="utf-8") as f:
            f.write(content)

    def _update_project_status(self, version: str, info: dict):
        """Update PROJECT_STATUS.md"""
        with open(PROJECT_STATUS_FILE, encoding="utf-8") as f:
            content = f.read()

        status = "Production Ready" if info["status"] == "stable" else f"Development Ready (v{version} Staging)"

        # Update version and status
        content = re.sub(r"\*\*Version\*\*: [^\n]+", f'**Version**: {version} ({info["status"].title()})', content)

        content = re.sub(r"\*\*Last Updated\*\*: [^\n]+", f'**Last Updated**: {info["release_date"]}', content)

        content = re.sub(r"## 🎯 Current Status: [^\n]+", f"## 🎯 Current Status: {status}", content)

        with open(PROJECT_STATUS_FILE, "w", encoding="utf-8") as f:
            f.write(content)

    def create_release_notes(self, version: str) -> str:
        """Create detailed release notes file"""
        info = self.versions_config["versions"][version]

        release_notes_file = DOCS_RELEASES / f"RELEASE_NOTES_v{version}.md"

        # Create comprehensive release notes
        release_notes = f"""# 🧹 Second Brain v{version} - {info["title"]}

## 📋 Release Overview

**Version**: v{version} ({info["focus"]})  
**Release Date**: {info["release_date"]}  
**Focus**: {info["title"]}  
**Status**: {info["status"].title()}

## 🎯 Key Improvements

{self._format_changes_for_release_notes(info["changes"])}

## 🚀 Deployment Instructions

### For Development/Testing
```bash
git checkout testing
git pull origin testing
docker-compose up --build
```

### For Production (when stable)
```bash
git checkout main
git pull origin main
docker-compose up -d --build
```

## 📚 Documentation

- **[Architecture Guide](../architecture/ARCHITECTURE.md)**: System design details
- **[Release History](README.md)**: Complete version history
- **[Migration Guide](MIGRATION_v{version}.md)**: Upgrade instructions

## 🔗 Links

**Repository**: [github.com/raold/second-brain](https://github.com/raold/second-brain)  
**Documentation**: [Project Documentation](../../README.md)  
**Issues**: [GitHub Issues](https://github.com/raold/second-brain/issues)

---
*Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | Second Brain v{version}*
"""

        with open(release_notes_file, "w", encoding="utf-8") as f:
            f.write(release_notes)

        return str(release_notes_file)

    def _format_changes_for_release_notes(self, changes: list[str]) -> str:
        """Format changes for detailed release notes"""
        formatted = []
        for change in changes:
            formatted.append(f"- **{change}**: Detailed implementation and impact")
        return "\n".join(formatted)

    def prepare_release(self, version: str):
        """Prepare everything for a release"""
        if version not in self.versions_config["versions"]:
            print(f"❌ Version {version} not found in configuration")
            return

        info = self.versions_config["versions"][version]

        print(f"🚀 Preparing release for v{version}")
        print(f"   Title: {info['title']}")
        print(f"   Status: {info['status']}")
        print(f"   Changes: {len(info['changes'])} items")

        # Update all version files
        self.update_version(version, info)

        # Create release notes
        release_notes_path = self.create_release_notes(version)
        print(f"📄 Release notes created: {release_notes_path}")

        # Generate git commands
        self.generate_git_commands(version, info)

    def generate_git_commands(self, version: str, info: dict):
        """Generate git commands for release"""
        print(f"\n📋 Git Commands for v{version}:")
        print("=" * 50)

        commit_msg = info["commit_message"]

        if info["git_workflow"] == "testing->main->release":
            print("# Stage and commit changes")
            print("git add .")
            print(f'git commit -m "{commit_msg}"')
            print("git push origin testing")
            print()

            if info.get("pr_testing", False):
                print("# Create PR for testing -> main (with CI/CD validation)")
                print(
                    'gh pr create --title "Release v{version}" --body "See RELEASE_NOTES_v{version}.md for details" --base main --head testing'
                )
                print()
                print("# 🧪 TESTING CHECKLIST (Required before merge):")
                print("# 1. ✅ Unit tests pass: pytest tests/unit/")
                print("# 2. ✅ Integration tests pass: pytest tests/integration/")
                print("# 3. ✅ Performance tests pass: pytest tests/performance/")
                print("# 4. ✅ Migration tests pass: pytest tests/migration/")
                print("# 5. ✅ GitHub Actions CI pipeline passes")
                print("# 6. ✅ Manual testing in staging environment")
                print("# 7. ✅ Security scan results reviewed")
                print("# 8. ✅ Documentation updated and verified")
                print()
                print("# After PR approval, merge, and production testing:")
                print("git checkout main")
                print("git pull origin main")
            else:
                print("# Direct merge to main")
                print("git checkout main")
                print("git merge testing")
                print("git push origin main")

            print()
            print("# Create release tag (after production validation)")
            print(f"git tag -a v{version} -m \"Release v{version}: {info['title']}\"")
            print(f"git push origin v{version}")

        elif info["git_workflow"] == "develop->testing->main->release":
            print("# Develop -> Testing -> Main -> Release workflow")
            print("git add .")
            print(f'git commit -m "{commit_msg}"')
            print("git push origin develop")
            print()
            print("# Merge to testing branch")
            print("git checkout testing")
            print("git pull origin testing")
            print("git merge develop")
            print("python scripts/version_manager.py test all  # Validate integration")
            print("git push origin testing")
            print()

            if info.get("pr_testing", False):
                print("# Create PR for testing -> main (with CI/CD validation)")
                print(
                    'gh pr create --title "Release v{version}" --body "See RELEASE_NOTES_v{version}.md for details" --base main --head testing'
                )
                print()
                print("# 🧪 TESTING CHECKLIST (Required before merge):")
                print("# 1. ✅ Develop branch CI passes")
                print("# 2. ✅ Testing branch integration validated")
                print("# 3. ✅ Full test suite passes: python scripts/version_manager.py test all")
                print("# 4. ✅ GitHub Actions CI pipeline passes")
                print("# 5. ✅ Manual testing in staging environment")
                print("# 6. ✅ Cross-feature compatibility verified")
                print("# 7. ✅ Performance impact assessment")
                print("# 8. ✅ Documentation updated and verified")
                print()
                print("# After PR approval, merge, and production testing:")
                print("git checkout main")
                print("git pull origin main")

            print()
            print("# Create release tag (after production validation)")
            print(f"git tag -a v{version} -m \"Release v{version}: {info['title']}\"")
            print(f"git push origin v{version}")

        elif info["git_workflow"] == "develop->main->release":
            print("# Direct develop -> main workflow")
            print("git add .")
            print(f'git commit -m "{commit_msg}"')
            print("git push origin develop")
            print()
            print("# Create PR for develop -> main")
            print(
                'gh pr create --title "Release v{version}" --body "See RELEASE_NOTES_v{version}.md for details" --base main --head develop'
            )
            print("# After approval and merge:")
            print("git checkout main")
            print("git pull origin main")
            print(f"git tag -a v{version} -m \"Release v{version}: {info['title']}\"")
            print(f"git push origin v{version}")

        elif info["git_workflow"] == "direct->main":
            print("# Direct to main workflow")
            print("git add .")
            print(f'git commit -m "{commit_msg}"')
            print("git push origin main")
            print(f"git tag -a v{version} -m \"Release v{version}: {info['title']}\"")
            print(f"git push origin v{version}")

        print()
        print("# 🚀 Production Deployment Commands")
        print("docker-compose down")
        print("docker-compose pull")
        print("docker-compose up -d --build")
        print("# Verify deployment: curl http://localhost:8000/health")
        print()
        print("# GitHub Release (optional)")
        print(
            f'gh release create v{version} --title "Second Brain v{version}" --notes-file docs/releases/RELEASE_NOTES_v{version}.md'
        )

    def run_test_suite(self, test_type: str = "all") -> bool:
        """Run comprehensive test suite"""
        print(f"🧪 Running {test_type} tests...")

        test_commands = {
            "unit": ["python", "-m", "pytest", "tests/unit/", "-v"],
            "integration": ["python", "-m", "pytest", "tests/integration/", "-v"],
            "performance": ["python", "-m", "pytest", "tests/performance/", "-v", "-m", "performance"],
            "migration": ["python", "-m", "pytest", "tests/migration/", "-v"],
            "all": ["python", "-m", "pytest", "tests/", "--cov=app", "--cov-report=term-missing"],
        }

        if test_type not in test_commands:
            print(f"❌ Unknown test type: {test_type}")
            return False

        try:
            import subprocess

            result = subprocess.run(
                test_commands[test_type], capture_output=True, text=True, encoding="utf-8", errors="ignore"
            )

            if result.returncode == 0:
                print(f"✅ {test_type.title()} tests passed!")
                if result.stdout:
                    print(result.stdout[-500:])  # Show last 500 chars to avoid overflow
                return True
            else:
                print(f"❌ {test_type.title()} tests failed!")
                if result.stderr:
                    print("STDERR:", result.stderr[-500:])  # Show last 500 chars
                if result.stdout:
                    print("STDOUT:", result.stdout[-500:])  # Show last 500 chars
                return False

        except Exception as e:
            print(f"❌ Error running tests: {e}")
            return False

    def validate_pre_release(self, version: str) -> bool:
        """Validate all requirements before release"""
        print(f"🔍 Validating pre-release requirements for v{version}...")

        checks = [
            ("Unit Tests", lambda: self.run_test_suite("unit")),
            ("Integration Tests", lambda: self.run_test_suite("integration")),
            ("Performance Tests", lambda: self.run_test_suite("performance")),
            ("Migration Tests", lambda: self.run_test_suite("migration")),
        ]

        all_passed = True
        for check_name, check_func in checks:
            print(f"\n🧪 Running {check_name}...")
            if not check_func():
                print(f"❌ {check_name} failed!")
                all_passed = False
            else:
                print(f"✅ {check_name} passed!")

        if all_passed:
            print(f"\n🎉 All pre-release validations passed for v{version}!")
            print("✅ Ready for release!")
        else:
            print(f"\n⚠️  Some validations failed for v{version}")
            print("❌ Fix issues before proceeding with release")

        return all_passed

    def show_current_status(self):
        """Show current version status"""
        current_stable = self.versions_config["current_stable"]
        current_dev = self.versions_config["current_development"]

        print("📊 Current Version Status")
        print("=" * 30)
        print(f"Stable Release:     v{current_stable}")
        print(f"Development:        v{current_dev}")
        print(f"App Version:        v{self.current_version}")
        print(f"Branch Strategy:    {self.versions_config['branch_strategy']}")
        print()

        # Show version details
        for version in [current_dev, current_stable]:
            if version in self.versions_config["versions"]:
                info = self.versions_config["versions"][version]
                print(f"v{version} ({info['status']}): {info['title']}")
                for change in info["changes"][:3]:  # Show first 3 changes
                    print(f"  • {change}")
                if len(info["changes"]) > 3:
                    print(f"  • ... and {len(info['changes']) - 3} more")
                print()
        """Show current version status"""
        current_stable = self.versions_config["current_stable"]
        current_dev = self.versions_config["current_development"]

        print("📊 Current Version Status")
        print("=" * 30)
        print(f"Stable Release:     v{current_stable}")
        print(f"Development:        v{current_dev}")
        print(f"App Version:        v{self.current_version}")
        print(f"Branch Strategy:    {self.versions_config['branch_strategy']}")
        print()

        # Show version details
        for version in [current_dev, current_stable]:
            if version in self.versions_config["versions"]:
                info = self.versions_config["versions"][version]
                print(f"v{version} ({info['status']}): {info['title']}")
                for change in info["changes"][:3]:  # Show first 3 changes
                    print(f"  • {change}")
                if len(info["changes"]) > 3:
                    print(f"  • ... and {len(info['changes']) - 3} more")
                print()


def main():
    """Main CLI interface"""
    if len(sys.argv) < 2:
        print("Usage: python version_manager.py <command> [args]")
        print("Commands:")
        print("  status              - Show current version status")
        print("  prepare <version>   - Prepare release for version")
        print("  update <version>    - Update to new version")
        print("  create-config       - Create new version configuration")
        print("  test [type]         - Run test suite (unit|integration|performance|migration|all)")
        print("  validate <version>  - Validate pre-release requirements")
        return

    vm = VersionManager()
    command = sys.argv[1]

    if command == "status":
        vm.show_current_status()

    elif command == "prepare":
        if len(sys.argv) < 3:
            print("Usage: python version_manager.py prepare <version>")
            return
        version = sys.argv[2]
        vm.prepare_release(version)

    elif command == "update":
        if len(sys.argv) < 3:
            print("Usage: python version_manager.py update <version>")
            return
        version = sys.argv[2]
        if version not in vm.versions_config["versions"]:
            print(f"Version {version} not found. Add it to version_config.json first.")
            return
        info = vm.versions_config["versions"][version]
        vm.update_version(version, info)

    elif command == "test":
        test_type = sys.argv[2] if len(sys.argv) > 2 else "all"
        vm.run_test_suite(test_type)

    elif command == "validate":
        if len(sys.argv) < 3:
            print("Usage: python version_manager.py validate <version>")
            return
        version = sys.argv[2]
        vm.validate_pre_release(version)

    elif command == "create-config":
        vm.load_versions_config()  # This will create default if not exists
        print("✅ Version configuration created at docs/releases/version_config.json")

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
