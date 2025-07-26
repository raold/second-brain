#!/usr/bin/env python3
"""
Archive unused files to clean up the codebase
"""
import os
import shutil
from pathlib import Path
from datetime import datetime

def main():
    # Files to archive
    files_to_archive = [
        # Bulk operations duplicates
        "app/bulk_memory_operations.py",
        "app/bulk_memory_operations_advanced.py",
        "app/bulk_validation_safety.py", 
        "app/bulk_performance_optimizer.py",
        "app/bulk_monitoring_analytics.py",
        
        # Migration/schema files
        "app/dashboard_migrations.py",
        "app/database_importance_schema.py",
        "app/memory_migration_tools.py",
        "app/migration_engine.py",
        "app/migration_framework.py",
        "app/cross_memory_relationships.py",
        
        # Unused ingestion modules
        "app/ingestion/streaming_ingestion.py",
        "app/ingestion/domain_classifier.py",
        "app/ingestion/preprocessor.py",
        
        # Unused services
        "app/services/git_service.py",
        "app/services/graph_query_parser.py",
        "app/services/deduplication_orchestrator.py",
        "app/services/memory_merger.py",
        "app/services/similarity_analyzers.py",
        "app/services/synthesis/export_import.py",
        "app/services/synthesis/graph_visualization.py",
        "app/services/synthesis/workflow_automation.py",
        
        # Observer pattern (entire directory)
        "app/observers/cache_observer.py",
        "app/observers/metrics_observer.py",
        "app/observers/observable.py",
        "app/observers/websocket_observer.py",
        
        # Unused restored routes
        "app/routes/bulk_routes.py",
        "app/routes/github_routes.py",
        "app/routes/migration_routes.py",
        "app/routes/todo_routes.py",
        
        # Other unused files
        "app/database_mock.py",
        "app/version.py",  # Keep if actually used
        "app/shared.py",   # Keep - imported in app.py
    ]
    
    # Create archive directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = Path(f"archive/cleanup_{timestamp}")
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    archived_count = 0
    errors = []
    
    for file_path in files_to_archive:
        src = Path(file_path)
        if src.exists():
            # Create destination preserving directory structure
            rel_path = src.relative_to("app")
            dst = archive_dir / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                shutil.move(str(src), str(dst))
                print(f"[ARCHIVED] {file_path}")
                archived_count += 1
            except Exception as e:
                errors.append(f"{file_path}: {e}")
                print(f"[ERROR] {file_path}: {e}")
        else:
            print(f"[NOT FOUND] {file_path}")
    
    # Remove empty observer directory if all files archived
    observers_dir = Path("app/observers")
    if observers_dir.exists() and not any(observers_dir.iterdir()):
        observers_dir.rmdir()
        print("[REMOVED] Empty app/observers directory")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Archived {archived_count} files to {archive_dir}")
    if errors:
        print(f"\nErrors encountered:")
        for error in errors:
            print(f"  - {error}")
    
    # Create summary file
    summary_file = archive_dir / "ARCHIVE_SUMMARY.md"
    with open(summary_file, "w") as f:
        f.write(f"# Archive Summary - {timestamp}\n\n")
        f.write(f"Total files archived: {archived_count}\n\n")
        f.write("## Files Archived\n\n")
        for file_path in files_to_archive:
            if Path(file_path).exists():
                f.write(f"- {file_path}\n")
        if errors:
            f.write("\n## Errors\n\n")
            for error in errors:
                f.write(f"- {error}\n")
    
    print(f"\nSummary written to: {summary_file}")

if __name__ == "__main__":
    main()