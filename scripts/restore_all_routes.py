#!/usr/bin/env python3
"""
Restore all missing route files from archive
"""
import shutil
from pathlib import Path


def main():
    # Routes to restore based on app.py imports
    routes_to_restore = [
        "github_routes.py",
        "migration_routes.py",
        "session_routes.py",
        "todo_routes.py",
        "visualization_routes.py",
        "bulk_routes.py",
    ]

    src_dir = Path("archive/pre-v3/unused-routes")
    dst_dir = Path("app/routes")

    restored = 0
    for route_file in routes_to_restore:
        src = src_dir / route_file
        dst = dst_dir / route_file

        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
            print(f"[RESTORED] {route_file}")
            restored += 1
        elif dst.exists():
            print(f"[EXISTS] {route_file}")
        else:
            print(f"[NOT FOUND] {route_file}")

    print(f"\nTotal routes restored: {restored}")

if __name__ == "__main__":
    main()
