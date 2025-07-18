"""
Migration 001: Add User Preferences Table

Creates a user preferences table to store dashboard themes, notification settings,
and other user-specific configuration options.
"""

from datetime import datetime

from app.database_migrations import DatabaseSchemaMigration
from app.migration_framework import MigrationMetadata, MigrationType


class AddUserPreferencesTable(DatabaseSchemaMigration):
    """Migration to add user preferences functionality."""
    
    def _get_metadata(self) -> MigrationMetadata:
        return MigrationMetadata(
            id="001_add_user_preferences",
            name="Add user preferences table",
            description="Creates table for storing user preferences including themes and settings",
            version="2.5.0",
            migration_type=MigrationType.DATABASE_SCHEMA,
            author="system",
            created_at=datetime(2024, 1, 15),
            dependencies=[],
            reversible=True,
            checksum="a1b2c3d4e5f6g7h8"
        )
    
    def get_required_extensions(self) -> list[str]:
        """No special extensions required."""
        return []
    
    async def get_forward_statements(self) -> list[str]:
        return [
            """
            CREATE TABLE user_preferences (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL,
                
                -- Dashboard preferences
                theme VARCHAR(50) DEFAULT 'gruvbox_light' 
                    CHECK (theme IN ('gruvbox_light', 'gruvbox_dark', 'dracula', 'solarized_dark')),
                dashboard_layout JSONB DEFAULT '{"layout": "default"}',
                
                -- Notification preferences
                notifications_enabled BOOLEAN DEFAULT true,
                email_notifications BOOLEAN DEFAULT false,
                
                -- Memory preferences
                default_memory_type VARCHAR(20) DEFAULT 'semantic'
                    CHECK (default_memory_type IN ('semantic', 'episodic', 'procedural')),
                auto_classify_memories BOOLEAN DEFAULT true,
                
                -- Search preferences
                search_result_limit INTEGER DEFAULT 10 CHECK (search_result_limit BETWEEN 1 AND 100),
                importance_threshold DECIMAL(3,2) DEFAULT 0.5 CHECK (importance_threshold BETWEEN 0 AND 1),
                
                -- Timestamps
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                
                -- Constraints
                UNIQUE(user_id)
            )
            """,
            """
            CREATE INDEX idx_user_preferences_user_id 
            ON user_preferences(user_id)
            """,
            """
            CREATE INDEX idx_user_preferences_theme 
            ON user_preferences(theme)
            """,
            """
            CREATE OR REPLACE FUNCTION update_user_preferences_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """,
            """
            CREATE TRIGGER trigger_update_user_preferences_updated_at
                BEFORE UPDATE ON user_preferences
                FOR EACH ROW
                EXECUTE FUNCTION update_user_preferences_updated_at()
            """
        ]
    
    async def get_rollback_statements(self) -> list[str]:
        return [
            "DROP TRIGGER IF EXISTS trigger_update_user_preferences_updated_at ON user_preferences",
            "DROP FUNCTION IF EXISTS update_user_preferences_updated_at()",
            "DROP INDEX IF EXISTS idx_user_preferences_theme",
            "DROP INDEX IF EXISTS idx_user_preferences_user_id",
            "DROP TABLE IF EXISTS user_preferences"
        ]
    
    async def _validate_custom_postconditions(self, conn) -> bool:
        """Validate the table was created with all expected columns."""
        # Check table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS(
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'user_preferences'
            )
        """)
        
        if not table_exists:
            return False
        
        # Check required columns exist
        required_columns = [
            'id', 'user_id', 'theme', 'dashboard_layout', 
            'notifications_enabled', 'default_memory_type',
            'search_result_limit', 'importance_threshold',
            'created_at', 'updated_at'
        ]
        
        for column in required_columns:
            exists = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'user_preferences' 
                    AND column_name = $1
                )
            """, column)
            
            if not exists:
                return False
        
        # Check indexes exist
        index_exists = await conn.fetchval("""
            SELECT COUNT(*) FROM pg_indexes 
            WHERE tablename = 'user_preferences'
        """)
        
        return index_exists >= 2  # Should have at least 2 indexes
    
    async def _estimate_changes(self) -> dict[str, int]:
        """Estimate the impact of this migration."""
        return {
            "estimated_items": 1,  # One table
            "create_operations": 6,  # Table + 2 indexes + function + trigger + constraints
            "alter_operations": 0,
            "drop_operations": 0,
            "estimated_rows_affected": 0
        } 