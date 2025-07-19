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

### Current Workflow: `develop -> testing -> main -> release`

Our three-branch strategy provides comprehensive quality gates:

- **develop**: Experimental features and active development
- **testing**: Feature integration and release preparation
- **main**: Production-ready code with automated deployment
- **tags**: Immutable release versions

#### Phase 1: Development (develop branch)
```bash
# Check current status
python scripts/version_manager.py status

# Active development on develop branch
git checkout develop
git pull origin develop

# Make changes and test frequently
python scripts/version_manager.py test unit integration

# Commit and push to develop
git commit -m "feat: new search algorithm"
git push origin develop
```

#### Phase 2: Integration (develop -> testing)
```bash
# Integrate features for release preparation
git checkout testing
git pull origin testing
git merge develop

# Run full test suite
python scripts/version_manager.py test all
git push origin testing

# Prepare release version
python scripts/version_manager.py prepare 2.4.3
```

#### Phase 3: Testing & PR (testing -> main)
```bash
# Generated commands from version_manager.py:
git add .
git commit -m "Release v2.4.3: Quality Excellence & Dashboard Enhancements"
git push origin testing

# Create PR for review (with automatic CI/CD testing)
gh pr create --title "Release v2.4.3" --body "See RELEASE_NOTES_v2.4.3.md" --base main --head testing
```

#### Phase 4: Release (after PR approval)
```bash
# After PR merge:
git checkout main
git pull origin main
git tag -a v2.4.3 -m "Release v2.4.3: Quality Excellence & Dashboard Enhancements"
git push origin v2.4.3

# Optional GitHub Release
gh release create v2.4.3 --title "Second Brain v2.4.3" --notes-file docs/releases/RELEASE_NOTES_v2.4.3.md
```

## 📊 Current Version Status

### Version Hierarchy
- **Stable Release**: v2.4.2 (main branch, production-ready)
- **Testing Phase**: v2.4.3 (testing branch, 85% complete - Quality Excellence)
- **Current Focus**: Quality Excellence milestone completion (28 days remaining)
- **Next Planned**: v2.4.4 (Production Readiness) → v2.5.0 (Memory Architecture Foundation)

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
# Check current status
python scripts\version_manager.py status

# Prepare release 
python scripts\version_manager.py prepare 2.4.3

## 📋 Version Configuration Structure

### Example Version Entry
```json
{
  "2.4.3": {
    "status": "testing",
    "title": "Quality Excellence & Dashboard Enhancements",
    "focus": "Quality Excellence", 
    "release_date": "2025-07-18",
    "progress_percent": 85,
    "days_remaining": 28,
    "changes": [
      "Comprehensive dashboard system with paradigm shift roadmaps",
      "Enhanced testing infrastructure (81 tests passing)",
      "Documentation completeness improvements (API: 92%, User: 85%)",
      "Performance optimization and monitoring",
      "Security baseline implementation"
    ],
    "commit_message": "Release v2.4.3: Quality Excellence & Dashboard Enhancements",
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
- **Testing docs**: Reference testing version (v2.4.3 - Quality Excellence)
- **Stable references**: Reference stable version (v2.4.2)
- **Historical docs**: Maintain version history accurately
- **Dashboard metrics**: Real-time progress tracking (85% completion)

## ✅ Release Checklist

### Pre-Release (v2.4.3 Quality Excellence - 90% Complete)
- [x] Dashboard system implemented with paradigm shift roadmaps
- [x] Testing infrastructure enhanced (209 tests passing, 34% coverage)
- [x] **MASSIVE test coverage expansion (32% → 34%, +152 new tests)**
- [x] **Memory Aging Algorithms: 0% → 77% coverage (29 comprehensive tests)**
- [x] **Zero-coverage module elimination (6 major modules now covered)**
- [x] Documentation improvements (API: 92%, User guides: 85%, Developer: 88%)
- [ ] Test coverage expansion continuation (target: 90%)
- [ ] Docker CI/CD optimization completion
- [ ] Security baseline implementation finalization
- [ ] Performance optimization validation
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

### v2.4.4 Planning (Production Readiness)
- Enhanced deployment automation
- Performance benchmark tracking
- Production monitoring integration
- Security hardening completion

### v2.5.0 Planning (Memory Architecture Foundation)
- Advanced PostgreSQL optimizations
- Memory architecture paradigm shift implementation
- Enhanced version automation
- Next-generation retrieval systems

### Version Manager Features
- Automated dependency updates
- Version compatibility checking
- Release note generation from git commits
- Integration with CI/CD pipelines
- Real-time dashboard progress tracking

---

**Last Updated**: v2.4.3 Quality Excellence - July 18, 2025  
**Maintained By**: Second Brain Development Team  
**Review Schedule**: Updated with each release  
**Current Milestone**: Quality Excellence (90% complete, 25 days remaining)  
**Latest Achievement**: Massive test coverage expansion (+152 tests, 32% → 34%)
