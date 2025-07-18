#!/usr/bin/env python3
"""
Production-Ready Version Bump Script for Second Brain
Handles complete version bumping workflow including:
- Version updates in app/version.py
- README.md updates with badges and version references
- CHANGELOG.md updates
- PROJECT_STATUS.md updates
- Documentation updates across all files
- Git operations with proper tagging
- Release notes generation
"""

import re
import subprocess
import sys
import glob
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


class ProductionVersionBumper:
    def __init__(self, root_dir: Optional[str] = None):
        self.root_dir = Path(root_dir) if root_dir else Path(__file__).parent.parent
        self.version_file = self.root_dir / "app" / "version.py"
        self.readme_file = self.root_dir / "README.md"
        self.changelog_file = self.root_dir / "CHANGELOG.md"
        self.project_status_file = self.root_dir / "PROJECT_STATUS.md"
        self.security_file = self.root_dir / "SECURITY.md"
        
        # Version patterns for different file types
        self.version_patterns = {
            "python": r'__version__ = "(.*?)"',
            "readme_header": r"# Second Brain v(.*?) 🧠",
            "readme_latest": r"## 🚀 Latest in v(.*?):",
            "changelog_version": r"## \[v(.*?)\]",
            "project_status": r'"Current Version": `v(.*?)`',
            "security_version": r'"Current Version": v(.*?) \(',
            "badge_version": r"Second%20Brain-v(.*?)-",
            "generic_version": r"v(\d+\.\d+\.\d+)",
            "version_display": r"Current: v(\d+\.\d+\.\d+)",
            "next_version": r"Next: v(\d+\.\d+\.\d+)"
        }

        # Current version info
        self.current_version: Optional[str] = None
        self.new_version: Optional[str] = None
        self.version_type: Optional[str] = None
        self.release_date = datetime.now().strftime("%Y-%m-%d")

    def get_current_version(self) -> str:
        """Get current version from version.py"""
        if not self.version_file.exists():
            raise FileNotFoundError(f"Version file not found: {self.version_file}")

        content = self.version_file.read_text()
        match = re.search(self.version_patterns["python"], content)
        if not match:
            raise ValueError("Version not found in version.py")

        self.current_version = match.group(1)
        return self.current_version

    def calculate_new_version(self, bump_type: str) -> str:
        """Calculate new version based on bump type"""
        if not self.current_version:
            self.get_current_version()
        
        parts = self.current_version.split('.')
        if len(parts) != 3:
            raise ValueError(f"Invalid version format: {self.current_version}")
        
        major, minor, patch = map(int, parts)
        
        if bump_type == "major":
            self.new_version = f"{major + 1}.0.0"
        elif bump_type == "minor":
            self.new_version = f"{major}.{minor + 1}.0"
        elif bump_type == "patch":
            self.new_version = f"{major}.{minor}.{patch + 1}"
        else:
            raise ValueError(f"Invalid bump type: {bump_type}")
        
        self.version_type = bump_type
        return self.new_version

    def update_version_file(self) -> None:
        """Update app/version.py with new version"""
        content = self.version_file.read_text()
        
        # Update version
        content = re.sub(
            self.version_patterns["python"],
            f'__version__ = "{self.new_version}"',
            content
        )
        
        # Update version_info tuple
        parts = self.new_version.split('.')
        version_tuple = f"({parts[0]}, {parts[1]}, {parts[2]})"
        content = re.sub(
            r'__version_info__ = \(.*?\)',
            f'__version_info__ = {version_tuple}',
            content
        )
        
        # Update release date
        content = re.sub(
            r'__release_date__ = ".*?"',
            f'__release_date__ = "{self.release_date}"',
            content
        )
        
        self.version_file.write_text(content)
        print(f"✅ Updated {self.version_file}: {self.current_version} → {self.new_version}")

    def update_readme(self) -> None:
        """Update README.md with new version"""
        content = self.readme_file.read_text()
        
        # Update header
        content = re.sub(
            self.version_patterns["readme_header"],
            f"# Second Brain v{self.new_version} 🧠",
            content
        )
        
        # Update "Latest in" section
        content = re.sub(
            self.version_patterns["readme_latest"],
            f"## 🚀 Latest in v{self.new_version}:",
            content
        )
        
        # Update badges
        badge_version = self.new_version.replace(".", "%2E")
        content = re.sub(
            r"Second%20Brain-v[\d%2E]+-",
            f"Second%20Brain-v{badge_version}-",
            content
        )
        
        self.readme_file.write_text(content)
        print(f"✅ Updated {self.readme_file}: version references updated")

    def update_changelog(self) -> None:
        """Update CHANGELOG.md with new version entry"""
        content = self.changelog_file.read_text()
        
        # Create new entry
        new_entry = f"""## [v{self.new_version}] - {self.release_date} - Version Bump

### **🔧 Version Management**
- **Version Update**: Updated from v{self.current_version} to v{self.new_version}
- **Release Type**: {self.version_type.title()} release
- **Build Date**: {self.release_date}

---

"""
        
        # Insert after the header
        lines = content.split('\n')
        insert_index = None
        for i, line in enumerate(lines):
            if line.startswith('## [v') and 'changelog' not in line.lower():
                insert_index = i
                break
        
        if insert_index is not None:
            lines.insert(insert_index, new_entry.strip())
            content = '\n'.join(lines)
        else:
            # If no previous entries, add after the header
            header_end = content.find('\n\n')
            if header_end != -1:
                content = content[:header_end + 2] + new_entry + content[header_end + 2:]
        
        self.changelog_file.write_text(content)
        print(f"✅ Updated {self.changelog_file}: added v{self.new_version} entry")

    def update_project_status(self) -> None:
        """Update PROJECT_STATUS.md with new version"""
        content = self.project_status_file.read_text()
        
        # Update current version
        content = re.sub(
            self.version_patterns["project_status"],
            f'"Current Version": `v{self.new_version}`',
            content
        )
        
        # Update release date
        content = re.sub(
            r'- \*\*Release Date\*\*: [^\n]+',
            f'- **Release Date**: {self.release_date}',
            content
        )
        
        self.project_status_file.write_text(content)
        print(f"✅ Updated {self.project_status_file}: version updated")

    def update_security_file(self) -> None:
        """Update SECURITY.md with new version"""
        if not self.security_file.exists():
            return
            
        content = self.security_file.read_text()
        
        # Update current version reference
        content = re.sub(
            self.version_patterns["security_version"],
            f'"Current Version": v{self.new_version} (',
            content
        )
        
        self.security_file.write_text(content)
        print(f"✅ Updated {self.security_file}: version updated")

    def update_documentation_files(self) -> None:
        """Update all documentation files with version references"""
        doc_files = [
            *glob.glob(str(self.root_dir / "docs" / "**" / "*.md"), recursive=True),
            *glob.glob(str(self.root_dir / "examples" / "*.py")),
        ]
        
        updated_files = []
        
        for file_path in doc_files:
            try:
                file_path = Path(file_path)
                content = file_path.read_text(encoding='utf-8')
                original_content = content
                
                # Update various version patterns
                for pattern_name, pattern in self.version_patterns.items():
                    if pattern_name in ["python"]:  # Skip Python-specific patterns
                        continue
                        
                    content = re.sub(pattern, lambda m: m.group(0).replace(m.group(1), self.new_version), content)
                
                # Update generic version references
                content = re.sub(
                    r'\bv\d+\.\d+\.\d+\b',
                    f'v{self.new_version}',
                    content
                )
                
                if content != original_content:
                    file_path.write_text(content, encoding='utf-8')
                    updated_files.append(str(file_path))
                    
            except Exception as e:
                print(f"⚠️ Warning: Could not update {file_path}: {e}")
        
        if updated_files:
            print(f"✅ Updated {len(updated_files)} documentation files")
            for file in updated_files[:5]:  # Show first 5
                print(f"   - {file}")
            if len(updated_files) > 5:
                print(f"   ... and {len(updated_files) - 5} more")

    def create_release_notes(self) -> None:
        """Create release notes for the new version"""
        releases_dir = self.root_dir / "releases"
        releases_dir.mkdir(exist_ok=True)
        
        release_notes_file = releases_dir / f"RELEASE_NOTES_v{self.new_version}.md"
        
        release_notes = f"""# 🔧 Second Brain v{self.new_version} - Version Bump

## 📋 Release Information

**Release Date**: {self.release_date}  
**Version**: v{self.new_version}  
**Previous Version**: v{self.current_version}  
**Release Type**: {self.version_type.title()} Release  

---

## 🎯 Release Overview

Second Brain v{self.new_version} is a **{self.version_type} release** that updates the version from v{self.current_version} to v{self.new_version}.

## ✨ Changes

### **🔧 Version Management**
- **Version Update**: Updated from v{self.current_version} to v{self.new_version}
- **Documentation**: All version references updated across the project
- **Build Date**: {self.release_date}
- **Release Type**: {self.version_type.title()} release

### **📋 Updated Files**
- **app/version.py**: Core version information updated
- **README.md**: Header and badge versions updated
- **CHANGELOG.md**: New release entry added
- **PROJECT_STATUS.md**: Current version updated
- **Documentation**: All version references updated

## 🛠️ **Technical Details**

### **No Functional Changes**
- **API Compatibility**: 100% backward compatible
- **Database**: No schema changes
- **Dependencies**: No changes required
- **Performance**: Same performance characteristics

## 🎯 **Next Steps**

Continue with planned development roadmap for future releases.

---

**Download**: [Second Brain v{self.new_version}](https://github.com/raold/second-brain/releases/tag/v{self.new_version})  
**Previous Release**: [v{self.current_version}](https://github.com/raold/second-brain/releases/tag/v{self.current_version})
"""
        
        release_notes_file.write_text(release_notes)
        print(f"✅ Created release notes: {release_notes_file}")

    def git_operations(self, skip_push: bool = False) -> None:
        """Perform git operations"""
        try:
            # Add all changes
            subprocess.run(["git", "add", "-A"], check=True, cwd=self.root_dir)
            print("✅ Staged all changes")
            
            # Commit
            commit_message = f"🚀 Release v{self.new_version}\n\nVersion bump from v{self.current_version} to v{self.new_version}\n- {self.version_type.title()} release\n- Updated all version references\n- Generated release notes"
            subprocess.run(["git", "commit", "-m", commit_message], check=True, cwd=self.root_dir)
            print(f"✅ Committed changes: v{self.current_version} → v{self.new_version}")
            
            # Create tag
            tag_message = f"Second Brain v{self.new_version}\n\n{self.version_type.title()} release with version updates and documentation improvements."
            subprocess.run(["git", "tag", "-a", f"v{self.new_version}", "-m", tag_message], check=True, cwd=self.root_dir)
            print(f"✅ Created tag: v{self.new_version}")
            
            if not skip_push:
                # Push changes
                subprocess.run(["git", "push", "origin", "main"], check=True, cwd=self.root_dir)
                print("✅ Pushed changes to origin/main")
                
                # Push tag
                subprocess.run(["git", "push", "origin", f"v{self.new_version}"], check=True, cwd=self.root_dir)
                print(f"✅ Pushed tag v{self.new_version}")
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Git operation failed: {e}")
            raise

    def generate_github_release_info(self) -> Dict[str, str]:
        """Generate GitHub release information"""
        return {
            "title": f"🚀 Second Brain v{self.new_version} - {self.version_type.title()} Release",
            "tag": f"v{self.new_version}",
            "body": f"""# 🚀 Second Brain v{self.new_version}

**Release Date**: {self.release_date}  
**Release Type**: {self.version_type.title()} Release  
**Previous Version**: v{self.current_version}

## 🎯 Changes

Version bump from v{self.current_version} to v{self.new_version} with updated documentation and version references across all files.

### 📋 Updated Components
- Core version information
- Documentation and README
- Release notes and changelog
- Project status and security files

## 🛠️ Compatibility

- **API**: 100% backward compatible
- **Database**: No schema changes
- **Dependencies**: No changes required

**Ready for production deployment!** 🎉

---

**Full Changelog**: https://github.com/raold/second-brain/blob/main/CHANGELOG.md
"""
        }

    def run_version_bump(self, bump_type: str, dry_run: bool = False, skip_push: bool = False) -> None:
        """Run complete version bump workflow"""
        try:
            print(f"🚀 Starting version bump: {bump_type}")
            print(f"📁 Working directory: {self.root_dir}")
            
            if dry_run:
                print("🧪 DRY RUN MODE - No changes will be made")
            
            # Get current version and calculate new version
            self.get_current_version()
            self.calculate_new_version(bump_type)
            
            print(f"\n🔄 Version bump: {self.current_version} → {self.new_version}")
            
            if dry_run:
                print(f"📊 Would update:")
                print(f"   - app/version.py: {self.current_version} → {self.new_version}")
                print(f"   - README.md with new version and badges")
                print(f"   - CHANGELOG.md with new entry")
                print(f"   - PROJECT_STATUS.md with current version")
                print(f"   - Documentation files with version references")
                print(f"   - Git commit and tag v{self.new_version}")
                return
            
            # Perform updates
            self.update_version_file()
            self.update_readme()
            self.update_changelog()
            self.update_project_status()
            self.update_security_file()
            self.update_documentation_files()
            self.create_release_notes()
            
            # Git operations
            self.git_operations(skip_push=skip_push)
            
            # Generate GitHub release info
            release_info = self.generate_github_release_info()
            
            print(f"\n🎉 Version bump completed successfully!")
            print("=" * 60)
            print("📋 GITHUB RELEASE INFORMATION")
            print("=" * 60)
            print(f"\n🏷️ RELEASE TITLE:")
            print(release_info["title"])
            print(f"\n📝 RELEASE NOTES:")
            print(release_info["body"])
            print("=" * 60)
            print("\n✅ Ready to create GitHub release!")
            
        except Exception as e:
            print(f"❌ Version bump failed: {e}")
            sys.exit(1)


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python version_bump.py [major|minor|patch] [--dry-run] [--skip-push]")
        print("Example: python version_bump.py patch")
        print("Example: python version_bump.py minor --dry-run")
        print("Example: python version_bump.py patch --skip-push")
        sys.exit(1)

    bump_type = sys.argv[1].lower()
    if bump_type not in ["major", "minor", "patch"]:
        print("Error: bump_type must be 'major', 'minor', or 'patch'")
        sys.exit(1)

    # Check for flags
    dry_run = "--dry-run" in sys.argv
    skip_push = "--skip-push" in sys.argv

    # Initialize version bumper
    bumper = ProductionVersionBumper()
    bumper.run_version_bump(bump_type, dry_run=dry_run, skip_push=skip_push)


if __name__ == "__main__":
    main()
