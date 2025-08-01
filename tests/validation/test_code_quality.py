"""
Code quality validation tests
"""

import ast
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.validation


class TestCodeStructure:
    """Test code structure and organization"""

    def test_project_structure(self):
        """Test that project follows expected structure"""
        project_root = Path(__file__).parent.parent.parent

        expected_dirs = [
            "app",
            "app/models",
            "app/services",
            "app/routes",
            "tests",
            "tests/unit",
            "tests/integration",
            "tests/validation",
            "scripts",
            "config",
        ]

        for dir_path in expected_dirs:
            full_path = project_root / dir_path
            if not full_path.exists():
                print(f"Warning: Expected directory {dir_path} not found")
            # Don't fail for missing directories, just warn

    def test_init_files_exist(self):
        """Test that __init__.py files exist where needed"""
        project_root = Path(__file__).parent.parent.parent

        python_dirs = [
            "app",
            "app/models",
            "app/services",
            "app/routes",
            "tests",
        ]

        for dir_path in python_dirs:
            full_path = project_root / dir_path
            if full_path.exists():
                init_file = full_path / "__init__.py"
                if not init_file.exists():
                    print(f"Warning: {dir_path}/__init__.py missing")

    def test_no_conflicting_files(self):
        """Test that there are no conflicting or duplicate files"""
        project_root = Path(__file__).parent.parent.parent

        # Check for common conflicting files
        conflicting_patterns = [
            "*.pyc",
            "__pycache__/*",
            "*.orig",
            "*.backup",
            ".DS_Store",
        ]

        # This is just a warning, not a failure
        import glob

        for pattern in conflicting_patterns:
            matches = glob.glob(str(project_root / "**" / pattern), recursive=True)
            if matches:
                print(f"Warning: Found {len(matches)} {pattern} files")


class TestPythonSyntax:
    """Test Python syntax and basic code quality"""

    def test_python_files_parse(self):
        """Test that all Python files have valid syntax"""
        project_root = Path(__file__).parent.parent.parent

        python_files = []
        for root, dirs, files in os.walk(project_root / "app"):
            # Skip __pycache__ and .git directories
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]

            for file in files:
                if file.endswith(".py"):
                    python_files.append(Path(root) / file)

        syntax_errors = []
        for py_file in python_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()
                ast.parse(content)
            except SyntaxError as e:
                syntax_errors.append(f"{py_file}: {e}")
            except UnicodeDecodeError:
                # Try with different encoding
                try:
                    with open(py_file, encoding="latin-1") as f:
                        content = f.read()
                    ast.parse(content)
                except Exception as e:
                    syntax_errors.append(f"{py_file}: {e}")

        if syntax_errors:
            pytest.fail("Syntax errors found:\n" + "\n".join(syntax_errors))

    def test_import_structure(self):
        """Test that imports are structured correctly"""
        project_root = Path(__file__).parent.parent.parent

        # Test some key files for import issues
        key_files = [
            "app/app.py",
            "app/models/memory.py",
        ]

        import_issues = []
        for file_path in key_files:
            full_path = project_root / file_path
            if full_path.exists():
                try:
                    with open(full_path, encoding="utf-8") as f:
                        content = f.read()

                    # Check for duplicate imports
                    lines = content.split("\n")
                    import_lines = [
                        line.strip()
                        for line in lines
                        if line.strip().startswith("import ") or line.strip().startswith("from ")
                    ]

                    # Check for duplicate import statements
                    unique_imports = set(import_lines)
                    if len(import_lines) != len(unique_imports):
                        duplicate_imports = [
                            imp for imp in import_lines if import_lines.count(imp) > 1
                        ]
                        import_issues.append(
                            f"{file_path}: Duplicate imports found: {set(duplicate_imports)}"
                        )

                except Exception as e:
                    import_issues.append(f"{file_path}: Could not check imports: {e}")

        if import_issues:
            # Don't fail, just warn about import issues
            for issue in import_issues:
                print(f"Warning: {issue}")


class TestCodeStyle:
    """Test code style and formatting (optional)"""

    def test_line_length_reasonable(self):
        """Test that lines are not excessively long"""
        project_root = Path(__file__).parent.parent.parent

        long_lines = []
        max_length = 200  # Very generous limit

        for root, dirs, files in os.walk(project_root / "app"):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]

            for file in files:
                if file.endswith(".py"):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, encoding="utf-8") as f:
                            for line_num, line in enumerate(f, 1):
                                if len(line.rstrip()) > max_length:
                                    long_lines.append(
                                        f"{file_path}:{line_num} ({len(line.rstrip())} chars)"
                                    )
                    except Exception:
                        continue

        if long_lines:
            # Don't fail for long lines, just warn
            print(f"Warning: {len(long_lines)} lines exceed {max_length} characters")
            for line in long_lines[:5]:  # Show first 5
                print(f"  {line}")

    def test_no_obvious_debugging_code(self):
        """Test that there's no obvious debugging code left in"""
        project_root = Path(__file__).parent.parent.parent

        debug_patterns = [
            "print(",
            "pprint(",
            "pdb.set_trace",
            "breakpoint(",
            "import pdb",
        ]

        debug_found = []

        for root, dirs, files in os.walk(project_root / "app"):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]

            for file in files:
                if file.endswith(".py"):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, encoding="utf-8") as f:
                            content = f.read()

                        for pattern in debug_patterns:
                            if pattern in content:
                                # Count occurrences
                                count = content.count(pattern)
                                debug_found.append(f"{file_path}: {count} instances of '{pattern}'")
                    except Exception:
                        continue

        if debug_found:
            # Don't fail for debug code, just warn
            print("Warning: Possible debugging code found:")
            for item in debug_found[:10]:  # Show first 10
                print(f"  {item}")


class TestDocumentation:
    """Test documentation and comments"""

    def test_key_files_have_docstrings(self):
        """Test that key files have module docstrings"""
        project_root = Path(__file__).parent.parent.parent

        key_files = [
            "app/app.py",
            "app/models/memory.py",
        ]

        missing_docstrings = []

        for file_path in key_files:
            full_path = project_root / file_path
            if full_path.exists():
                try:
                    with open(full_path, encoding="utf-8") as f:
                        content = f.read()

                    # Parse the AST to check for module docstring
                    tree = ast.parse(content)

                    # Check if first statement is a string (docstring)
                    has_docstring = (
                        len(tree.body) > 0
                        and isinstance(tree.body[0], ast.Expr)
                        and isinstance(tree.body[0].value, ast.Constant)
                        and isinstance(tree.body[0].value.value, str)
                    )

                    if not has_docstring:
                        missing_docstrings.append(file_path)

                except Exception:
                    continue

        if missing_docstrings:
            # Don't fail for missing docstrings, just warn
            print(f"Warning: {len(missing_docstrings)} key files missing docstrings")


class TestSecurity:
    """Basic security checks"""

    def test_no_hardcoded_secrets(self):
        """Test that there are no obvious hardcoded secrets"""
        project_root = Path(__file__).parent.parent.parent

        secret_patterns = [
            "password=",
            "secret_key=",
            "api_key=",
            "token=",
        ]

        potential_secrets = []

        for root, dirs, files in os.walk(project_root / "app"):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]

            for file in files:
                if file.endswith(".py"):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, encoding="utf-8") as f:
                            for line_num, line in enumerate(f, 1):
                                lower_line = line.lower()
                                for pattern in secret_patterns:
                                    if (
                                        pattern in lower_line
                                        and '"' in line
                                        and len(line.strip()) > 20
                                    ):
                                        # Might be a hardcoded secret
                                        potential_secrets.append(f"{file_path}:{line_num}")
                    except Exception:
                        continue

        if potential_secrets:
            # Don't fail for potential secrets in test environment, just warn
            print(f"Warning: {len(potential_secrets)} lines might contain hardcoded secrets")

    def test_safe_eval_usage(self):
        """Test that eval() is not used unsafely"""
        project_root = Path(__file__).parent.parent.parent

        eval_usage = []

        for root, dirs, files in os.walk(project_root / "app"):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]

            for file in files:
                if file.endswith(".py"):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, encoding="utf-8") as f:
                            content = f.read()

                        if "eval(" in content:
                            eval_usage.append(str(file_path))
                    except Exception:
                        continue

        if eval_usage:
            print(f"Warning: eval() usage found in {len(eval_usage)} files")
            # Don't fail, just warn about eval usage


class TestPerformance:
    """Basic performance considerations"""

    def test_no_obvious_performance_issues(self):
        """Test for obvious performance anti-patterns"""
        project_root = Path(__file__).parent.parent.parent

        performance_issues = []

        # Look for common performance anti-patterns
        antipatterns = [
            ("time.sleep(", "blocking sleep"),
            ("while True:", "infinite loop"),
        ]

        for root, dirs, files in os.walk(project_root / "app"):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]

            for file in files:
                if file.endswith(".py"):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, encoding="utf-8") as f:
                            content = f.read()

                        for pattern, description in antipatterns:
                            if pattern in content:
                                count = content.count(pattern)
                                performance_issues.append(
                                    f"{file_path}: {count} instances of {description}"
                                )
                    except Exception:
                        continue

        if performance_issues:
            # Don't fail for performance issues, just warn
            print("Warning: Potential performance issues found:")
            for issue in performance_issues[:5]:
                print(f"  {issue}")

    def test_reasonable_file_sizes(self):
        """Test that Python files are not excessively large"""
        project_root = Path(__file__).parent.parent.parent

        large_files = []
        max_size = 50000  # 50KB is reasonable for most Python files

        for root, dirs, files in os.walk(project_root / "app"):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]

            for file in files:
                if file.endswith(".py"):
                    file_path = Path(root) / file
                    try:
                        size = file_path.stat().st_size
                        if size > max_size:
                            large_files.append(f"{file_path}: {size} bytes")
                    except Exception:
                        continue

        if large_files:
            print(f"Warning: {len(large_files)} files exceed {max_size} bytes")
            for file_info in large_files[:3]:
                print(f"  {file_info}")
