#!/usr/bin/env python3
"""
Cleanup unused route files not imported in app.py
"""
import os
from pathlib import Path

# Routes that are imported in app.py (these should be kept)
USED_ROUTES = {
    "analysis_routes.py",
    "bulk_operations_routes.py", 
    "graph_routes.py",
    "importance_routes.py",
    "insights.py",
    "relationship_routes.py",
    "synthesis_routes.py",  # Note: Already archived, but still referenced
    "ingestion_routes.py",
    "google_drive_routes.py",
    "__init__.py",  # Keep init files
}

# Core routes that should be kept even if not directly imported
CORE_ROUTES = {
    "auth.py",  # Authentication is core
    "health_routes.py",  # Health checks are important
    "memory_routes.py",  # Core memory functionality
}

def main():
    print("=== Unused Routes Cleanup ===\n")
    
    routes_dir = Path("app/routes")
    archive_dir = Path("archive/pre-v3/unused-routes")
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all route files
    all_routes = {f.name for f in routes_dir.glob("*.py") if f.is_file()}
    
    # Determine unused routes
    unused_routes = all_routes - USED_ROUTES - CORE_ROUTES
    
    print(f"Found {len(all_routes)} total route files")
    print(f"Used routes: {len(USED_ROUTES)}")
    print(f"Core routes: {len(CORE_ROUTES)}")
    print(f"Unused routes to archive: {len(unused_routes)}\n")
    
    # Archive unused routes
    archived_count = 0
    for route_file in sorted(unused_routes):
        src = routes_dir / route_file
        dst = archive_dir / route_file
        
        try:
            src.rename(dst)
            print(f"[ARCHIVED] {route_file}")
            archived_count += 1
        except Exception as e:
            print(f"[ERROR] archiving {route_file}: {e}")
    
    print(f"\nArchived {archived_count} unused route files to: {archive_dir}")
    
    # List remaining routes
    print("\n=== Remaining Routes ===")
    remaining = sorted([f.name for f in routes_dir.glob("*.py") if f.is_file()])
    for route in remaining:
        status = "[USED]" if route in USED_ROUTES else "[CORE]" if route in CORE_ROUTES else "[OTHER]"
        print(f"{status} {route}")
    
    # Create summary
    summary_file = archive_dir / "ROUTES_CLEANUP.md"
    with summary_file.open("w") as f:
        f.write("# Unused Routes Cleanup\n\n")
        f.write(f"## Archived Routes ({len(unused_routes)})\n")
        for route in sorted(unused_routes):
            f.write(f"- {route}\n")
        f.write(f"\n## Kept Routes ({len(USED_ROUTES | CORE_ROUTES)})\n")
        f.write("### Used in app.py\n")
        for route in sorted(USED_ROUTES):
            f.write(f"- {route}\n")
        f.write("\n### Core functionality\n")
        for route in sorted(CORE_ROUTES):
            f.write(f"- {route}\n")


if __name__ == "__main__":
    main()