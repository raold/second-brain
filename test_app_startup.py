#!/usr/bin/env python3
"""
Quick test to see if the app can start without errors
"""

import sys
import traceback
from datetime import datetime

def test_app_startup():
    """Test if the app can import and start."""
    
    print("🧪 Testing app startup...")
    print(f"⏰ Time: {datetime.now()}")
    print(f"🐍 Python: {sys.version}")
    
    try:
        print("\n1. Testing app import...")
        from app.app import app
        print("✅ App imported successfully")
        
        print("\n2. Testing V2 API import...")
        from app.routes.v2_api_new import router
        print("✅ V2 API router imported successfully")
        
        print("\n3. Testing dependencies...")
        from app.dependencies_new import get_current_user, verify_api_key
        print("✅ Dependencies imported successfully")
        
        print("\n4. Testing database...")
        from app.database_new import get_database
        print("✅ Database module imported successfully")
        
        print("\n5. Testing memory service...")
        from app.services.memory_service_new import MemoryService
        print("✅ Memory service imported successfully")
        
        print("\n6. Testing logging...")
        from app.utils.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("Test log message")
        print("✅ Logging works correctly")
        
        print("\n🎉 ALL IMPORTS SUCCESSFUL!")
        print("✅ The app should start without errors")
        
        return True
        
    except Exception as e:
        print(f"\n❌ IMPORT ERROR: {e}")
        print(f"📍 Error type: {type(e).__name__}")
        print(f"📄 Traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_app_startup()
    sys.exit(0 if success else 1)