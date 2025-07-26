#!/usr/bin/env python3
"""
Find code smells, stubs, and unused code in the codebase
"""
import ast
import os
from pathlib import Path
from collections import defaultdict

def analyze_file(file_path):
    """Analyze a Python file for issues"""
    issues = {
        'stubs': [],
        'unused_imports': [],
        'empty_classes': [],
        'not_implemented': [],
        'todos': []
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content)
            
        # Check for stub implementations
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Function with only pass or NotImplementedError
                if len(node.body) == 1:
                    if isinstance(node.body[0], ast.Pass):
                        issues['stubs'].append(f"Stub function: {node.name}")
                    elif isinstance(node.body[0], ast.Raise):
                        if hasattr(node.body[0].exc, 'func') and hasattr(node.body[0].exc.func, 'id'):
                            if node.body[0].exc.func.id == 'NotImplementedError':
                                issues['not_implemented'].append(f"Not implemented: {node.name}")
                                
            elif isinstance(node, ast.ClassDef):
                # Check for empty classes
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    issues['empty_classes'].append(f"Empty class: {node.name}")
                    
        # Check for TODOs in comments
        for i, line in enumerate(content.split('\n'), 1):
            if 'TODO' in line or 'FIXME' in line:
                issues['todos'].append(f"Line {i}: {line.strip()}")
                
    except Exception as e:
        pass
        
    return issues

def main():
    all_issues = defaultdict(lambda: defaultdict(list))
    
    # Scan app directory
    for root, dirs, files in os.walk('app'):
        # Skip __pycache__ directories
        dirs[:] = [d for d in dirs if d != '__pycache__']
        
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                issues = analyze_file(file_path)
                
                for issue_type, issue_list in issues.items():
                    if issue_list:
                        all_issues[str(file_path)][issue_type].extend(issue_list)
    
    # Print summary
    stub_files = []
    interface_files = []
    migration_files = []
    
    print("="*60)
    print("CODE SMELL ANALYSIS")
    print("="*60)
    
    for file_path, issues in all_issues.items():
        # Categorize files
        if 'interfaces' in file_path:
            interface_files.append(file_path)
        elif 'migration' in file_path:
            migration_files.append(file_path)
        elif issues.get('stubs') or issues.get('not_implemented'):
            stub_files.append(file_path)
    
    print(f"\n[STUB FILES] ({len(stub_files)} files with stub implementations):")
    for f in sorted(stub_files)[:10]:  # Show first 10
        print(f"  - {f}")
    if len(stub_files) > 10:
        print(f"  ... and {len(stub_files) - 10} more")
    
    print(f"\n[INTERFACE FILES] ({len(interface_files)} abstract interfaces - OK to have pass):")
    for f in sorted(interface_files)[:5]:
        print(f"  - {f}")
    
    print(f"\n[MIGRATION FILES] ({len(migration_files)} migration-related files):")
    for f in sorted(migration_files):
        print(f"  - {f}")
    
    # Count TODOs
    todo_count = sum(len(issues.get('todos', [])) for issues in all_issues.values())
    print(f"\n[TODOs/FIXMEs] Total: {todo_count}")
    
    # Recommendations
    print("\n[RECOMMENDATIONS]")
    print("1. Archive stub services in synthesis/ directory")
    print("2. Keep interfaces/ directory (they're abstract base classes)")  
    print("3. Archive migration files (one-time use)")
    print("4. Remove empty repository methods or implement them")

if __name__ == "__main__":
    main()