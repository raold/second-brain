#!/usr/bin/env python3
"""
Restore synthesis model files from archive to fix CI errors
"""
import shutil
from pathlib import Path


def main():
    archive_dir = Path("archive/pre-v3/v2.8.2-synthesis/app/models/synthesis")
    target_dir = Path("app/models/synthesis")

    # Files to restore
    files_to_restore = [
        "repetition_models.py",
        "report_models.py",
        "websocket_models.py"
    ]

    for file_name in files_to_restore:
        src = archive_dir / file_name
        dst = target_dir / file_name

        if src.exists():
            shutil.copy2(src, dst)
            print(f"[RESTORED] {file_name}")
        else:
            print(f"[NOT FOUND] {file_name}")

if __name__ == "__main__":
    main()
