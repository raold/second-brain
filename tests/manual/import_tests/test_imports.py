#!/usr/bin/env python3
"""Quick import test to identify broken imports"""

import sys
import traceback


def test_import(module_name):
    try:
        __import__(module_name)
        print(f"✅ {module_name}")
        return True
    except Exception as e:
        print(f"❌ {module_name}: {e}")
        print(f"   {traceback.format_exc().splitlines()[-1]}")
        return False

# Test key imports
modules_to_test = [
    "app.app",
    "app.services.service_factory",
    "app.services.synthesis.advanced_synthesis",
    "app.models.synthesis.advanced_models",
    "app.core.dependencies",
    "app.routes.memory_routes",
    "app.database",
    "app.ingestion.engine"
]

print("Testing critical imports...")
failed = 0
for module in modules_to_test:
    if not test_import(module):
        failed += 1

print(f"\nResult: {len(modules_to_test) - failed}/{len(modules_to_test)} imports successful")
if failed > 0:
    print(f"❌ {failed} imports failed - app is broken")
    sys.exit(1)
else:
    print("✅ All imports successful - app should work")
