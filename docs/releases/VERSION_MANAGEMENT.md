# 🏷️ Second Brain Version Management System

## 📋 Overview

This document describes the centralized version management system for Second Brain. All version information, release processes, and git workflows are managed through a unified system.

## 🗂️ Centralized Configuration

### Core Files
- **`version_config.json`** - Central version database with all release information
- **`scripts/version_manager.py`** - Automated version management tool
- **`VERSION_MANAGEMENT.md`** - This documentation file

### Version Information Storage
For each version, we maintain:
1. **Version Number** (semantic versioning)
2. **Changes** (detailed list of improvements)
3. **Release Notes** (comprehensive documentation)
4. **Release Title** (descriptive name)
5. **Commit Message** (standardized format)
6. **PR Testing** (if applicable)
7. **Git Commands** (automated workflow)

## 🚀 Release Process

### Current Workflow: `testing -> main -> release`

#### Phase 1: Development (testing branch)
```bash
# Check current status
python scripts/version_manager.py status

# Prepare release 
python scripts/version_manager.py prepare 2.4.2
```

#### Phase 2: Testing & PR
```bash
# Generated commands (from version_manager.py):
git add .
git commit -m "Release v2.4.2: Architecture cleanup and dependency optimization"
git push origin testing

# Create PR for review
gh pr create --title "Release v2.4.2" --body "See RELEASE_NOTES_v2.4.2.md" --base main --head testing
```

#### Phase 3: Release (after PR approval)
```bash
# After PR merge:
git checkout main
git pull origin main
git tag -a v2.4.2 -m "Release v2.4.2: Architecture Cleanup & Optimization"
git push origin v2.4.2

# Optional GitHub Release
gh release create v2.4.2 --title "Second Brain v2.4.2" --notes-file docs/releases/RELEASE_NOTES_v2.4.2.md
```

## 📊 Current Version Status

### Version Hierarchy
- **Stable Release**: v2.4.1 (main branch, production-ready)
- **Development**: v2.4.2 (testing branch, staging)
- **Next Planned**: v2.5.0 (advanced PostgreSQL optimizations)

### File Synchronization
The version manager automatically updates:
- ✅ `app/version.py` - Application version
- ✅ `README.md` - Project documentation
- ✅ `CHANGELOG.md` - Release history
- ✅ `PROJECT_STATUS.md` - Current status
- ✅ `docs/releases/README.md` - Release index

## 🛠️ Version Manager Commands

### Virtual Environment Setup
```bash
# Activate virtual environment
.venv\Scripts\activate

# Check current status
python scripts\version_manager.py status

# Prepare release
python scripts\version_manager.py prepare 2.4.2
```

### Manual Process (if Python issues)
If the Python script has issues, you can follow the manual process:

1. **Check Current Version**
   - Review `version_config.json` for current stable vs development
   - Check `app/version.py` for app version
   - Verify `README.md` header version

2. **Update Version Files Manually**
   - `app/version.py`: Update `__version__`, `__version_info__`, `__release_date__`
   - `README.md`: Update title and architecture overview
   - `CHANGELOG.md`: Add new version entry
   - `PROJECT_STATUS.md`: Update version and status

3. **Create Release Notes**
   - Copy template from existing `RELEASE_NOTES_v*.md`
   - Update version number, date, and changes
   - Save as `docs/releases/RELEASE_NOTES_v{version}.md`

### Automated Commands
```bash
# Check status
python scripts\version_manager.py status

# Prepare release 
python scripts\version_manager.py prepare 2.4.2

## 📋 Version Configuration Structure

### Example Version Entry
```json
{
  "2.4.2": {
    "status": "development",
    "title": "Architecture Cleanup & Optimization",
    "focus": "Cleanup", 
    "release_date": "2025-07-18",
    "changes": [
      "Complete Qdrant dependency removal",
      "Project organization cleanup",
      "Documentation consistency improvements"
    ],
    "commit_message": "Release v2.4.2: Architecture cleanup and dependency optimization",
    "pr_testing": true,
    "git_workflow": "testing->main->release"
  }
}
```

### Git Workflow Types
- **`testing->main->release`**: Full PR review process
- **`direct->main`**: Direct merge for minor updates
- **`hotfix->main`**: Emergency fixes

## 🔄 Standard Release Workflows

### Major Release (x.0.0)
1. Create feature branch from `testing`
2. Develop and test features
3. Update version configuration
4. Run version manager: `prepare <version>`
5. Create PR: `testing -> main`
6. Review, test, and merge
7. Create git tag and GitHub release

### Minor Release (x.y.0)
1. Work in `testing` branch
2. Update version configuration  
3. Run version manager: `prepare <version>`
4. Create PR: `testing -> main`
5. Review and merge
6. Create git tag

### Patch Release (x.y.z)
1. Quick fixes in `testing` branch
2. Update version configuration
3. Run version manager: `prepare <version>`
4. Direct merge or PR based on complexity
5. Create git tag

## 📚 Documentation Standards

### Release Notes Structure
Each version gets:
- **`RELEASE_NOTES_v{version}.md`** - Comprehensive release documentation
- **CHANGELOG.md entry** - Brief summary for history
- **Migration guide** (if needed) - Upgrade instructions

### Version References
- **Development docs**: Reference development version (v2.4.2)
- **Stable references**: Reference stable version (v2.4.1)
- **Historical docs**: Maintain version history accurately

## ✅ Release Checklist

### Pre-Release
- [ ] All tests pass (`pytest -v`)
- [ ] Documentation links work
- [ ] Version consistency across files
- [ ] Release notes complete and accurate
- [ ] Migration guide created (if needed)

### Release Process
- [ ] Version configuration updated
- [ ] Version manager executed successfully
- [ ] All files updated automatically
- [ ] Git commands generated and reviewed
- [ ] PR created and reviewed (if applicable)

### Post-Release
- [ ] Git tag created and pushed
- [ ] GitHub release published (optional)
- [ ] Documentation updated
- [ ] Version marked as "stable" in config

## 🚀 Future Enhancements

### v2.5.0 Planning
- Enhanced version automation
- Automated testing integration
- Performance benchmark tracking
- Deployment automation

### Version Manager Features
- Automated dependency updates
- Version compatibility checking
- Release note generation from git commits
- Integration with CI/CD pipelines

---

**Last Updated**: v2.4.2 - July 18, 2025  
**Maintained By**: Second Brain Development Team  
**Review Schedule**: Updated with each release
