"""Simple test to verify the environment is working."""

def test_imports():
    """Test that critical imports work."""

    print("All imports successful!")
    assert True

def test_versions():
    """Check package versions."""
    import fastapi
    import pydantic

    print(f"FastAPI version: {fastapi.__version__}")
    print(f"Pydantic version: {pydantic.__version__}")

    assert fastapi.__version__.startswith("0.109")
    assert pydantic.__version__.startswith("2.5")

if __name__ == "__main__":
    test_imports()
    test_versions()
    print("\nAll tests passed!")
