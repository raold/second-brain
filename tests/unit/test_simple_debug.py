"""Simple test to verify pytest discovery is working."""

import pytest

pytestmark = pytest.mark.unit


def test_simple():
    """A simple test to verify pytest is working."""
    assert True


class TestSimple:
    def test_method(self):
        """A simple test method."""
        assert 2 + 2 == 4
