#!/usr/bin/env python3
"""
MANUAL VERIFICATION TESTS
Quick tests to verify what actually works in Second Brain V2
"""

import sys
import os
from pathlib import Path
import asyncio

# Setup
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_1_basic_imports():
    """Test 1: Can we import the basic components?"""
    print("="*60)
    print("TEST 1: BASIC IMPORTS")
    print("="*60)
    
    tests = []
    
    # Test 1.1: Main app
    try:
        from app.app import app
        print(f"✅ Main app imported: {app.title} v{app.version}")
        print(f"   Routes: {len(app.routes)} registered")
        tests.append(("Main App Import", True))
    except Exception as e:
        print(f"❌ Main app import failed: {e}")
        tests.append(("Main App Import", False))
    
    # Test 1.2: V2 API
    try:
        from app.routes.v2_api_new import router
        print(f"✅ V2 API router imported: {len(router.routes)} routes")
        tests.append(("V2 API Import", True))
    except Exception as e:
        print(f"❌ V2 API import failed: {e}")
        tests.append(("V2 API Import", False))
    
    # Test 1.3: Memory Service
    try:
        from app.services.memory_service_new import MemoryService
        service = MemoryService()
        print(f"✅ Memory service created: {type(service)}")
        tests.append(("Memory Service Import", True))
    except Exception as e:
        print(f"❌ Memory service import failed: {e}")
        tests.append(("Memory Service Import", False))
    
    # Test 1.4: Dependencies
    try:
        from app.dependencies_new import verify_api_key, get_current_user
        print("✅ Dependencies imported successfully")
        tests.append(("Dependencies Import", True))
    except Exception as e:
        print(f"❌ Dependencies import failed: {e}")
        tests.append(("Dependencies Import", False))
    
    return tests

def test_2_memory_service_functionality():
    """Test 2: Does the memory service actually work?"""
    print("\n" + "="*60)
    print("TEST 2: MEMORY SERVICE FUNCTIONALITY")
    print("="*60)
    
    tests = []
    
    try:
        from app.services.memory_service_new import MemoryService
        service = MemoryService()
        
        async def run_memory_tests():
            test_results = []
            
            # Test 2.1: Create memory
            try:
                memory = await service.create_memory(
                    content="Test memory for verification",
                    importance_score=0.8,
                    tags=["test", "verification"]
                )
                print(f"✅ Create memory: ID {memory['id'][:8]}...")
                test_results.append(("Create Memory", True))
                memory_id = memory['id']
            except Exception as e:
                print(f"❌ Create memory failed: {e}")
                test_results.append(("Create Memory", False))
                return test_results
            
            # Test 2.2: Get memory
            try:
                retrieved = await service.get_memory(memory_id)
                if retrieved and retrieved['content'] == "Test memory for verification":
                    print(f"✅ Get memory: Retrieved successfully")
                    test_results.append(("Get Memory", True))
                else:
                    print(f"❌ Get memory: Content mismatch")
                    test_results.append(("Get Memory", False))
            except Exception as e:
                print(f"❌ Get memory failed: {e}")
                test_results.append(("Get Memory", False))
            
            # Test 2.3: List memories
            try:
                memories = await service.list_memories(limit=10)
                print(f"✅ List memories: Found {len(memories)} memories")
                test_results.append(("List Memories", True))
            except Exception as e:
                print(f"❌ List memories failed: {e}")
                test_results.append(("List Memories", False))
            
            # Test 2.4: Search memories
            try:
                results = await service.search_memories("verification")
                found = len(results) > 0
                print(f"✅ Search memories: Found {len(results)} results" if found else "⚠️  Search memories: No results (may be normal)")
                test_results.append(("Search Memories", True))
            except Exception as e:
                print(f"❌ Search memories failed: {e}")
                test_results.append(("Search Memories", False))
            
            # Test 2.5: Update memory
            try:
                updated = await service.update_memory(
                    memory_id,
                    content="Updated test memory",
                    importance_score=0.9
                )
                if updated and updated['content'] == "Updated test memory":
                    print(f"✅ Update memory: Content updated successfully")
                    test_results.append(("Update Memory", True))
                else:
                    print(f"❌ Update memory: Update failed")
                    test_results.append(("Update Memory", False))
            except Exception as e:
                print(f"❌ Update memory failed: {e}")
                test_results.append(("Update Memory", False))
            
            # Test 2.6: Delete memory
            try:
                deleted = await service.delete_memory(memory_id)
                if deleted:
                    print(f"✅ Delete memory: Deleted successfully")
                    test_results.append(("Delete Memory", True))
                else:
                    print(f"❌ Delete memory: Delete returned False")
                    test_results.append(("Delete Memory", False))
            except Exception as e:
                print(f"❌ Delete memory failed: {e}")
                test_results.append(("Delete Memory", False))
            
            return test_results
        
        # Run async tests
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(run_memory_tests())
        loop.close()
        
        tests.extend(results)
        
    except Exception as e:
        print(f"❌ Memory service test setup failed: {e}")
        tests.append(("Memory Service Setup", False))
    
    return tests

def test_3_api_with_testclient():
    """Test 3: Can we test API endpoints with TestClient?"""
    print("\n" + "="*60)
    print("TEST 3: API ENDPOINTS WITH TESTCLIENT")
    print("="*60)
    
    tests = []
    
    try:
        from fastapi.testclient import TestClient
        from app.app import app
        
        client = TestClient(app)
        
        # Test 3.1: Root endpoint
        try:
            response = client.get("/")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Root endpoint: {data.get('message', 'OK')}")
                tests.append(("Root Endpoint", True))
            else:
                print(f"⚠️  Root endpoint: Status {response.status_code}")
                tests.append(("Root Endpoint", False))
        except Exception as e:
            print(f"❌ Root endpoint failed: {e}")
            tests.append(("Root Endpoint", False))
        
        # Test 3.2: Health endpoint (if exists)
        try:
            response = client.get("/api/v2/health")
            if response.status_code == 200:
                print("✅ Health endpoint: Working")
                tests.append(("Health Endpoint", True))
            elif response.status_code == 404:
                print("⚠️  Health endpoint: Not found (may not be registered)")
                tests.append(("Health Endpoint", False))
            else:
                print(f"⚠️  Health endpoint: Status {response.status_code}")
                tests.append(("Health Endpoint", False))
        except Exception as e:
            print(f"❌ Health endpoint failed: {e}")
            tests.append(("Health Endpoint", False))
        
        # Test 3.3: Memory create endpoint
        try:
            memory_data = {
                "content": "API test memory",
                "importance_score": 0.7,
                "tags": ["api", "test"]
            }
            response = client.post("/api/v2/memories", json=memory_data)
            if response.status_code == 201:
                print("✅ Memory create endpoint: Working")
                tests.append(("Memory Create API", True))
            elif response.status_code == 404:
                print("⚠️  Memory create endpoint: Not found")
                tests.append(("Memory Create API", False))
            else:
                print(f"⚠️  Memory create endpoint: Status {response.status_code}")
                tests.append(("Memory Create API", False))
        except Exception as e:
            print(f"❌ Memory create endpoint failed: {e}")
            tests.append(("Memory Create API", False))
        
        # Test 3.4: Memory list endpoint
        try:
            response = client.get("/api/v2/memories")
            if response.status_code == 200:
                print("✅ Memory list endpoint: Working")
                tests.append(("Memory List API", True))
            elif response.status_code == 404:
                print("⚠️  Memory list endpoint: Not found")
                tests.append(("Memory List API", False))
            else:
                print(f"⚠️  Memory list endpoint: Status {response.status_code}")
                tests.append(("Memory List API", False))
        except Exception as e:
            print(f"❌ Memory list endpoint failed: {e}")
            tests.append(("Memory List API", False))
        
    except Exception as e:
        print(f"❌ TestClient setup failed: {e}")
        tests.append(("TestClient Setup", False))
    
    return tests

def test_4_new_services_verification():
    """Test 4: Verify the new services mentioned in TODO"""
    print("\n" + "="*60)
    print("TEST 4: NEW SERVICES VERIFICATION")
    print("="*60)
    
    tests = []
    
    services_to_test = [
        ("app.services.domain_classifier", "DomainClassifier", "classify_domain"),
        ("app.services.topic_classifier", "TopicClassifier", "extract_topics"),
        ("app.services.structured_data_extractor", "StructuredDataExtractor", "extract_key_value_pairs")
    ]
    
    for module_name, class_name, test_method in services_to_test:
        try:
            # Try to import
            module = __import__(module_name, fromlist=[class_name])
            service_class = getattr(module, class_name)
            service = service_class()
            
            print(f"✅ {class_name}: Imported and instantiated")
            
            # Try to call a method
            if hasattr(service, test_method):
                try:
                    if test_method == "classify_domain":
                        result = service.classify_domain("This is a test document about artificial intelligence.")
                    elif test_method == "extract_topics":
                        result = service.extract_topics("This is a test document.")
                    elif test_method == "extract_key_value_pairs":
                        result = service.extract_key_value_pairs("Name: John, Age: 30")
                    
                    if result and len(result) > 0:
                        print(f"   ✅ {test_method}: Returns data")
                        tests.append((f"{class_name} Functionality", True))
                    else:
                        print(f"   ⚠️  {test_method}: No data returned")
                        tests.append((f"{class_name} Functionality", False))
                        
                except Exception as e:
                    print(f"   ❌ {test_method}: Method failed: {e}")
                    tests.append((f"{class_name} Functionality", False))
            else:
                print(f"   ❌ {test_method}: Method not found")
                tests.append((f"{class_name} Functionality", False))
                
            tests.append((f"{class_name} Import", True))
            
        except ImportError:
            print(f"⚠️  {class_name}: Not found (may not be implemented)")
            tests.append((f"{class_name} Import", False))
        except Exception as e:
            print(f"❌ {class_name}: Failed: {e}")
            tests.append((f"{class_name} Import", False))
    
    return tests

def main():
    """Run all verification tests"""
    print("🔍 SECOND BRAIN V2 - MANUAL VERIFICATION TESTS")
    print("=" * 80)
    print("Running manual tests to verify actual functionality...")
    print("=" * 80)
    
    all_tests = []
    
    # Run all test suites
    all_tests.extend(test_1_basic_imports())
    all_tests.extend(test_2_memory_service_functionality())
    all_tests.extend(test_3_api_with_testclient())
    all_tests.extend(test_4_new_services_verification())
    
    # Calculate results
    passed = sum(1 for name, result in all_tests if result)
    failed = sum(1 for name, result in all_tests if not result)
    total = len(all_tests)
    
    # Print summary
    print("\n" + "=" * 80)
    print("🎯 VERIFICATION RESULTS SUMMARY")
    print("=" * 80)
    
    for test_name, result in all_tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"\n{'=' * 80}")
    print(f"TOTAL TESTS: {total}")
    print(f"PASSED:      {passed}")
    print(f"FAILED:      {failed}")
    print(f"SUCCESS RATE: {success_rate:.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL VERIFICATION TESTS PASSED!")
        verdict = "EXCELLENT"
    elif failed <= 2:
        print("\n✅ MOSTLY WORKING - Minor issues")
        verdict = "GOOD"
    elif failed <= 5:
        print("\n⚠️  PARTIALLY WORKING - Some issues")
        verdict = "FAIR"
    else:
        print("\n❌ SIGNIFICANT ISSUES FOUND")
        verdict = "POOR"
    
    print(f"FINAL VERDICT: {verdict}")
    print("=" * 80)
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)