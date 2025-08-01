#!/usr/bin/env python3
"""
Fix remaining import issues including:
1. F811 - Duplicate imports
2. E402 - Module level imports not at top of file
"""

import re
from pathlib import Path


def fix_duplicate_imports(file_path: Path, content: str) -> str:
    """Fix duplicate import issues (F811)."""
    
    # Fix app.py - remove duplicate MemoryType import from docs
    if file_path.name == "app.py" and "app/app.py" in str(file_path):
        content = content.replace(
            "from app.docs import (\n    ContextualSearchRequest,\n    EpisodicMemoryRequest,\n    HealthResponse,\n    MemoryResponse,\n    MemoryType,\n    ProceduralMemoryRequest,\n    SemanticMemoryRequest,\n    StatusResponse,\n    setup_openapi_documentation,\n)",
            "from app.docs import (\n    ContextualSearchRequest,\n    EpisodicMemoryRequest,\n    HealthResponse,\n    MemoryResponse,\n    ProceduralMemoryRequest,\n    SemanticMemoryRequest,\n    StatusResponse,\n    setup_openapi_documentation,\n)"
        )
    
    # Fix core/dependencies.py - remove duplicate imports
    if file_path.name == "dependencies.py" and "core/dependencies.py" in str(file_path):
        lines = content.split('\n')
        seen_imports = set()
        new_lines = []
        
        for line in lines:
            # Check if it's an import line
            if line.strip().startswith('from ') or line.strip().startswith('import '):
                # Extract what's being imported
                if ' import ' in line:
                    parts = line.split(' import ')
                    if len(parts) == 2:
                        module = parts[0].strip()
                        imports = parts[1].strip()
                        
                        # Skip duplicate imports
                        if module == "from app.database" and "get_database" in imports and "app.database.get_database" in seen_imports:
                            continue
                        if module == "from app.services.service_factory" and any(x in imports for x in ["get_health_service", "get_memory_service", "get_session_service"]):
                            if any(f"service_factory.{x}" in seen_imports for x in ["get_health_service", "get_memory_service", "get_session_service"]):
                                continue
                        
                        # Track imports
                        for imp in imports.split(','):
                            seen_imports.add(f"{module[5:]}.{imp.strip()}")
            
            new_lines.append(line)
        
        content = '\n'.join(new_lines)
    
    # Fix core/exceptions.py - remove duplicate class definitions
    if file_path.name == "exceptions.py" and "core/exceptions.py" in str(file_path):
        # Remove duplicate exception class definitions
        content = re.sub(r'class SecondBrainException\(Exception\):\s*"""Base exception.*?"""[\s\S]*?(?=class|\Z)', '', content, count=1)
        content = re.sub(r'class UnauthorizedException\(SecondBrainException\):\s*"""Unauthorized.*?"""[\s\S]*?(?=class|\Z)', '', content, count=1)
        content = re.sub(r'class ValidationException\(SecondBrainException\):\s*"""Validation.*?"""[\s\S]*?(?=class|\Z)', '', content, count=1)
        content = re.sub(r'class DatabaseException\(SecondBrainException\):\s*"""Database.*?"""[\s\S]*?(?=class|\Z)', '', content, count=1)
    
    # Fix core/logging.py - remove duplicate get_logger
    if file_path.name == "logging.py" and "core/logging.py" in str(file_path):
        # Remove the duplicate get_logger definition
        content = re.sub(r'def get_logger\(name: str[^)]*\) -> logging\.Logger:\s*"""Get logger.*?"""[\s\S]*?return logger\n', '', content, count=1)
    
    # Fix core/monitoring.py - remove duplicate MetricsCollector
    if file_path.name == "monitoring.py" and "core/monitoring.py" in str(file_path):
        # Remove duplicate class definition
        content = re.sub(r'class MetricsCollector:\s*"""Metrics collection.*?"""[\s\S]*?(?=class|\Z)', '', content, count=1)
    
    # Fix core/rate_limiting.py - remove duplicate get_logger import
    if file_path.name == "rate_limiting.py" and "core/rate_limiting.py" in str(file_path):
        content = re.sub(r'from app\.utils\.logging_config import get_logger\s*\n', '', content, count=1)
    
    # Fix core/redis_manager.py
    if file_path.name == "redis_manager.py" and "core/redis_manager.py" in str(file_path):
        # Remove duplicate get_logger import
        content = re.sub(r'from app\.utils\.logging_config import get_logger\s*\n', '', content, count=1)
        # Remove duplicate get_redis_client function
        content = re.sub(r'async def get_redis_client\(\) -> redis\.Redis \| None:\s*"""Get Redis client.*?"""[\s\S]*?return _redis_client\n', '', content, count=1)
    
    return content


def fix_module_level_imports(file_path: Path, content: str) -> str:
    """Fix module level import issues (E402)."""
    
    lines = content.split('\n')
    
    # Find where imports should go (after module docstring and __future__ imports)
    import_start_idx = 0
    in_docstring = False
    docstring_count = 0
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Track docstrings
        if '"""' in line or "'''" in line:
            if in_docstring:
                in_docstring = False
                docstring_count += 1
            else:
                in_docstring = True
        
        # Skip empty lines and comments at the start
        if not in_docstring and stripped and not stripped.startswith('#'):
            # If this is not an import or docstring, we found where imports should go
            if not (stripped.startswith('from ') or stripped.startswith('import ') or 
                    stripped.startswith('"""') or stripped.startswith("'''")):
                import_start_idx = i
                break
    
    # Collect all imports
    imports = []
    other_lines = []
    
    for i, line in enumerate(lines):
        if i < import_start_idx:
            other_lines.append(line)
        elif line.strip().startswith('from ') or line.strip().startswith('import '):
            imports.append(line)
        else:
            other_lines.append(line)
    
    # Remove duplicates from imports
    unique_imports = []
    seen = set()
    
    for imp in imports:
        if imp.strip() and imp.strip() not in seen:
            seen.add(imp.strip())
            unique_imports.append(imp)
    
    # Reconstruct the file
    new_content = []
    
    # Add everything up to import_start_idx
    new_content.extend(other_lines[:import_start_idx])
    
    # Add all imports
    if unique_imports:
        new_content.extend(unique_imports)
        # Add blank line after imports
        if new_content[-1].strip():
            new_content.append('')
    
    # Add the rest
    new_content.extend(other_lines[import_start_idx:])
    
    return '\n'.join(new_content)


def main():
    """Fix import issues in all Python files."""
    
    # Files with import issues based on ruff output
    files_to_fix = [
        "app/algorithms/memory_aging_algorithms.py",
        "app/app.py",
        "app/conversation_processor.py",
        "app/core/dependencies.py",
        "app/core/exceptions.py",
        "app/core/logging.py",
        "app/core/monitoring.py",
        "app/core/rate_limiting.py",
        "app/core/redis_manager.py",
        "app/core/security_audit.py",
    ]
    
    base_dir = Path("/Users/dro/Documents/second-brain")
    
    for file_path in files_to_fix:
        full_path = base_dir / file_path
        
        if full_path.exists():
            print(f"Fixing {file_path}...")
            
            try:
                content = full_path.read_text()
                original_content = content
                
                # Fix duplicate imports first
                content = fix_duplicate_imports(full_path, content)
                
                # Then fix module level imports
                content = fix_module_level_imports(full_path, content)
                
                # Only write if content changed
                if content != original_content:
                    full_path.write_text(content)
                    print(f"  ✓ Fixed {file_path}")
                else:
                    print(f"  - No changes needed for {file_path}")
                    
            except Exception as e:
                print(f"  ✗ Error fixing {file_path}: {e}")
        else:
            print(f"  ✗ File not found: {file_path}")
    
    print("\nDone!")


if __name__ == "__main__":
    main()