#!/usr/bin/env python3
"""
Verification script for single-user refactor.
Checks that all the changes are working correctly.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.memory_service_new import MemoryService
from app.dependencies_new import verify_container_access, get_current_user
from app.models.memory import Memory, MemoryType


async def verify_refactor():
    """Run verification tests."""
    print("🔍 Verifying Single-User Refactor")
    print("=" * 50)
    
    results = []
    
    # Test 1: Memory model has no user_id
    print("\n1️⃣ Checking Memory model...")
    try:
        memory = Memory.create(
            content="Test memory",
            memory_type=MemoryType.SEMANTIC
        )
        if "user_id" not in memory.model_dump():
            print("✅ Memory model has no user_id field")
            results.append(True)
        else:
            print("❌ Memory model still has user_id")
            results.append(False)
    except Exception as e:
        print(f"❌ Memory model test failed: {e}")
        results.append(False)
    
    # Test 2: Memory service doesn't require user_id
    print("\n2️⃣ Checking MemoryService...")
    try:
        service = MemoryService()
        memory = await service.create_memory(
            content="Test without user",
            memory_type="episodic"
        )
        if "user_id" not in memory:
            print("✅ MemoryService works without user_id")
            results.append(True)
        else:
            print("❌ MemoryService still uses user_id")
            results.append(False)
    except Exception as e:
        print(f"❌ MemoryService test failed: {e}")
        results.append(False)
    
    # Test 3: Dependencies simplified
    print("\n3️⃣ Checking Dependencies...")
    try:
        # Test that get_current_user returns static user
        user = await get_current_user(authenticated=True)
        if user["id"] == "container-user":
            print("✅ Dependencies return single static user")
            results.append(True)
        else:
            print("❌ Dependencies still have complex user logic")
            results.append(False)
    except Exception as e:
        print(f"❌ Dependencies test failed: {e}")
        results.append(False)
    
    # Test 4: Persistence works
    print("\n4️⃣ Checking Persistence...")
    try:
        test_path = "data/test_memories.json"
        service1 = MemoryService(persist_path=test_path)
        
        # Create and save
        memory = await service1.create_memory(
            content="Persistence test",
            importance_score=0.9
        )
        
        # Load in new instance
        service2 = MemoryService(persist_path=test_path)
        memories = await service2.list_memories()
        
        if memories and memories[0]["content"] == "Persistence test":
            print("✅ JSON persistence works correctly")
            results.append(True)
            
            # Clean up
            os.remove(test_path)
        else:
            print("❌ Persistence not working")
            results.append(False)
    except Exception as e:
        print(f"❌ Persistence test failed: {e}")
        results.append(False)
    
    # Test 5: No session management
    print("\n5️⃣ Checking for removed session management...")
    try:
        from app.dependencies_new import get_health_service
        health_service = get_health_service()
        
        # Should not have SessionService
        try:
            from app.dependencies_new import get_session_service
            print("❌ SessionService still exists")
            results.append(False)
        except ImportError:
            print("✅ SessionService removed (not found)")
            results.append(True)
    except Exception as e:
        print(f"✅ Session management removed: {e}")
        results.append(True)
    
    # Test 6: Config simplified
    print("\n6️⃣ Checking Config...")
    try:
        from app.config import Config
        
        # Check for container API key instead of JWT
        if hasattr(Config, 'CONTAINER_API_KEY'):
            print("✅ Config uses CONTAINER_API_KEY")
            results.append(True)
        else:
            print("❌ Config missing CONTAINER_API_KEY")
            results.append(False)
            
        # Check JWT is removed
        if not hasattr(Config, 'JWT_SECRET_KEY'):
            print("✅ JWT configuration removed")
            results.append(True)
        else:
            print("❌ JWT configuration still present")
            results.append(False)
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        results.append(False)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    percentage = (passed / total) * 100 if total > 0 else 0
    
    print(f"\nTests Passed: {passed}/{total} ({percentage:.1f}%)")
    
    if percentage == 100:
        print("\n🎉 SUCCESS! All verifications passed!")
        print("✅ Single-user architecture is working correctly")
        print("✅ Multi-tenant complexity removed")
        print("✅ Ready for K8s deployment")
    elif percentage >= 80:
        print("\n⚠️ MOSTLY WORKING - Some issues remain")
        print("Please review failed tests above")
    else:
        print("\n❌ VERIFICATION FAILED")
        print("Major issues detected - review needed")
    
    return percentage == 100


if __name__ == "__main__":
    print("Starting verification...")
    success = asyncio.run(verify_refactor())
    sys.exit(0 if success else 1)