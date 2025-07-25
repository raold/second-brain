#!/usr/bin/env python3
"""
CI/CD Checks without external dependencies
This script performs checks that don't require installed packages
"""

import ast
import os
import re
import sys
from pathlib import Path

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

errors = []
warnings = []

def print_header(text):
    print(f"\n{BLUE}=== {text} ==={RESET}")

def print_ok(text):
    print(f"{GREEN}✓{RESET} {text}")

def print_error(text):
    print(f"{RED}✗{RESET} {text}")
    errors.append(text)

def print_warning(text):
    print(f"{YELLOW}⚠{RESET} {text}")
    warnings.append(text)

def check_file_exists(path, description):
    """Check if a file exists."""
    if Path(path).exists():
        print_ok(f"{description} exists")
        return True
    else:
        print_error(f"{description} missing: {path}")
        return False

def check_python_syntax(filepath):
    """Check Python file syntax using AST."""
    try:
        with open(filepath, encoding='utf-8') as f:
            ast.parse(f.read())
        return True
    except SyntaxError as e:
        print_error(f"Syntax error in {filepath}: {e}")
        return False
    except Exception as e:
        print_error(f"Error parsing {filepath}: {e}")
        return False

def check_imports_in_file(filepath):
    """Check if imports in a file look valid."""
    try:
        with open(filepath, encoding='utf-8') as f:
            content = f.read()

        # Parse the AST
        tree = ast.parse(content)

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")

        return True, imports
    except Exception as e:
        return False, str(e)

def check_no_debug_code(filepath):
    """Check for common debug code patterns."""
    debug_patterns = [
        r'\bprint\s*\(',  # print statements
        r'\bbreakpoint\s*\(',  # breakpoint calls
        r'\bpdb\.set_trace',  # pdb traces
        r'\bipdb\.set_trace',  # ipdb traces
        r'# *TODO(?!:)',  # TODO without colon
        r'# *FIXME(?!:)',  # FIXME without colon
        r'# *XXX(?!:)',  # XXX without colon
    ]

    try:
        with open(filepath, encoding='utf-8') as f:
            content = f.read()

        issues = []
        for i, line in enumerate(content.splitlines(), 1):
            for pattern in debug_patterns:
                if re.search(pattern, line):
                    issues.append((i, pattern, line.strip()))

        return issues
    except Exception as e:
        print_error(f"Error checking {filepath}: {e}")
        return []

def check_trailing_whitespace(filepath):
    """Check for trailing whitespace."""
    try:
        with open(filepath, encoding='utf-8') as f:
            lines = f.readlines()

        issues = []
        for i, line in enumerate(lines, 1):
            if line.rstrip() != line.rstrip('\n').rstrip('\r'):
                issues.append(i)

        return issues
    except Exception:
        return []

def validate_synthesis_structure():
    """Validate synthesis module structure."""
    print_header("Synthesis Module Structure")

    required_files = [
        ("app/models/__init__.py", "Models package"),
        ("app/models/synthesis/__init__.py", "Synthesis models package"),
        ("app/models/synthesis/report_models.py", "Report models"),
        ("app/models/synthesis/repetition_models.py", "Repetition models"),
        ("app/models/synthesis/websocket_models.py", "WebSocket models"),
        ("app/services/__init__.py", "Services package"),
        ("app/services/synthesis/__init__.py", "Synthesis services package"),
        ("app/services/synthesis/report_generator.py", "Report generator"),
        ("app/services/synthesis/repetition_scheduler.py", "Repetition scheduler"),
        ("app/services/synthesis/websocket_service.py", "WebSocket service"),
        ("app/routes/synthesis_routes.py", "Synthesis routes"),
    ]

    all_exist = True
    for filepath, description in required_files:
        if not check_file_exists(filepath, description):
            all_exist = False

    return all_exist

def check_python_files():
    """Check all Python files for syntax errors."""
    print_header("Python Syntax Check")

    python_files = []
    for pattern in ["app/**/*.py", "tests/**/*.py"]:
        python_files.extend(Path(".").glob(pattern))

    syntax_errors = 0
    for filepath in python_files:
        if not check_python_syntax(filepath):
            syntax_errors += 1

    if syntax_errors == 0:
        print_ok(f"All {len(python_files)} Python files have valid syntax")
    else:
        print_error(f"{syntax_errors} files have syntax errors")

    return syntax_errors == 0

def check_synthesis_imports():
    """Check synthesis module imports."""
    print_header("Synthesis Import Structure")

    # Check __init__.py exports
    init_file = "app/models/synthesis/__init__.py"
    if Path(init_file).exists():
        with open(init_file) as f:
            content = f.read()

        # Check for required exports
        required_exports = [
            "ReportType", "ReportFormat", "ReportFilter",
            "ReviewDifficulty", "BulkReviewRequest",
            "WebSocketMetrics"
        ]

        missing = []
        for export in required_exports:
            if export not in content:
                missing.append(export)

        if missing:
            print_warning(f"Missing exports in {init_file}: {', '.join(missing)}")
        else:
            print_ok("All required exports found in synthesis __init__.py")

    return True

def check_test_files():
    """Check test files."""
    print_header("Test Files")

    test_files = [
        "tests/unit/synthesis/test_report_models.py",
        "tests/unit/synthesis/test_repetition_models.py",
        "tests/unit/synthesis/test_websocket_models.py",
        "tests/unit/synthesis/test_report_generator.py",
        "tests/unit/synthesis/test_repetition_scheduler.py",
        "tests/unit/synthesis/test_websocket_service.py",
        "tests/integration/synthesis/test_synthesis_integration.py",
    ]

    all_valid = True
    for test_file in test_files:
        if Path(test_file).exists():
            if check_python_syntax(test_file):
                print_ok(f"Test file valid: {test_file}")
            else:
                all_valid = False
        else:
            print_error(f"Test file missing: {test_file}")
            all_valid = False

    return all_valid

def check_code_quality():
    """Check code quality issues."""
    print_header("Code Quality Checks")

    # Check for debug code in synthesis files
    synthesis_files = list(Path("app").glob("**/synthesis/**/*.py"))

    debug_issues = []
    whitespace_issues = []

    for filepath in synthesis_files:
        debug = check_no_debug_code(filepath)
        if debug:
            debug_issues.append((filepath, debug))

        whitespace = check_trailing_whitespace(filepath)
        if whitespace:
            whitespace_issues.append((filepath, whitespace))

    if not debug_issues:
        print_ok("No debug code found in synthesis files")
    else:
        for filepath, issues in debug_issues:
            for line_no, pattern, line in issues:
                print_warning(f"{filepath}:{line_no} - Found {pattern}")

    if not whitespace_issues:
        print_ok("No trailing whitespace in synthesis files")
    else:
        for filepath, lines in whitespace_issues:
            print_warning(f"{filepath} has trailing whitespace on lines: {lines[:5]}{'...' if len(lines) > 5 else ''}")

    return True

def check_version_consistency():
    """Check version consistency across files."""
    print_header("Version Consistency")

    version_locations = [
        ("app/version.py", r'__version__\s*=\s*["\']([^"\']+)["\']'),
        ("static/dashboard.html", r'v([\d.]+)'),
        ("CHANGELOG.md", r'\[(\d+\.\d+\.\d+)\]'),
    ]

    versions = {}
    for filepath, pattern in version_locations:
        if Path(filepath).exists():
            with open(filepath, encoding='utf-8') as f:
                content = f.read()

            match = re.search(pattern, content)
            if match:
                versions[filepath] = match.group(1)
                print_ok(f"{filepath}: v{match.group(1)}")
            else:
                print_warning(f"Could not find version in {filepath}")

    # Check if all versions match
    unique_versions = set(versions.values())
    if len(unique_versions) == 1:
        print_ok(f"All files have consistent version: v{list(unique_versions)[0]}")
    elif len(unique_versions) > 1:
        print_warning(f"Version mismatch found: {versions}")

    return True

def check_requirements():
    """Check requirements.txt."""
    print_header("Requirements Check")

    if not Path("requirements.txt").exists():
        print_error("requirements.txt not found")
        return False

    with open("requirements.txt") as f:
        content = f.read()

    # Check critical versions
    checks = [
        ("ruff==0.12.4", "Ruff version for CI/CD"),
        ("fastapi==", "FastAPI"),
        ("pydantic==", "Pydantic"),
        ("pytest==", "Pytest"),
    ]

    for check, description in checks:
        if check in content:
            print_ok(f"{description} found")
        else:
            print_warning(f"{description} not found or version mismatch")

    return True

def main():
    """Run all checks."""
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Second Brain v2.8.2 - CI/CD Validation (No Dependencies){RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

    # Change to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)

    # Run checks
    checks = [
        ("Module Structure", validate_synthesis_structure),
        ("Python Syntax", check_python_files),
        ("Import Structure", check_synthesis_imports),
        ("Test Files", check_test_files),
        ("Code Quality", check_code_quality),
        ("Version Consistency", check_version_consistency),
        ("Requirements", check_requirements),
    ]

    for check_name, check_func in checks:
        check_func()

    # Summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Summary:{RESET}")

    if errors:
        print(f"{RED}✗ {len(errors)} errors found:{RESET}")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
    else:
        print(f"{GREEN}✓ No errors found{RESET}")

    if warnings:
        print(f"{YELLOW}⚠ {len(warnings)} warnings found{RESET}")

    if not errors:
        print(f"\n{GREEN}✓ Code is ready for CI/CD!{RESET}")
        return 0
    else:
        print(f"\n{RED}✗ Please fix errors before pushing to main{RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
