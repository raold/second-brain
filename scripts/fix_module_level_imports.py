#!/usr/bin/env python3
"""
Fix module-level import issues (E402) by moving imports to the top of the file.
"""

import re
from pathlib import Path
from typing import List, Tuple

def fix_module_imports(file_path: Path) -> bool:
    """Fix module-level import issues in a Python file."""
    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        # Find all imports and their positions
        imports = []
        other_lines = []
        docstring_lines = []
        in_docstring = False
        docstring_count = 0
        
        for i, line in enumerate(lines):
            # Handle module docstrings (only the first one)
            if i == 0 and line.strip().startswith('"""'):
                if line.strip().endswith('"""') and len(line.strip()) > 6:
                    # Single line docstring
                    docstring_lines.append(line)
                    continue
                else:
                    # Multi-line docstring start
                    in_docstring = True
                    docstring_count = 1
                    docstring_lines.append(line)
                    continue
            elif in_docstring:
                docstring_lines.append(line)
                if '"""' in line:
                    docstring_count += line.count('"""')
                    if docstring_count >= 2:
                        in_docstring = False
                continue
            
            # Skip empty lines and comments at the beginning
            if not line.strip() and not imports and not other_lines:
                continue
                
            # Detect imports
            if (line.strip().startswith('import ') or 
                line.strip().startswith('from ') or
                (line.strip() and i > 0 and lines[i-1].strip().endswith('\\'))):
                imports.append(line)
            else:
                other_lines.append(line)
        
        # If no reorganization needed, return
        if not imports:
            return False
            
        # Rebuild the file
        new_lines = []
        
        # Add docstring if exists
        if docstring_lines:
            new_lines.extend(docstring_lines)
            new_lines.append('')  # Empty line after docstring
        
        # Add all imports at the top
        new_lines.extend(imports)
        
        # Add empty line after imports
        if imports and other_lines and other_lines[0].strip():
            new_lines.append('')
        
        # Add the rest of the content
        new_lines.extend(other_lines)
        
        # Clean up multiple empty lines
        cleaned_lines = []
        prev_empty = False
        for line in new_lines:
            if not line.strip():
                if not prev_empty:
                    cleaned_lines.append(line)
                prev_empty = True
            else:
                cleaned_lines.append(line)
                prev_empty = False
        
        # Write back
        new_content = '\n'.join(cleaned_lines)
        if new_content != content:
            file_path.write_text(new_content, encoding='utf-8')
            return True
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Fix module-level imports in all Python files."""
    # Files with E402 errors from ruff
    files_to_fix = [
        "app/algorithms/memory_aging_algorithms.py",
        "app/conversation_processor.py", 
        "app/core/dependencies.py",
        "app/core/logging.py",
        "app/core/monitoring.py",
        "app/core/rate_limiting.py",
        "app/core/security_audit.py",
        "app/database_mock.py",
        "app/ingestion/core_extraction_pipeline.py",
        "app/ingestion/google_drive_client.py",
        "app/ingestion/models.py",
        "app/models/memory.py",
        "app/services/memory_deduplication_engine.py",
        "app/services/monitoring/metrics_collector.py",
        "app/services/synthesis/advanced_synthesis.py",
        "app/services/synthesis/consolidation_engine.py",
        "app/services/synthesis/repetition_scheduler.py",
        "app/services/synthesis/suggestion_engine.py",
        "app/services/synthesis/websocket_service.py",
        "app/session_manager.py",
        "app/utils/context_managers.py",
        "app/utils/decorators.py",
        "app/utils/embedding_cache.py",
        "app/utils/logging_config.py",
        "app/utils/metaclasses.py",
        "app/utils/openai_client.py",
        "app/utils/pythonic.py",
        "app/utils/time_utils.py"
    ]
    
    fixed_count = 0
    for file_path in files_to_fix:
        path = Path(file_path)
        if path.exists():
            if fix_module_imports(path):
                print(f"✓ Fixed {file_path}")
                fixed_count += 1
        else:
            print(f"✗ File not found: {file_path}")
    
    print(f"\nFixed {fixed_count} files")

if __name__ == "__main__":
    main()