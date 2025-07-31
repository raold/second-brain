#!/usr/bin/env python3
"""
Test key imports that are most likely to have issues
"""

import sys
import os

# Add the project root to sys.path
sys.path.insert(0, '/Users/dro/Documents/second-brain')

def test_import(module_name, description):
    """Test importing a module and report results"""
    print(f"Testing {description}: {module_name}")
    try:
        exec(f"import {module_name}")
        print("  ✅ SUCCESS")
        return True
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False

def main():
    """Test critical imports"""
    print("Testing critical imports...")
    print("=" * 60)
    
    failed_imports = []
    
    # Test key modules
    tests = [
        ("app.app", "Main FastAPI app"),
        ("app.services.synthesis.graph_metrics_service", "Graph metrics service"),
        ("app.models.synthesis.metrics_models", "Metrics models"),
        ("app.routes.memory_routes", "Memory routes"),
        ("app.routes.synthesis_routes", "Synthesis routes"),
        ("app.services.service_factory", "Service factory"),
        ("app.database", "Database module"),
        ("app.config", "Configuration"),
    ]
    
    for module_name, description in tests:
        if not test_import(module_name, description):
            failed_imports.append(module_name)
    
    print("\n" + "=" * 60)
    print(f"Results: {len(tests) - len(failed_imports)}/{len(tests)} imports successful")
    
    if failed_imports:
        print(f"\nFailed imports:")
        for module in failed_imports:
            print(f"  - {module}")
        return 1
    else:
        print("\n🎉 All critical imports successful!")
        return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)