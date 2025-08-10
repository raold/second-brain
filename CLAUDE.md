# Claude Memory - Second Brain Project

## 🔥 CONTEXT HOTSWAP - READ THESE FILES FIRST
1. **TODO.md** - Current tasks, blockers, project state (PRIMARY CONTEXT)
2. **DEVELOPMENT_CONTEXT.md** - Session history, decisions, user prefs
3. **This file (CLAUDE.md)** - Core principles, patterns, architecture

## 🎯 CURRENT STATE (as of August 9, 2025 - Session 6)
- **Version**: 4.2.3 - Production Ready with Security Patches
- **Test Status**: 55+ tests passing, comprehensive PostgreSQL validation
- **Architecture**: Single database (PostgreSQL) for vectors, text, and metadata
- **Performance**: 50% faster searches, 60% storage reduction
- **Documentation**: CLEANED - 17 focused docs (was 50+), removed 27K lines
- **Frontend**: NEW SvelteKit UI with real-time WebSocket updates
- **User Mode**: AUTONOMOUS - no confirmations needed
- **Active Branch**: main
- **Development**: Cross-platform with Google Drive sync
- **Next Action**: Check TODO.md for priority tasks

## ⚠️ IMPORTANT USER PREFERENCES
- **NO CO-AUTHOR LINES IN COMMITS** - User has requested multiple times
- **FULL AUTONOMOUS MODE** - NO PROMPTS, NO CONFIRMATIONS:
  - Auto-commit all changes without asking
  - Auto-push to remote without asking
  - Execute all operations immediately
  - User will interrupt or undo if needed
- **CROSS-PLATFORM DEVELOPMENT** - User works across multiple machines:
  - Windows, macOS, and Linux environments
  - Project synced via Google Drive for seamless access
  - "Developer kindness" for platform differences

## 🏗️ PROJECT ARCHITECTURE (v4.2.3)

### PostgreSQL-First Architecture
```
second-brain/
├── app/
│   ├── core/              # Infrastructure (logging, dependencies, env_manager)
│   ├── models/            # Pydantic models + synthesis stubs
│   ├── routes/            # API routes (v2_api_new.py ONLY)
│   ├── services/          # Business logic
│   ├── events/            # Domain events (stub)
│   ├── insights/          # Analytics (stub)
│   └── config.py          # Centralized configuration
├── tests/                 # Test suites
├── scripts/               # Essential scripts + startup/
├── docs/                  # CLEAN documentation (17 files)
│   ├── releases/          # Version history
│   ├── ui/                # HTML interfaces
│   ├── api/               # OpenAPI specs
│   └── *.md               # Core guides (simplified)
├── .env.example           # SINGLE env template
└── SECURITY.md           # Security guidelines
```

### Documentation Structure (Session 6 Cleanup)
**Before**: 50+ docs with massive redundancy (27,000+ lines)
**After**: 17 focused, developer-friendly guides
- Consolidated CI/CD: 16 docs → 1 simple guide
- Removed all v3 legacy documentation
- Simplified massive docs (2000+ lines → concise)
- Organized into proper subdirectories

### Key Technical Decisions
- **Unified Database**: PostgreSQL + pgvector replaces Qdrant/Redis
- **Single API**: Enhanced V2 API with new endpoints
- **Frontend**: SvelteKit + TypeScript + Tailwind CSS
- **Performance**: HNSW indexes for 95% faster vector search
- **Environment**: Single `.env.example` template, `.env` for local
- **Cipher Integration**: Memory layer connected via service

### Strict Database Constraint
- **NO sqlite, no qdrant, no redis, nothing else. ONLY postgressql**

[... rest of the existing content remains unchanged ...]