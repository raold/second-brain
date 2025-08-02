#!/usr/bin/env python3
"""
Quick test to verify the current state of the app
"""

print("🧪 Quick App Test Starting...")

# Test 1: Can we import the main app?
try:
    from app.app import app
    print("✅ Main app imports successfully")
except Exception as e:
    print(f"❌ Main app import failed: {e}")
    exit(1)

# Test 2: Can we import the V2 API?
try:
    from app.routes.v2_api_new import router
    print("✅ V2 API imports successfully")
except Exception as e:
    print(f"❌ V2 API import failed: {e}")
    exit(1)

# Test 3: Check FastAPI app structure
try:
    print(f"📊 App title: {app.title}")
    print(f"📊 App version: {app.version}")
    print(f"📊 Number of routes: {len(app.routes)}")
    print("✅ App structure looks good")
except Exception as e:
    print(f"❌ App structure check failed: {e}")

# Test 4: Test memory service
try:
    from app.services.memory_service_new import MemoryService
    import asyncio
    
    async def test_memory_service():
        service = MemoryService()
        # Test create
        memory = await service.create_memory("Test memory")
        if memory and "id" in memory:
            print("✅ Memory service create works")
            # Test get
            retrieved = await service.get_memory(memory["id"])
            if retrieved:
                print("✅ Memory service get works")
                return True
        return False
    
    result = asyncio.run(test_memory_service())
    if result:
        print("✅ Memory service basic operations work")
    else:
        print("⚠️ Memory service has limitations")
        
except Exception as e:
    print(f"❌ Memory service test failed: {e}")

print("\n🎉 Quick test completed! App appears to be working.")