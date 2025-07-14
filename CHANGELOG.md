# Changelog

## [1.2.0] - 2025-07-14

### Added
- Consolidated router functionality into single `app/router.py` file.
- Proper Pydantic v2 compatibility using `model_dump()` instead of deprecated `dict()`.
- Enhanced type hints and error handling in storage modules.

### Changed
- Removed duplicate `search_router.py` and consolidated all endpoints in `router.py`.
- Updated import paths to use correct `app.storage.*` module structure.
- Fixed `get_openai_embedding()` function signature to accept optional client parameter.
- Updated test mocks to use correct import paths for storage modules.
- Router now uses proper Pydantic models for request validation.

### Fixed
- Code duplication between routers causing maintenance issues.
- Import path inconsistencies between `app.qdrant_client` and `app.storage.qdrant_client`.
- Test failures due to incorrect mock patching paths.
- Pydantic v2 deprecation warnings for `dict()` method usage.
- Function signature mismatch in OpenAI embedding client.

### Upcoming
- Full mocking of external dependencies (OpenAI, Qdrant) in test suite.
- Metrics, monitoring, and rate limiting.

---

## [1.1.0] - 2025-07-14

### Added
- `.env.example` expanded with all configuration options including APP_ENV for CI/testing.
- `SECURITY.md` with policies and reporting guidelines.
- `CONTRIBUTING.md` with clear contribution and security disclosure guidelines.
- Docker Compose healthchecks for both API and Qdrant services.
- CI-safe defaults injected via `APP_ENV=ci` in docker-compose.yml.

### Changed
- Centralized configuration via `Config` class in `config.py`, including environment-aware defaults.
- `auth.py` now reads tokens from centralized config and logs invalid attempts.
- Token injection and mocking enabled in `test_ingest.py` and `test_search.py` for CI compatibility.
- Docker Compose networking explicitly configured to use a dedicated `app-net` bridge.

### Fixed
- Authentication failures in CI due to missing tokens.
- Broken Docker Compose volume paths and network configs.

### Upcoming
- Full mocking of external dependencies (OpenAI, Qdrant) in test suite.
- Metrics, monitoring, and rate limiting.

---

For previous versions, see repository commit history.