"""Mock database for testing and development"""

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid


class MockDatabase:
    """Mock database implementation for testing"""
    
    def __init__(self):
        """Initialize mock database with in-memory storage"""
        self.data: Dict[str, List[Dict[str, Any]]] = {
            'memories': [],
            'users': [],
            'relationships': [],
            'sessions': []
        }
        self.connected = False
    
    async def connect(self):
        """Simulate database connection"""
        self.connected = True
        return self
    
    async def disconnect(self):
        """Simulate database disconnection"""
        self.connected = False
    
    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Simulate fetching one record"""
        # Simple mock - return first item from appropriate table
        table = self._extract_table_from_query(query)
        if table and table in self.data and self.data[table]:
            return self.data[table][0]
        return None
    
    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """Simulate fetching all records"""
        # Simple mock - return all items from appropriate table
        table = self._extract_table_from_query(query)
        if table and table in self.data:
            return self.data[table]
        return []
    
    async def execute(self, query: str, *args) -> str:
        """Simulate executing a query"""
        # Simple mock - just return success
        return "OK"
    
    async def execute_many(self, query: str, values: List[tuple]) -> None:
        """Simulate executing many queries"""
        # Simple mock - just pass
        pass
    
    def _extract_table_from_query(self, query: str) -> Optional[str]:
        """Extract table name from query (very simple implementation)"""
        query_lower = query.lower()
        for table in self.data.keys():
            if table in query_lower:
                return table
        return None
    
    # Test helper methods
    def add_memory(self, memory: Dict[str, Any]):
        """Add a memory to the mock database"""
        if 'id' not in memory:
            memory['id'] = str(uuid.uuid4())
        if 'created_at' not in memory:
            memory['created_at'] = datetime.utcnow()
        self.data['memories'].append(memory)
    
    def add_user(self, user: Dict[str, Any]):
        """Add a user to the mock database"""
        if 'id' not in user:
            user['id'] = str(uuid.uuid4())
        self.data['users'].append(user)
    
    def clear(self):
        """Clear all data from mock database"""
        for table in self.data:
            self.data[table] = []


# Singleton instance
_mock_db_instance = None


def get_mock_database():
    """Get singleton mock database instance"""
    global _mock_db_instance
    if _mock_db_instance is None:
        _mock_db_instance = MockDatabase()
    return _mock_db_instance