#!/usr/bin/env python3
"""
Logging Migration Helper Script

This script helps automate the migration from old logging patterns to the new
structured logging system.

Usage:
    python scripts/migrate_logging.py --scan      # Analyze current patterns
    python scripts/migrate_logging.py --migrate   # Perform automatic migrations
    python scripts/migrate_logging.py --validate  # Validate migrations
"""

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LoggingIssue:
    file_path: str
    line_number: int
    line_content: str
    issue_type: str
    severity: str
    suggestion: str


class LoggingMigrationHelper:
    """Helper class for migrating logging patterns."""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.issues: list[LoggingIssue] = []

    def scan_codebase(self) -> list[LoggingIssue]:
        """Scan codebase for logging issues and patterns."""
        self.issues = []

        # Find Python files more carefully to avoid permission issues
        python_files = []
        skip_patterns = [
            "migrations/", "__pycache__/", ".git/", "examples/", "archive/",
            ".venv", "venv/", "node_modules/", ".pytest_cache/"
        ]

        try:
            for file_path in self.project_root.rglob("*.py"):
                file_str = str(file_path)
                if any(skip in file_str for skip in skip_patterns):
                    continue
                python_files.append(file_path)
        except (OSError, PermissionError) as e:
            # Fallback to manual directory walking
            print(f"Permission issue with rglob, using manual scan: {e}")
            python_files = self._manual_scan()

        for file_path in python_files:
            self._scan_file(file_path)

        return self.issues

    def _manual_scan(self) -> list[Path]:
        """Manual directory scan to avoid permission issues."""
        python_files = []
        skip_patterns = [
            ".venv", "venv", "__pycache__", ".git", "node_modules",
            ".pytest_cache", "examples", "archive"
        ]

        def scan_directory(directory):
            try:
                for item in directory.iterdir():
                    if item.name.startswith('.') or item.name in skip_patterns:
                        continue
                    if item.is_file() and item.suffix == '.py':
                        python_files.append(item)
                    elif item.is_dir():
                        scan_directory(item)
            except (OSError, PermissionError):
                pass  # Skip directories we can't access

        scan_directory(self.project_root)
        return python_files

    def _scan_file(self, file_path: Path):
        """Scan individual file for logging issues."""
        try:
            with open(file_path, encoding='utf-8') as f:
                lines = f.readlines()
        except (UnicodeDecodeError, PermissionError):
            return

        for line_no, line in enumerate(lines, 1):
            line = line.strip()

            # Check for print statements
            if self._is_print_statement(line):
                self.issues.append(LoggingIssue(
                    file_path=str(file_path),
                    line_number=line_no,
                    line_content=line,
                    issue_type="print_statement",
                    severity="high",
                    suggestion="Replace with logger.info() or logger.debug()"
                ))

            # Check for old logger imports
            if self._is_old_logger_import(line):
                self.issues.append(LoggingIssue(
                    file_path=str(file_path),
                    line_number=line_no,
                    line_content=line,
                    issue_type="old_logger_import",
                    severity="medium",
                    suggestion="Use: from app.utils.logging_config import get_logger"
                ))

            # Check for basicConfig usage
            if "logging.basicConfig" in line:
                self.issues.append(LoggingIssue(
                    file_path=str(file_path),
                    line_number=line_no,
                    line_content=line,
                    issue_type="basic_config",
                    severity="high",
                    suggestion="Remove - use centralized configure_logging()"
                ))

            # Check for f-string logging (potential performance issue)
            if self._is_fstring_logging(line):
                self.issues.append(LoggingIssue(
                    file_path=str(file_path),
                    line_number=line_no,
                    line_content=line,
                    issue_type="fstring_logging",
                    severity="low",
                    suggestion="Use logger.info('message', extra={...}) for structured data"
                ))

            # Check for exception handling without logging
            if self._is_bare_except(line):
                self.issues.append(LoggingIssue(
                    file_path=str(file_path),
                    line_number=line_no,
                    line_content=line,
                    issue_type="bare_except",
                    severity="medium",
                    suggestion="Add logger.exception() for proper error tracking"
                ))

            # Check for traceback.print_exc
            if "traceback.print_exc" in line:
                self.issues.append(LoggingIssue(
                    file_path=str(file_path),
                    line_number=line_no,
                    line_content=line,
                    issue_type="traceback_print",
                    severity="medium",
                    suggestion="Use logger.exception() instead"
                ))

    def _is_print_statement(self, line: str) -> bool:
        """Check if line contains a print statement."""
        # Exclude docstring examples and comments
        if line.startswith('#') or '"""' in line or "'''" in line:
            return False
        return re.match(r'^\s*print\s*\(', line) is not None

    def _is_old_logger_import(self, line: str) -> bool:
        """Check for old logger import patterns."""
        patterns = [
            r'logger\s*=\s*logging\.getLogger\s*\(',
            r'from\s+app\.utils\.logger\s+import',
        ]
        return any(re.search(pattern, line) for pattern in patterns)

    def _is_fstring_logging(self, line: str) -> bool:
        """Check for f-string in logging statements."""
        if 'logger.' not in line:
            return False
        return 'f"' in line or "f'" in line

    def _is_bare_except(self, line: str) -> bool:
        """Check for bare except clauses."""
        return re.match(r'^\s*except\s*:', line) is not None

    def generate_report(self) -> str:
        """Generate migration report."""
        if not self.issues:
            return "No logging issues found!"

        report = ["Logging Migration Report", "=" * 40, ""]

        # Group by severity
        by_severity = {}
        for issue in self.issues:
            if issue.severity not in by_severity:
                by_severity[issue.severity] = []
            by_severity[issue.severity].append(issue)

        # Summary
        report.append(f"Total issues found: {len(self.issues)}")
        for severity in ["high", "medium", "low"]:
            count = len(by_severity.get(severity, []))
            if count > 0:
                report.append(f"  {severity.upper()}: {count}")
        report.append("")

        # Detailed issues by type
        by_type = {}
        for issue in self.issues:
            if issue.issue_type not in by_type:
                by_type[issue.issue_type] = []
            by_type[issue.issue_type].append(issue)

        for issue_type, issues in by_type.items():
            report.append(f"## {issue_type.replace('_', ' ').title()} ({len(issues)} issues)")
            report.append("")

            # Show a few examples
            for issue in issues[:5]:  # Limit to first 5 examples
                file_rel = os.path.relpath(issue.file_path, self.project_root)
                report.append(f"  File: {file_rel}:{issue.line_number}")
                report.append(f"     {issue.line_content}")
                report.append(f"     Suggestion: {issue.suggestion}")
                report.append("")

            if len(issues) > 5:
                report.append(f"     ... and {len(issues) - 5} more")
                report.append("")

        return "\n".join(report)

    def auto_migrate_safe_patterns(self) -> list[str]:
        """Automatically migrate safe, straightforward patterns."""
        migrated_files = []

        for issue in self.issues:
            if issue.issue_type == "old_logger_import" and issue.severity == "medium":
                if self._migrate_logger_import(issue):
                    migrated_files.append(issue.file_path)

        return list(set(migrated_files))  # Remove duplicates

    def _migrate_logger_import(self, issue: LoggingIssue) -> bool:
        """Migrate logger import in a file."""
        try:
            with open(issue.file_path, encoding='utf-8') as f:
                content = f.read()

            # Replace old patterns
            patterns = [
                (
                    r'import logging\n.*?logger = logging\.getLogger\(__name__\)',
                    'from app.utils.logging_config import get_logger\nlogger = get_logger(__name__)'
                ),
                (
                    r'from app\.utils\.logger import logger',
                    'from app.utils.logging_config import get_logger\nlogger = get_logger(__name__)'
                ),
            ]

            modified = False
            for old_pattern, new_pattern in patterns:
                if re.search(old_pattern, content, re.MULTILINE | re.DOTALL):
                    content = re.sub(old_pattern, new_pattern, content, flags=re.MULTILINE | re.DOTALL)
                    modified = True

            if modified:
                with open(issue.file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True

        except Exception as e:
            print(f"Error migrating {issue.file_path}: {e}")

        return False

    def generate_migration_plan(self) -> str:
        """Generate step-by-step migration plan."""
        plan = [
            "Logging Migration Plan",
            "=" * 30,
            "",
            "Phase 1: Critical Issues (Do First)",
            "- Remove all print() statements from production code",
            "- Fix multiple logging.basicConfig() calls",
            "- Replace traceback.print_exc() with logger.exception()",
            "",
            "Phase 2: Import Migration",
            "- Update logger import statements",
            "- Test each file after migration",
            "",
            "Phase 3: Enhancement",
            "- Add structured logging with context",
            "- Implement request tracing",
            "- Add performance monitoring",
            "",
            "Phase 4: Cleanup",
            "- Remove deprecated imports",
            "- Update documentation",
            "- Add monitoring dashboards",
        ]

        # Add specific file counts
        by_type = {}
        for issue in self.issues:
            by_type[issue.issue_type] = by_type.get(issue.issue_type, 0) + 1

        if by_type:
            plan.extend([
                "",
                "Issues by Type:",
                ""
            ])
            for issue_type, count in sorted(by_type.items()):
                plan.append(f"  {issue_type.replace('_', ' ').title()}: {count} files")

        return "\n".join(plan)


def main():
    parser = argparse.ArgumentParser(description="Logging Migration Helper")
    parser.add_argument("--scan", action="store_true", help="Scan codebase for issues")
    parser.add_argument("--migrate", action="store_true", help="Perform safe migrations")
    parser.add_argument("--validate", action="store_true", help="Validate migrations")
    parser.add_argument("--plan", action="store_true", help="Generate migration plan")
    parser.add_argument("--root", default=".", help="Project root directory")

    args = parser.parse_args()

    if not any([args.scan, args.migrate, args.validate, args.plan]):
        parser.print_help()
        return

    helper = LoggingMigrationHelper(args.root)

    if args.scan or args.migrate or args.validate or args.plan:
        print("Scanning codebase for logging patterns...")
        issues = helper.scan_codebase()

        if args.scan:
            print(helper.generate_report())

        if args.plan:
            print(helper.generate_migration_plan())

        if args.migrate:
            print("Performing safe migrations...")
            migrated = helper.auto_migrate_safe_patterns()
            if migrated:
                print(f"Migrated {len(migrated)} files:")
                for file in migrated:
                    print(f"  - {file}")
            else:
                print("No safe migrations available")

        if args.validate:
            print("Validation complete")
            if not issues:
                print("   No remaining issues found")
            else:
                print(f"   {len(issues)} issues still need manual attention")


if __name__ == "__main__":
    main()
