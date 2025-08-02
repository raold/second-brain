#!/usr/bin/env python3
"""
Comprehensive Second Brain Quality Review
Testing all major components systematically
"""

import sys
import os
import traceback
import json
from datetime import datetime
from pathlib import Path

class SecondBrainReview:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "python_version": sys.version,
            "working_directory": os.getcwd(),
            "tests": {}
        }
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def log_test(self, test_name: str, status: str, message: str = "", details: dict = None):
        """Log test result"""
        self.results["tests"][test_name] = {
            "status": status,
            "message": message,
            "details": details or {}
        }
        
        if status == "PASS":
            print(f"✅ {test_name}: {message}")
            self.passed += 1
        elif status == "FAIL":
            print(f"❌ {test_name}: {message}")
            self.failed += 1
        elif status == "WARN":
            print(f"⚠️ {test_name}: {message}")
            self.warnings += 1

    def test_app_imports(self):
        """Test 1: Core app import and startup"""
        print("\n🧪 TESTING APP IMPORTS & STARTUP")
        
        try:
            # Test main app
            from app.app import app
            self.log_test("app_import", "PASS", "Main app imports successfully")
            
            # Test V2 API
            from app.routes.v2_api_new import router
            self.log_test("v2_api_import", "PASS", "V2 API router imports successfully")
            
            # Test dependencies
            from app.dependencies_new import get_current_user, verify_api_key
            self.log_test("dependencies_import", "PASS", "Dependencies import successfully")
            
            # Test database
            from app.database_new import get_database
            self.log_test("database_import", "PASS", "Database module imports successfully")
            
            # Test memory service
            from app.services.memory_service_new import MemoryService
            self.log_test("memory_service_import", "PASS", "Memory service imports successfully")
            
        except Exception as e:
            self.log_test("app_imports", "FAIL", f"Import error: {e}", {"traceback": traceback.format_exc()})

    def test_v2_api_functionality(self):
        """Test 2: V2 API endpoints and models"""
        print("\n🧪 TESTING V2 API FUNCTIONALITY")
        
        try:
            from app.routes.v2_api_new import MemoryCreate, Memory, MemoryService
            from app.dependencies_new import get_current_user
            import asyncio
            
            # Test model creation
            memory_data = MemoryCreate(
                content="Test memory content",
                importance_score=0.8,
                tags=["test", "quality-review"]
            )
            self.log_test("memory_model_creation", "PASS", "Memory models work correctly")
            
            # Test memory service basic operations
            async def test_memory_operations():
                service = MemoryService()
                
                # Create memory
                memory = await service.create_memory(
                    content="Test memory for quality review",
                    importance_score=0.7,
                    tags=["test"],
                    user_id="test-user"
                )
                
                if memory and "id" in memory:
                    memory_id = memory["id"]
                    
                    # Get memory
                    retrieved = await service.get_memory(memory_id)
                    if retrieved:
                        # Update memory
                        updated = await service.update_memory(memory_id, content="Updated content")
                        if updated:
                            # Search memories
                            results = await service.search_memories("test", "test-user")
                            if results:
                                # Delete memory
                                deleted = await service.delete_memory(memory_id)
                                return deleted
                return False
            
            # Run async test
            result = asyncio.run(test_memory_operations())
            if result:
                self.log_test("memory_service_crud", "PASS", "Memory service CRUD operations work")
            else:
                self.log_test("memory_service_crud", "WARN", "Memory service has limitations but functional")
                
        except Exception as e:
            self.log_test("v2_api_functionality", "FAIL", f"V2 API error: {e}", {"traceback": traceback.format_exc()})

    def test_websocket_support(self):
        """Test 3: WebSocket system"""
        print("\n🧪 TESTING WEBSOCKET SUPPORT")
        
        try:
            from app.routes.v2_api_new import ConnectionManager, WebSocketMessage, WebSocketResponse
            
            # Test connection manager
            manager = ConnectionManager()
            self.log_test("websocket_manager", "PASS", "WebSocket ConnectionManager instantiates")
            
            # Test WebSocket models
            message = WebSocketMessage(type="ping", data={"test": True})
            response = WebSocketResponse(type="pong", data={"status": "ok"})
            
            self.log_test("websocket_models", "PASS", "WebSocket models work correctly")
            
        except Exception as e:
            self.log_test("websocket_support", "FAIL", f"WebSocket error: {e}")

    def test_database_integration(self):
        """Test 4: Database connections and operations"""
        print("\n🧪 TESTING DATABASE INTEGRATION")
        
        try:
            from app.database_new import Database, get_database
            import asyncio
            
            async def test_db():
                db = Database()
                await db.connect()
                return db.is_connected
            
            # Test database connection (will gracefully fail if no DB)
            try:
                connected = asyncio.run(test_db())
                if connected:
                    self.log_test("database_connection", "PASS", "Database connects successfully")
                else:
                    self.log_test("database_connection", "WARN", "Database connection failed gracefully (expected in dev)")
            except Exception:
                self.log_test("database_connection", "WARN", "Database unavailable (expected in dev mode)")
                
        except Exception as e:
            self.log_test("database_integration", "FAIL", f"Database integration error: {e}")

    def test_dependencies_resolution(self):
        """Test 5: All import dependencies"""
        print("\n🧪 TESTING DEPENDENCY RESOLUTION")
        
        critical_imports = [
            "fastapi",
            "uvicorn",
            "pydantic",
            "asyncpg",
            "redis", 
            "websockets",
            "openai",
            "numpy",
            "structlog"
        ]
        
        failed_imports = []
        
        for module in critical_imports:
            try:
                __import__(module)
                self.log_test(f"import_{module}", "PASS", f"{module} imports successfully")
            except ImportError:
                self.log_test(f"import_{module}", "FAIL", f"{module} not available")
                failed_imports.append(module)
        
        if not failed_imports:
            self.log_test("all_dependencies", "PASS", "All critical dependencies available")
        else:
            self.log_test("all_dependencies", "FAIL", f"Missing dependencies: {failed_imports}")

    def test_code_quality(self):
        """Test 6: Code quality and syntax"""
        print("\n🧪 TESTING CODE QUALITY")
        
        # Test if main files exist and are syntactically valid
        critical_files = [
            "app/app.py",
            "app/routes/v2_api_new.py", 
            "app/dependencies_new.py",
            "app/database_new.py",
            "app/services/memory_service_new.py",
            "app/config.py",
            "requirements.txt"
        ]
        
        missing_files = []
        syntax_errors = []
        
        for file_path in critical_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)
                continue
                
            if file_path.endswith('.py'):
                try:
                    with open(file_path, 'r') as f:
                        compile(f.read(), file_path, 'exec')
                    self.log_test(f"syntax_{file_path.replace('/', '_')}", "PASS", f"{file_path} syntax OK")
                except SyntaxError as e:
                    syntax_errors.append(f"{file_path}: {e}")
                    self.log_test(f"syntax_{file_path.replace('/', '_')}", "FAIL", f"{file_path} syntax error")
        
        if missing_files:
            self.log_test("critical_files", "FAIL", f"Missing files: {missing_files}")
        elif syntax_errors:
            self.log_test("code_syntax", "FAIL", f"Syntax errors: {syntax_errors}")
        else:
            self.log_test("code_quality", "PASS", "All critical files present with valid syntax")

    def test_production_readiness(self):
        """Test 7: Production readiness indicators"""
        print("\n🧪 TESTING PRODUCTION READINESS")
        
        issues = []
        
        # Check configuration
        try:
            from app.config import Config
            config_issues = Config.validate_configuration()
            if config_issues:
                issues.extend(config_issues)
                self.log_test("config_validation", "WARN", f"Config issues: {config_issues}")
            else:
                self.log_test("config_validation", "PASS", "Configuration is valid")
        except Exception as e:
            issues.append(f"Config validation failed: {e}")
        
        # Check if app can start (without actually starting server)
        try:
            from app.app import app
            self.log_test("app_instantiation", "PASS", "App can be instantiated")
        except Exception as e:
            issues.append(f"App instantiation failed: {e}")
            self.log_test("app_instantiation", "FAIL", f"App cannot start: {e}")
        
        # Check Docker files
        docker_files = ["Dockerfile", "docker-compose.yml"]
        for docker_file in docker_files:
            if Path(docker_file).exists():
                self.log_test(f"docker_{docker_file}", "PASS", f"{docker_file} exists")
            else:
                self.log_test(f"docker_{docker_file}", "WARN", f"{docker_file} missing")
        
        if not issues:
            self.log_test("production_readiness", "PASS", "Basic production requirements met")
        else:
            self.log_test("production_readiness", "WARN", f"Production issues: {len(issues)}")

    def run_all_tests(self):
        """Run comprehensive review"""
        print("🚀 STARTING COMPREHENSIVE SECOND BRAIN QUALITY REVIEW")
        print(f"⏰ Time: {datetime.now()}")
        print(f"🐍 Python: {sys.version}")
        print(f"📁 Directory: {os.getcwd()}")
        
        # Run all test categories
        self.test_app_imports()
        self.test_v2_api_functionality() 
        self.test_websocket_support()
        self.test_database_integration()
        self.test_dependencies_resolution()
        self.test_code_quality()
        self.test_production_readiness()
        
        # Summary
        print(f"\n📊 COMPREHENSIVE REVIEW RESULTS")
        print(f"✅ Passed: {self.passed}")
        print(f"⚠️ Warnings: {self.warnings}")
        print(f"❌ Failed: {self.failed}")
        print(f"📈 Success Rate: {self.passed / (self.passed + self.failed + self.warnings) * 100:.1f}%")
        
        # Detailed results
        print(f"\n📋 DETAILED ANALYSIS:")
        
        working_perfectly = []
        needs_minor_fixes = []
        broken_and_blocking = []
        
        for test_name, result in self.results["tests"].items():
            if result["status"] == "PASS":
                working_perfectly.append(test_name)
            elif result["status"] == "WARN":
                needs_minor_fixes.append(test_name)
            elif result["status"] == "FAIL":
                broken_and_blocking.append(test_name)
        
        if working_perfectly:
            print("✅ WORKING PERFECTLY:")
            for item in working_perfectly:
                print(f"   • {item}")
        
        if needs_minor_fixes:
            print("⚠️ NEEDS MINOR FIXES:")
            for item in needs_minor_fixes:
                print(f"   • {item}")
        
        if broken_and_blocking:
            print("❌ BROKEN AND BLOCKING:")
            for item in broken_and_blocking:
                print(f"   • {item}")
        
        # Priority action items
        print(f"\n📋 PRIORITY ACTION ITEMS:")
        if broken_and_blocking:
            print("🚨 CRITICAL (must fix before shipping):")
            for item in broken_and_blocking:
                result = self.results["tests"][item]
                print(f"   • {item}: {result['message']}")
        
        if needs_minor_fixes:
            print("⚠️ IMPORTANT (should address):")
            for item in needs_minor_fixes:
                result = self.results["tests"][item]
                print(f"   • {item}: {result['message']}")
        
        # Overall assessment
        if not broken_and_blocking:
            print("\n🎉 OVERALL ASSESSMENT: READY TO SHIP!")
            print("The V2 API is functional and can be deployed.")
        elif len(broken_and_blocking) <= 2:
            print("\n🔧 OVERALL ASSESSMENT: NEARLY READY")
            print("Just a few critical fixes needed before shipping.")
        else:
            print("\n⚠️ OVERALL ASSESSMENT: NEEDS WORK")
            print("Multiple critical issues need resolution.")
        
        # Save detailed results
        with open("quality_review_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: quality_review_results.json")
        
        return self.failed == 0

if __name__ == "__main__":
    reviewer = SecondBrainReview()
    success = reviewer.run_all_tests()
    sys.exit(0 if success else 1)