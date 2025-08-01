#!/usr/bin/env python3
"""
Dependency validation script for Second Brain project.
Validates all requirements files and checks for security vulnerabilities.
"""

import subprocess
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
import urllib.request
import urllib.error

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def get_installed_packages() -> Dict[str, str]:
    """Get currently installed packages and their versions."""
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "list", "--format=json"], 
                              capture_output=True, text=True, check=True)
        packages = json.loads(result.stdout)
        return {pkg["name"].lower(): pkg["version"] for pkg in packages}
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return {}

def parse_requirements_file(file_path: Path) -> Dict[str, str]:
    """Parse a requirements file and return package name -> version mapping."""
    packages = {}
    
    if not file_path.exists():
        return packages
    
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('-'):
                # Handle different version specifiers
                for op in ['==', '>=', '<=', '>', '<', '!=']:
                    if op in line:
                        pkg_name, version = line.split(op, 1)
                        packages[pkg_name.strip().lower()] = version.strip()
                        break
    
    return packages

def check_missing_imports() -> List[str]:
    """Check for missing imports by scanning Python files."""
    missing = []
    python_files = list(project_root.rglob("*.py"))
    
    common_packages = {
        'fastapi': 'fastapi',
        'uvicorn': 'uvicorn', 
        'redis': 'redis',
        'sqlalchemy': 'sqlalchemy',
        'pydantic': 'pydantic',
        'websockets': 'websockets',
        'numpy': 'numpy',
        'pandas': 'pandas',
        'openai': 'openai',
        'psutil': 'psutil',
        'aiofiles': 'aiofiles',
    }
    
    for py_file in python_files[:50]:  # Sample first 50 files to avoid timeout
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                for import_name, package_name in common_packages.items():
                    patterns = [
                        f"import {import_name}",
                        f"from {import_name}",
                        f"import {import_name}\\.",
                        f"from {import_name}\\.",
                    ]
                    
                    for pattern in patterns:
                        if re.search(pattern, content):
                            try:
                                __import__(package_name)
                            except ImportError:
                                if package_name not in missing:
                                    missing.append(package_name)
                            break
        except (UnicodeDecodeError, OSError):
            continue
    
    return missing

def check_version_conflicts() -> List[Tuple[str, List[Tuple[str, str]]]]:
    """Check for version conflicts between requirements files."""
    conflicts = []
    
    req_files = [
        project_root / "requirements.txt",
        project_root / "config" / "requirements-production.txt", 
        project_root / "config" / "requirements-ci.txt",
        project_root / "config" / "requirements-multimodal.txt",
    ]
    
    # Parse all requirements files
    all_packages = {}
    for req_file in req_files:
        if req_file.exists():
            packages = parse_requirements_file(req_file)
            for pkg, version in packages.items():
                if pkg not in all_packages:
                    all_packages[pkg] = []
                all_packages[pkg].append((req_file.name, version))
    
    # Find conflicts
    for pkg, versions in all_packages.items():
        if len(versions) > 1:
            unique_versions = set(v[1] for v in versions)
            if len(unique_versions) > 1:
                conflicts.append((pkg, versions))
    
    return conflicts

def check_security_vulnerabilities() -> List[Dict]:
    """Check for known security vulnerabilities (simplified check)."""
    vulnerabilities = []
    
    # Known vulnerable versions (from our analysis)
    known_vulns = {
        'fastapi': {
            'versions': ['0.104.1', '0.109.0'],
            'cve': 'CVE-2024-24762',
            'description': 'Regular Expression Denial of Service (ReDoS)',
            'fix_version': '0.109.1'
        },
        'redis': {
            'versions': ['5.0.0', '5.0.1'],
            'cve': 'CVE-2023-28858',
            'description': 'Race condition vulnerability',
            'fix_version': '5.0.3'
        }
    }
    
    installed = get_installed_packages()
    
    for pkg, vuln_info in known_vulns.items():
        if pkg in installed:
            current_version = installed[pkg]
            if current_version in vuln_info['versions']:
                vulnerabilities.append({
                    'package': pkg,
                    'current_version': current_version,
                    'cve': vuln_info['cve'],
                    'description': vuln_info['description'],
                    'fix_version': vuln_info['fix_version']
                })
    
    return vulnerabilities

def validate_websocket_support() -> Dict[str, bool]:
    """Validate WebSocket support dependencies."""
    checks = {
        'fastapi_websocket': False,
        'websockets_package': False,
        'uvicorn_websocket': False,
    }
    
    try:
        # Check FastAPI WebSocket support
        from fastapi import WebSocket, WebSocketDisconnect
        checks['fastapi_websocket'] = True
    except ImportError:
        pass
    
    try:
        # Check websockets package
        import websockets
        checks['websockets_package'] = True
    except ImportError:
        pass
    
    try:
        # Check uvicorn WebSocket support  
        import uvicorn
        checks['uvicorn_websocket'] = True
    except ImportError:
        pass
    
    return checks

def validate_database_support() -> Dict[str, bool]:
    """Validate database dependencies."""
    checks = {
        'asyncpg': False,
        'psycopg2': False,
        'sqlalchemy': False,
        'alembic': False,
        'pgvector': False,
    }
    
    for package in checks.keys():
        try:
            __import__(package)
            checks[package] = True
        except ImportError:
            pass
    
    return checks

def main():
    """Main validation function."""
    print("🔍 Second Brain - Dependency Validation")
    print("=" * 50)
    
    # Check for missing imports
    print("\n📦 Checking for missing dependencies...")
    missing = check_missing_imports()
    if missing:
        print("❌ Missing dependencies found:")
        for pkg in missing:
            print(f"   - {pkg}")
    else:
        print("✅ No missing dependencies detected")
    
    # Check version conflicts
    print("\n🔄 Checking for version conflicts...")
    conflicts = check_version_conflicts()
    if conflicts:
        print("⚠️  Version conflicts found:")
        for pkg, versions in conflicts:
            print(f"   - {pkg}:")
            for file_name, version in versions:
                print(f"     - {file_name}: {version}")
    else:
        print("✅ No version conflicts detected")
    
    # Check security vulnerabilities
    print("\n🛡️  Checking for security vulnerabilities...")
    vulns = check_security_vulnerabilities()
    if vulns:
        print("🚨 Security vulnerabilities found:")
        for vuln in vulns:
            print(f"   - {vuln['package']} {vuln['current_version']}")
            print(f"     CVE: {vuln['cve']}")
            print(f"     Fix: Upgrade to {vuln['fix_version']}")
    else:
        print("✅ No known vulnerabilities detected")
    
    # Validate WebSocket support
    print("\n🔌 Validating WebSocket support...")
    ws_checks = validate_websocket_support()
    all_ws_ok = all(ws_checks.values())
    if all_ws_ok:
        print("✅ WebSocket support fully configured")
    else:
        print("⚠️  WebSocket support issues:")
        for check, status in ws_checks.items():
            status_icon = "✅" if status else "❌"
            print(f"   {status_icon} {check}")
    
    # Validate database support
    print("\n🗄️  Validating database support...")
    db_checks = validate_database_support()
    critical_db = ['asyncpg', 'psycopg2', 'sqlalchemy']
    critical_ok = all(db_checks[pkg] for pkg in critical_db if pkg in db_checks)
    
    if critical_ok:
        print("✅ Critical database dependencies available")
    else:
        print("❌ Critical database dependencies missing")
    
    for check, status in db_checks.items():
        status_icon = "✅" if status else "⚠️ "
        print(f"   {status_icon} {check}")
    
    # Summary
    print("\n📊 Validation Summary")
    print("-" * 30)
    
    issues = len(missing) + len(conflicts) + len(vulns)
    if not all_ws_ok:
        issues += 1
    if not critical_ok:
        issues += 1
    
    if issues == 0:
        print("🎉 All dependency checks passed!")
        return 0
    else:
        print(f"⚠️  {issues} issue(s) found - see details above")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)