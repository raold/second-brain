#!/usr/bin/env python3
"""
Fix redefinition issues (F811) and undefined names (F821) in the codebase.
"""

import re
from pathlib import Path

def fix_dependencies_file():
    """Fix core/dependencies.py issues."""
    file_path = Path("app/core/dependencies.py")
    content = file_path.read_text(encoding='utf-8')
    
    # Remove duplicate import of asyncio
    lines = content.split('\n')
    new_lines = []
    seen_asyncio = False
    
    for line in lines:
        if "import asyncio" in line and not line.strip().startswith('#'):
            if not seen_asyncio:
                seen_asyncio = True
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    # Fix undefined _get_database by creating async function
    async_db_func = '''
async def _get_database():
    """Async database getter."""
    from app.database import Database
    return Database()
'''
    
    # Insert after imports and before get_database function
    insert_pos = content.find("@lru_cache(maxsize=1)\ndef get_database():")
    if insert_pos > 0:
        content = content[:insert_pos] + async_db_func + '\n' + content[insert_pos:]
    
    # Remove redefinitions of service functions
    # Keep only the first definition of each function
    functions_to_fix = ["get_database", "get_health_service", "get_memory_service", "get_session_service"]
    
    for func_name in functions_to_fix:
        pattern = rf'(def {func_name}\([^)]*\):.*?)(?=\ndef|\Z)'
        matches = list(re.finditer(pattern, content, re.DOTALL))
        if len(matches) > 1:
            # Keep first, remove others
            for match in matches[1:]:
                content = content.replace(match.group(0), '')
    
    file_path.write_text(content, encoding='utf-8')
    print(f"✓ Fixed {file_path}")

def fix_logging_file():
    """Fix core/logging.py issues."""
    file_path = Path("app/core/logging.py")
    content = file_path.read_text(encoding='utf-8')
    
    # Remove duplicate get_logger function
    # Keep the one at line ~282, remove the one from import
    lines = content.split('\n')
    new_lines = []
    
    for i, line in enumerate(lines):
        if "from app.utils.logging_config import get_logger" in line:
            # Comment it out since we define get_logger in this file
            new_lines.append("# " + line + " # Removed - defined in this file")
        else:
            new_lines.append(line)
    
    file_path.write_text('\n'.join(new_lines), encoding='utf-8')
    print(f"✓ Fixed {file_path}")

def fix_monitoring_file():
    """Fix core/monitoring.py issues."""  
    file_path = Path("app/core/monitoring.py")
    content = file_path.read_text(encoding='utf-8')
    
    # Fix import order for prometheus_client
    lines = content.split('\n')
    new_lines = []
    prometheus_imports = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Collect prometheus imports
        if "from prometheus_client import" in line and "(" in line:
            # Multi-line import
            prometheus_imports.append(line)
            i += 1
            while i < len(lines) and ")" not in lines[i-1]:
                prometheus_imports.append(lines[i])
                i += 1
            continue
        elif "from prometheus_client import" in line:
            prometheus_imports.append(line)
            i += 1
            continue
            
        new_lines.append(line)
        i += 1
    
    # Rebuild with proper prometheus imports
    final_lines = []
    imports_done = False
    
    for line in new_lines:
        if not imports_done and line.strip() and not line.strip().startswith('"""'):
            # Insert prometheus imports here
            final_lines.extend([
                "from prometheus_client import (",
                "    CONTENT_TYPE_LATEST,",
                "    Counter,",
                "    Gauge,", 
                "    Histogram,",
                "    Summary,",
                "    generate_latest,",
                ")",
                ""
            ])
            imports_done = True
        final_lines.append(line)
    
    # Remove duplicate MetricsCollector class
    content = '\n'.join(final_lines)
    
    # Keep only first MetricsCollector definition
    pattern = r'(class MetricsCollector.*?)(?=\nclass|\Z)'
    matches = list(re.finditer(pattern, content, re.DOTALL))
    if len(matches) > 1:
        # Remove duplicates
        for match in matches[1:]:
            content = content.replace(match.group(0), '')
    
    file_path.write_text(content, encoding='utf-8')
    print(f"✓ Fixed {file_path}")

def main():
    """Fix all redefinition and undefined name issues."""
    fix_dependencies_file()
    fix_logging_file()
    fix_monitoring_file()
    
    print("\nFixed redefinition and undefined name issues")

if __name__ == "__main__":
    main()