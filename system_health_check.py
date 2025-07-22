#!/usr/bin/env python3
"""
Second Brain System Health Check - "Claude Doctor"
Comprehensive diagnostic tool to assess system health and identify issues.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import importlib.util

class SystemHealthChecker:
    """Comprehensive system health diagnostic tool"""
    
    def __init__(self):
        self.base_path = Path(".")
        self.issues = []
        self.warnings = []
        self.recommendations = []
        self.health_score = 100
        
    def log_issue(self, category: str, message: str, severity: str = "error"):
        """Log an issue with the system"""
        issue = {
            "category": category,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now().isoformat()
        }
        
        if severity == "error":
            self.issues.append(issue)
            self.health_score -= 10
        elif severity == "warning":
            self.warnings.append(issue)
            self.health_score -= 5
        elif severity == "recommendation":
            self.recommendations.append(issue)
            self.health_score -= 2
    
    def check_directory_structure(self):
        """Check if core directory structure exists"""
        print("🏗️  Checking directory structure...")
        
        required_dirs = [
            "app",
            "tests",
            "docs",
            "scripts",
            ".github/workflows"
        ]
        
        critical_files = [
            "requirements.txt",
            "pytest.ini",
            "app/__init__.py",
            "tests/conftest.py"
        ]
        
        for directory in required_dirs:
            dir_path = self.base_path / directory
            if not dir_path.exists():
                self.log_issue("structure", f"Missing directory: {directory}", "error")
            elif not dir_path.is_dir():
                self.log_issue("structure", f"Path exists but is not a directory: {directory}", "error")
        
        for file_path in critical_files:
            file_obj = self.base_path / file_path
            if not file_obj.exists():
                self.log_issue("structure", f"Missing critical file: {file_path}", "warning")
        
        # Check app subdirectories
        app_subdirs = ["routes", "security", "models"]
        for subdir in app_subdirs:
            subdir_path = self.base_path / "app" / subdir
            if subdir_path.exists():
                print(f"  ✅ Found app/{subdir}")
            else:
                self.log_issue("structure", f"Missing app subdirectory: {subdir}", "recommendation")
    
    def check_python_environment(self):
        """Check Python environment and dependencies"""
        print("🐍 Checking Python environment...")
        
        # Check Python version
        python_version = sys.version_info
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
            self.log_issue("python", f"Python version {python_version.major}.{python_version.minor} is too old (need 3.8+)", "error")
        else:
            print(f"  ✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        # Check virtual environment
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            print("  ✅ Virtual environment active")
        else:
            self.log_issue("python", "No virtual environment detected", "warning")
        
        # Check requirements.txt
        req_file = self.base_path / "requirements.txt"
        if req_file.exists():
            try:
                requirements = req_file.read_text().strip().split('\n')
                print(f"  ✅ Found {len(requirements)} requirements")
                
                # Check critical dependencies
                critical_deps = ["fastapi", "pytest", "pydantic", "uvicorn"]
                found_deps = []
                
                for req in requirements:
                    if req.strip() and not req.startswith('#'):
                        dep_name = req.split('==')[0].split('>=')[0].split('<=')[0].strip()
                        if dep_name in critical_deps:
                            found_deps.append(dep_name)
                
                missing_deps = set(critical_deps) - set(found_deps)
                if missing_deps:
                    self.log_issue("dependencies", f"Missing critical dependencies: {', '.join(missing_deps)}", "error")
                
            except Exception as e:
                self.log_issue("dependencies", f"Error reading requirements.txt: {e}", "error")
    
    def check_configuration_files(self):
        """Check configuration files"""
        print("⚙️  Checking configuration files...")
        
        config_files = {
            "pytest.ini": ["testpaths", "asyncio_mode", "addopts"],
            ".gitignore": ["__pycache__", "*.pyc", ".env"],
            "pyproject.toml": None,  # Optional
            ".env": None,  # Optional
        }
        
        for config_file, required_content in config_files.items():
            file_path = self.base_path / config_file
            
            if file_path.exists():
                content = file_path.read_text()
                print(f"  ✅ Found {config_file}")
                
                if required_content:
                    missing_content = []
                    for item in required_content:
                        if item not in content:
                            missing_content.append(item)
                    
                    if missing_content:
                        self.log_issue("config", f"{config_file} missing: {', '.join(missing_content)}", "warning")
            else:
                if config_file in ["pytest.ini"]:
                    self.log_issue("config", f"Missing critical config file: {config_file}", "error")
                else:
                    self.log_issue("config", f"Missing optional config file: {config_file}", "recommendation")
    
    def check_app_modules(self):
        """Check app module structure and imports"""
        print("📦 Checking app modules...")
        
        app_dir = self.base_path / "app"
        if not app_dir.exists():
            self.log_issue("modules", "App directory does not exist", "error")
            return
        
        # Check for key modules
        key_modules = [
            "app.py",
            "database.py", 
            "batch_processor.py",
            "__init__.py"
        ]
        
        for module in key_modules:
            module_path = app_dir / module
            if module_path.exists():
                print(f"  ✅ Found {module}")
                
                # Try to check for basic syntax
                try:
                    content = module_path.read_text()
                    if len(content.strip()) == 0:
                        self.log_issue("modules", f"Module {module} is empty", "warning")
                    elif "import" not in content and "def" not in content and "class" not in content:
                        self.log_issue("modules", f"Module {module} appears to have no code", "warning")
                except Exception as e:
                    self.log_issue("modules", f"Error reading {module}: {e}", "error")
            else:
                if module == "__init__.py":
                    self.log_issue("modules", f"Missing {module} (required for Python package)", "error")
                else:
                    self.log_issue("modules", f"Missing module: {module}", "warning")
        
        # Check routes directory
        routes_dir = app_dir / "routes"
        if routes_dir.exists():
            route_files = list(routes_dir.glob("*.py"))
            print(f"  ✅ Found {len(route_files)} route files")
            
            if len(route_files) == 0:
                self.log_issue("modules", "Routes directory exists but is empty", "warning")
        else:
            self.log_issue("modules", "No routes directory found", "recommendation")
    
    def check_test_infrastructure(self):
        """Check test infrastructure"""
        print("🧪 Checking test infrastructure...")
        
        tests_dir = self.base_path / "tests"
        if not tests_dir.exists():
            self.log_issue("tests", "Tests directory does not exist", "error")
            return
        
        # Count test files
        test_files = list(tests_dir.rglob("test_*.py"))
        if len(test_files) == 0:
            self.log_issue("tests", "No test files found", "error")
        else:
            print(f"  ✅ Found {len(test_files)} test files")
        
        # Check for conftest.py
        conftest_path = tests_dir / "conftest.py"
        if conftest_path.exists():
            print("  ✅ Found conftest.py")
        else:
            self.log_issue("tests", "Missing conftest.py (recommended for shared fixtures)", "recommendation")
        
        # Check test subdirectories
        test_subdirs = ["unit", "integration", "performance"]
        for subdir in test_subdirs:
            subdir_path = tests_dir / subdir
            if subdir_path.exists():
                files_in_subdir = list(subdir_path.glob("test_*.py"))
                print(f"  ✅ Found {subdir} tests ({len(files_in_subdir)} files)")
            else:
                self.log_issue("tests", f"Missing {subdir} test directory", "recommendation")
    
    def check_git_repository(self):
        """Check git repository status"""
        print("📋 Checking git repository...")
        
        git_dir = self.base_path / ".git"
        if not git_dir.exists():
            self.log_issue("git", "Not a git repository", "warning")
            return
        
        try:
            # Check git status
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=self.base_path
            )
            
            if result.returncode == 0:
                changes = result.stdout.strip().split('\n') if result.stdout.strip() else []
                if changes and changes[0]:  # Filter out empty strings
                    print(f"  ⚠️  {len(changes)} uncommitted changes")
                    if len(changes) > 10:
                        self.log_issue("git", f"Many uncommitted changes ({len(changes)})", "warning")
                else:
                    print("  ✅ Working directory clean")
            
            # Check branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                cwd=self.base_path
            )
            
            if result.returncode == 0:
                branch = result.stdout.strip()
                print(f"  ✅ Current branch: {branch}")
            
        except Exception as e:
            self.log_issue("git", f"Error checking git status: {e}", "warning")
    
    def check_documentation(self):
        """Check documentation"""
        print("📚 Checking documentation...")
        
        docs_dir = self.base_path / "docs"
        if docs_dir.exists():
            doc_files = list(docs_dir.rglob("*.md"))
            print(f"  ✅ Found {len(doc_files)} documentation files")
            
            # Check for key documentation
            key_docs = ["README.md", "API.md", "TESTING.md"]
            for doc in key_docs:
                doc_path = docs_dir / doc
                if not doc_path.exists():
                    # Check in root directory
                    root_doc_path = self.base_path / doc
                    if not root_doc_path.exists():
                        self.log_issue("docs", f"Missing documentation: {doc}", "recommendation")
        else:
            self.log_issue("docs", "No docs directory found", "recommendation")
        
        # Check for README in root
        readme_path = self.base_path / "README.md"
        if readme_path.exists():
            print("  ✅ Found README.md")
        else:
            self.log_issue("docs", "Missing README.md in root directory", "warning")
    
    def check_security_configuration(self):
        """Check security configuration"""
        print("🔒 Checking security configuration...")
        
        # Check for .env file (should exist but not be in git)
        env_file = self.base_path / ".env"
        env_example = self.base_path / ".env.example"
        
        if env_file.exists():
            print("  ✅ Found .env file")
        else:
            self.log_issue("security", "No .env file found (may need environment variables)", "warning")
        
        if env_example.exists():
            print("  ✅ Found .env.example")
        else:
            self.log_issue("security", "No .env.example file (recommended for setup)", "recommendation")
        
        # Check .gitignore for security patterns
        gitignore_path = self.base_path / ".gitignore"
        if gitignore_path.exists():
            content = gitignore_path.read_text()
            security_patterns = [".env", "*.key", "*.pem", "__pycache__"]
            
            missing_patterns = []
            for pattern in security_patterns:
                if pattern not in content:
                    missing_patterns.append(pattern)
            
            if missing_patterns:
                self.log_issue("security", f"Missing .gitignore patterns: {', '.join(missing_patterns)}", "warning")
            else:
                print("  ✅ Security patterns in .gitignore")
    
    def check_performance_indicators(self):
        """Check performance indicators"""
        print("⚡ Checking performance indicators...")
        
        # Check for large files that might impact performance
        large_files = []
        for file_path in self.base_path.rglob("*"):
            if file_path.is_file() and not any(part.startswith('.') for part in file_path.parts):
                try:
                    size = file_path.stat().st_size
                    if size > 10 * 1024 * 1024:  # 10MB
                        large_files.append((file_path, size))
                except:
                    pass
        
        if large_files:
            for file_path, size in large_files:
                size_mb = size / (1024 * 1024)
                self.log_issue("performance", f"Large file detected: {file_path} ({size_mb:.1f}MB)", "warning")
        else:
            print("  ✅ No large files detected")
        
        # Check for potential performance issues in code
        python_files = list(self.base_path.rglob("*.py"))
        performance_issues = []
        
        for py_file in python_files[:10]:  # Check first 10 files to avoid long scan
            try:
                content = py_file.read_text()
                lines = content.split('\n')
                
                # Check for long lines
                long_lines = [i for i, line in enumerate(lines, 1) if len(line) > 120]
                if len(long_lines) > 5:
                    performance_issues.append(f"{py_file.name}: {len(long_lines)} long lines")
                
                # Check for potential inefficiencies
                if content.count('for ') > 50:  # Many loops might indicate complexity
                    performance_issues.append(f"{py_file.name}: High loop count")
                    
            except:
                pass
        
        if performance_issues:
            for issue in performance_issues[:3]:  # Show first 3
                self.log_issue("performance", f"Code complexity: {issue}", "recommendation")
    
    def run_comprehensive_check(self):
        """Run all health checks"""
        print("🏥 Second Brain System Health Check")
        print("=" * 50)
        
        self.check_directory_structure()
        self.check_python_environment()
        self.check_configuration_files()
        self.check_app_modules()
        self.check_test_infrastructure()
        self.check_git_repository()
        self.check_documentation()
        self.check_security_configuration()
        self.check_performance_indicators()
        
        return self.generate_health_report()
    
    def generate_health_report(self):
        """Generate comprehensive health report"""
        print("\n" + "=" * 50)
        print("🩺 HEALTH REPORT")
        print("=" * 50)
        
        # Health score
        health_status = "🟢 HEALTHY" if self.health_score >= 80 else "🟡 NEEDS ATTENTION" if self.health_score >= 60 else "🔴 CRITICAL"
        print(f"Overall Health Score: {self.health_score}/100 {health_status}")
        
        # Summary
        print(f"\n📊 Summary:")
        print(f"- Issues (Critical): {len(self.issues)}")
        print(f"- Warnings: {len(self.warnings)}")
        print(f"- Recommendations: {len(self.recommendations)}")
        
        # Critical Issues
        if self.issues:
            print(f"\n🚨 Critical Issues ({len(self.issues)}):")
            for issue in self.issues:
                print(f"  ❌ [{issue['category']}] {issue['message']}")
        
        # Warnings
        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  ⚠️  [{warning['category']}] {warning['message']}")
        
        # Recommendations
        if self.recommendations:
            print(f"\n💡 Recommendations ({len(self.recommendations)}):")
            for rec in self.recommendations:
                print(f"  💡 [{rec['category']}] {rec['message']}")
        
        # Treatment Plan
        print(f"\n🔧 Treatment Plan:")
        if self.health_score >= 80:
            print("  ✅ System is healthy! Continue regular maintenance.")
        elif self.health_score >= 60:
            print("  🔨 Address warnings to improve system health.")
            print("  📋 Review recommendations for optimization.")
        else:
            print("  🚨 IMMEDIATE ACTION REQUIRED!")
            print("  🔧 Fix critical issues before proceeding.")
            print("  ⚠️  Address all warnings.")
        
        # Next Steps
        if self.issues:
            print(f"\n🎯 Priority Actions:")
            for i, issue in enumerate(self.issues[:3], 1):
                print(f"  {i}. Fix: {issue['message']}")
        
        print(f"\n📅 Diagnosis completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return {
            "health_score": self.health_score,
            "issues": self.issues,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "status": health_status
        }

if __name__ == "__main__":
    doctor = SystemHealthChecker()
    report = doctor.run_comprehensive_check()
    
    # Save report to file
    report_file = Path("system_health_report.json")
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Detailed report saved to: {report_file}")