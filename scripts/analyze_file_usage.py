#!/usr/bin/env python3
"""
Analyze file usage in the codebase
"""
import os
from pathlib import Path
from collections import defaultdict

def main():
    # Collect all Python files
    all_files = set()
    for root, dirs, files in os.walk('app'):
        for file in files:
            if file.endswith('.py'):
                rel_path = os.path.relpath(os.path.join(root, file), 'app')
                all_files.add(rel_path)
    
    print(f"Total Python files in app/: {len(all_files)}")
    
    # Files that are likely unused based on functionality
    potentially_unused = {
        # Bulk operations (seem to have multiple versions)
        "bulk_memory_operations.py",
        "bulk_memory_operations_advanced.py",
        "bulk_validation_safety.py", 
        "bulk_performance_optimizer.py",
        "bulk_monitoring_analytics.py",
        
        # Old/duplicate functionality
        "dashboard_migrations.py",
        "database_importance_schema.py",
        "memory_migration_tools.py",
        "migration_engine.py",
        "migration_framework.py",
        "cross_memory_relationships.py",
        
        # Unused ingestion modules
        "ingestion/streaming_ingestion.py",
        "ingestion/domain_classifier.py",
        "ingestion/preprocessor.py",
        
        # Unused services
        "services/git_service.py",
        "services/graph_query_parser.py",
        "services/deduplication_orchestrator.py",
        "services/memory_merger.py",
        "services/similarity_analyzers.py",
        
        # Synthesis modules that might be redundant
        "services/synthesis/export_import.py",
        "services/synthesis/graph_visualization.py",
        "services/synthesis/workflow_automation.py",
        
        # Observer pattern (unused)
        "observers/cache_observer.py",
        "observers/metrics_observer.py",
        "observers/observable.py",
        "observers/websocket_observer.py",
        
        # Routes that were restored but might not be used
        "routes/migration_routes.py",
        "routes/github_routes.py",
        "routes/bulk_routes.py", 
        "routes/todo_routes.py",
        
        # Other potentially unused
        "shared.py",
        "version.py",
        "database_mock.py",
    }
    
    # Categorize files
    core_files = {
        "app.py", "config.py", "database.py", "dependencies.py",
        "models/memory.py", "routes/memory_routes.py", "services/memory_service.py"
    }
    
    print("\n[CORE FILES] (definitely keep):")
    for f in sorted(core_files):
        if f in all_files or f.replace('/', os.sep) in all_files:
            print(f"  - {f}")
    
    print("\n[POTENTIALLY UNUSED FILES]:")
    found_unused = []
    for f in sorted(potentially_unused):
        if f in all_files or f.replace('/', os.sep) in all_files:
            found_unused.append(f)
            print(f"  - {f}")
    
    print(f"\nTotal potentially unused: {len(found_unused)} files")
    
    # Active modules based on imports in app.py
    print("\n[ACTIVELY USED] (imported in app.py):")
    active_modules = [
        "routes/__init__.py",
        "connection_pool.py",
        "conversation_processor.py", 
        "dashboard_api.py",
        "docs.py",
        "security.py",
        "services/service_factory.py",
        "session_api.py",
        "session_manager.py",
        "shared.py",
    ]
    for f in sorted(active_modules):
        print(f"  - {f}")

if __name__ == "__main__":
    main()