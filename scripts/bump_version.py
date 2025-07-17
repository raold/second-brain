#!/usr/bin/env python3
"""
Version Bumping Script for Second Brain
Automatically updates version numbers across all files
"""

import re
import sys
from datetime import datetime
from pathlib import Path

VERSION_FILES = [
    "app/version.py",
    "app/__init__.py", 
    "README.md",
    "CHANGELOG.md"
]

def get_current_version():
    """Get current version from version.py"""
    version_file = Path("app/version.py")
    if version_file.exists():
        content = version_file.read_text()
        match = re.search(r'__version__ = "([^"]+)"', content)
        if match:
            return match.group(1)
    return "0.0.0"

def increment_version(current_version, bump_type):
    """Increment version based on bump type"""
    major, minor, patch = map(int, current_version.split('.'))
    
    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")

def update_version_file(new_version):
    """Update app/version.py with new version"""
    version_file = Path("app/version.py")
    content = version_file.read_text()
    
    # Update version
    content = re.sub(
        r'__version__ = "[^"]+"',
        f'__version__ = "{new_version}"',
        content
    )
    
    # Update version_info tuple
    major, minor, patch = map(int, new_version.split('.'))
    content = re.sub(
        r'__version_info__ = \([^)]+\)',
        f'__version_info__ = ({major}, {minor}, {patch})',
        content
    )
    
    # Update release date
    today = datetime.now().strftime("%Y-%m-%d")
    content = re.sub(
        r'__release_date__ = "[^"]+"',
        f'__release_date__ = "{today}"',
        content
    )
    
    version_file.write_text(content)
    print(f"✅ Updated {version_file}")

def update_changelog(new_version):
    """Add new version entry to CHANGELOG.md"""
    changelog_file = Path("CHANGELOG.md")
    content = changelog_file.read_text()
    
    today = datetime.now().strftime("%Y-%m-%d")
    new_entry = f"""## [{new_version}] - {today}

### **Added**
- 

### **Changed**
- 

### **Fixed**
- 

---

"""
    
    # Insert after the header
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('## ['):
            lines.insert(i, new_entry)
            break
    
    changelog_file.write_text('\n'.join(lines))
    print(f"✅ Updated {changelog_file}")

def update_readme(new_version):
    """Update version badge in README.md"""
    readme_file = Path("README.md")
    if readme_file.exists():
        try:
            content = readme_file.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # Try with different encoding if UTF-8 fails
            content = readme_file.read_text(encoding='latin-1')
        
        # Update version badge
        content = re.sub(
            r'# Second Brain v[^-]+ -',
            f'# Second Brain v{new_version} -',
            content
        )
        
        readme_file.write_text(content, encoding='utf-8')
        print(f"✅ Updated {readme_file}")

def main():
    """Main version bumping logic"""
    if len(sys.argv) != 2:
        print("Usage: python bump_version.py <major|minor|patch>")
        sys.exit(1)
    
    bump_type = sys.argv[1].lower()
    if bump_type not in ["major", "minor", "patch"]:
        print("Error: bump_type must be major, minor, or patch")
        sys.exit(1)
    
    current_version = get_current_version()
    new_version = increment_version(current_version, bump_type)
    
    print(f"🔄 Bumping version from {current_version} to {new_version}")
    
    # Update all files
    update_version_file(new_version)
    update_changelog(new_version)
    update_readme(new_version)
    
    print(f"✅ Version bumped to {new_version}")
    print(f"📝 Next steps:")
    print(f"   1. Update CHANGELOG.md with release notes")
    print(f"   2. Commit changes: git commit -am 'chore: bump version to {new_version}'")
    print(f"   3. Tag release: git tag v{new_version}")
    print(f"   4. Push changes: git push origin main --tags")

if __name__ == "__main__":
    main()
