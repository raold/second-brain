# Version Bump Scripts

Automated version bumping system for Second Brain project.

## 🚀 Quick Start

### 1. Setup (One-time)
```bash
# Run the setup script
python scripts/setup_versionbump.py
```

### 2. Usage

#### Windows (PowerShell)
```powershell
# From project root
scripts\VERSIONBUMP.ps1 patch
scripts\VERSIONBUMP.ps1 minor
scripts\VERSIONBUMP.ps1 major
```

#### Windows (Command Prompt)
```cmd
# From project root
scripts\VERSIONBUMP.bat patch
scripts\VERSIONBUMP.bat minor
scripts\VERSIONBUMP.bat major
```

#### Direct Python
```bash
# From project root
python scripts/version_bump.py patch
python scripts/version_bump.py minor
python scripts/version_bump.py major
```

## 🔧 What It Does

The version bump script performs a complete release workflow:

### 1. **Version Updates**
- ✅ Updates `app/version.py` with new version and release date
- ✅ Updates `README.md` with version references
- ✅ Updates `CHANGELOG.md` with new release entry
- ✅ Recursively updates `docs/` files with version references

### 2. **Git Operations**
- ✅ `git add -A` - Stages all changes
- ✅ `git commit -m "..."` - Commits with auto-generated message
- ✅ `git push origin main` - Pushes to remote
- ✅ `git tag -a v{version}` - Creates annotated tag
- ✅ `git push origin v{version}` - Pushes tag

### 3. **Release Information**
- ✅ Generates GitHub release title
- ✅ Generates copy-paste ready release notes in Markdown
- ✅ Provides all information needed for GitHub release

## 📋 Script Files

| File | Purpose |
|------|---------|
| `version_bump.py` | Main Python script with full logic |
| `VERSIONBUMP.ps1` | PowerShell wrapper for Windows |
| `VERSIONBUMP.bat` | Batch file wrapper for Windows |
| `versionbump_command.py` | Command handler for VERSIONBUMP alias |
| `setup_versionbump.py` | Setup script for system-wide commands |

## 🎯 Version Types

### Patch (1.0.0 → 1.0.1)
```bash
VERSIONBUMP patch
```
- Bug fixes
- Minor improvements
- Documentation updates

### Minor (1.0.0 → 1.1.0)
```bash
VERSIONBUMP minor
```
- New features
- Enhancements
- Non-breaking changes

### Major (1.0.0 → 2.0.0)
```bash
VERSIONBUMP major
```
- Breaking changes
- Major architecture updates
- Significant new features

## 📝 Example Output

```
🚀 Starting version bump: patch
📁 Working directory: c:\Users\dro\second-brain

🔄 Version bump: 2.1.1 → 2.1.2

✅ Updated version.py: 2.1.1 → 2.1.2
✅ Updated README.md with version 2.1.2
✅ Updated CHANGELOG.md with version 2.1.2
✅ Updated 3 files in docs/:
   - docs/ARCHITECTURE.md
   - docs/DEPLOYMENT.md
   - docs/USAGE.md

✅ Added all changes to git
✅ Committed changes with message
   🔧 Release v2.1.2
✅ Pushed changes to origin/main
✅ Created and pushed tag v2.1.2

🎉 Version bump completed successfully!

============================================================
📋 GITHUB RELEASE INFORMATION
============================================================

🏷️ RELEASE TITLE:
🔧 Second Brain v2.1.2 - Bug Fix Release

📝 RELEASE NOTES (Copy-paste ready):
----------------------------------------
## 🔧 Second Brain v2.1.2

**Release Date:** 2025-07-17  
**Version Type:** Patch  
**Previous Version:** v2.1.1

### 📋 What's Changed

This release includes the following updates:

- **Version Bump**: Updated from v2.1.1 to v2.1.2
- **Documentation**: Updated README.md and documentation files
- **Changelog**: Added comprehensive release notes
- **Stability**: Continued production-ready quality

...
----------------------------------------

✅ Ready to create GitHub release!
```

## 🔄 Workflow Integration

### Typical Release Workflow

1. **Development** - Work on features/fixes
2. **Testing** - Run test suite (`pytest --cov=app`)
3. **Version Bump** - Run `VERSIONBUMP [type]`
4. **GitHub Release** - Copy-paste generated release notes
5. **Verification** - Confirm tag and release are live

### CI/CD Integration

The scripts work with existing CI/CD pipelines and don't interfere with automated testing or deployment processes.

## ⚙️ Configuration

All configuration is automatic based on:
- Current version in `app/version.py`
- Git repository state
- Project structure conventions

No manual configuration required!

## 🛠️ Troubleshooting

### Common Issues

1. **Git not clean**: Ensure working directory is clean before version bump
2. **Permission denied**: Make sure you have push access to the repository
3. **Python path**: Ensure Python is in your PATH and script is run from project root
4. **Version format**: Current version must be in semantic version format (x.y.z)

### Debug Mode

Add debug output by modifying the script or running with verbose Git output:

```bash
# Enable Git verbose output
git config --global push.default simple
git config --global core.autocrlf true
```

## 🤝 Contributing

To improve the version bump system:

1. Edit `scripts/version_bump.py` for core functionality
2. Update wrapper scripts for platform-specific improvements
3. Test on your platform before submitting changes
4. Update this README with any new features

---

**Happy version bumping!** 🚀📦✨
