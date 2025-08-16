#!/usr/bin/env python3
"""
Analyze all imports and dependencies in the project
"""

import ast
import os
import re
from pathlib import Path
from collections import defaultdict
import sys
import io

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def extract_imports(file_path):
    """Extract all imports from a Python file"""
    imports = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Get base module name
                    base_module = alias.name.split('.')[0]
                    imports.add(base_module)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    # Get base module name
                    base_module = node.module.split('.')[0]
                    # Skip relative imports (starting with app)
                    if not base_module.startswith('app'):
                        imports.add(base_module)
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
    
    return imports

def get_all_imports(root_dir):
    """Get all imports from all Python files"""
    all_imports = defaultdict(set)
    
    # Skip these directories
    skip_dirs = {'.venv', 'venv', '.git', '__pycache__', 'build', 'dist', '.egg-info'}
    
    for root, dirs, files in os.walk(root_dir):
        # Remove skip directories from search
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                imports = extract_imports(file_path)
                for imp in imports:
                    all_imports[imp].add(str(file_path.relative_to(root_dir)))
    
    return all_imports

def load_requirements():
    """Load requirements.txt"""
    requirements = {}
    req_file = Path('requirements.txt')
    
    if req_file.exists():
        with open(req_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Parse requirement line
                    match = re.match(r'^([a-zA-Z0-9\-_]+)', line)
                    if match:
                        package_name = match.group(1).lower()
                        # Handle package name variations
                        package_name = package_name.replace('-', '_')
                        requirements[package_name] = line
    
    return requirements

def map_import_to_package(import_name):
    """Map import name to package name"""
    # Common mappings
    mappings = {
        'jose': 'python-jose',
        'dotenv': 'python-dotenv',
        'sklearn': 'scikit-learn',
        'PIL': 'Pillow',
        'cv2': 'opencv-python',
        'yaml': 'pyyaml',
        'magicpdf': 'pypdf',
        'PyPDF2': 'pypdf',
        'community': 'python-louvain',
        'redis': 'redis',  # Note: This might be imported but not in requirements
        'qdrant_client': 'qdrant-client',  # Old dependency
    }
    
    # Check direct mapping
    if import_name in mappings:
        return mappings[import_name]
    
    # Return as-is
    return import_name.replace('_', '-')

def analyze():
    """Main analysis function"""
    print("=" * 60)
    print("DEPENDENCY ANALYSIS FOR SECOND BRAIN")
    print("=" * 60)
    
    # Get all imports
    root_dir = Path.cwd()
    all_imports = get_all_imports(root_dir)
    
    # Load requirements
    requirements = load_requirements()
    
    # Analyze
    used_packages = set()
    unused_requirements = set(requirements.keys())
    missing_packages = set()
    
    # Standard library modules to ignore
    stdlib_modules = {
        'os', 'sys', 'json', 'datetime', 'time', 'pathlib', 'typing', 'enum',
        'collections', 'itertools', 'functools', 'asyncio', 're', 'math',
        'random', 'string', 'hashlib', 'base64', 'uuid', 'logging', 'warnings',
        'traceback', 'copy', 'io', 'csv', 'sqlite3', 'urllib', 'http', 'socket',
        'subprocess', 'tempfile', 'shutil', 'zipfile', 'configparser', 'argparse',
        'unittest', 'contextlib', 'abc', 'dataclasses', 'inspect', 'importlib',
        'types', 'weakref', 'pickle', 'shelve', 'multiprocessing', 'threading',
        'queue', 'secrets', 'hmac', 'email', 'mimetypes', 'webbrowser', 'platform',
        'getpass', 'pwd', 'grp', 'struct', 'binascii', 'codecs', 'locale',
        'textwrap', 'pprint', 'statistics', 'decimal', 'fractions', 'numbers'
    }
    
    print("\n📦 IMPORTED MODULES:")
    print("-" * 40)
    
    for import_name in sorted(all_imports.keys()):
        if import_name in stdlib_modules:
            continue
            
        package_name = map_import_to_package(import_name).replace('-', '_')
        files = all_imports[import_name]
        
        print(f"\n• {import_name}")
        if len(files) <= 3:
            for f in list(files)[:3]:
                print(f"  └─ {f}")
        else:
            print(f"  └─ Used in {len(files)} files")
        
        # Check if in requirements
        if package_name in requirements:
            used_packages.add(package_name)
            if package_name in unused_requirements:
                unused_requirements.remove(package_name)
        else:
            # Check variations
            found = False
            for req_pkg in requirements:
                if req_pkg.startswith(package_name) or package_name.startswith(req_pkg):
                    used_packages.add(req_pkg)
                    if req_pkg in unused_requirements:
                        unused_requirements.remove(req_pkg)
                    found = True
                    break
            
            if not found and import_name not in {'app'}:
                missing_packages.add(import_name)
    
    print("\n\n❌ UNUSED DEPENDENCIES IN REQUIREMENTS.TXT:")
    print("-" * 40)
    for pkg in sorted(unused_requirements):
        if not pkg.startswith('certifi') and not pkg.startswith('urllib3'):  # These are indirect deps
            print(f"• {pkg}: {requirements[pkg]}")
    
    print("\n\n⚠️  IMPORTS WITHOUT REQUIREMENTS:")
    print("-" * 40)
    for pkg in sorted(missing_packages):
        print(f"• {pkg} (used in {len(all_imports[pkg])} files)")
    
    print("\n\n✅ SUMMARY:")
    print("-" * 40)
    print(f"Total unique imports: {len(all_imports)}")
    print(f"Packages in requirements.txt: {len(requirements)}")
    print(f"Used packages: {len(used_packages)}")
    print(f"Unused requirements: {len(unused_requirements)}")
    print(f"Missing from requirements: {len(missing_packages)}")

if __name__ == "__main__":
    analyze()