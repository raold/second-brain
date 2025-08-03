"""
SQLite Storage Backend
Provides persistent storage using SQLite for single-user containers
"""

import json
import sqlite3
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class SQLiteBackend:
    """SQLite storage backend for memories"""
    
    def __init__(self, db_path: str = "/data/memories.db"):
        """
        Initialize SQLite backend
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_directory()
        self._init_database()
        logger.info(f"SQLite backend initialized at {db_path}")
    
    def _ensure_directory(self):
        """Ensure the database directory exists"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper cleanup"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_database(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create memories table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    memory_type TEXT DEFAULT 'generic',
                    importance_score REAL DEFAULT 0.5,
                    tags TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}',
                    embedding TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TEXT
                )
            """)
            
            # Create indexes for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_created_at 
                ON memories(created_at DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_importance 
                ON memories(importance_score DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_type 
                ON memories(memory_type)
            """)
            
            # Create FTS5 virtual table for full-text search
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    id UNINDEXED,
                    content,
                    tags,
                    tokenize='porter unicode61'
                )
            """)
            
            # Create metadata table for statistics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            """)
            
            logger.info("Database schema initialized")
    
    async def create_memory(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new memory
        
        Args:
            memory: Memory data dictionary
        
        Returns:
            Created memory with ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert into main table
            cursor.execute("""
                INSERT INTO memories (
                    id, content, memory_type, importance_score,
                    tags, metadata, embedding, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory['id'],
                memory['content'],
                memory.get('memory_type', 'generic'),
                memory.get('importance_score', 0.5),
                json.dumps(memory.get('tags', [])),
                json.dumps(memory.get('metadata', {})),
                json.dumps(memory.get('embedding')) if memory.get('embedding') else None,
                memory['created_at'],
                memory['updated_at']
            ))
            
            # Insert into FTS table for search
            cursor.execute("""
                INSERT INTO memories_fts (id, content, tags)
                VALUES (?, ?, ?)
            """, (
                memory['id'],
                memory['content'],
                ' '.join(memory.get('tags', []))
            ))
            
            # Update statistics
            self._update_statistics(cursor, 'total_memories', 1)
            
            return memory
    
    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a memory by ID
        
        Args:
            memory_id: Memory ID
        
        Returns:
            Memory data or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM memories WHERE id = ?
            """, (memory_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Update access count and last accessed
            cursor.execute("""
                UPDATE memories 
                SET access_count = access_count + 1,
                    last_accessed = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), memory_id))
            
            return self._row_to_dict(row)
    
    async def update_memory(
        self, 
        memory_id: str, 
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a memory
        
        Args:
            memory_id: Memory ID
            updates: Fields to update
        
        Returns:
            Updated memory or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Build update query
            update_fields = []
            values = []
            
            for field in ['content', 'memory_type', 'importance_score']:
                if field in updates:
                    update_fields.append(f"{field} = ?")
                    values.append(updates[field])
            
            if 'tags' in updates:
                update_fields.append("tags = ?")
                values.append(json.dumps(updates['tags']))
            
            if 'metadata' in updates:
                update_fields.append("metadata = ?")
                values.append(json.dumps(updates['metadata']))
            
            if not update_fields:
                return await self.get_memory(memory_id)
            
            # Add updated_at
            update_fields.append("updated_at = ?")
            values.append(datetime.now().isoformat())
            
            # Add memory_id for WHERE clause
            values.append(memory_id)
            
            # Execute update
            cursor.execute(f"""
                UPDATE memories 
                SET {', '.join(update_fields)}
                WHERE id = ?
            """, values)
            
            if cursor.rowcount == 0:
                return None
            
            # Update FTS if content or tags changed
            if 'content' in updates or 'tags' in updates:
                cursor.execute("""
                    UPDATE memories_fts 
                    SET content = ?, tags = ?
                    WHERE id = ?
                """, (
                    updates.get('content', ''),
                    ' '.join(updates.get('tags', [])),
                    memory_id
                ))
            
            return await self.get_memory(memory_id)
    
    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory
        
        Args:
            memory_id: Memory ID
        
        Returns:
            True if deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Delete from main table
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            
            if cursor.rowcount == 0:
                return False
            
            # Delete from FTS table
            cursor.execute("DELETE FROM memories_fts WHERE id = ?", (memory_id,))
            
            # Update statistics
            self._update_statistics(cursor, 'total_memories', -1)
            
            return True
    
    async def list_memories(
        self,
        limit: int = 20,
        offset: int = 0,
        order_by: str = "created_at DESC"
    ) -> List[Dict[str, Any]]:
        """
        List memories with pagination
        
        Args:
            limit: Maximum number of memories to return
            offset: Number of memories to skip
            order_by: Sort order
        
        Returns:
            List of memory dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Validate order_by to prevent SQL injection
            valid_orders = {
                "created_at DESC": "created_at DESC",
                "created_at ASC": "created_at ASC",
                "importance_score DESC": "importance_score DESC",
                "updated_at DESC": "updated_at DESC"
            }
            order_by = valid_orders.get(order_by, "created_at DESC")
            
            cursor.execute(f"""
                SELECT * FROM memories 
                ORDER BY {order_by}
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            return [self._row_to_dict(row) for row in cursor.fetchall()]
    
    async def search_memories(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search memories using full-text search
        
        Args:
            query: Search query
            limit: Maximum results
        
        Returns:
            List of matching memories with relevance scores
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Use FTS5 for search
            cursor.execute("""
                SELECT m.*, 
                       rank * -1 as relevance_score
                FROM memories_fts f
                JOIN memories m ON f.id = m.id
                WHERE memories_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit))
            
            results = []
            for row in cursor.fetchall():
                memory = self._row_to_dict(row)
                # Add relevance score
                memory['relevance_score'] = row['relevance_score']
                results.append(memory)
            
            return results
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get total memories
            cursor.execute("SELECT COUNT(*) as count FROM memories")
            total = cursor.fetchone()['count']
            
            # Get memory type distribution
            cursor.execute("""
                SELECT memory_type, COUNT(*) as count 
                FROM memories 
                GROUP BY memory_type
            """)
            type_distribution = {
                row['memory_type']: row['count'] 
                for row in cursor.fetchall()
            }
            
            # Get database size
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            db_size = cursor.fetchone()['size']
            
            return {
                "total_memories": total,
                "type_distribution": type_distribution,
                "database_size_bytes": db_size,
                "database_path": self.db_path
            }
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to a dictionary"""
        memory = dict(row)
        
        # Parse JSON fields
        if memory.get('tags'):
            memory['tags'] = json.loads(memory['tags'])
        else:
            memory['tags'] = []
        
        if memory.get('metadata'):
            memory['metadata'] = json.loads(memory['metadata'])
        else:
            memory['metadata'] = {}
        
        if memory.get('embedding'):
            memory['embedding'] = json.loads(memory['embedding'])
        
        return memory
    
    def _update_statistics(self, cursor, key: str, increment: int):
        """Update statistics in metadata table"""
        cursor.execute("""
            INSERT INTO metadata (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = CAST(COALESCE(value, 0) AS INTEGER) + ?,
                updated_at = ?
        """, (key, increment, datetime.now().isoformat(), increment, datetime.now().isoformat()))
    
    async def optimize(self):
        """Optimize the database"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("VACUUM")
            cursor.execute("ANALYZE")
            logger.info("Database optimized")
    
    async def backup(self, backup_path: str):
        """Create a backup of the database"""
        with self._get_connection() as conn:
            backup_conn = sqlite3.connect(backup_path)
            conn.backup(backup_conn)
            backup_conn.close()
            logger.info(f"Database backed up to {backup_path}")