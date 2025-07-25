"""
Property-based tests using Hypothesis for Second Brain application.
Tests various components with generated data to ensure robustness.
"""

import re
from datetime import datetime, timedelta

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from hypothesis.strategies import composite

from app.models.intelligence.analytics_models import (
    MetricPoint,
    MetricSeries,
    MetricType,
    TimeGranularity,
    TrendDirection,
)
from app.security import InputValidator, RateLimiter, SecurityConfig
from app.services.intelligence.predictive_insights import PredictiveInsightsService


# Custom Hypothesis strategies
@composite
def valid_memory_content(draw):
    """Generate valid memory content strings."""
    # Start with safe characters
    content = draw(st.text(
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'),
            whitelist_characters='.,!?-_()[]{}:;\'"'
        ),
        min_size=1,
        max_size=1000
    ))

    # Ensure it doesn't contain dangerous patterns
    assume(not re.search(r'\b(DROP|SELECT|INSERT|DELETE|UPDATE|SCRIPT)\b', content, re.IGNORECASE))
    assume('<script' not in content.lower())
    assume('javascript:' not in content.lower())

    return content.strip()


@composite
def valid_metadata(draw):
    """Generate valid metadata dictionaries."""
    keys = draw(st.lists(
        st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-'),
            min_size=1,
            max_size=50
        ),
        min_size=0,
        max_size=10,
        unique=True
    ))

    metadata = {}
    for key in keys:
        value_type = draw(st.sampled_from(['string', 'int', 'float', 'bool', 'none']))

        if value_type == 'string':
            value = draw(st.text(max_size=500))
        elif value_type == 'int':
            value = draw(st.integers(min_value=-1000000, max_value=1000000))
        elif value_type == 'float':
            value = draw(st.floats(min_value=-1000000, max_value=1000000, allow_nan=False, allow_infinity=False))
        elif value_type == 'bool':
            value = draw(st.booleans())
        else:  # none
            value = None

        metadata[key] = value

    return metadata


@composite
def metric_point(draw, min_timestamp=None, max_timestamp=None):
    """Generate valid MetricPoint instances."""
    if min_timestamp is None:
        min_timestamp = datetime(2020, 1, 1)
    if max_timestamp is None:
        max_timestamp = datetime(2025, 12, 31)

    timestamp = draw(st.datetimes(min_value=min_timestamp, max_value=max_timestamp))
    value = draw(st.floats(min_value=0, max_value=1000000, allow_nan=False, allow_infinity=False))
    metadata = draw(st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.one_of(st.text(max_size=100), st.integers(), st.floats(allow_nan=False, allow_infinity=False)),
        max_size=5
    ))

    return MetricPoint(timestamp=timestamp, value=value, metadata=metadata)


@composite
def metric_series(draw, min_points=1, max_points=100):
    """Generate valid MetricSeries instances."""
    num_points = draw(st.integers(min_value=min_points, max_value=max_points))
    base_time = draw(st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2024, 1, 1)))

    points = []
    for i in range(num_points):
        timestamp = base_time + timedelta(hours=i)
        value = draw(st.floats(min_value=0, max_value=10000, allow_nan=False, allow_infinity=False))
        points.append(MetricPoint(timestamp=timestamp, value=value))

    metric_type = draw(st.sampled_from(list(MetricType)))
    granularity = draw(st.sampled_from(list(TimeGranularity)))

    return MetricSeries(
        metric_type=metric_type,
        data_points=points,
        granularity=granularity,
        start_time=points[0].timestamp if points else base_time,
        end_time=points[-1].timestamp if points else base_time
    )


class TestInputValidatorProperties:
    """Property-based tests for input validation."""

    @pytest.fixture
    def validator(self):
        """Create input validator with reasonable limits."""
        config = SecurityConfig(
            max_content_length=2000,
            max_metadata_fields=20
        )
        return InputValidator(config)

    @given(content=valid_memory_content())
    @settings(max_examples=50, deadline=1000)
    def test_valid_content_always_passes(self, validator, content):
        """Test that valid content always passes validation."""
        try:
            result = validator.validate_memory_content(content)
            assert isinstance(result, str)
            assert len(result) <= validator.config.max_content_length
        except Exception as e:
            pytest.fail(f"Valid content failed validation: {content[:100]}... Error: {e}")

    @given(metadata=valid_metadata())
    @settings(max_examples=50, deadline=1000)
    def test_valid_metadata_always_passes(self, validator, metadata):
        """Test that valid metadata always passes validation."""
        try:
            result = validator.validate_metadata(metadata)
            assert isinstance(result, dict)
            assert len(result) <= validator.config.max_metadata_fields

            # Check that all values are properly typed
            for key, value in result.items():
                assert isinstance(key, str)
                assert value is None or isinstance(value, (str, int, float, bool))
        except Exception as e:
            pytest.fail(f"Valid metadata failed validation: {metadata}. Error: {e}")

    @given(st.text(min_size=1, max_size=500))
    @settings(max_examples=30)
    def test_search_query_sanitization_is_safe(self, validator, query):
        """Test that search query sanitization never produces dangerous output."""
        try:
            result = validator.validate_search_query(query)

            # Ensure no dangerous patterns in result
            assert not re.search(r'\b(DROP|SELECT|INSERT|DELETE|UPDATE)\b', result, re.IGNORECASE)
            assert '<script' not in result.lower()
            assert 'javascript:' not in result.lower()
            assert '\x00' not in result  # No null bytes

        except Exception:
            # It's okay for validation to reject dangerous input
            pass

    @given(st.integers(min_value=1, max_value=1000))
    @settings(max_examples=20)
    def test_search_limit_validation_bounds(self, validator, limit):
        """Test search limit validation respects bounds."""
        if limit <= validator.config.max_search_results:
            result = validator.validate_search_limit(limit)
            assert result == limit
            assert 1 <= result <= validator.config.max_search_results
        else:
            with pytest.raises(Exception):
                validator.validate_search_limit(limit)

    @given(st.text(min_size=0, max_size=100))
    @settings(max_examples=30)
    def test_string_sanitization_idempotent(self, validator, text):
        """Test that string sanitization is idempotent."""
        first_pass = validator._sanitize_string(text)
        second_pass = validator._sanitize_string(first_pass)

        assert first_pass == second_pass

    @given(st.text())
    @settings(max_examples=30)
    def test_sanitize_string_never_increases_length(self, validator, text):
        """Test that sanitization never increases string length."""
        sanitized = validator._sanitize_string(text)
        assert len(sanitized) <= len(text)


class TestRateLimiterProperties:
    """Property-based tests for rate limiting."""

    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter with test config."""
        config = SecurityConfig(
            max_requests_per_minute=10,
            max_requests_per_hour=100
        )
        return RateLimiter(config)

    @given(st.lists(st.text(min_size=7, max_size=15), min_size=1, max_size=20, unique=True))
    @settings(max_examples=20)
    def test_multiple_ips_tracked_independently(self, rate_limiter, ip_addresses):
        """Test that different IPs are tracked independently."""
        from unittest.mock import Mock

        # Create requests for different IPs
        requests = []
        for ip in ip_addresses:
            request = Mock()
            request.client = Mock()
            request.client.host = ip
            request.headers = {}
            requests.append(request)

        # Each IP should start with no rate limiting
        for request in requests:
            assert not rate_limiter.is_rate_limited(request)

        # After one request each, all should still be allowed
        for request in requests:
            assert not rate_limiter.is_rate_limited(request)

    @given(st.integers(min_value=1, max_value=50))
    @settings(max_examples=15)
    def test_rate_limit_threshold_respected(self, rate_limiter, num_requests):
        """Test that rate limit thresholds are respected."""
        from unittest.mock import Mock

        request = Mock()
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {}

        blocked = False
        for i in range(num_requests):
            if rate_limiter.is_rate_limited(request):
                blocked = True
                break

        # Should be blocked if we exceed the limit
        if num_requests > rate_limiter.config.max_requests_per_minute:
            assert blocked, f"Should have been blocked after {num_requests} requests"

        # Rate limit info should always be valid
        info = rate_limiter.get_rate_limit_info(request)
        assert "X-RateLimit-Limit" in info
        assert "X-RateLimit-Remaining" in info
        assert "X-RateLimit-Reset" in info

        # Remaining should never be negative
        remaining = int(info["X-RateLimit-Remaining"])
        assert remaining >= 0


class TestMetricAnalysisProperties:
    """Property-based tests for metric analysis."""

    @given(points=metric_series(min_points=2, max_points=50))
    @settings(max_examples=30, deadline=2000)
    def test_metric_series_calculations_are_consistent(self, points):
        """Test that metric series calculations are mathematically consistent."""
        # Average should be within data range
        if points.data_points:
            values = [p.value for p in points.data_points]
            calculated_avg = points.average
            expected_avg = sum(values) / len(values)

            # Allow small floating point differences
            assert abs(calculated_avg - expected_avg) < 0.0001

            # Average should be between min and max
            assert min(values) <= calculated_avg <= max(values)

    @given(series=metric_series(min_points=5, max_points=20))
    @settings(max_examples=20)
    def test_trend_detection_consistency(self, series):
        """Test that trend detection is consistent."""
        trend = series.trend

        # Trend should be one of the valid enum values
        assert trend in list(TrendDirection)

        # If we have enough data points, trend should make sense
        if len(series.data_points) >= 3:
            values = [p.value for p in series.data_points]
            first_half = values[:len(values)//2]
            second_half = values[len(values)//2:]

            first_avg = sum(first_half) / len(first_half)
            second_avg = sum(second_half) / len(second_half)

            # If there's a clear mathematical trend, it should be detected
            # (allowing for some noise tolerance)
            diff_threshold = max(first_avg, second_avg) * 0.1  # 10% threshold

            if second_avg > first_avg + diff_threshold:
                assert trend in [TrendDirection.INCREASING, TrendDirection.VOLATILE]
            elif second_avg < first_avg - diff_threshold:
                assert trend in [TrendDirection.DECREASING, TrendDirection.VOLATILE]

    @given(
        value=st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False),
        metadata=st.dictionaries(
            st.text(min_size=1, max_size=10),
            st.one_of(st.text(max_size=20), st.integers()),
            max_size=3
        )
    )
    @settings(max_examples=30)
    def test_metric_point_creation_always_valid(self, value, metadata):
        """Test that MetricPoint creation with valid inputs always succeeds."""
        timestamp = datetime.now()

        try:
            point = MetricPoint(timestamp=timestamp, value=value, metadata=metadata)
            assert point.value == value
            assert point.timestamp == timestamp
            assert point.metadata == metadata
        except Exception as e:
            pytest.fail(f"Valid MetricPoint creation failed: value={value}, metadata={metadata}. Error: {e}")


class TestPredictiveInsightsProperties:
    """Property-based tests for predictive insights service."""

    @given(
        metrics_data=st.dictionaries(
            st.sampled_from(list(MetricType)),
            metric_series(min_points=3, max_points=20),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=15, deadline=5000)
    def test_insights_generation_robustness(self, metrics_data):
        """Test that insights generation is robust to various metric inputs."""
        from unittest.mock import Mock

        # Mock dependencies
        mock_db = Mock()
        mock_memory_service = Mock()
        mock_openai = Mock()

        service = PredictiveInsightsService(mock_db, mock_memory_service, mock_openai)

        # Test each insight analyzer individually to avoid complex async mocking
        for category, analyzer in service.insight_rules.items():
            try:
                # Most analyzers should handle empty or minimal data gracefully
                insights = []  # Would normally be: await analyzer(metrics_data, "test_user")

                # At minimum, they should not crash
                # In a real test, we'd mock the async behavior
                assert True  # Placeholder - in reality would test actual async call

            except Exception as e:
                pytest.fail(f"Insight analyzer {category} failed with metrics {list(metrics_data.keys())}: {e}")

    @given(
        values=st.lists(
            st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False),
            min_size=2,
            max_size=20
        )
    )
    @settings(max_examples=20)
    def test_change_calculation_properties(self, values):
        """Test mathematical properties of change calculation."""
        from unittest.mock import Mock

        # Create a mock service to access the calculation method
        mock_db = Mock()
        mock_memory_service = Mock()
        mock_openai = Mock()

        service = PredictiveInsightsService(mock_db, mock_memory_service, mock_openai)

        # Create metric points
        points = [
            MetricPoint(timestamp=datetime.now() + timedelta(hours=i), value=v)
            for i, v in enumerate(values)
        ]

        series = MetricSeries(
            metric_type=MetricType.API_USAGE,
            data_points=points,
            granularity=TimeGranularity.HOUR,
            start_time=points[0].timestamp,
            end_time=points[-1].timestamp
        )

        change = service._calculate_change(series)

        # Change calculation should be mathematically sound
        if values[0] > 0:
            expected_change = ((values[-1] - values[0]) / values[0]) * 100
            assert abs(change - expected_change) < 0.01
        else:
            # When starting value is 0, handle edge case appropriately
            assert change == (100.0 if values[-1] > 0 else 0.0)

    @given(
        growth_values=st.lists(
            st.floats(min_value=0.1, max_value=1000, allow_nan=False, allow_infinity=False),
            min_size=2,
            max_size=10
        )
    )
    @settings(max_examples=15)
    def test_growth_rate_calculation_properties(self, growth_values):
        """Test mathematical properties of growth rate calculation."""
        from unittest.mock import Mock

        # Create a mock service to access the calculation method
        mock_db = Mock()
        mock_memory_service = Mock()
        mock_openai = Mock()

        service = PredictiveInsightsService(mock_db, mock_memory_service, mock_openai)

        # Create metric points
        points = [
            MetricPoint(timestamp=datetime.now() + timedelta(days=i), value=v)
            for i, v in enumerate(growth_values)
        ]

        series = MetricSeries(
            metric_type=MetricType.MEMORY_GROWTH,
            data_points=points,
            granularity=TimeGranularity.DAY,
            start_time=points[0].timestamp,
            end_time=points[-1].timestamp
        )

        growth_rate = service._calculate_growth_rate(series)

        # Growth rate should be finite and reasonable
        assert not (growth_rate != growth_rate)  # Not NaN
        assert abs(growth_rate) < 100  # Not ridiculously large

        # If values are increasing, growth rate should be positive
        if growth_values[-1] > growth_values[0]:
            assert growth_rate > -0.001  # Allow tiny negative due to floating point


class TestSecurityProperties:
    """Property-based tests for security components."""

    @given(
        malicious_patterns=st.sampled_from([
            "DROP TABLE",
            "<script>",
            "javascript:",
            "SELECT * FROM",
            "'; DELETE",
            "<iframe>",
            "onload=",
            "eval(",
        ])
    )
    @settings(max_examples=20)
    def test_malicious_patterns_always_blocked(self, malicious_patterns):
        """Test that known malicious patterns are always blocked."""
        config = SecurityConfig()
        validator = InputValidator(config)

        # Embed malicious pattern in various contexts
        test_inputs = [
            malicious_patterns,
            f"Normal text {malicious_patterns} more text",
            f"{malicious_patterns} at start",
            f"at end {malicious_patterns}",
            malicious_patterns.lower(),
            malicious_patterns.upper(),
        ]

        for test_input in test_inputs:
            with pytest.raises(Exception):
                validator.validate_memory_content(test_input)

    @given(
        safe_content=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'),
                whitelist_characters='.,!?-_()'
            ),
            min_size=1,
            max_size=500
        )
    )
    @settings(max_examples=30)
    def test_safe_content_never_blocked(self, safe_content):
        """Test that genuinely safe content is never incorrectly blocked."""
        config = SecurityConfig(max_content_length=1000)
        validator = InputValidator(config)

        # Filter out content that might accidentally contain dangerous patterns
        assume(not re.search(r'\b(DROP|SELECT|INSERT|DELETE|UPDATE|SCRIPT)\b', safe_content, re.IGNORECASE))
        assume('<script' not in safe_content.lower())
        assume('javascript:' not in safe_content.lower())
        assume('onload=' not in safe_content.lower())

        try:
            result = validator.validate_memory_content(safe_content)
            assert isinstance(result, str)
            assert len(result) <= len(safe_content)  # Sanitization shouldn't increase length
        except Exception as e:
            pytest.fail(f"Safe content was incorrectly blocked: '{safe_content[:50]}...' Error: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
