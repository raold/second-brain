# Second Brain - Version Management System

## Semantic Versioning Strategy

### Format: `MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]`

### Version Types:

#### **MAJOR (X.0.0)**
- **Breaking Changes**: API incompatibilities, database schema changes
- **Architectural Changes**: Complete system refactors
- **Dependencies**: Major framework/library changes
- **Examples**: 1.0.0 → 2.0.0 (current refactor)

#### **MINOR (X.Y.0)**
- **New Features**: New endpoints, major functionality
- **Performance**: Significant optimizations
- **Database**: New tables/columns (backward compatible)
- **Examples**: 2.0.0 → 2.1.0 (new search features)

#### **PATCH (X.Y.Z)**
- **Bug Fixes**: Error corrections, stability improvements
- **Documentation**: Updates, clarifications
- **Dependencies**: Minor updates, security patches
- **Examples**: 2.0.0 → 2.0.1 (bug fixes)

#### **PRERELEASE (X.Y.Z-alpha/beta/rc)**
- **Alpha**: Internal testing, unstable features
- **Beta**: External testing, feature complete
- **RC**: Release candidate, final testing
- **Examples**: 2.1.0-alpha.1, 2.1.0-beta.1, 2.1.0-rc.1

#### **BUILD METADATA (+BUILD)**
- **Commit SHA**: For traceability
- **Build Info**: CI/CD pipeline identifiers
- **Examples**: 2.0.1+abc1234, 2.1.0-beta.1+build.123

## Version Bump Rules

### **Commit Message → Version Bump**
```
feat: new feature → MINOR bump
fix: bug fix → PATCH bump
docs: documentation → PATCH bump
style: formatting → PATCH bump
refactor: code cleanup → PATCH bump
test: testing → PATCH bump
chore: maintenance → PATCH bump
perf: performance → MINOR bump
BREAKING CHANGE: → MAJOR bump
```

### **Current Version**: `2.0.0`
### **Next Planned**: `2.0.1` (documentation and test improvements)

## Release Cadence

### **Schedule**
- **Major Releases**: Quarterly (Q1, Q2, Q3, Q4)
- **Minor Releases**: Monthly
- **Patch Releases**: As needed (bugs, security)
- **Prerelease**: Weekly during development

### **Branch Strategy**
- **main**: Production-ready code
- **develop**: Integration branch for features
- **feature/***: Individual feature development
- **release/***: Release preparation
- **hotfix/***: Emergency fixes

## Version Tracking

### **Files to Update**
- `CHANGELOG.md`: Version history
- `app/version.py`: Primary version definition
- `app/__init__.py`: Application version
- `README.md`: Version badges
- `docker-compose.yml`: Image tags

### **Automation**
- **CI/CD**: Automatic version detection
- **Git Tags**: Version tagging on release
- **Docker**: Version-tagged images
- **GitHub Releases**: Automatic release notes
