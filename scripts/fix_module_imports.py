#!/usr/bin/env python3
"""Fix module level import issues (E402)."""

from pathlib import Path


def fix_module_imports(file_path):
    """Move all imports to the top of the file."""
    with open(file_path) as f:
        lines = f.readlines()

    # Separate imports and non-imports
    imports = []
    non_imports = []
    docstring_lines = []
    in_docstring = False
    docstring_complete = False

    for i, line in enumerate(lines):
        # Handle module docstring
        if i == 0 and (line.strip().startswith('"""') or line.strip().startswith("'''")):
            in_docstring = True
            docstring_lines.append(line)
            if line.count('"""') >= 2 or line.count("'''") >= 2:
                in_docstring = False
                docstring_complete = True
            continue

        if in_docstring:
            docstring_lines.append(line)
            if '"""' in line or "'''" in line:
                in_docstring = False
                docstring_complete = True
            continue

        if docstring_complete and not line.strip():
            docstring_lines.append(line)
            docstring_complete = False
            continue

        # Check if it's an import statement
        stripped = line.strip()
        if (stripped.startswith('import ') or
            stripped.startswith('from ') or
            (stripped and any(prev.strip().endswith('\\') for prev in imports[-1:]))):
            imports.append(line)
        else:
            non_imports.append(line)

    # If no changes needed, return False
    if not imports or all(line in lines[:len(docstring_lines) + len(imports)] for line in imports):
        return False

    # Reconstruct the file
    new_content = docstring_lines + imports

    # Add blank line after imports if needed
    if imports and non_imports and non_imports[0].strip():
        new_content.append('\n')

    new_content.extend(non_imports)

    with open(file_path, 'w') as f:
        f.writelines(new_content)

    return True

def main():
    """Find and fix all Python files with module import issues."""
    # Specific files with E402 errors from ruff output
    files_to_fix = [
        'app/app.py',
        'app/core/logging.py',
        'tests/unit/test_error_handling_comprehensive.py',
        'tests/validation/test_domain_only.py',
    ]

    fixed_count = 0
    for file_path in files_to_fix:
        path = Path(file_path)
        if path.exists() and fix_module_imports(path):
            print(f"Fixed: {file_path}")
            fixed_count += 1

    print(f"\nFixed {fixed_count} files with module import issues.")

if __name__ == "__main__":
    main()
