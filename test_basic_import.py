#!/usr/bin/env python3
"""
Basic import test to see if the app can even be imported
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("🔍 Testing basic imports...")
print(f"Python version: {sys.version}")
print(f"Project root: {project_root}")

try:
    print("\n1. Testing app.app import...")
    from app.app import app
    print(f"✅ SUCCESS: FastAPI app imported")
    print(f"   App title: {app.title}")
    print(f"   App version: {app.version}")
    print(f"   Routes: {len(app.routes)}")
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n2. Testing basic models...")
    from app.models.memory import Memory, MemoryCreate
    print(f"✅ SUCCESS: Memory models imported")
except Exception as e:
    print(f"❌ FAILED: {e}")

try:
    print("\n3. Testing database...")
    from app.database import get_database
    db = get_database()
    print(f"✅ SUCCESS: Database instance: {type(db)}")
except Exception as e:
    print(f"❌ FAILED: {e}")

try:
    print("\n4. Testing service factory...")
    from app.core.dependencies import get_memory_service
    service = get_memory_service()
    print(f"✅ SUCCESS: Memory service: {type(service)}")
except Exception as e:
    print(f"❌ FAILED: {e}")

print("\n✅ Basic import test complete!")