#!/usr/bin/env python3
"""
Fix missing auth dependencies in route files
"""

import os


def add_auth_imports(filepath):
    """Add auth imports to a route file"""
    try:
        with open(filepath) as f:
            content = f.read()

        # Check if file uses verify_api_key or get_current_user
        if 'verify_api_key' in content or 'get_current_user' in content or 'get_db_instance' in content:
            # Check if import already exists
            if 'from app.dependencies.auth import' not in content:
                # Find where to insert import
                lines = content.split('\n')
                insert_idx = 0

                # Find last import or after logging import
                for i, line in enumerate(lines):
                    if 'from app.utils.logging_config import' in line:
                        insert_idx = i + 1
                        break
                    elif line.startswith('from ') or line.startswith('import '):
                        insert_idx = i + 1

                # Insert the import
                lines.insert(insert_idx, 'from app.dependencies.auth import verify_api_key, get_current_user, get_db_instance')

                # Write back
                with open(filepath, 'w') as f:
                    f.write('\n'.join(lines))

                print(f"Fixed {filepath}")
                return True
    except Exception as e:
        print(f"Error fixing {filepath}: {e}")

    return False

def main():
    routes_dir = "/Users/dro/Documents/second-brain/app/routes"
    fixed_count = 0

    for filename in os.listdir(routes_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            filepath = os.path.join(routes_dir, filename)
            if add_auth_imports(filepath):
                fixed_count += 1

    print(f"\nFixed {fixed_count} files")

if __name__ == "__main__":
    main()
