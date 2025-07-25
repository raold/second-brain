"""Test if the FastAPI app can be imported successfully"""

import sys
import traceback

try:
    print("Testing FastAPI app import...")
    from app.app import app
    print("✓ App imported successfully!")
    
    print("\nTesting ingestion routes import...")
    from app.routes.ingestion_routes import router as ingestion_router
    print("✓ Ingestion routes imported successfully!")
    
    print("\nApp is ready to run!")
    print("Run: python run_server.py")
    
except Exception as e:
    print(f"\n✗ Error importing app: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)