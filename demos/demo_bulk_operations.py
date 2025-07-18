#!/usr/bin/env python3
"""
Comprehensive Bulk Operations Demo
Demonstrates import/export, migration, classification, and deduplication functionality
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, List

from app.bulk_memory_manager import (
    BulkMemoryManager, ImportFormat, ExportFormat, ImportResult, ExportResult
)
from app.memory_migration_tools import (
    MigrationManager, MigrationConfig, MemoryTypeMigration
)
from app.batch_classification_engine import (
    BatchClassificationEngine, ClassificationConfig, ClassificationMethod
)
from app.memory_deduplication_engine import (
    MemoryDeduplicationEngine, DeduplicationConfig, SimilarityMethod, DuplicateAction
)


async def demo_bulk_import_export():
    """Demonstrate bulk import and export functionality"""
    print("\n🚀 BULK IMPORT/EXPORT DEMONSTRATION")
    print("=" * 60)
    
    bulk_manager = BulkMemoryManager()
    
    # Sample data for import
    sample_memories = [
        {
            "content": "Python is a high-level programming language known for its simplicity and readability.",
            "metadata": {"type": "semantic", "category": "programming", "tags": ["python", "programming"]},
            "memory_type": "semantic"
        },
        {
            "content": "Yesterday I attended a fascinating conference about artificial intelligence trends.",
            "metadata": {"type": "episodic", "category": "experience", "tags": ["conference", "ai"]},
            "memory_type": "episodic"
        },
        {
            "content": "To create a virtual environment in Python: 1) Install virtualenv, 2) Run 'python -m venv myenv', 3) Activate with 'source myenv/bin/activate'",
            "metadata": {"type": "procedural", "category": "tutorial", "tags": ["python", "setup"]},
            "memory_type": "procedural"
        },
        {
            "content": "Machine learning algorithms can be categorized into supervised, unsupervised, and reinforcement learning.",
            "metadata": {"type": "semantic", "category": "ai", "tags": ["machine learning", "algorithms"]},
            "memory_type": "semantic"
        },
        {
            "content": "Remember to update the project documentation before the deadline next Friday.",
            "metadata": {"type": "episodic", "category": "task", "tags": ["documentation", "deadline"]},
            "memory_type": "episodic"
        }
    ]
    
    print(f"📥 Importing {len(sample_memories)} sample memories...")
    
    # Test JSON import
    start_time = time.time()
    import_result = await bulk_manager.import_memories(
        data=sample_memories,
        format_type=ImportFormat.JSON,
        options={"check_duplicates": True}
    )
    import_time = time.time() - start_time
    
    print(f"✅ Import completed in {import_time:.2f}s")
    print(f"   📊 Total processed: {import_result.total_processed}")
    print(f"   ✅ Successful: {import_result.successful_imports}")
    print(f"   ❌ Failed: {import_result.failed_imports}")
    print(f"   🔄 Duplicates: {import_result.duplicate_count}")
    
    if import_result.errors:
        print(f"   ⚠️ Errors: {import_result.errors[:3]}")  # Show first 3 errors
    
    # Test CSV import
    csv_data = """content,memory_type,category,tags
"FastAPI is a modern web framework for building APIs with Python","semantic","programming","fastapi,python,web"
"Today I learned about async programming patterns","episodic","learning","async,programming"
"To deploy with Docker: 1) Create Dockerfile 2) Build image 3) Run container","procedural","deployment","docker,deployment"
"""
    
    print(f"\n📥 Importing CSV data...")
    csv_import_result = await bulk_manager.import_memories(
        data=csv_data,
        format_type=ImportFormat.CSV,
        options={"has_header": True, "delimiter": ","}
    )
    
    print(f"✅ CSV import: {csv_import_result.successful_imports} memories imported")
    
    # Test export in multiple formats
    print(f"\n📤 Exporting memories in different formats...")
    
    export_formats = [
        (ExportFormat.JSON, "JSON"),
        (ExportFormat.CSV, "CSV"),
        (ExportFormat.MARKDOWN, "Markdown"),
        (ExportFormat.XML, "XML")
    ]
    
    for format_type, format_name in export_formats:
        try:
            start_time = time.time()
            export_result = await bulk_manager.export_memories(
                filter_criteria={"memory_type": "semantic"},
                format_type=format_type,
                options={}
            )
            export_time = time.time() - start_time
            
            print(f"   ✅ {format_name}: {export_result.total_exported} memories, "
                  f"{export_result.file_size_bytes} bytes, {export_time:.2f}s")
            
            # Show sample of exported content for JSON
            if format_type == ExportFormat.JSON and export_result.file_content:
                content_str = export_result.file_content.decode('utf-8')[:200]
                print(f"      Sample: {content_str}...")
                
        except Exception as e:
            print(f"   ❌ {format_name} export failed: {e}")


async def demo_memory_migration():
    """Demonstrate memory migration functionality"""
    print("\n🔄 MEMORY MIGRATION DEMONSTRATION")
    print("=" * 60)
    
    migration_manager = MigrationManager()
    
    # Create a memory type migration
    print("📝 Creating memory type migration: 'semantic' → 'knowledge'")
    
    migration_id = migration_manager.create_memory_type_migration(
        from_type="semantic",
        to_type="knowledge",
        filter_criteria={"content_contains": "programming"}
    )
    
    print(f"✅ Migration created with ID: {migration_id}")
    
    # Validate migration
    print("🔍 Validating migration...")
    is_valid, validation_errors = await migration_manager.validate_migration(migration_id)
    
    if is_valid:
        print("✅ Migration validation passed")
    else:
        print(f"❌ Migration validation failed: {validation_errors}")
        return
    
    # Configure migration
    config = MigrationConfig(
        batch_size=10,
        backup_before_migration=True,
        validate_before_execution=True,
        rollback_on_failure=True
    )
    
    print("🚀 Executing migration...")
    start_time = time.time()
    
    try:
        result = await migration_manager.execute_migration(migration_id, config)
        migration_time = time.time() - start_time
        
        print(f"✅ Migration completed in {migration_time:.2f}s")
        print(f"   📊 Status: {result.status.value}")
        print(f"   📝 Total records: {result.total_records}")
        print(f"   ✅ Processed: {result.processed_records}")
        print(f"   ✅ Successful: {result.successful_records}")
        print(f"   ❌ Failed: {result.failed_records}")
        
        if result.errors:
            print(f"   ⚠️ Errors: {result.errors[:3]}")
        
        if result.performance_metrics:
            print(f"   ⚡ Performance metrics: {result.performance_metrics}")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
    
    # List all migrations
    print("\n📋 Available migrations:")
    migrations = await migration_manager.list_available_migrations()
    for migration in migrations:
        print(f"   • {migration['name']} ({migration['migration_id']})")
        print(f"     Steps: {migration['steps']}, Dependencies: {migration['dependencies']}")


async def demo_batch_classification():
    """Demonstrate batch classification functionality"""
    print("\n🎯 BATCH CLASSIFICATION DEMONSTRATION")
    print("=" * 60)
    
    classification_engine = BatchClassificationEngine()
    
    # Sample memories for classification
    sample_memories = [
        {"id": "1", "content": "The capital of France is Paris. It's located in the northern part of the country.", "metadata": {}},
        {"id": "2", "content": "Yesterday I went to the grocery store and bought apples, bread, and milk.", "metadata": {}},
        {"id": "3", "content": "To bake a cake: 1) Preheat oven to 350°F, 2) Mix dry ingredients, 3) Add wet ingredients, 4) Bake for 30 minutes.", "metadata": {}},
        {"id": "4", "content": "Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data.", "metadata": {}},
        {"id": "5", "content": "I remember the first time I rode a bicycle. I was seven years old and my father taught me in the park.", "metadata": {}},
        {"id": "6", "content": "How to install Python: 1) Download from python.org, 2) Run the installer, 3) Add to PATH, 4) Verify installation.", "metadata": {}},
    ]
    
    print(f"🎯 Classifying {len(sample_memories)} memories...")
    
    # Test different classification methods
    methods = [
        (ClassificationMethod.KEYWORD_BASED, "Keyword-based"),
        (ClassificationMethod.SEMANTIC_SIMILARITY, "Semantic similarity"),
        (ClassificationMethod.PATTERN_MATCHING, "Pattern matching"),
        (ClassificationMethod.HYBRID, "Hybrid approach")
    ]
    
    for method, method_name in methods:
        print(f"\n📊 Testing {method_name} classification...")
        
        config = ClassificationConfig(
            method=method,
            batch_size=10,
            confidence_threshold=0.5,
            parallel_workers=2,
            enable_caching=True
        )
        
        start_time = time.time()
        result = await classification_engine.classify_batch(sample_memories, config)
        classification_time = time.time() - start_time
        
        print(f"✅ Classification completed in {classification_time:.2f}s")
        print(f"   📊 Processed: {result.processed_memories}")
        print(f"   ✅ Successful: {result.successful_classifications}")
        print(f"   ❌ Failed: {result.failed_classifications}")
        print(f"   ⚡ Throughput: {result.performance_metrics.get('throughput', 0):.1f} memories/sec")
        print(f"   🎯 Avg confidence: {result.performance_metrics.get('avg_confidence', 0):.2f}")
        
        # Show classification results
        print("   🏷️ Classification results:")
        for classification in result.classification_results[:3]:  # Show first 3
            print(f"      Memory {classification.memory_id}: {classification.predicted_type} "
                  f"(confidence: {classification.confidence:.2f})")
        
        if result.errors:
            print(f"   ⚠️ Errors: {result.errors[:2]}")
    
    # Show engine statistics
    print(f"\n📈 Classification engine statistics:")
    stats = classification_engine.get_classification_statistics()
    print(f"   💾 Cache size: {stats.get('cache_size', 0)}")
    print(f"   🔧 Available methods: {stats.get('available_methods', [])}")


async def demo_memory_deduplication():
    """Demonstrate memory deduplication functionality"""
    print("\n🧹 MEMORY DEDUPLICATION DEMONSTRATION")
    print("=" * 60)
    
    deduplication_engine = MemoryDeduplicationEngine()
    
    # Sample memories with intentional duplicates
    sample_memories = [
        {"id": "1", "content": "Python is a programming language", "metadata": {"type": "semantic"}, "created_at": "2024-01-01"},
        {"id": "2", "content": "Python is a programming language", "metadata": {"type": "semantic"}, "created_at": "2024-01-02"},  # Exact duplicate
        {"id": "3", "content": "Python is a programming language used for development", "metadata": {"type": "semantic"}, "created_at": "2024-01-03"},  # Similar
        {"id": "4", "content": "JavaScript is a web programming language", "metadata": {"type": "semantic"}, "created_at": "2024-01-04"},
        {"id": "5", "content": "I went to the store yesterday", "metadata": {"type": "episodic"}, "created_at": "2024-01-05"},
        {"id": "6", "content": "Yesterday I went to the store", "metadata": {"type": "episodic"}, "created_at": "2024-01-06"},  # Fuzzy duplicate
        {"id": "7", "content": "How to install Python packages with pip", "metadata": {"type": "procedural"}, "created_at": "2024-01-07"},
    ]
    
    print(f"🔍 Analyzing {len(sample_memories)} memories for duplicates...")
    
    # Test different similarity methods
    methods = [
        (SimilarityMethod.EXACT_MATCH, "Exact matching"),
        (SimilarityMethod.FUZZY_MATCH, "Fuzzy matching"),
        (SimilarityMethod.SEMANTIC_SIMILARITY, "Semantic similarity"),
        (SimilarityMethod.HYBRID, "Hybrid approach")
    ]
    
    for method, method_name in methods:
        print(f"\n🎯 Testing {method_name}...")
        
        config = DeduplicationConfig(
            similarity_method=method,
            similarity_threshold=0.8,
            content_weight=0.7,
            metadata_weight=0.2,
            structural_weight=0.1,
            duplicate_action=DuplicateAction.MARK_DUPLICATE,
            dry_run=True  # Don't actually modify data
        )
        
        start_time = time.time()
        result = await deduplication_engine.deduplicate_memories(config, None)
        dedup_time = time.time() - start_time
        
        print(f"✅ Deduplication completed in {dedup_time:.2f}s")
        print(f"   📊 Total memories: {result.total_memories}")
        print(f"   🔍 Duplicate groups found: {result.duplicate_groups_found}")
        print(f"   📝 Total duplicates: {result.total_duplicates}")
        print(f"   📈 Duplicate rate: {result.performance_metrics.get('duplicate_rate', 0):.1%}")
        
        # Show duplicate groups
        if result.duplicate_groups:
            print("   🏷️ Duplicate groups:")
            for group in result.duplicate_groups[:2]:  # Show first 2 groups
                print(f"      Group {group.group_id}: {len(group.memory_ids)} memories")
                print(f"      Primary: {group.primary_memory_id}")
                print(f"      Similarities: {len(group.similarity_scores)} scores")
                
                # Show similarity details
                for score in group.similarity_scores[:1]:  # Show first similarity
                    print(f"        {score.memory_id_1} ↔ {score.memory_id_2}: "
                          f"{score.overall_similarity:.2f} ({score.reasoning})")
        
        if result.errors:
            print(f"   ⚠️ Errors: {result.errors[:2]}")
    
    # Show deduplication statistics
    print(f"\n📈 Deduplication engine statistics:")
    stats = deduplication_engine.get_deduplication_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")


async def demo_integrated_workflow():
    """Demonstrate integrated workflow using all systems"""
    print("\n🔗 INTEGRATED WORKFLOW DEMONSTRATION")
    print("=" * 60)
    
    print("🚀 Running integrated workflow:")
    print("   1. Import diverse memory data")
    print("   2. Classify memories by type")
    print("   3. Deduplicate similar memories")
    print("   4. Migrate memory types if needed")
    print("   5. Export final dataset")
    
    # Step 1: Import
    print(f"\n📥 Step 1: Importing sample dataset...")
    bulk_manager = BulkMemoryManager()
    
    diverse_memories = [
        {"content": "Artificial intelligence mimics human cognitive functions", "metadata": {"source": "textbook"}},
        {"content": "AI mimics human cognitive functions", "metadata": {"source": "notes"}},  # Similar to above
        {"content": "Today I attended an AI conference in San Francisco", "metadata": {"source": "diary"}},
        {"content": "To install TensorFlow: pip install tensorflow", "metadata": {"source": "tutorial"}},
        {"content": "Neural networks are inspired by biological neurons", "metadata": {"source": "research"}},
        {"content": "I remember my first programming class in college", "metadata": {"source": "memory"}},
        {"content": "Step 1: Import data, Step 2: Preprocess, Step 3: Train model", "metadata": {"source": "guide"}},
    ]
    
    import_result = await bulk_manager.import_memories(
        data=diverse_memories,
        format_type=ImportFormat.JSON
    )
    print(f"   ✅ Imported {import_result.successful_imports} memories")
    
    # Step 2: Classification
    print(f"\n🎯 Step 2: Classifying memories...")
    classification_engine = BatchClassificationEngine()
    
    config = ClassificationConfig(
        method=ClassificationMethod.HYBRID,
        confidence_threshold=0.6,
        auto_apply_results=False
    )
    
    classification_result = await classification_engine.classify_batch(diverse_memories, config)
    print(f"   ✅ Classified {classification_result.successful_classifications} memories")
    
    # Show classification distribution
    type_dist = classification_result.performance_metrics.get('type_distribution', {})
    print(f"   📊 Type distribution: {type_dist}")
    
    # Step 3: Deduplication
    print(f"\n🧹 Step 3: Deduplicating memories...")
    deduplication_engine = MemoryDeduplicationEngine()
    
    dedup_config = DeduplicationConfig(
        similarity_method=SimilarityMethod.HYBRID,
        similarity_threshold=0.85,
        duplicate_action=DuplicateAction.MARK_DUPLICATE,
        dry_run=True
    )
    
    dedup_result = await deduplication_engine.deduplicate_memories(dedup_config)
    print(f"   ✅ Found {dedup_result.total_duplicates} duplicates in {dedup_result.duplicate_groups_found} groups")
    
    # Step 4: Export
    print(f"\n📤 Step 4: Exporting processed dataset...")
    export_result = await bulk_manager.export_memories(
        format_type=ExportFormat.JSON,
        options={"include_metadata": True}
    )
    print(f"   ✅ Exported {export_result.total_exported} memories ({export_result.file_size_bytes} bytes)")
    
    print(f"\n🎉 Integrated workflow completed successfully!")
    print(f"   📊 Final statistics:")
    print(f"      • Imported: {import_result.successful_imports} memories")
    print(f"      • Classified: {classification_result.successful_classifications} memories")
    print(f"      • Duplicates found: {dedup_result.total_duplicates}")
    print(f"      • Final dataset: {export_result.total_exported} unique memories")


async def main():
    """Run all bulk operations demonstrations"""
    print("🚀 SECOND BRAIN - BULK OPERATIONS COMPREHENSIVE DEMO")
    print("=" * 80)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    demos = [
        ("Bulk Import/Export", demo_bulk_import_export),
        ("Memory Migration", demo_memory_migration),
        ("Batch Classification", demo_batch_classification),
        ("Memory Deduplication", demo_memory_deduplication),
        ("Integrated Workflow", demo_integrated_workflow),
    ]
    
    total_start_time = time.time()
    
    for demo_name, demo_func in demos:
        try:
            print(f"\n{'='*20} {demo_name.upper()} {'='*20}")
            demo_start = time.time()
            await demo_func()
            demo_time = time.time() - demo_start
            print(f"\n✅ {demo_name} completed in {demo_time:.2f}s")
        except Exception as e:
            print(f"\n❌ {demo_name} failed: {e}")
            import traceback
            traceback.print_exc()
    
    total_time = time.time() - total_start_time
    
    print(f"\n{'='*80}")
    print(f"🎉 ALL DEMONSTRATIONS COMPLETED!")
    print(f"⏱️ Total time: {total_time:.2f}s")
    print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(main()) 