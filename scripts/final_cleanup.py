#!/usr/bin/env python3
"""
Final cleanup of remaining code smells and stubs
"""
import shutil
from datetime import datetime
from pathlib import Path


def main():
    # Additional files to archive
    files_to_archive = [
        # Stub synthesis services
        "app/services/synthesis/consolidation_engine.py",
        "app/services/synthesis/graph_metrics_service.py",
        "app/services/synthesis/knowledge_summarizer.py",
        "app/services/synthesis/suggestion_engine.py",

        # Migration-related files
        "app/database_migrations.py",
        "app/memory_migrations.py",

        # Factories with many stub methods
        "app/factories/dependency_container.py",
        "app/factories/repository_factory.py",
        "app/factories/service_factory.py",

        # Empty/stub implementations
        "app/services/service_factory.py",  # Just has 'pass'

        # Batch processing (replaced by bulk_operations_routes.py)
        "app/batch_classification_engine.py",

        # Mock/test utilities in main codebase
        # Keep database_mock.py - already archived
    ]

    # Create archive directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = Path(f"archive/final_cleanup_{timestamp}")
    archive_dir.mkdir(parents=True, exist_ok=True)

    archived_count = 0
    errors = []

    print("="*60)
    print("FINAL CLEANUP - Removing Stubs and Unused Code")
    print("="*60)

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

    # Clean up empty synthesis directory if needed
    synthesis_dir = Path("app/services/synthesis")
    if synthesis_dir.exists():
        remaining_files = list(synthesis_dir.glob("*.py"))
        if len(remaining_files) <= 1:  # Only __init__.py or empty
            print(f"[INFO] Synthesis directory has only {len(remaining_files)} files remaining")

    # Summary
    print(f"\n{'='*60}")
    print(f"Archived {archived_count} additional files to {archive_dir}")

    # Recommendations
    print("\n[NEXT STEPS]")
    print("1. Update imports in tests that reference archived files")
    print("2. Consider implementing needed functionality or removing tests")
    print("3. The interfaces/ directory should stay (abstract base classes)")
    print("4. Repository base classes can stay (they define contracts)")

    # Create summary file
    summary_file = archive_dir / "CLEANUP_SUMMARY.md"
    with open(summary_file, "w") as f:
        f.write(f"# Final Cleanup - {timestamp}\n\n")
        f.write(f"Total files archived: {archived_count}\n\n")
        f.write("## Archived Files\n\n")
        f.write("### Stub Services\n")
        f.write("- Synthesis services with only stub implementations\n\n")
        f.write("### Migration Files\n")
        f.write("- One-time migration utilities\n\n")
        f.write("### Factory Stubs\n")
        f.write("- Factory classes with many unimplemented methods\n\n")

        if errors:
            f.write("\n## Errors\n\n")
            for error in errors:
                f.write(f"- {error}\n")

if __name__ == "__main__":
    main()
