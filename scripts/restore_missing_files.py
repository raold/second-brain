#!/usr/bin/env python3
"""
Restore all missing files needed by app and tests
"""
import shutil
from pathlib import Path


def main():
    # Files that need to be restored based on import errors
    files_to_restore = [
        # Already restored manually
        ("archive/pre-v3/pre-v3-core/app/connection_pool.py", "app/connection_pool.py"),
        ("archive/pre-v3/unused-routes/dashboard_routes.py", "app/routes/dashboard_routes.py"),

        # Check for other potentially missing files
        ("archive/pre-v3/unused-routes/report_routes.py", "app/routes/report_routes.py"),
        ("archive/pre-v3/unused-routes/review_routes.py", "app/routes/review_routes.py"),
        ("archive/pre-v3/unused-routes/scheduling_routes.py", "app/routes/scheduling_routes.py"),
        ("archive/pre-v3/unused-routes/synthesis_routes.py", "app/routes/synthesis_routes.py"),
        ("archive/pre-v3/unused-routes/websocket_routes.py", "app/routes/websocket_routes.py"),

        # Services that might be missing
        ("archive/pre-v3/v2.8.2-synthesis/app/services/report_generation.py", "app/services/report_generation.py"),
        ("archive/pre-v3/v2.8.2-synthesis/app/services/repetition_scheduler.py", "app/services/repetition_scheduler.py"),
        ("archive/pre-v3/v2.8.2-synthesis/app/services/websocket_updates.py", "app/services/websocket_updates.py"),
    ]

    restored_count = 0
    for src, dst in files_to_restore:
        src_path = Path(src)
        dst_path = Path(dst)

        if src_path.exists() and not dst_path.exists():
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)
            print(f"[RESTORED] {dst}")
            restored_count += 1
        elif dst_path.exists():
            print(f"[EXISTS] {dst}")
        else:
            print(f"[NOT FOUND] Source file {src} does not exist")

    print(f"\nTotal files restored: {restored_count}")

if __name__ == "__main__":
    main()
