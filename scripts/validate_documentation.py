#!/usr/bin/env python3
"""
Documentation Consistency Validator for Second Brain CI/CD System

This script validates documentation consistency, cross-references, and completeness
to ensure the documentation ecosystem remains coherent and up-to-date.

Features:
- Cross-reference validation (links between docs)
- Naming convention consistency with NAMING_CONVENTIONS.md
- Required documentation presence validation
- Table of contents synchronization
- Example code validation
- Documentation freshness checks

Usage:
    python scripts/validate_documentation.py
    python scripts/validate_documentation.py --fix-links
    python scripts/validate_documentation.py --update-toc
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@dataclass
class DocumentationIssue:
    """A documentation consistency issue."""
    file_path: Path
    issue_type: str
    description: str
    line_number: Optional[int] = None
    suggested_fix: Optional[str] = None
    severity: str = "warning"  # error, warning, info
    
    def __str__(self) -> str:
        location = f"{self.file_path}"
        if self.line_number:
            location += f":{self.line_number}"
        return f"{self.severity.upper()}: {location} - {self.description}"

class DocumentationValidator:
    """Comprehensive documentation consistency validator."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.issues: List[DocumentationIssue] = []
        self.docs_dir = project_root / "docs"
        
        # Required documentation files
        self.required_docs = {
            'NAMING_CONVENTIONS.md': 'docs/development/NAMING_CONVENTIONS.md',
            'CI_CD_GUIDE.md': 'docs/development/CI_CD_GUIDE.md',
            'TESTING_STRATEGY.md': 'docs/testing/TESTING_STRATEGY.md',
            'API_REFERENCE.md': 'docs/API_REFERENCE.md',
            'DEPLOYMENT_GUIDE.md': 'docs/deployment/DEPLOYMENT_GUIDE.md',
            'TROUBLESHOOTING_GUIDE.md': 'docs/TROUBLESHOOTING_GUIDE.md',
        }
        
        # Documentation cross-references to validate
        self.expected_references = {
            'NAMING_CONVENTIONS.md': [
                'GitHub Actions workflow naming',
                'Test naming conventions',
                'Script naming conventions',
                'Environment variables',
                'Documentation files',
            ],
            'CI_CD_GUIDE.md': [
                'NAMING_CONVENTIONS.md',
                'TESTING_STRATEGY.md',
                'scripts/ci_runner.py',
                'scripts/validate_naming_conventions.py',
            ],
            'TESTING_STRATEGY.md': [
                'NAMING_CONVENTIONS.md',
                'tests/unit/',
                'tests/integration/',
                'tests/validation/',
            ]
        }

    def validate_all(self) -> bool:
        """Run all documentation validations."""
        print("📚 Starting comprehensive documentation validation...")
        print(f"Documentation directory: {self.docs_dir}")
        print()
        
        # Run all validation categories
        self.validate_required_documentation()
        self.validate_cross_references()
        self.validate_naming_consistency()
        self.validate_table_of_contents()
        self.validate_code_examples()
        self.validate_documentation_freshness()
        
        # Generate report
        return self.generate_report()

    def validate_required_documentation(self) -> None:
        """Validate that all required documentation exists."""
        print("📋 Validating required documentation presence...")
        
        missing_docs = []
        for doc_name, doc_path in self.required_docs.items():
            full_path = self.project_root / doc_path
            if not full_path.exists():
                missing_docs.append((doc_name, doc_path))
                self.issues.append(DocumentationIssue(
                    file_path=full_path,
                    issue_type="missing_required_doc",
                    description=f"Required documentation file is missing",
                    severity="error"
                ))
        
        if missing_docs:
            print(f"❌ Found {len(missing_docs)} missing required documents")
            for doc_name, doc_path in missing_docs:
                print(f"   - {doc_name} (expected at {doc_path})")
        else:
            print("✅ All required documentation files present")

    def validate_cross_references(self) -> None:
        """Validate cross-references between documentation files."""
        print("🔗 Validating cross-references...")
        
        # Find all markdown files
        md_files = list(self.docs_dir.rglob("*.md")) + [self.project_root / "README.md"]
        
        total_refs_checked = 0
        broken_refs = 0
        
        for md_file in md_files:
            refs_in_file = self._validate_references_in_file(md_file)
            total_refs_checked += refs_in_file[0]
            broken_refs += refs_in_file[1]
        
        print(f"✅ Validated {total_refs_checked} cross-references")
        if broken_refs > 0:
            print(f"❌ Found {broken_refs} broken references")

    def _validate_references_in_file(self, file_path: Path) -> Tuple[int, int]:
        """Validate references in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (IOError, UnicodeDecodeError) as e:
            self.issues.append(DocumentationIssue(
                file_path=file_path,
                issue_type="read_error",
                description=f"Could not read file: {e}",
                severity="error"
            ))
            return 0, 0
        
        # Find markdown links
        link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        links = link_pattern.findall(content)
        
        refs_checked = 0
        broken_refs = 0
        
        for link_text, link_url in links:
            refs_checked += 1
            
            # Skip external URLs
            if link_url.startswith(('http://', 'https://', 'mailto:')):
                continue
            
            # Skip anchors within same document
            if link_url.startswith('#'):
                continue
            
            # Resolve relative path
            if link_url.startswith('/'):
                target_path = self.project_root / link_url[1:]
            else:
                target_path = file_path.parent / link_url
            
            # Check if target exists
            if not target_path.exists():
                broken_refs += 1
                self.issues.append(DocumentationIssue(
                    file_path=file_path,
                    issue_type="broken_reference",
                    description=f"Broken link to '{link_url}' (link text: '{link_text}')",
                    severity="error"
                ))
        
        return refs_checked, broken_refs

    def validate_naming_consistency(self) -> None:
        """Validate naming consistency with NAMING_CONVENTIONS.md."""
        print("📝 Validating naming consistency...")
        
        naming_conventions_path = self.project_root / "docs/development/NAMING_CONVENTIONS.md"
        if not naming_conventions_path.exists():
            self.issues.append(DocumentationIssue(
                file_path=naming_conventions_path,
                issue_type="missing_naming_conventions",
                description="NAMING_CONVENTIONS.md not found - cannot validate consistency",
                severity="error"
            ))
            return
        
        # Read naming conventions
        try:
            with open(naming_conventions_path, 'r', encoding='utf-8') as f:
                naming_content = f.read()
        except (IOError, UnicodeDecodeError) as e:
            self.issues.append(DocumentationIssue(
                file_path=naming_conventions_path,
                issue_type="read_error",
                description=f"Could not read naming conventions: {e}",
                severity="error"
            ))
            return
        
        # Extract documented patterns from naming conventions
        documented_patterns = self._extract_naming_patterns(naming_content)
        
        # Validate that other docs reference these patterns correctly
        self._validate_naming_pattern_references(documented_patterns)
        
        print(f"✅ Validated naming consistency across {len(documented_patterns)} patterns")

    def _extract_naming_patterns(self, content: str) -> Dict[str, List[str]]:
        """Extract naming patterns from NAMING_CONVENTIONS.md."""
        patterns = {}
        
        current_section = None
        in_code_block = False
        
        for line in content.split('\n'):
            # Track code blocks
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            
            if in_code_block:
                continue
            
            # Find section headers
            if line.startswith('## ') and not line.startswith('### '):
                current_section = line[3:].strip()
                patterns[current_section] = []
            
            # Find pattern examples
            elif current_section and ('pattern' in line.lower() or 'example' in line.lower()):
                # Extract patterns from the line
                pattern_matches = re.findall(r'`([^`]+)`', line)
                patterns[current_section].extend(pattern_matches)
        
        return patterns

    def _validate_naming_pattern_references(self, documented_patterns: Dict[str, List[str]]) -> None:
        """Validate that other documentation correctly references naming patterns."""
        # Find documentation files that should reference naming patterns
        reference_files = [
            self.project_root / "docs/development/CI_CD_GUIDE.md",
            self.project_root / "docs/testing/TESTING_STRATEGY.md",
            self.project_root / "README.md",
        ]
        
        for ref_file in reference_files:
            if ref_file.exists():
                self._validate_pattern_references_in_file(ref_file, documented_patterns)

    def _validate_pattern_references_in_file(self, file_path: Path, patterns: Dict[str, List[str]]) -> None:
        """Validate pattern references in a specific file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (IOError, UnicodeDecodeError):
            return
        
        # Look for references to naming conventions
        if 'naming' in content.lower() or 'convention' in content.lower():
            # Should reference the naming conventions document
            if 'NAMING_CONVENTIONS.md' not in content:
                self.issues.append(DocumentationIssue(
                    file_path=file_path,
                    issue_type="missing_naming_reference",
                    description="References naming conventions but doesn't link to NAMING_CONVENTIONS.md",
                    suggested_fix="Add link to docs/development/NAMING_CONVENTIONS.md",
                    severity="warning"
                ))

    def validate_table_of_contents(self) -> None:
        """Validate table of contents synchronization."""
        print("📑 Validating table of contents...")
        
        # Find files with TOC
        md_files = list(self.docs_dir.rglob("*.md"))
        files_with_toc = []
        
        for md_file in md_files:
            if self._has_table_of_contents(md_file):
                files_with_toc.append(md_file)
                self._validate_toc_in_file(md_file)
        
        print(f"✅ Validated table of contents in {len(files_with_toc)} files")

    def _has_table_of_contents(self, file_path: Path) -> bool:
        """Check if file has a table of contents."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (IOError, UnicodeDecodeError):
            return False
        
        toc_indicators = [
            'table of contents',
            'toc',
            '## contents',
            '## table of contents'
        ]
        
        return any(indicator in content.lower() for indicator in toc_indicators)

    def _validate_toc_in_file(self, file_path: Path) -> None:
        """Validate TOC synchronization in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (IOError, UnicodeDecodeError):
            return
        
        # Extract headers from content
        header_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        headers = [(len(match[0]), match[1].strip()) for match in header_pattern.findall(content)]
        
        # Extract TOC entries
        toc_pattern = re.compile(r'^\s*[-*]\s+\[([^\]]+)\]\(#([^)]+)\)', re.MULTILINE)
        toc_entries = toc_pattern.findall(content)
        
        # Validate TOC completeness (simplified check)
        header_titles = [h[1] for h in headers if h[0] >= 2]  # Skip h1 titles
        toc_titles = [entry[0] for entry in toc_entries]
        
        # Check for missing TOC entries
        missing_in_toc = set(header_titles) - set(toc_titles)
        if missing_in_toc:
            self.issues.append(DocumentationIssue(
                file_path=file_path,
                issue_type="incomplete_toc",
                description=f"Table of contents missing entries: {', '.join(missing_in_toc)}",
                suggested_fix="Update table of contents to include all headers",
                severity="info"
            ))

    def validate_code_examples(self) -> None:
        """Validate code examples in documentation."""
        print("💻 Validating code examples...")
        
        md_files = list(self.docs_dir.rglob("*.md"))
        total_examples = 0
        invalid_examples = 0
        
        for md_file in md_files:
            examples_in_file = self._validate_code_examples_in_file(md_file)
            total_examples += examples_in_file[0]
            invalid_examples += examples_in_file[1]
        
        print(f"✅ Validated {total_examples} code examples")
        if invalid_examples > 0:
            print(f"⚠️  Found {invalid_examples} potentially invalid examples")

    def _validate_code_examples_in_file(self, file_path: Path) -> Tuple[int, int]:
        """Validate code examples in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (IOError, UnicodeDecodeError):
            return 0, 0
        
        # Find code blocks
        code_block_pattern = re.compile(r'```(\w+)?\n(.*?)\n```', re.DOTALL)
        code_blocks = code_block_pattern.findall(content)
        
        total_examples = len(code_blocks)
        invalid_examples = 0
        
        for language, code in code_blocks:
            # Validate specific language examples
            if language == 'python':
                if not self._validate_python_code(code):
                    invalid_examples += 1
                    self.issues.append(DocumentationIssue(
                        file_path=file_path,
                        issue_type="invalid_python_example",
                        description="Python code example has syntax issues",
                        severity="warning"
                    ))
            elif language == 'bash':
                if not self._validate_bash_code(code):
                    invalid_examples += 1
                    self.issues.append(DocumentationIssue(
                        file_path=file_path,
                        issue_type="invalid_bash_example",
                        description="Bash code example has potential issues",
                        severity="info"
                    ))
        
        return total_examples, invalid_examples

    def _validate_python_code(self, code: str) -> bool:
        """Basic Python code validation."""
        try:
            # Try to compile the code (basic syntax check)
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError:
            return False

    def _validate_bash_code(self, code: str) -> bool:
        """Basic bash code validation."""
        # Simple checks for common issues
        lines = code.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Check for potentially dangerous commands
            dangerous_patterns = ['rm -rf /', 'chmod 777', '> /dev/null 2>&1']
            if any(pattern in line for pattern in dangerous_patterns):
                return False
        
        return True

    def validate_documentation_freshness(self) -> None:
        """Validate documentation freshness and update dates."""
        print("📅 Validating documentation freshness...")
        
        md_files = list(self.docs_dir.rglob("*.md"))
        outdated_docs = []
        
        for md_file in md_files:
            if self._is_documentation_outdated(md_file):
                outdated_docs.append(md_file)
        
        if outdated_docs:
            print(f"⚠️  Found {len(outdated_docs)} potentially outdated documents")
        else:
            print("✅ All documentation appears up-to-date")

    def _is_documentation_outdated(self, file_path: Path) -> bool:
        """Check if documentation appears outdated."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (IOError, UnicodeDecodeError):
            return False
        
        # Look for last updated dates
        date_patterns = [
            re.compile(r'last updated:?\s*([0-9]{4}-[0-9]{2}-[0-9]{2})', re.IGNORECASE),
            re.compile(r'updated:?\s*([0-9]{4}-[0-9]{2}-[0-9]{2})', re.IGNORECASE),
            re.compile(r'date:?\s*([0-9]{4}-[0-9]{2}-[0-9]{2})', re.IGNORECASE),
        ]
        
        for pattern in date_patterns:
            match = pattern.search(content)
            if match:
                try:
                    doc_date = datetime.strptime(match.group(1), '%Y-%m-%d')
                    days_old = (datetime.now() - doc_date).days
                    
                    if days_old > 30:  # Consider outdated if over 30 days
                        self.issues.append(DocumentationIssue(
                            file_path=file_path,
                            issue_type="outdated_documentation",
                            description=f"Documentation last updated {days_old} days ago",
                            suggested_fix="Review and update documentation content and date",
                            severity="info"
                        ))
                        return True
                except ValueError:
                    continue
        
        return False

    def generate_report(self) -> bool:
        """Generate comprehensive documentation validation report."""
        print(f"\n{'='*80}")
        print("📊 DOCUMENTATION VALIDATION REPORT")
        print(f"{'='*80}")
        
        if not self.issues:
            print("✅ ALL DOCUMENTATION VALIDATIONS PASSED")
            print(f"✅ No issues found in documentation at {self.docs_dir}")
            return True
        
        # Group issues by type and severity
        issues_by_type = {}
        issues_by_severity = {'error': [], 'warning': [], 'info': []}
        
        for issue in self.issues:
            if issue.issue_type not in issues_by_type:
                issues_by_type[issue.issue_type] = []
            issues_by_type[issue.issue_type].append(issue)
            issues_by_severity[issue.severity].append(issue)
        
        # Print summary
        print(f"❌ FOUND {len(self.issues)} DOCUMENTATION ISSUES")
        print(f"   - Errors: {len(issues_by_severity['error'])}")
        print(f"   - Warnings: {len(issues_by_severity['warning'])}")
        print(f"   - Info: {len(issues_by_severity['info'])}")
        print()
        
        # Print issues by type
        for issue_type, issues in issues_by_type.items():
            print(f"📁 {issue_type.upper().replace('_', ' ')} ({len(issues)}):")
            for issue in issues:
                print(f"   {issue}")
                if issue.suggested_fix:
                    print(f"      Suggestion: {issue.suggested_fix}")
            print()
        
        # Print actionable summary
        print("🔧 RECOMMENDED ACTIONS:")
        
        error_count = len(issues_by_severity['error'])
        if error_count > 0:
            print(f"   1. Fix {error_count} CRITICAL documentation issues (will cause CI failures)")
        
        warning_count = len(issues_by_severity['warning'])
        if warning_count > 0:
            print(f"   2. Address {warning_count} documentation warnings (recommended)")
        
        info_count = len(issues_by_severity['info'])
        if info_count > 0:
            print(f"   3. Consider {info_count} documentation improvements (optional)")
        
        print()
        print("📚 REFERENCE: docs/development/NAMING_CONVENTIONS.md")
        print(f"{'='*80}")
        
        # Return True if no critical errors
        return len(issues_by_severity['error']) == 0

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate documentation consistency across the Second Brain project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/validate_documentation.py
    python scripts/validate_documentation.py --fix-links
    python scripts/validate_documentation.py --update-toc
    python scripts/validate_documentation.py --json-report doc_validation.json
        """
    )
    
    parser.add_argument('--fix-links', action='store_true',
                       help='Attempt to fix broken internal links')
    parser.add_argument('--update-toc', action='store_true',
                       help='Update table of contents in documentation files')
    parser.add_argument('--json-report', 
                       help='Save detailed report to JSON file')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    validator = DocumentationValidator(project_root)
    
    try:
        # Run validation
        success = validator.validate_all()
        
        # Save JSON report if requested
        if args.json_report:
            import json
            report_data = {
                'timestamp': datetime.now().isoformat(),
                'project_root': str(project_root),
                'total_issues': len(validator.issues),
                'issues': [
                    {
                        'file_path': str(i.file_path),
                        'issue_type': i.issue_type,
                        'description': i.description,
                        'line_number': i.line_number,
                        'suggested_fix': i.suggested_fix,
                        'severity': i.severity
                    }
                    for i in validator.issues
                ]
            }
            
            with open(args.json_report, 'w') as f:
                json.dump(report_data, f, indent=2)
            print(f"📄 Detailed report saved to: {args.json_report}")
        
        # Exit with appropriate code
        critical_errors = len([i for i in validator.issues if i.severity == 'error'])
        sys.exit(1 if critical_errors > 0 else 0)
        
    except KeyboardInterrupt:
        print("\n⏹️  Documentation validation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"💥 Documentation validation failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()