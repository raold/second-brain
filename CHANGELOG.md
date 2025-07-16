## [v1.4.0] - 2025-07-15
### Added
- Test suite now fully mocks OpenAI embedding and Qdrant vector DB for all integration tests. No real API keys or running Qdrant instance are required for tests. This is achieved by:
  - Patching `get_openai_embedding` to return a fixed vector in all test files.
  - Patching `QdrantClient.upsert` and `QdrantClient.search` in tests that require Qdrant operations, returning controlled results.
  - Patching `to_uuid` to return a string for test compatibility with Qdrant's expected ID type.
- This approach ensures tests are fast, reliable, and isolated from external dependencies.
- Version history is now tracked for each record in Qdrant. Every upsert appends the current model/embedding version and timestamp to a `version_history` list in metadata.
- New API endpoint `/records/{id}/version-history` returns the full version history for a given record ID.
- Minimal web UI at `/ui/version_history.html` to view current model versions and version history for any record.
- Prometheus metrics integration: `/metrics` endpoint exposes API metrics for Prometheus scraping.
- Sentry error monitoring: If `SENTRY_DSN` is set, errors and traces are sent to Sentry.
- Docs updated to describe metrics and monitoring setup.
- Hybrid search: `/search` endpoint now supports metadata filtering (model_version, embedding_model, type, timestamp range) combined with vector similarity using Qdrant's hybrid search API.
- Ranking pipeline: `/ranked-search` endpoint returns results with weighted scores (vector + metadata relevance) and explanations for each result.
- All ranking and hybrid search logic is fully covered by tests, including timestamp range handling and score explanations.

## [1.3.0] - 2025-07-14
### Added
- **Advanced Version History UI:**
  - Web UI at `/ui/version_history.html` now lists records with search/filter, shows metadata, and allows clicking to view version history.
- **/records API Endpoint:**
  - List records with filtering and pagination. Supports filtering by type and note content.
- **Prometheus Metrics Integration:**
  - `/metrics` endpoint exposes API metrics (request count, latency, errors) for Prometheus scraping.
- **Sentry Error Monitoring:**
  - If `SENTRY_DSN` is set, errors and traces are sent to Sentry for monitoring.
- **Testing & Mocking:**
  - All new endpoints and integrations are covered by tests.
  - Mocking patterns for Qdrant, OpenAI, Prometheus, and Sentry are documented in `docs/TESTING.md`.
- **Documentation:**
  - All new features and integrations are fully documented in the README, ARCHITECTURE.md, and TESTING.md.

### Changed
- Improved UI/UX for version history and record management.
- Enhanced documentation and cross-linking for all features.

### Fixed
- Ensured all endpoints and integrations are robustly tested and isolated from external dependencies in CI. 

## [1.2.4] - 2025-07-14
### Added
- Prometheus metrics and Sentry error monitoring integration. 

## [1.2.3] - 2025-07-14
### Added
- Version history tracking for model/embedding versions per record in Qdrant.
- `/records/{id}/version-history` API endpoint.
- Simple web UI for version history display. 

## [1.2.2] - 2025-07-14
### Added
- New `docs/TESTING.md` with a comprehensive guide to running, extending, and mocking tests (OpenAI, Qdrant) for fast, reliable integration tests.
- All documentation files now cross-link to each other, including the new Testing Guide, ensuring no missing or broken links.
- README, USAGE, ARCHITECTURE, CONTRIBUTING, SECURITY, CI_CACHING, and ENVIRONMENT_VARIABLES docs updated to reference the Testing Guide and clarify the mocking/testing approach.

### Changed
- Documentation reviewed and improved for clarity, completeness, and cross-referencing. 
