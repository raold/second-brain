# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.0] - 2025-08-01

### Added
- **Unified V2 API** - Combined V1 robustness with V2 features into a single API
- **WebSocket Support** - Real-time updates for metrics, memory creation, and system status
- **Comprehensive Test Suite** - 190+ tests covering unit, integration, and performance scenarios
- **API Documentation** - Complete OpenAPI 3.0 specification and usage examples
- **Dependency Validation** - Script to monitor and validate project dependencies
- **Live Dashboard Updates** - WebSocket integration in development dashboard

### Changed
- Migrated development dashboard from V1 to V2 unified API
- Enhanced StructuredDataExtractor with better error handling and logging
- Standardized dependency versions across all requirements files
- Improved API response times and memory usage

### Fixed
- Critical security vulnerabilities (FastAPI CVE-2024-24762, Redis CVE-2023-28858)
- StructuredDataExtractor bugs with proper error handling
- Missing websockets package for WebSocket client support
- Type inconsistencies in code extraction (lines field)

### Security
- Patched FastAPI ReDoS vulnerability by upgrading to 0.109.1
- Patched Redis race condition vulnerability by upgrading to 5.0.3
- Added comprehensive input validation across all endpoints

## [3.0.0] - 2025-07-27

### Added
- Clean Architecture implementation with Domain/Application/Infrastructure layers
- Docker-first development environment
- Enterprise-ready features and scalability
- Comprehensive testing framework
- Production deployment guides

### Changed
- Complete architectural overhaul from v2.x
- New directory structure following clean architecture principles
- Enhanced security and performance optimizations

### Removed
- Legacy v2.x architecture and dependencies
- Old monolithic structure