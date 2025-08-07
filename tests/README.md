# Test Organization Guide

## Directory Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_*.py           # Individual module tests
│   ├── test_graph_query_parser.py
│   ├── test_graph_visualization.py
│   ├── test_knowledge_graph_builder.py
│   ├── test_reasoning_engine.py
│   ├── test_knowledge_graph_minimal.py
│   ├── test_reasoning_minimal.py
│   ├── test_visualization_minimal.py
│   └── test_visualization_simple.py
│
├── integration/            # Integration tests for API and features
│   ├── test_api_endpoints.py
│   ├── test_integration_features.py
│   ├── test_health.py
│   └── test_markdown_functionality.py
│
├── comprehensive/          # Comprehensive end-to-end tests
│   ├── test_bulk_operations_comprehensive.py
│   ├── test_importance_system.py
│   └── test_runner_comprehensive.py
│
├── performance/            # Performance and benchmark tests
│   └── test_performance_benchmark.py
│
├── manual/                 # Manual testing utilities
│   ├── debug_dashboard.py
│   ├── test_dashboard_api.py
│   ├── test_git_service.py
│   └── test_versions.py
│
├── conftest.py            # Shared pytest configuration
└── setup_test_env.py      # Test environment setup

```

## Running Tests

### All Tests
```bash
pytest tests/ -v
```

### Unit Tests Only
```bash
pytest tests/unit/ -v
```

### Integration Tests Only
```bash
pytest tests/integration/ -v
```

### Comprehensive Tests
```bash
pytest tests/comprehensive/ -v
```

### Performance Tests
```bash
pytest tests/performance/ -v
```

### Specific Feature Tests
```bash
# Knowledge Graph Tests
pytest tests/unit/test_knowledge_graph*.py -v

# Reasoning Engine Tests
pytest tests/unit/test_reasoning*.py -v

# Visualization Tests
pytest tests/unit/test_visualization*.py -v
```

## Test Categories

### Unit Tests (`/unit`)
- Fast, isolated tests for individual functions/classes
- No external dependencies (use mocks)
- Should run in < 1 second each
- Examples: algorithm tests, utility function tests

### Integration Tests (`/integration`)
- Test multiple components working together
- May use test database or mock services
- API endpoint tests
- Examples: API routes, service integration

### Comprehensive Tests (`/comprehensive`)
- End-to-end testing of complete features
- May take longer to run
- Test real workflows
- Examples: bulk operations, full system tests

### Performance Tests (`/performance`)
- Benchmark and performance validation
- Load testing
- Memory usage tests
- Examples: query performance, scaling tests

### Manual Tests (`/manual`)
- Scripts for manual testing and debugging
- Not run automatically in CI
- Developer utilities
- Examples: dashboard testing, service debugging