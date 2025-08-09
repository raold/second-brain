# Second Brain Release Notes

## Latest Release: v4.2.0

See [RELEASE_NOTES_V4.2.0.md](RELEASE_NOTES_V4.2.0.md) for the latest v4.2.0 release details.

---

## Previous Releases

### v4.1.0 - Application Factory & Graceful Degradation

**Release Date**: August 3, 2025  
**Status**: Superseded by v4.2.0

#### What's New in v4.1.0

1. **Application Factory Pattern** 
   - Clean separation between development, production, and testing environments
   - Better testability and configuration management
   - Proper startup/shutdown lifecycle handling

2. **Tagged Router Architecture**
   - Organized API structure with routes grouped by functionality
   - Enhanced Swagger UI with collapsible sections
   - Modular design for easy feature addition/removal

3. **Comprehensive Health Monitoring**
   - Full health checks at `/api/v2/health`
   - Kubernetes-ready probes (`/health/live` and `/health/ready`)
   - System metrics endpoint for resource monitoring

4. **Graceful Degradation System**
   - Service continues operating even when components fail
   - Automatic fallback: Semantic → Full-text → Keyword search
   - Four degradation levels: FULL → NO_VECTOR → NO_PERSISTENCE → READONLY

5. **SQLite Persistence with FTS5**
   - ACID compliance and concurrent access
   - Full-text search with ranking via FTS5
   - Auto-detection of best available storage backend

### v4.0.0 - Clean Architecture

**Release Date**: August 1, 2025  
**Status**: Superseded by v4.2.0

Major refactoring to clean, maintainable architecture.

---

For the latest features and improvements, please see [RELEASE_NOTES_V4.2.0.md](RELEASE_NOTES_V4.2.0.md).