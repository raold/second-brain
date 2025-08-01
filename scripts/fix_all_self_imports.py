#!/usr/bin/env python3
"""
Fix all self-imports in the codebase.
A self-import is when a module imports from itself, causing circular import errors.
"""

import re
from pathlib import Path


def get_module_path(file_path: Path) -> str:
    """Convert file path to Python module path."""
    # Remove the base directory and .py extension
    base_dir = Path("/Users/dro/Documents/second-brain")
    relative_path = file_path.relative_to(base_dir)
    module_path = str(relative_path).replace('/', '.').replace('.py', '')
    return module_path


def fix_self_imports(file_path: Path) -> bool:
    """Fix self-imports in a Python file."""
    try:
        content = file_path.read_text()
        original_content = content
        
        # Get the module path for this file
        module_path = get_module_path(file_path)
        
        # Pattern to find imports from the same module
        # This will match things like:
        # from app.models.memory import Memory (when in app/models/memory.py)
        pattern = rf'from {re.escape(module_path)} import .*'
        
        # Find all self-imports
        self_imports = re.findall(pattern, content)
        
        if self_imports:
            print(f"Found {len(self_imports)} self-import(s) in {file_path.name}:")
            for imp in self_imports:
                print(f"  - {imp}")
                # Remove the self-import line
                content = content.replace(imp + '\n', '')
                content = content.replace(imp, '')
            
            # Also check for docstring placement issues
            # Move docstrings to the top of the file
            lines = content.split('\n')
            new_lines = []
            docstring_lines = []
            imports = []
            other_lines = []
            
            in_docstring = False
            docstring_count = 0
            
            for line in lines:
                if '"""' in line or "'''" in line:
                    if not in_docstring:
                        in_docstring = True
                        docstring_count += 1
                    else:
                        in_docstring = False
                    
                    if docstring_count == 1:  # First docstring (module docstring)
                        docstring_lines.append(line)
                    else:
                        other_lines.append(line)
                elif in_docstring and docstring_count == 1:
                    docstring_lines.append(line)
                elif line.strip().startswith(('import ', 'from ')):
                    imports.append(line)
                else:
                    other_lines.append(line)
            
            # Reconstruct file with proper order
            new_content = []
            
            # Add module docstring first
            if docstring_lines:
                new_content.extend(docstring_lines)
                new_content.append('')  # Blank line after docstring
            
            # Add imports
            if imports:
                # Remove duplicates while preserving order
                seen = set()
                unique_imports = []
                for imp in imports:
                    if imp.strip() and imp.strip() not in seen:
                        seen.add(imp.strip())
                        unique_imports.append(imp)
                new_content.extend(unique_imports)
                new_content.append('')  # Blank line after imports
            
            # Add the rest
            new_content.extend(other_lines)
            
            # Clean up multiple blank lines
            content = '\n'.join(new_content)
            content = re.sub(r'\n\n\n+', '\n\n', content)
            
            # Write back only if changed
            if content != original_content:
                file_path.write_text(content)
                print(f"  ✓ Fixed {file_path}")
                return True
            
    except Exception as e:
        print(f"  ✗ Error processing {file_path}: {e}")
    
    return False


def main():
    """Find and fix all self-imports in the codebase."""
    base_dir = Path("/Users/dro/Documents/second-brain")
    app_dir = base_dir / "app"
    
    # Find all Python files
    python_files = list(app_dir.rglob("*.py"))
    
    print(f"Checking {len(python_files)} Python files for self-imports...\n")
    
    fixed_count = 0
    
    for file_path in python_files:
        if fix_self_imports(file_path):
            fixed_count += 1
    
    print(f"\nFixed {fixed_count} files with self-imports.")


if __name__ == "__main__":
    main()