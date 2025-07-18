#!/usr/bin/env python3
"""
Database Schema Updates for Importance Scoring System
Creates additional tables and indexes to support automated importance calculation
"""

import logging
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)


async def setup_importance_tracking_schema(pool: asyncpg.Pool) -> bool:
    """
    Set up database schema for importance tracking and access logging.

    Creates:
    1. memory_access_log - Track every memory access with context
    2. search_result_log - Track memory appearances in search results
    3. user_feedback_log - Track explicit user interactions
    4. importance_calculation_log - Audit trail of importance changes
    """
    try:
        async with pool.acquire() as conn:
            logger.info("Setting up importance tracking schema...")

            # Memory access log table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_access_log (
                    id SERIAL PRIMARY KEY,
                    memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
                    access_type VARCHAR(50) NOT NULL DEFAULT 'retrieval',
                    search_position INTEGER,
                    user_action VARCHAR(100),
                    session_id VARCHAR(100),
                    accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    response_time_ms INTEGER,
                    client_ip INET,
                    user_agent TEXT
                );
            """)

            # Search result log table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS search_result_log (
                    id SERIAL PRIMARY KEY,
                    memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
                    search_query TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    relevance_score DECIMAL(5,4),
                    clicked BOOLEAN DEFAULT FALSE,
                    click_timestamp TIMESTAMP WITH TIME ZONE,
                    session_id VARCHAR(100),
                    search_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)

            # User feedback log table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_feedback_log (
                    id SERIAL PRIMARY KEY,
                    memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
                    feedback_type VARCHAR(50) NOT NULL, -- 'upvote', 'downvote', 'save', 'share', 'edit'
                    feedback_value INTEGER, -- numeric feedback where applicable
                    feedback_text TEXT, -- textual feedback
                    session_id VARCHAR(100),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)

            # Importance calculation audit log
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS importance_calculation_log (
                    id SERIAL PRIMARY KEY,
                    memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
                    old_score DECIMAL(5,4),
                    new_score DECIMAL(5,4),
                    frequency_score DECIMAL(5,4),
                    recency_score DECIMAL(5,4),
                    search_relevance_score DECIMAL(5,4),
                    content_quality_score DECIMAL(5,4),
                    type_weight DECIMAL(5,4),
                    decay_factor DECIMAL(5,4),
                    confidence DECIMAL(5,4),
                    explanation TEXT,
                    calculation_reason VARCHAR(100), -- 'access_triggered', 'batch_update', 'manual'
                    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)

            # Performance indexes for access patterns
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_access_log_memory_id 
                ON memory_access_log(memory_id);
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_access_log_accessed_at 
                ON memory_access_log(accessed_at);
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_access_log_recent 
                ON memory_access_log(memory_id, accessed_at) 
                WHERE accessed_at > NOW() - INTERVAL '30 days';
            """)

            # Search result indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_search_result_log_memory_id 
                ON search_result_log(memory_id);
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_search_result_log_clicked 
                ON search_result_log(memory_id, clicked, click_timestamp) 
                WHERE clicked = TRUE;
            """)

            # User feedback indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_feedback_log_memory_id 
                ON user_feedback_log(memory_id, feedback_type);
            """)

            # Importance calculation indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_importance_calculation_log_memory_id 
                ON importance_calculation_log(memory_id, calculated_at);
            """)

            # Memory-specific performance views
            await conn.execute("""
                CREATE OR REPLACE VIEW memory_access_summary AS
                SELECT 
                    m.id,
                    m.content[1:100] as content_preview,
                    m.memory_type,
                    m.importance_score,
                    m.access_count,
                    m.last_accessed,
                    COALESCE(recent.recent_accesses, 0) as recent_accesses_7d,
                    COALESCE(search.search_appearances, 0) as search_appearances,
                    COALESCE(search.avg_position, 10.0) as avg_search_position,
                    COALESCE(search.click_rate, 0.0) as search_click_rate,
                    COALESCE(feedback.positive_feedback, 0) as positive_feedback,
                    COALESCE(feedback.negative_feedback, 0) as negative_feedback
                FROM memories m
                LEFT JOIN (
                    SELECT 
                        memory_id, 
                        COUNT(*) as recent_accesses
                    FROM memory_access_log 
                    WHERE accessed_at > NOW() - INTERVAL '7 days'
                    GROUP BY memory_id
                ) recent ON m.id = recent.memory_id
                LEFT JOIN (
                    SELECT 
                        memory_id,
                        COUNT(*) as search_appearances,
                        AVG(position) as avg_position,
                        COALESCE(AVG(CASE WHEN clicked THEN 1.0 ELSE 0.0 END), 0.0) as click_rate
                    FROM search_result_log
                    GROUP BY memory_id
                ) search ON m.id = search.memory_id
                LEFT JOIN (
                    SELECT 
                        memory_id,
                        SUM(CASE WHEN feedback_type IN ('upvote', 'save', 'share') THEN 1 ELSE 0 END) as positive_feedback,
                        SUM(CASE WHEN feedback_type IN ('downvote') THEN 1 ELSE 0 END) as negative_feedback
                    FROM user_feedback_log
                    GROUP BY memory_id
                ) feedback ON m.id = feedback.memory_id;
            """)

            # Trigger to update access_count automatically
            await conn.execute("""
                CREATE OR REPLACE FUNCTION update_memory_access_count()
                RETURNS TRIGGER AS $$
                BEGIN
                    UPDATE memories 
                    SET access_count = access_count + 1,
                        last_accessed = NEW.accessed_at
                    WHERE id = NEW.memory_id;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)

            await conn.execute("""
                DROP TRIGGER IF EXISTS trigger_update_memory_access_count ON memory_access_log;
            """)

            await conn.execute("""
                CREATE TRIGGER trigger_update_memory_access_count
                    AFTER INSERT ON memory_access_log
                    FOR EACH ROW EXECUTE FUNCTION update_memory_access_count();
            """)

            # Function to get importance analytics
            await conn.execute("""
                CREATE OR REPLACE FUNCTION get_importance_statistics()
                RETURNS TABLE(
                    total_memories BIGINT,
                    avg_importance DECIMAL,
                    high_importance_count BIGINT,
                    medium_importance_count BIGINT,
                    low_importance_count BIGINT,
                    most_accessed_today BIGINT,
                    least_accessed_month BIGINT
                ) AS $$
                BEGIN
                    RETURN QUERY
                    SELECT 
                        COUNT(*) as total_memories,
                        AVG(importance_score) as avg_importance,
                        COUNT(*) FILTER (WHERE importance_score >= 0.8) as high_importance_count,
                        COUNT(*) FILTER (WHERE importance_score >= 0.5 AND importance_score < 0.8) as medium_importance_count,
                        COUNT(*) FILTER (WHERE importance_score < 0.5) as low_importance_count,
                        COUNT(*) FILTER (WHERE last_accessed >= CURRENT_DATE) as most_accessed_today,
                        COUNT(*) FILTER (WHERE last_accessed < NOW() - INTERVAL '30 days' OR last_accessed IS NULL) as least_accessed_month
                    FROM memories;
                END;
                $$ LANGUAGE plpgsql;
            """)

            logger.info("✅ Importance tracking schema setup completed successfully")
            return True

    except Exception as e:
        logger.error(f"❌ Error setting up importance tracking schema: {e}")
        return False


async def create_sample_access_data(pool: asyncpg.Pool, memory_id: str) -> None:
    """Create sample access data for testing importance calculations"""
    try:
        async with pool.acquire() as conn:
            # Simulate various access patterns
            access_types = ["retrieval", "search_result", "direct_access", "api_call"]

            for i in range(10):
                await conn.execute(
                    """
                    INSERT INTO memory_access_log 
                    (memory_id, access_type, search_position, accessed_at)
                    VALUES ($1, $2, $3, NOW() - INTERVAL '%s days')
                """,
                    memory_id,
                    access_types[i % len(access_types)],
                    (i % 5) + 1,
                    str(i % 7),
                )

            # Add search result appearances
            queries = ["database optimization", "memory management", "performance tuning"]
            for i, query in enumerate(queries):
                await conn.execute(
                    """
                    INSERT INTO search_result_log 
                    (memory_id, search_query, position, relevance_score, clicked)
                    VALUES ($1, $2, $3, $4, $5)
                """,
                    memory_id,
                    query,
                    i + 1,
                    0.8 - (i * 0.1),
                    i == 0,
                )

            # Add user feedback
            await conn.execute(
                """
                INSERT INTO user_feedback_log 
                (memory_id, feedback_type, feedback_value)
                VALUES ($1, 'upvote', 1), ($1, 'save', 1)
            """,
                memory_id,
            )

            logger.info(f"Created sample access data for memory {memory_id}")

    except Exception as e:
        logger.error(f"Error creating sample access data: {e}")


async def cleanup_old_access_logs(pool: asyncpg.Pool, days_to_keep: Any) -> dict[str, Any]:
    """
    Clean up old access logs to prevent database bloat.
    Keeps detailed logs for recent activity, summarizes older data.
    """
    try:
        async with pool.acquire() as conn:
            cutoff_date = f"NOW() - INTERVAL '{days_to_keep} days'"

            # Count records to be cleaned
            old_access_count = await conn.fetchval(f"""
                SELECT COUNT(*) FROM memory_access_log 
                WHERE accessed_at < {cutoff_date}
            """)

            old_search_count = await conn.fetchval(f"""
                SELECT COUNT(*) FROM search_result_log 
                WHERE search_timestamp < {cutoff_date}
            """)

            # Clean up old access logs (keep summary in memories table)
            await conn.execute(f"""
                DELETE FROM memory_access_log 
                WHERE accessed_at < {cutoff_date}
            """)

            # Clean up old search logs (keep summary data)
            await conn.execute(f"""
                DELETE FROM search_result_log 
                WHERE search_timestamp < {cutoff_date}
            """)

            # Clean up old importance calculation logs (keep recent ones for analysis)
            old_calc_count = await conn.fetchval(f"""
                SELECT COUNT(*) FROM importance_calculation_log 
                WHERE calculated_at < {cutoff_date}
            """)

            await conn.execute(f"""
                DELETE FROM importance_calculation_log 
                WHERE calculated_at < {cutoff_date}
            """)

            logger.info(
                f"Cleaned up {old_access_count} access logs, {old_search_count} search logs, {old_calc_count} calculation logs"
            )

            return {
                "access_logs_cleaned": old_access_count,
                "search_logs_cleaned": old_search_count,
                "calculation_logs_cleaned": old_calc_count,
                "cutoff_days": days_to_keep,
            }

    except Exception as e:
        logger.error(f"Error cleaning up old access logs: {e}")
        return {"error": str(e)}


async def get_memory_importance_history(pool: asyncpg.Pool, memory_id: str, limit: int = 20) -> list[dict]:
    """Get the importance score history for a specific memory"""
    try:
        async with pool.acquire() as conn:
            history = await conn.fetch(
                """
                SELECT 
                    old_score,
                    new_score,
                    frequency_score,
                    recency_score,
                    search_relevance_score,
                    content_quality_score,
                    explanation,
                    calculation_reason,
                    calculated_at
                FROM importance_calculation_log
                WHERE memory_id = $1
                ORDER BY calculated_at DESC
                LIMIT $2
            """,
                memory_id,
                limit,
            )

            return [dict(row) for row in history]

    except Exception as e:
        logger.error(f"Error getting importance history for {memory_id}: {e}")
        return []
