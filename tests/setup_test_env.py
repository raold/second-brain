"""
Test environment setup for Second Brain.
Fixes common testing issues.
"""
import os
import tempfile
from pathlib import Path

def setup_test_environment():
    """Setup test environment variables and directories."""
    
    # Set test environment variables
    test_env_vars = {
        "OPENAI_API_KEY": "test-key-sk-test123456789",
        "API_TOKENS": "test-token-123",
        "QDRANT_HOST": "localhost",
        "QDRANT_PORT": "6333",
        "QDRANT_COLLECTION": "test_collection",
        "APP_ENV": "testing",
        "DATA_DIR": "./test_data",
        "POSTGRES_URL": "sqlite:///test.db",  # Use SQLite for testing
    }
    
    for key, value in test_env_vars.items():
        if key not in os.environ:
            os.environ[key] = value
    
    # Create test data directory
    test_data_dir = Path("./test_data")
    test_data_dir.mkdir(exist_ok=True)
    
    print("✅ Test environment setup complete")
    return test_env_vars

def cleanup_test_environment():
    """Clean up test environment."""
    import shutil
    
    # Clean up test data
    test_dirs = ["./test_data", "./test_logs"]
    for test_dir in test_dirs:
        if Path(test_dir).exists():
            shutil.rmtree(test_dir)
    
    print("✅ Test environment cleanup complete")

if __name__ == "__main__":
    setup_test_environment()
