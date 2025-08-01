"""
Test configuration and utilities for comprehensive test suite
Provides test markers, fixtures, and utilities for V2 API, StructuredDataExtractor, and WebSocket tests
"""

import os
import pytest
from typing import Generator, List, Dict, Any

# Test markers configuration
pytest_plugins = []


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: Unit tests - fast, isolated tests with no external dependencies"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests - test component interactions"
    )
    config.addinivalue_line(
        "markers", "performance: Performance tests - measure speed, memory, and throughput"
    )
    config.addinivalue_line("markers", "websocket: WebSocket-specific tests")
    config.addinivalue_line("markers", "extraction: StructuredDataExtractor-specific tests")
    config.addinivalue_line("markers", "api_v2: V2 API endpoint tests")
    config.addinivalue_line("markers", "security: Security-focused tests")
    config.addinivalue_line("markers", "edge_case: Edge case and error condition tests")
    config.addinivalue_line("markers", "load: Load testing - high volume operations")
    config.addinivalue_line("markers", "slow: Slower tests that may take more time")


class TestDataGenerator:
    """Generate test data for various scenarios"""

    @staticmethod
    def generate_structured_content(complexity: str = "medium") -> str:
        """Generate structured content for testing extraction"""
        if complexity == "simple":
            return """
            Name: Simple Test
            Value: 42
            Status: Active
            """

        elif complexity == "medium":
            return """
            # Project Documentation
            
            **Project Name**: Test Project
            **Status**: In Progress
            **Priority**: High
            **Budget**: $50,000
            
            ## Tasks
            - Design phase
            - Development phase
            - Testing phase
            - Deployment
            
            | Phase | Duration | Resources |
            |-------|----------|-----------|
            | Design | 2 weeks | 2 people |
            | Dev | 6 weeks | 4 people |
            | Test | 2 weeks | 2 people |
            
            ```python
            def process_data():
                return "processed"
            ```
            
            Contact: test@example.com
            Website: https://example.com
            """

        else:  # complex
            return """
            # Comprehensive System Analysis Report
            
            **Report ID**: RPT-2024-001
            **Generated**: 2024-01-15T10:30:00Z
            **Author**: System Administrator
            **Classification**: Internal
            **Version**: 2.1.0
            **Status**: Final
            **Distribution**: Engineering Team
            **Next Review**: 2024-04-15
            
            ## Executive Summary
            
            This comprehensive analysis covers system performance, security posture,
            and operational metrics for Q1 2024. Key findings indicate strong
            performance across all major subsystems with identified areas for optimization.
            
            ## System Metrics
            
            ### Performance Indicators
            - CPU Utilization: 68% average
            - Memory Usage: 72% average  
            - Disk I/O: 45% average
            - Network Throughput: 2.3 Gbps average
            - Response Time: 150ms p95
            - Error Rate: 0.02%
            
            ### Availability Metrics
            - Uptime: 99.97%
            - MTBF: 720 hours
            - MTTR: 12 minutes
            - Planned Downtime: 99.5%
            - Unplanned Outages: 2
            
            ## Component Analysis
            
            ### Database Performance
            | Metric | Current | Target | Status |
            |--------|---------|--------|--------|
            | Query Response | 45ms | <50ms | ✓ |
            | Throughput | 15K TPS | 10K TPS | ✓ |
            | Connection Pool | 85% | <90% | ✓ |
            | Cache Hit Rate | 94% | >90% | ✓ |
            | Storage Used | 2.1TB | <3TB | ✓ |
            
            ### API Performance
            | Endpoint | Requests/sec | Avg Response | Error Rate |
            |----------|--------------|--------------|------------|
            | /api/v1/users | 450 | 85ms | 0.01% |
            | /api/v1/data | 320 | 120ms | 0.03% |
            | /api/v2/metrics | 180 | 95ms | 0.00% |
            | /api/v2/health | 50 | 25ms | 0.00% |
            
            ## Security Assessment
            
            ### Vulnerability Scan Results
            - Critical: 0
            - High: 2 (patched)
            - Medium: 5 (scheduled)
            - Low: 12 (monitoring)
            - Info: 28
            
            ### Access Control Audit
            - Users with admin access: 8
            - Service accounts: 15
            - API keys active: 142
            - Failed login attempts: 23 (last 24h)
            - Suspicious activities: 0
            
            ## Infrastructure Details
            
            ### Server Configuration
            ```yaml
            production:
              app_servers:
                count: 6
                cpu: "16 cores"
                memory: "64GB"
                storage: "1TB NVMe"
              
              database:
                type: "PostgreSQL 15"
                cpu: "32 cores"  
                memory: "128GB"
                storage: "4TB NVMe"
                replicas: 2
              
              cache:
                type: "Redis"
                memory: "32GB"
                persistence: "RDB + AOF"
                cluster_nodes: 3
            ```
            
            ### Monitoring Stack
            ```python
            # Monitoring configuration
            import prometheus_client
            from datadog import DogStatsdClient
            
            class SystemMonitor:
                def __init__(self):
                    self.metrics = prometheus_client.CollectorRegistry()
                    self.dogstatsd = DogStatsdClient()
                
                def record_metric(self, name, value, tags=None):
                    # Prometheus metric
                    gauge = prometheus_client.Gauge(
                        name, 'System metric', registry=self.metrics
                    )
                    gauge.set(value)
                    
                    # DataDog metric
                    self.dogstatsd.gauge(name, value, tags=tags)
                
                def health_check(self):
                    checks = {
                        'database': self.check_database(),
                        'cache': self.check_cache(),
                        'storage': self.check_storage(),
                        'network': self.check_network()
                    }
                    return all(checks.values())
            ```
            
            ## Recommendations
            
            ### Immediate Actions (1-2 weeks)
            1. **Scale API Infrastructure**
               - Add 2 additional API servers
               - Implement connection pooling optimization
               - Configure auto-scaling policies
            
            2. **Security Hardening**
               - Rotate API keys older than 90 days
               - Enable MFA for admin accounts
               - Update WAF rules for new threat patterns
            
            3. **Performance Optimization**
               - Optimize slow database queries (>500ms)
               - Implement Redis cluster sharding
               - Enable CDN for static assets
            
            ### Medium-term Goals (1-3 months)
            1. **Monitoring Enhancement**
               - Deploy distributed tracing
               - Implement anomaly detection
               - Create custom dashboards for each team
            
            2. **Disaster Recovery**
               - Test backup restoration procedures
               - Document runbook procedures
               - Conduct DR simulation exercise
            
            ### Long-term Strategy (3-12 months)
            1. **Architecture Evolution**
               - Migrate to microservices architecture
               - Implement event-driven patterns
               - Adopt Infrastructure as Code
            
            2. **Automation Initiatives**
               - Automated deployment pipelines
               - Self-healing infrastructure
               - Predictive scaling algorithms
            
            ## Appendices
            
            ### Contact Information
            - Technical Lead: tech.lead@company.com
            - Operations Manager: ops.manager@company.com
            - Security Officer: security@company.com
            - Project Manager: pm@company.com
            
            ### Resources
            - Documentation: https://docs.company.com/systems
            - Monitoring Dashboard: https://monitoring.company.com
            - Incident Response: https://incidents.company.com
            - Change Management: https://changes.company.com
            
            ### Compliance
            - SOC 2 Type II: Compliant
            - GDPR: Compliant
            - HIPAA: Not Applicable
            - PCI DSS: Compliant (Level 2)
            - ISO 27001: In Progress
            
            ---
            
            **Document Classification**: Internal Use Only
            **Retention Period**: 2 years
            **Review Cycle**: Quarterly
            **Distribution List**: Engineering, Operations, Security, Management
            """

    @staticmethod
    def generate_websocket_messages(count: int = 10) -> List[Dict[str, Any]]:
        """Generate WebSocket test messages"""
        messages = []
        for i in range(count):
            messages.append(
                {
                    "type": f"test.message.{i}",
                    "id": f"msg-{i:03d}",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "data": {
                        "sequence": i,
                        "content": f"Test message {i}",
                        "priority": "normal" if i % 3 != 0 else "high",
                    },
                }
            )
        return messages

    @staticmethod
    def generate_api_test_data() -> Dict[str, Any]:
        """Generate test data for API endpoints"""
        return {
            "memory_content": {
                "simple": "Simple memory content for testing",
                "structured": """
                Project: API Test
                Status: Testing
                
                Features:
                - Authentication
                - Rate limiting
                - Error handling
                """,
                "complex": TestDataGenerator.generate_structured_content("complex"),
            },
            "invalid_inputs": [
                "",  # Empty string
                None,  # None value
                "x" * 100000,  # Very long string
                "<script>alert('xss')</script>",  # XSS attempt
                "'; DROP TABLE memories; --",  # SQL injection attempt
                "\x00\x01\x02",  # Binary data
                "🚀" * 1000,  # Unicode spam
            ],
            "valid_memory_types": [
                "note",
                "task",
                "meeting",
                "document",
                "idea",
                "reference",
                "project",
                "research",
                "learning",
            ],
            "valid_tags": [
                ["test"],
                ["api", "v2"],
                ["performance", "load"],
                ["security", "validation"],
                ["integration", "e2e"],
            ],
        }


class TestUtilities:
    """Utility functions for tests"""

    @staticmethod
    def assert_response_structure(response_data: Dict[str, Any], required_fields: List[str]):
        """Assert that response has required structure"""
        for field in required_fields:
            assert field in response_data, f"Missing required field: {field}"

    @staticmethod
    def assert_performance_metrics(
        duration: float, memory_delta: float, max_duration: float = 5.0, max_memory: float = 50.0
    ):
        """Assert performance metrics are within acceptable ranges"""
        assert duration < max_duration, f"Duration {duration:.3f}s exceeds limit {max_duration}s"
        assert (
            memory_delta < max_memory
        ), f"Memory delta {memory_delta:.1f}MB exceeds limit {max_memory}MB"

    @staticmethod
    def validate_extraction_results(extracted_data, min_elements: int = 1):
        """Validate structured data extraction results"""
        total_elements = (
            len(extracted_data.key_value_pairs)
            + len(extracted_data.lists)
            + len(extracted_data.tables)
            + len(extracted_data.code_snippets)
        )
        assert (
            total_elements >= min_elements
        ), f"Expected at least {min_elements} extracted elements"

    @staticmethod
    def create_mock_websocket_responses():
        """Create mock WebSocket responses for testing"""
        return {
            "connection_success": {
                "type": "connection",
                "status": "connected",
                "timestamp": "2024-01-15T10:30:00Z",
            },
            "subscription_ack": {
                "type": "subscription",
                "status": "acknowledged",
                "event_types": ["memory.created", "memory.updated"],
            },
            "heartbeat": {"type": "heartbeat", "timestamp": "2024-01-15T10:30:00Z"},
            "error": {
                "type": "error",
                "code": "INVALID_MESSAGE",
                "message": "Invalid message format",
            },
        }


# Environment-specific configurations
TEST_ENVIRONMENTS = {
    "unit": {
        "database": "mock",
        "external_apis": "mock",
        "performance_limits": {"response_time": 1.0, "memory_usage": 25.0},
    },
    "integration": {
        "database": "test_db",
        "external_apis": "sandbox",
        "performance_limits": {"response_time": 3.0, "memory_usage": 100.0},
    },
    "performance": {
        "database": "test_db",
        "external_apis": "mock",
        "performance_limits": {"response_time": 5.0, "memory_usage": 200.0},
        "load_parameters": {"concurrent_requests": 50, "test_duration": 30, "ramp_up_time": 5},
    },
}


def get_test_config(test_type: str = "unit") -> Dict[str, Any]:
    """Get configuration for specific test type"""
    return TEST_ENVIRONMENTS.get(test_type, TEST_ENVIRONMENTS["unit"])


# Pytest fixtures that can be imported by test files
@pytest.fixture
def test_data_generator():
    """Provide test data generator instance"""
    return TestDataGenerator()


@pytest.fixture
def test_utilities():
    """Provide test utilities instance"""
    return TestUtilities()


@pytest.fixture
def performance_config():
    """Provide performance test configuration"""
    return get_test_config("performance")


@pytest.fixture
def integration_config():
    """Provide integration test configuration"""
    return get_test_config("integration")


# Test collection and execution utilities
def collect_test_metrics() -> Dict[str, Any]:
    """Collect metrics about test execution"""
    return {
        "test_files_created": [
            "test_v2_unified_api.py",
            "test_structured_data_extractor.py",
            "test_websocket_functionality.py",
            "test_v2_api_integration.py",
            "test_comprehensive_performance.py",
        ],
        "test_categories": {
            "unit": 100,  # Estimated test count
            "integration": 30,
            "performance": 20,
            "security": 15,
            "edge_cases": 25,
        },
        "coverage_targets": {
            "v2_api": 95,
            "structured_extractor": 90,
            "websocket": 85,
            "integration": 80,
        },
    }


if __name__ == "__main__":
    # Print test configuration summary
    print("Test Configuration Summary")
    print("=" * 40)

    metrics = collect_test_metrics()
    print(f"Test files: {len(metrics['test_files_created'])}")
    print(f"Total estimated tests: {sum(metrics['test_categories'].values())}")
    print(f"Coverage targets: {metrics['coverage_targets']}")

    print("\nTest Categories:")
    for category, count in metrics["test_categories"].items():
        print(f"  {category}: {count} tests")

    print("\nTest Files Created:")
    for test_file in metrics["test_files_created"]:
        print(f"  tests/{test_file}")
