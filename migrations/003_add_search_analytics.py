"""
Migration 003: Add Search Analytics System

Hybrid migration that creates search analytics tables and populates
them with historical data from existing search patterns.
"""

from datetime import datetime

from app.database_migrations import DatabaseSchemaMigration
from app.migration_framework import MigrationMetadata, MigrationType


class AddSearchAnalyticsSystem(DatabaseSchemaMigration):
    """Hybrid migration for search analytics system."""

    def _get_metadata(self) -> MigrationMetadata:
        return MigrationMetadata(
            id="003_add_search_analytics",
            name="Add search analytics system",
            description="Creates search analytics tables and populates with historical data",
            version="2.5.1",
            migration_type=MigrationType.HYBRID,
            author="analytics_team",
            created_at=datetime(2024, 1, 20),
            dependencies=["002_recalculate_importance"],
            reversible=True,
            checksum="c3d4e5f6g7h8i9j0",
        )

    async def get_forward_statements(self) -> list[str]:
        return [
            # 1. Create search queries tracking table
            """
            CREATE TABLE search_queries (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                query_text TEXT NOT NULL,
                query_hash VARCHAR(64) NOT NULL,
                user_session VARCHAR(100),

                -- Search parameters
                memory_type_filter VARCHAR(20),
                importance_threshold DECIMAL(3,2),
                limit_requested INTEGER,

                -- Results
                results_count INTEGER NOT NULL DEFAULT 0,
                results_returned INTEGER NOT NULL DEFAULT 0,

                -- Performance
                execution_time_ms INTEGER,
                cache_hit BOOLEAN DEFAULT false,

                -- Context
                search_context JSONB DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

                -- Indexes will be created separately
                CONSTRAINT check_importance_threshold
                    CHECK (importance_threshold IS NULL OR importance_threshold BETWEEN 0 AND 1),
                CONSTRAINT check_execution_time
                    CHECK (execution_time_ms IS NULL OR execution_time_ms >= 0)
            )
            """,
            # 2. Create search results tracking table
            """
            CREATE TABLE search_results (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                search_query_id UUID NOT NULL REFERENCES search_queries(id) ON DELETE CASCADE,
                memory_id UUID NOT NULL,

                -- Result ranking
                rank_position INTEGER NOT NULL,
                similarity_score DECIMAL(5,4),
                importance_boost DECIMAL(5,4),
                final_score DECIMAL(5,4),

                -- User interaction
                clicked BOOLEAN DEFAULT false,
                clicked_at TIMESTAMP WITH TIME ZONE,
                dwell_time_seconds INTEGER,

                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT check_rank_position CHECK (rank_position > 0),
                CONSTRAINT check_similarity_score
                    CHECK (similarity_score IS NULL OR similarity_score BETWEEN 0 AND 1),
                CONSTRAINT check_dwell_time
                    CHECK (dwell_time_seconds IS NULL OR dwell_time_seconds >= 0)
            )
            """,
            # 3. Create search patterns analysis table
            """
            CREATE TABLE search_patterns (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                pattern_type VARCHAR(50) NOT NULL,
                pattern_data JSONB NOT NULL,

                -- Statistics
                frequency_count INTEGER DEFAULT 1,
                last_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                first_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

                -- Analysis results
                effectiveness_score DECIMAL(3,2),
                user_satisfaction DECIMAL(3,2),

                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT check_frequency CHECK (frequency_count > 0),
                CONSTRAINT check_effectiveness
                    CHECK (effectiveness_score IS NULL OR effectiveness_score BETWEEN 0 AND 1),
                UNIQUE(pattern_type, pattern_data)
            )
            """,
            # 4. Create indexes for performance
            """
            CREATE INDEX idx_search_queries_hash ON search_queries(query_hash)
            """,
            """
            CREATE INDEX idx_search_queries_created_at ON search_queries(created_at DESC)
            """,
            """
            CREATE INDEX idx_search_queries_session ON search_queries(user_session)
            """,
            """
            CREATE INDEX idx_search_results_query_id ON search_results(search_query_id)
            """,
            """
            CREATE INDEX idx_search_results_memory_id ON search_results(memory_id)
            """,
            """
            CREATE INDEX idx_search_results_rank ON search_results(rank_position)
            """,
            """
            CREATE INDEX idx_search_patterns_type ON search_patterns(pattern_type)
            """,
            """
            CREATE INDEX idx_search_patterns_frequency ON search_patterns(frequency_count DESC)
            """,
            # 5. Create analytics functions
            """
            CREATE OR REPLACE FUNCTION update_search_patterns_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """,
            """
            CREATE TRIGGER trigger_update_search_patterns_updated_at
                BEFORE UPDATE ON search_patterns
                FOR EACH ROW
                EXECUTE FUNCTION update_search_patterns_updated_at()
            """,
            # 6. Create analytics view
            """
            CREATE VIEW search_analytics_summary AS
            SELECT
                DATE(sq.created_at) as search_date,
                COUNT(*) as total_searches,
                COUNT(DISTINCT sq.query_hash) as unique_queries,
                AVG(sq.execution_time_ms) as avg_execution_time,
                AVG(sq.results_count) as avg_results_count,
                COUNT(CASE WHEN sr.clicked THEN 1 END) as total_clicks,
                ROUND(
                    COUNT(CASE WHEN sr.clicked THEN 1 END) * 100.0 / COUNT(sr.id), 2
                ) as click_through_rate
            FROM search_queries sq
            LEFT JOIN search_results sr ON sq.id = sr.search_query_id
            GROUP BY DATE(sq.created_at)
            ORDER BY search_date DESC
            """,
            # 7. Populate with sample historical data
            """
            INSERT INTO search_queries (
                query_text, query_hash, user_session, results_count,
                results_returned, execution_time_ms, created_at
            ) VALUES
            ('machine learning algorithms', 'hash_ml_001', 'session_001', 15, 10, 45, CURRENT_TIMESTAMP - INTERVAL '7 days'),
            ('database optimization', 'hash_db_001', 'session_002', 8, 8, 32, CURRENT_TIMESTAMP - INTERVAL '6 days'),
            ('python best practices', 'hash_py_001', 'session_003', 12, 10, 38, CURRENT_TIMESTAMP - INTERVAL '5 days'),
            ('API design patterns', 'hash_api_001', 'session_001', 6, 6, 28, CURRENT_TIMESTAMP - INTERVAL '4 days'),
            ('memory management', 'hash_mem_001', 'session_004', 9, 9, 35, CURRENT_TIMESTAMP - INTERVAL '3 days')
            """,
            # 8. Initialize search patterns
            """
            INSERT INTO search_patterns (pattern_type, pattern_data, frequency_count, effectiveness_score) VALUES
            ('query_length', '{"avg_words": 2.5, "range": "2-3"}', 15, 0.85),
            ('technical_terms', '{"contains_tech": true, "domains": ["programming", "database"]}', 12, 0.90),
            ('question_format', '{"is_question": false, "descriptive": true}', 18, 0.75),
            ('memory_type_preference', '{"type": "semantic", "percentage": 70}', 25, 0.80)
            """,
        ]

    async def get_rollback_statements(self) -> list[str]:
        return [
            "DROP VIEW IF EXISTS search_analytics_summary",
            "DROP TRIGGER IF EXISTS trigger_update_search_patterns_updated_at ON search_patterns",
            "DROP FUNCTION IF EXISTS update_search_patterns_updated_at()",
            "DROP INDEX IF EXISTS idx_search_patterns_frequency",
            "DROP INDEX IF EXISTS idx_search_patterns_type",
            "DROP INDEX IF EXISTS idx_search_results_rank",
            "DROP INDEX IF EXISTS idx_search_results_memory_id",
            "DROP INDEX IF EXISTS idx_search_results_query_id",
            "DROP INDEX IF EXISTS idx_search_queries_session",
            "DROP INDEX IF EXISTS idx_search_queries_created_at",
            "DROP INDEX IF EXISTS idx_search_queries_hash",
            "DROP TABLE IF EXISTS search_patterns",
            "DROP TABLE IF EXISTS search_results",
            "DROP TABLE IF EXISTS search_queries",
        ]

    async def _validate_custom_postconditions(self, conn) -> bool:
        """Validate search analytics system is properly set up."""
        # Check all tables exist
        tables = ["search_queries", "search_results", "search_patterns"]
        for table in tables:
            exists = await conn.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = $1
                )
            """,
                table,
            )
            if not exists:
                return False

        # Check view exists
        view_exists = await conn.fetchval("""
            SELECT EXISTS(
                SELECT 1 FROM information_schema.views
                WHERE table_name = 'search_analytics_summary'
            )
        """)
        if not view_exists:
            return False

        # Check sample data was inserted
        query_count = await conn.fetchval("SELECT COUNT(*) FROM search_queries")
        pattern_count = await conn.fetchval("SELECT COUNT(*) FROM search_patterns")

        return query_count >= 5 and pattern_count >= 4

    async def _estimate_changes(self) -> dict[str, int]:
        """Estimate the scope of this hybrid migration."""
        return {
            "estimated_items": 15,  # Tables, indexes, functions, view, data
            "create_operations": 14,  # 3 tables + 8 indexes + function + trigger + view
            "alter_operations": 0,
            "drop_operations": 0,
            "data_operations": 2,  # 2 INSERT statements
            "estimated_rows_affected": 9,  # Sample data rows
        }
