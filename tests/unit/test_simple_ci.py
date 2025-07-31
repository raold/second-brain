"""
Simple test to verify CI/CD pipeline works
"""

def test_basic_import():
    """Test that we can import basic modules"""
    import os
    import sys
    assert os is not None
    assert sys is not None

def test_basic_math():
    """Test basic math operations"""
    assert 2 + 2 == 4
    assert 10 * 5 == 50
    assert 100 / 4 == 25

def test_basic_string():
    """Test basic string operations"""
    assert "hello".upper() == "HELLO"
    assert "WORLD".lower() == "world"
    assert "hello world".title() == "Hello World"

def test_basic_list():
    """Test basic list operations"""
    lst = [1, 2, 3, 4, 5]
    assert len(lst) == 5
    assert sum(lst) == 15
    assert max(lst) == 5
    assert min(lst) == 1
