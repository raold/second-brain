"""Test configuration specifically for synthesis unit tests"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "test-key-mock")