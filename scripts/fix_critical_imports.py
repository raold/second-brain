#!/usr/bin/env python3
"""
Fix critical import errors in the codebase.
This script identifies and fixes the most common undefined name errors.
"""

import os
import re
from pathlib import Path

# Map of undefined names to their import statements
IMPORT_FIXES = {
    # Event imports
    "SearchPerformedEvent": "from app.events.domain_events import SearchPerformedEvent",
    "SystemHealthEvent": "from app.events.domain_events import SystemHealthEvent",
    "ErrorOccurredEvent": "from app.events.domain_events import ErrorOccurredEvent",
    "IngestionCompletedEvent": "from app.events.domain_events import IngestionCompletedEvent",
    "MemoryConsolidatedEvent": "from app.events.domain_events import MemoryConsolidatedEvent",
    "ConsolidationEvent": "from app.events.domain_events import ConsolidationEvent",
    "InsightGeneratedEvent": "from app.events.domain_events import InsightGeneratedEvent",
    "KnowledgeGapDetectedEvent": "from app.events.domain_events import KnowledgeGapDetectedEvent",
    "MemoryClusterDetectedEvent": "from app.events.domain_events import MemoryClusterDetectedEvent",
    "PatternDetectedEvent": "from app.events.domain_events import PatternDetectedEvent",
    "MemoryImportanceUpdatedEvent": "from app.events.domain_events import MemoryImportanceUpdatedEvent",
    
    # Model imports
    "StructuredData": "from app.ingestion.models import StructuredData",
    "MemoryCreate": "from app.models.memory import MemoryCreate",
    "Memory": "from app.models.memory import Memory",
    "MemoryUpdate": "from app.models.memory import MemoryUpdate",
    "UserProfile": "from app.models.user import UserProfile",
    "SearchQuery": "from app.models.search import SearchQuery",
    "SearchResult": "from app.models.search import SearchResult",
    
    # Service imports
    "Database": "from app.database import Database",
    "get_database": "from app.database import get_database",
    "get_redis_client": "from app.core.redis_manager import get_redis_client",
    "get_memory_service": "from app.services.service_factory import get_memory_service",
    "get_session_service": "from app.services.service_factory import get_session_service",
    "get_health_service": "from app.services.service_factory import get_health_service",
    
    # Common library imports
    "Optional": "from typing import Optional",
    "List": "from typing import List",
    "Dict": "from typing import Dict",
    "Any": "from typing import Any",
    "Union": "from typing import Union",
    "BaseModel": "from pydantic import BaseModel",
    "Field": "from pydantic import Field",
    "asyncio": "import asyncio",
    "datetime": "from datetime import datetime",
    "timedelta": "from datetime import timedelta",
    "timezone": "from datetime import timezone",
    "UUID": "from uuid import UUID",
    "uuid4": "from uuid import uuid4",
    "json": "import json",
    "logging": "import logging",
    "re": "import re",
    "os": "import os",
    "sys": "import sys",
    "time": "import time",
    "math": "import math",
    "hashlib": "import hashlib",
    "dataclass": "from dataclasses import dataclass",
    "field": "from dataclasses import field",
    "np": "import numpy as np",
    "pd": "import pandas as pd",
    "nx": "import networkx as nx",
    "plt": "import matplotlib.pyplot as plt",
    
    # FastAPI imports
    "HTTPException": "from fastapi import HTTPException",
    "Depends": "from fastapi import Depends",
    "APIRouter": "from fastapi import APIRouter",
    "WebSocket": "from fastapi import WebSocket",
    "WebSocketDisconnect": "from fastapi import WebSocketDisconnect",
    "Query": "from fastapi import Query",
    "Path": "from fastapi import Path",
    "Body": "from fastapi import Body",
    
    # Redis imports
    "Redis": "from redis import Redis",
    "RedisError": "from redis import RedisError",
    
    # Database imports
    "text": "from sqlalchemy import text",
    "select": "from sqlalchemy import select",
    "and_": "from sqlalchemy import and_",
    "or_": "from sqlalchemy import or_",
    "func": "from sqlalchemy import func",
    
    # Exceptions
    "SecondBrainException": "from app.core.exceptions import SecondBrainException",
    "ValidationException": "from app.core.exceptions import ValidationException",
    "DatabaseException": "from app.core.exceptions import DatabaseException",
    "ServiceException": "from app.core.exceptions import ServiceException",
    "AuthorizationException": "from app.core.exceptions import AuthorizationException",
    "UnauthorizedException": "from app.core.exceptions import UnauthorizedException",
    
    # Monitoring and logging
    "get_logger": "from app.utils.logging_config import get_logger",
    "MetricsCollector": "from app.services.monitoring.metrics_collector import MetricsCollector",
    
    # Memory models
    "MemoryType": "from app.models.memory import MemoryType",
    "MemoryStatus": "from app.models.memory import MemoryStatus",
    
    # Synthesis models
    "ConsolidationResult": "from app.models.synthesis.consolidation_models import ConsolidationResult",
    "SuggestionType": "from app.models.synthesis.suggestion_models import SuggestionType",
    "KnowledgeSummary": "from app.models.synthesis.summary_models import KnowledgeSummary",
    
    # Analytics models
    "AnalyticsTimeframe": "from app.models.intelligence.analytics_models import AnalyticsTimeframe",
    "AnalyticsMetric": "from app.models.intelligence.analytics_models import AnalyticsMetric",
    
    # WebSocket models
    "WebSocketMessage": "from app.models.synthesis.websocket_models import WebSocketMessage",
    "WebSocketMessageType": "from app.models.synthesis.websocket_models import WebSocketMessageType",
}

def fix_imports_in_file(file_path: Path) -> bool:
    """Fix imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        lines = content.split('\n')
        
        # Extract existing imports
        import_section_end = 0
        existing_imports = set()
        for i, line in enumerate(lines):
            if line.strip() and not (line.startswith('import ') or line.startswith('from ')):
                if any(line.startswith(prefix) for prefix in ['"""', "'''", '#', 'class ', 'def ', '@']):
                    import_section_end = i
                    break
            elif line.startswith('import ') or line.startswith('from '):
                existing_imports.add(line.strip())
        
        # Find undefined names in the file
        undefined_names = set()
        for name, import_stmt in IMPORT_FIXES.items():
            # Skip if already imported
            if any(name in imp for imp in existing_imports):
                continue
            
            # Look for usage patterns
            patterns = [
                rf'\b{name}\b',  # Word boundary
                rf'isinstance\([^,]+,\s*{name}\)',  # isinstance check
                rf':\s*{name}[\[\s\)]',  # Type annotation
                rf'except\s+{name}',  # Exception handling
                rf'raise\s+{name}',  # Raising exception
            ]
            
            for pattern in patterns:
                if re.search(pattern, content):
                    undefined_names.add(name)
                    break
        
        # Add missing imports
        imports_to_add = []
        for name in undefined_names:
            if name in IMPORT_FIXES:
                import_stmt = IMPORT_FIXES[name]
                if import_stmt not in existing_imports:
                    imports_to_add.append(import_stmt)
        
        if not imports_to_add:
            return False
        
        # Group imports by type
        std_imports = []
        third_party_imports = []
        local_imports = []
        
        for imp in sorted(set(imports_to_add)):
            if imp.startswith('from app.') or imp.startswith('import app.'):
                local_imports.append(imp)
            elif any(imp.startswith(f'from {lib}') or imp.startswith(f'import {lib}') 
                    for lib in ['typing', 'dataclasses', 'datetime', 'uuid', 'json', 'logging', 're', 'os', 'sys', 'time', 'math', 'hashlib', 'asyncio']):
                std_imports.append(imp)
            else:
                third_party_imports.append(imp)
        
        # Insert imports at the right position
        new_lines = lines[:import_section_end]
        
        # Add a blank line if needed
        if new_lines and new_lines[-1].strip():
            new_lines.append('')
        
        # Add imports in order
        if std_imports:
            new_lines.extend(std_imports)
            new_lines.append('')
        if third_party_imports:
            new_lines.extend(third_party_imports)
            new_lines.append('')
        if local_imports:
            new_lines.extend(local_imports)
            new_lines.append('')
        
        # Add the rest of the file
        new_lines.extend(lines[import_section_end:])
        
        # Write back
        new_content = '\n'.join(new_lines)
        if new_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Fixed imports in {file_path}")
            return True
        
        return False
        
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Main function to fix imports across the codebase."""
    project_root = Path(__file__).parent.parent
    app_dir = project_root / "app"
    
    # Files with the most critical import errors
    critical_files = [
        "events/event_handlers.py",
        "ingestion/structured_extractor.py",
        "ingestion/models.py",
        "services/synthesis/consolidation_engine.py",
        "services/synthesis/websocket_service.py",
        "services/memory_deduplication_engine.py",
        "services/knowledge_graph_builder.py",
        "services/reasoning_engine.py",
        "visualization/relationship_graph.py",
        "routes/synthesis_routes.py",
        "routes/websocket_routes.py",
        "routes/insights.py",
        "routes/v2_api.py",
    ]
    
    fixed_count = 0
    
    # Fix critical files first
    for file_path in critical_files:
        full_path = app_dir / file_path
        if full_path.exists():
            if fix_imports_in_file(full_path):
                fixed_count += 1
    
    # Then fix all Python files
    for py_file in app_dir.rglob("*.py"):
        if fix_imports_in_file(py_file):
            fixed_count += 1
    
    print(f"\nFixed imports in {fixed_count} files")

if __name__ == "__main__":
    main()