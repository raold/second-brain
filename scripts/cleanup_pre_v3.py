#!/usr/bin/env python3
"""
Cleanup script to archive or delete pre-v3.0.0 files and stubs
"""
import os
import shutil
from pathlib import Path

# Files to delete (empty stubs)
DELETE_FILES = [
    "app/models.py",
    "app/router_simplified.py",
    "app/storage/dual_storage.py",
    "app/storage/postgres_client.py",
    "app/storage/storage_handler.py",
    "app/utils/validation.py",
    "scripts/maintenance/check_schema.py",
    "scripts/maintenance/fix_schema.py",
    "scripts/setup/setup.py",
    "scripts/setup/setup_db.py",
    "docker-compose.yml.backup",
    "compose.yaml.complex-backup",
]

# Files to archive (pre-v3 implementations)
ARCHIVE_FILES = {
    # Pre-v3.0.0 core files
    "pre-v3-core": [
        "app/connection_pool.py",
        "app/security.py",
        "app/__init__.py",
        "app/enhanced_dashboard.py",
        "app/ingestion/engine.py",
        "app/insights/__init__.py",
    ],
    
    # v2.8.2 synthesis features
    "v2.8.2-synthesis": [
        "app/models/synthesis/repetition_models.py",
        "app/models/synthesis/report_models.py",
        "app/models/synthesis/websocket_models.py",
        "app/services/synthesis/repetition_scheduler.py",
        "app/services/synthesis/report_generator.py",
        "app/services/synthesis/websocket_service.py",
        "app/routes/synthesis_routes.py",
        "app/routes/advanced_synthesis_routes.py",
    ],
    
    # v2.8.3 intelligence features
    "v2.8.3-intelligence": [
        "app/models/intelligence/analytics_models.py",
        "app/services/intelligence/analytics_dashboard.py",
        "app/services/intelligence/anomaly_detection.py",
        "app/services/intelligence/predictive_insights.py",
        "app/services/intelligence/knowledge_gap_analysis.py",
        "app/routes/intelligence_routes.py",
    ],
    
    # Test files for non-existent features
    "tests-for-removed-features": [
        "tests/unit/test_consolidation_engine.py",
        "tests/unit/test_websocket_updates.py",
        "tests/unit/test_graph_metrics_service.py",
        "tests/unit/test_knowledge_summarizer.py",
        "tests/unit/test_suggestion_engine.py",
        "tests/unit/test_report_generation.py",
        "tests/unit/test_repetition_scheduler.py",
        "tests/unit/test_intelligence_analytics.py",
        "tests/integration/test_intelligence_routes.py",
        "tests/integration/test_advanced_synthesis_routes.py",
    ],
}

# Directories to archive entirely
ARCHIVE_DIRS = {
    "v2.8.2-synthesis-tests": "tests/unit/synthesis",
}


def main():
    print("=== Pre-v3.0.0 Cleanup Script ===\n")
    
    base_path = Path(".")
    archive_base = Path("archive/pre-v3")
    
    # Delete empty stub files
    print("1. Deleting empty stub files...")
    deleted_count = 0
    for file_path in DELETE_FILES:
        full_path = base_path / file_path
        if full_path.exists():
            try:
                full_path.unlink()
                print(f"   [DELETED] {file_path}")
                deleted_count += 1
            except Exception as e:
                print(f"   [ERROR] deleting {file_path}: {e}")
        else:
            print(f"   - Not found: {file_path}")
    
    print(f"\n   Deleted {deleted_count} files.\n")
    
    # Archive pre-v3 files
    print("2. Archiving pre-v3.0.0 files...")
    archived_count = 0
    
    for category, files in ARCHIVE_FILES.items():
        category_dir = archive_base / category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n   Category: {category}")
        for file_path in files:
            src = base_path / file_path
            if src.exists():
                # Preserve directory structure in archive
                relative_parts = Path(file_path).parts
                dst_dir = category_dir / Path(*relative_parts[:-1])
                dst_dir.mkdir(parents=True, exist_ok=True)
                dst = dst_dir / relative_parts[-1]
                
                try:
                    shutil.move(str(src), str(dst))
                    print(f"   [OK] Archived: {file_path}")
                    archived_count += 1
                except Exception as e:
                    print(f"   [ERROR] Error archiving {file_path}: {e}")
            else:
                print(f"   - Not found: {file_path}")
    
    # Archive entire directories
    print("\n3. Archiving entire directories...")
    for category, dir_path in ARCHIVE_DIRS.items():
        src = base_path / dir_path
        if src.exists() and src.is_dir():
            dst = archive_base / category
            try:
                shutil.move(str(src), str(dst))
                print(f"   [OK] Archived directory: {dir_path}")
                archived_count += 1
            except Exception as e:
                print(f"   [ERROR] Error archiving directory {dir_path}: {e}")
        else:
            print(f"   - Directory not found: {dir_path}")
    
    print(f"\n   Archived {archived_count} files/directories.\n")
    
    # Clean up empty directories
    print("4. Cleaning up empty directories...")
    empty_dirs = []
    
    # Directories that might now be empty
    check_dirs = [
        "app/storage",
        "scripts/maintenance",
        "scripts/setup",
        "app/services/synthesis",
        "app/services/intelligence",
        "app/models/synthesis",
        "app/models/intelligence",
        "app/routes",
    ]
    
    for dir_path in check_dirs:
        full_dir = base_path / dir_path
        if full_dir.exists() and full_dir.is_dir():
            # Check if directory is empty
            if not any(full_dir.iterdir()):
                try:
                    full_dir.rmdir()
                    empty_dirs.append(dir_path)
                    print(f"   [OK] Removed empty directory: {dir_path}")
                except Exception as e:
                    print(f"   [ERROR] Error removing directory {dir_path}: {e}")
    
    print(f"\n   Removed {len(empty_dirs)} empty directories.\n")
    
    # Summary
    print("=== Cleanup Summary ===")
    print(f"Files deleted: {deleted_count}")
    print(f"Files/directories archived: {archived_count}")
    print(f"Empty directories removed: {len(empty_dirs)}")
    print(f"\nArchived files can be found in: {archive_base}")
    
    # Create summary file
    summary_file = archive_base / "CLEANUP_SUMMARY.md"
    with open(summary_file, "w") as f:
        f.write("# Pre-v3.0.0 Cleanup Summary\n\n")
        from datetime import datetime
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d')}\n\n")
        f.write("## Files Deleted (Empty Stubs)\n")
        for file in DELETE_FILES:
            f.write(f"- {file}\n")
        f.write(f"\nTotal: {deleted_count} files\n\n")
        
        f.write("## Files Archived\n")
        for category, files in ARCHIVE_FILES.items():
            f.write(f"\n### {category}\n")
            for file in files:
                f.write(f"- {file}\n")
        
        f.write("\n## Directories Archived\n")
        for category, dir_path in ARCHIVE_DIRS.items():
            f.write(f"- {dir_path} -> {category}\n")
        
        f.write(f"\n## Empty Directories Removed\n")
        for dir_path in empty_dirs:
            f.write(f"- {dir_path}\n")
    
    print(f"\nCleanup summary written to: {summary_file}")


if __name__ == "__main__":
    main()