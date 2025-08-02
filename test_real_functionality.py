#!/usr/bin/env python3
"""
REAL FUNCTIONALITY TEST - What Actually Works in Second Brain V2
This test gives honest assessment of current functionality
"""
import os
import sys
import subprocess
import importlib
from pathlib import Path

# Setup environment
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
os.environ['PYTHONPATH'] = str(project_root)
os.environ['ENVIRONMENT'] = 'test'

class RealityTester:
    def __init__(self):
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0
        }
    
    def log_result(self, test_name, success, message="", is_warning=False):
        self.results["total_tests"] += 1
        if success:
            print(f"✅ {test_name}: {message}")
            self.results["passed"] += 1
        elif is_warning:
            print(f"⚠️  {test_name}: {message}")
            self.results["warnings"] += 1
            self.results["passed"] += 1  # Count warnings as passes
        else:
            print(f"❌ {test_name}: {message}")
            self.results["failed"] += 1
    
    def test_python_environment(self):
        """Test Python environment setup"""
        print("="*60)
        print("TEST SUITE 1: PYTHON ENVIRONMENT")
        print("="*60)
        
        # Python version
        version = sys.version_info
        self.log_result(
            "Python Version", 
            version.major == 3 and version.minor >= 9,
            f"{version.major}.{version.minor}.{version.micro}"
        )
        
        # Required packages
        required_packages = [
            ("fastapi", "0.109"),
            ("pydantic", "2.5"),
            ("uvicorn", None),
            ("pytest", None)
        ]
        
        for package_name, expected_version in required_packages:
            try:
                package = importlib.import_module(package_name)
                version = getattr(package, '__version__', 'unknown')
                if expected_version and not version.startswith(expected_version):
                    self.log_result(
                        f"Package {package_name}",
                        False,
                        f"Expected {expected_version}x, got {version}",
                        is_warning=True
                    )
                else:
                    self.log_result(
                        f"Package {package_name}",
                        True,
                        f"Version {version}"
                    )
            except ImportError:
                self.log_result(
                    f"Package {package_name}",
                    False,
                    "Not installed"
                )
    
    def test_basic_imports(self):
        """Test basic application imports"""
        print("\n" + "="*60)
        print("TEST SUITE 2: BASIC IMPORTS")
        print("="*60)
        
        import_tests = [
            ("app.config", "Configuration module"),
            ("app.models.memory", "Memory models"),
            ("app.database", "Database module"),
            ("app.core.dependencies", "Dependency injection"),
            ("app.app", "Main FastAPI application")
        ]
        
        for module_name, description in import_tests:
            try:
                importlib.import_module(module_name)
                self.log_result(f"Import {module_name}", True, description)
            except Exception as e:
                self.log_result(f"Import {module_name}", False, f"{description} - {str(e)[:100]}")
    
    def test_app_creation(self):
        """Test FastAPI app creation"""
        print("\n" + "="*60)
        print("TEST SUITE 3: APP CREATION")
        print("="*60)
        
        try:
            from app.app import app
            self.log_result("FastAPI App Creation", True, f"App created successfully")
            
            # Test app properties
            self.log_result("App Title", bool(app.title), f"Title: {app.title}")
            self.log_result("App Version", bool(app.version), f"Version: {app.version}")
            self.log_result("App Routes", len(app.routes) > 0, f"{len(app.routes)} routes registered")
            
            # Test specific important routes
            route_paths = [route.path for route in app.routes if hasattr(route, 'path')]
            important_routes = ["/health", "/v2", "/"]
            
            for route in important_routes:
                exists = any(route in path for path in route_paths)
                self.log_result(f"Route {route}", exists, "Route exists" if exists else "Route missing")
                
        except Exception as e:
            self.log_result("FastAPI App Creation", False, f"Failed: {str(e)[:200]}")
            return
    
    def test_database_setup(self):
        """Test database setup"""
        print("\n" + "="*60)
        print("TEST SUITE 4: DATABASE SETUP")
        print("="*60)
        
        try:
            from app.database import get_database
            db = get_database()
            
            self.log_result("Database Instance", db is not None, f"Type: {type(db)}")
            
            # Check if it's mock or real
            is_mock = hasattr(db, 'is_mock') and db.is_mock
            self.log_result(
                "Database Type", 
                True, 
                f"Mock database" if is_mock else "Real database",
                is_warning=is_mock
            )
            
        except Exception as e:
            self.log_result("Database Instance", False, f"Failed: {str(e)[:200]}")
    
    def test_service_layer(self):
        """Test service layer"""
        print("\n" + "="*60)
        print("TEST SUITE 5: SERVICE LAYER")
        print("="*60)
        
        service_tests = [
            ("app.core.dependencies", "get_memory_service", "Memory Service"),
            ("app.core.dependencies", "get_session_service", "Session Service"),
        ]
        
        for module_name, function_name, description in service_tests:
            try:
                module = importlib.import_module(module_name)
                service_func = getattr(module, function_name)
                service = service_func()
                self.log_result(f"{description}", True, f"Type: {type(service)}")
            except Exception as e:
                self.log_result(f"{description}", False, f"Failed: {str(e)[:100]}")
    
    def test_new_implemented_services(self):
        """Test newly implemented services from TODO"""
        print("\n" + "="*60)
        print("TEST SUITE 6: NEW IMPLEMENTED SERVICES")
        print("="*60)
        
        service_implementations = [
            ("app.services.domain_classifier", "DomainClassifier", "classify_domain"),
            ("app.services.topic_classifier", "TopicClassifier", "extract_topics"),
            ("app.services.structured_data_extractor", "StructuredDataExtractor", "extract_key_value_pairs"),
        ]
        
        for module_name, class_name, test_method in service_implementations:
            try:
                module = importlib.import_module(module_name)
                service_class = getattr(module, class_name)
                service = service_class()
                
                self.log_result(f"{class_name} Creation", True, f"Service instantiated")
                
                # Test the main method
                if hasattr(service, test_method):
                    try:
                        # Call with test data
                        if test_method == "classify_domain":
                            result = service.classify_domain("This is a test document about artificial intelligence and machine learning.")
                        elif test_method == "extract_topics":
                            result = service.extract_topics("This is a test document about artificial intelligence.")
                        elif test_method == "extract_key_value_pairs":
                            result = service.extract_key_value_pairs("Name: John Doe, Age: 30, City: New York")
                        
                        has_data = bool(result and len(result) > 0)
                        self.log_result(
                            f"{class_name}.{test_method}", 
                            has_data,
                            f"Returned data: {type(result)}" if has_data else "No data returned"
                        )
                    except Exception as e:
                        self.log_result(f"{class_name}.{test_method}", False, f"Method failed: {str(e)[:100]}")
                else:
                    self.log_result(f"{class_name}.{test_method}", False, "Method doesn't exist")
                    
            except Exception as e:
                self.log_result(f"{class_name} Creation", False, f"Failed: {str(e)[:100]}")
    
    def test_api_endpoints(self):
        """Test API endpoints"""
        print("\n" + "="*60)
        print("TEST SUITE 7: API ENDPOINTS")
        print("="*60)
        
        try:
            from app.app import app
            from fastapi.testclient import TestClient
            
            client = TestClient(app)
            
            endpoints_to_test = [
                ("/health", "Health Check"),
                ("/", "Root Endpoint"),
                ("/v2", "V2 API Root"),
                ("/v2/memories", "Memory List (GET)"),
            ]
            
            for endpoint, description in endpoints_to_test:
                try:
                    response = client.get(endpoint)
                    success = 200 <= response.status_code < 400
                    self.log_result(
                        f"Endpoint {endpoint}",
                        success,
                        f"{description} - Status: {response.status_code}"
                    )
                except Exception as e:
                    self.log_result(f"Endpoint {endpoint}", False, f"{description} - Error: {str(e)[:100]}")
                    
        except Exception as e:
            self.log_result("API Endpoints", False, f"TestClient failed: {str(e)[:200]}")
    
    def test_pytest_execution(self):
        """Test if pytest can run"""
        print("\n" + "="*60)
        print("TEST SUITE 8: PYTEST EXECUTION")
        print("="*60)
        
        test_files_to_try = [
            "tests/validation/test_simple.py",
            "tests/unit/test_models.py",
        ]
        
        for test_file in test_files_to_try:
            test_path = project_root / test_file
            if test_path.exists():
                try:
                    result = subprocess.run([
                        sys.executable, "-m", "pytest", str(test_path), "-v"
                    ], capture_output=True, text=True, timeout=30)
                    
                    success = result.returncode == 0
                    self.log_result(
                        f"Pytest {test_file}",
                        success,
                        f"Exit code: {result.returncode}" + (f", Output: {result.stdout[-100:]}" if not success else "")
                    )
                except subprocess.TimeoutExpired:
                    self.log_result(f"Pytest {test_file}", False, "Timed out")
                except Exception as e:
                    self.log_result(f"Pytest {test_file}", False, f"Error: {str(e)[:100]}")
            else:
                self.log_result(f"Pytest {test_file}", False, "File not found")
    
    def run_all_tests(self):
        """Run all test suites"""
        print("🔍 SECOND BRAIN V2 - COMPREHENSIVE REALITY CHECK")
        print("="*80)
        print("Honest assessment of what actually works vs what's broken")
        print("="*80)
        
        # Run all test suites
        self.test_python_environment()
        self.test_basic_imports()
        self.test_app_creation()
        self.test_database_setup()
        self.test_service_layer()
        self.test_new_implemented_services()
        self.test_api_endpoints()
        self.test_pytest_execution()
        
        # Final summary
        self.print_summary()
    
    def print_summary(self):
        """Print final test summary"""
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE REALITY CHECK RESULTS")
        print("="*80)
        
        total = self.results["total_tests"]
        passed = self.results["passed"]
        failed = self.results["failed"] 
        warnings = self.results["warnings"]
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"Total Tests:    {total}")
        print(f"Passed:         {passed}")
        print(f"Failed:         {failed}")
        print(f"Warnings:       {warnings}")
        print(f"Success Rate:   {success_rate:.1f}%")
        
        if failed == 0:
            print("\n🎉 EXCELLENT - Everything works perfectly!")
            status = "EXCELLENT"
        elif failed <= 2:
            print("\n✅ GOOD - Minor issues, mostly functional")
            status = "GOOD"
        elif failed <= 5:
            print("\n⚠️  FAIR - Some issues, partially functional")
            status = "FAIR"
        else:
            print("\n❌ POOR - Major issues, significant problems")
            status = "POOR"
        
        print("="*80)
        print(f"FINAL VERDICT: {status}")
        print("="*80)
        
        return failed == 0

def main():
    tester = RealityTester()
    success = tester.run_all_tests()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)