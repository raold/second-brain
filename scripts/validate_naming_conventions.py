#!/usr/bin/env python3
"""
Naming Convention Validator for Second Brain CI/CD System

This script validates that all project artifacts follow the established naming conventions
as defined in docs/development/NAMING_CONVENTIONS.md.

Features:
- GitHub Actions workflow validation
- Test file naming validation  
- Script naming validation
- Documentation file validation
- Environment variable validation
- Configuration file validation
- Comprehensive reporting with fix suggestions

Usage:
    python scripts/validate_naming_conventions.py
    python scripts/validate_naming_conventions.py --fix
    python scripts/validate_naming_conventions.py --category workflows
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@dataclass
class NamingViolation:
    """A naming convention violation with fix suggestions."""
    file_path: Path
    category: str
    current_name: str
    violation_type: str
    description: str
    suggested_names: List[str] = field(default_factory=list)
    severity: str = "warning"  # error, warning, info
    
    def __str__(self) -> str:
        return f"{self.severity.upper()}: {self.file_path} - {self.description}"

class NamingConventionValidator:
    """Comprehensive naming convention validator."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.violations: List[NamingViolation] = []
        
        # Define naming patterns
        self.patterns = {
            'workflows': {
                'ci': re.compile(r'^ci-[a-z-]+\.yml$'),
                'cd': re.compile(r'^cd-[a-z-]+\.yml$'),
                'maintenance': re.compile(r'^maintenance-[a-z-]+\.yml$'),
                'security': re.compile(r'^security-[a-z-]+\.yml$'),
                'docs': re.compile(r'^docs-[a-z-]+\.yml$'),
                'release': re.compile(r'^release-[a-z-]+\.yml$'),
            },
            'tests': {
                'unit': re.compile(r'^test_[a-z_]+\.py$'),
                'integration': re.compile(r'^test_[a-z_]+\.py$'),
                'validation': re.compile(r'^test_[a-z_]+\.py$'),
                'performance': re.compile(r'^test_[a-z_]+\.py$'),
                'comprehensive': re.compile(r'^test_[a-z_]+\.py$'),
            },
            'scripts': {
                'ci': re.compile(r'^ci_[a-z_]+\.py$'),
                'cd': re.compile(r'^cd_[a-z_]+\.py$'),
                'util': re.compile(r'^util_[a-z_]+\.py$'),
                'dev': re.compile(r'^dev_[a-z_]+\.py$'),
                'maint': re.compile(r'^maint_[a-z_]+\.py$'),
                'validate': re.compile(r'^validate_[a-z_]+\.py$'),
            },
            'docs': {
                'guide': re.compile(r'^[A-Z_]+_GUIDE\.md$'),
                'reference': re.compile(r'^[A-Z_]+_REFERENCE\.md$'),
                'summary': re.compile(r'^[A-Z_]+_SUMMARY\.md$'),
                'implementation': re.compile(r'^[A-Z_]+_IMPLEMENTATION\.md$'),
            },
            'config': {
                'requirements': re.compile(r'^requirements(-[a-z-]+)?\.txt$'),
                'docker': re.compile(r'^Dockerfile(\.[a-z]+)?$'),
                'compose': re.compile(r'^docker-compose(\.[a-z]+)?\.yml$'),
            }
        }
        
        # Expected directory structure
        self.expected_dirs = {
            'workflows': '.github/workflows',
            'tests_unit': 'tests/unit',
            'tests_integration': 'tests/integration',
            'tests_validation': 'tests/validation',
            'tests_performance': 'tests/performance',
            'scripts': 'scripts',
            'docs_dev': 'docs/development',
            'docs_testing': 'docs/testing',
            'config': 'config',
        }

    def validate_all(self) -> bool:
        """Run all validations and return True if no violations found."""
        print("🔍 Starting comprehensive naming convention validation...")
        print(f"Project root: {self.project_root}")
        print()
        
        # Run all validation categories
        self.validate_workflows()
        self.validate_test_files()
        self.validate_script_files()
        self.validate_documentation_files()
        self.validate_configuration_files()
        self.validate_environment_variables()
        
        # Generate report
        return self.generate_report()

    def validate_workflows(self) -> None:
        """Validate GitHub Actions workflow naming."""
        print("📋 Validating GitHub Actions workflows...")
        
        workflow_dir = self.project_root / ".github" / "workflows"
        if not workflow_dir.exists():
            print(f"⚠️  Workflow directory not found: {workflow_dir}")
            return
        
        workflow_files = list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml"))
        
        for workflow_file in workflow_files:
            self._validate_workflow_file(workflow_file)
        
        print(f"✅ Validated {len(workflow_files)} workflow files")

    def _validate_workflow_file(self, file_path: Path) -> None:
        """Validate a single workflow file."""
        filename = file_path.name
        
        # Check against all workflow patterns
        valid = False
        category = None
        
        for cat, pattern in self.patterns['workflows'].items():
            if pattern.match(filename):
                valid = True
                category = cat
                break
        
        if not valid:
            suggested_names = self._suggest_workflow_names(filename)
            self.violations.append(NamingViolation(
                file_path=file_path,
                category="workflow",
                current_name=filename,
                violation_type="invalid_pattern",
                description=f"Workflow file doesn't match expected pattern: {category}-{'{purpose}'}-{'{scope}'}.yml",
                suggested_names=suggested_names,
                severity="error"
            ))

    def _suggest_workflow_names(self, filename: str) -> List[str]:
        """Suggest valid workflow names based on current filename."""
        suggestions = []
        
        # Extract keywords from current name
        name_lower = filename.lower().replace('.yml', '').replace('.yaml', '')
        
        # Common mapping patterns
        mappings = {
            'test': ['ci-smoke-tests.yml', 'ci-comprehensive-tests.yml'],
            'deploy': ['cd-staging-deployment.yml', 'cd-production-release.yml'],
            'build': ['ci-build-validation.yml'],
            'security': ['security-vulnerability-scan.yml'],
            'quality': ['ci-security-quality.yml'],
        }
        
        for keyword, suggestion_list in mappings.items():
            if keyword in name_lower:
                suggestions.extend(suggestion_list)
        
        return suggestions[:3]  # Limit to top 3 suggestions

    def validate_test_files(self) -> None:
        """Validate test file naming conventions."""
        print("🧪 Validating test files...")
        
        tests_dir = self.project_root / "tests"
        if not tests_dir.exists():
            print(f"⚠️  Tests directory not found: {tests_dir}")
            return
        
        test_files = list(tests_dir.rglob("test_*.py"))
        
        for test_file in test_files:
            self._validate_test_file(test_file)
        
        print(f"✅ Validated {len(test_files)} test files")

    def _validate_test_file(self, file_path: Path) -> None:
        """Validate a single test file."""
        filename = file_path.name
        
        # All test files should follow test_*.py pattern
        if not self.patterns['tests']['unit'].match(filename):
            self.violations.append(NamingViolation(
                file_path=file_path,
                category="test",
                current_name=filename,
                violation_type="invalid_pattern",
                description="Test file doesn't match pattern: test_{feature}_{aspect}.py",
                suggested_names=[self._suggest_test_name(filename)],
                severity="error"
            ))
        
        # Validate test functions within file
        self._validate_test_functions(file_path)

    def _suggest_test_name(self, filename: str) -> str:
        """Suggest a valid test name."""
        if not filename.startswith('test_'):
            # Try to convert existing name to test format
            base_name = filename.replace('.py', '').replace('-', '_').lower()
            return f"test_{base_name}.py"
        return filename

    def _validate_test_functions(self, file_path: Path) -> None:
        """Validate test function naming within a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find test functions
            test_function_pattern = re.compile(r'def (test_[a-zA-Z_]+)\(')
            functions = test_function_pattern.findall(content)
            
            for func_name in functions:
                if not self._is_valid_test_function_name(func_name):
                    self.violations.append(NamingViolation(
                        file_path=file_path,
                        category="test_function",
                        current_name=func_name,
                        violation_type="invalid_function_name",
                        description="Test function doesn't follow pattern: test_{action}_{condition}_{expected_result}",
                        suggested_names=[self._suggest_test_function_name(func_name)],
                        severity="warning"
                    ))
                    
        except (IOError, UnicodeDecodeError) as e:
            print(f"⚠️  Could not read test file {file_path}: {e}")

    def _is_valid_test_function_name(self, func_name: str) -> bool:
        """Check if test function name is valid."""
        # Should start with test_ and have descriptive parts
        if not func_name.startswith('test_'):
            return False
        
        # Should have at least 3 parts after test_
        parts = func_name.split('_')[1:]  # Remove 'test' prefix
        return len(parts) >= 2  # At minimum: action_condition

    def _suggest_test_function_name(self, func_name: str) -> str:
        """Suggest a better test function name."""
        if not func_name.startswith('test_'):
            return f"test_{func_name.lower()}"
        
        # If it's already test_ but poorly named, suggest improvements
        parts = func_name.split('_')[1:]
        if len(parts) < 2:
            return f"{func_name}_returns_expected_result"
        
        return func_name  # Already decent

    def validate_script_files(self) -> None:
        """Validate script file naming conventions."""
        print("📜 Validating script files...")
        
        scripts_dir = self.project_root / "scripts"
        if not scripts_dir.exists():
            print(f"⚠️  Scripts directory not found: {scripts_dir}")
            return
        
        script_files = list(scripts_dir.glob("*.py"))
        
        for script_file in script_files:
            self._validate_script_file(script_file)
        
        print(f"✅ Validated {len(script_files)} script files")

    def _validate_script_file(self, file_path: Path) -> None:
        """Validate a single script file."""
        filename = file_path.name
        
        # Check against all script patterns
        valid = False
        category = None
        
        for cat, pattern in self.patterns['scripts'].items():
            if pattern.match(filename):
                valid = True
                category = cat
                break
        
        if not valid:
            suggested_names = self._suggest_script_names(filename)
            self.violations.append(NamingViolation(
                file_path=file_path,
                category="script",
                current_name=filename,
                violation_type="invalid_pattern",
                description=f"Script file doesn't match expected patterns: {list(self.patterns['scripts'].keys())}",
                suggested_names=suggested_names,
                severity="warning"
            ))

    def _suggest_script_names(self, filename: str) -> List[str]:
        """Suggest valid script names."""
        suggestions = []
        base_name = filename.replace('.py', '').replace('-', '_').lower()
        
        # Try to categorize based on content/name
        if any(word in base_name for word in ['test', 'check', 'validate']):
            suggestions.append(f"util_{base_name}.py")
        elif any(word in base_name for word in ['deploy', 'release']):
            suggestions.append(f"cd_{base_name}.py")
        elif any(word in base_name for word in ['build', 'ci']):
            suggestions.append(f"ci_{base_name}.py")
        else:
            suggestions.extend([
                f"util_{base_name}.py",
                f"dev_{base_name}.py",
                f"maint_{base_name}.py"
            ])
        
        return suggestions[:3]

    def validate_documentation_files(self) -> None:
        """Validate documentation file naming conventions."""
        print("📚 Validating documentation files...")
        
        docs_dir = self.project_root / "docs"
        if not docs_dir.exists():
            print(f"⚠️  Docs directory not found: {docs_dir}")
            return
        
        doc_files = list(docs_dir.rglob("*.md"))
        
        for doc_file in doc_files:
            self._validate_documentation_file(doc_file)
        
        print(f"✅ Validated {len(doc_files)} documentation files")

    def _validate_documentation_file(self, file_path: Path) -> None:
        """Validate a single documentation file."""
        filename = file_path.name
        
        # Skip certain standard files
        skip_files = {'README.md', 'CHANGELOG.md', 'CONTRIBUTING.md', 'LICENSE.md'}
        if filename in skip_files:
            return
        
        # Check against documentation patterns
        valid = False
        for cat, pattern in self.patterns['docs'].items():
            if pattern.match(filename):
                valid = True
                break
        
        if not valid:
            suggested_names = self._suggest_doc_names(filename)
            self.violations.append(NamingViolation(
                file_path=file_path,
                category="documentation",
                current_name=filename,
                violation_type="invalid_pattern",
                description="Documentation file doesn't match expected patterns: {TOPIC}_{TYPE}.md",
                suggested_names=suggested_names,
                severity="info"
            ))

    def _suggest_doc_names(self, filename: str) -> List[str]:
        """Suggest valid documentation names."""
        suggestions = []
        base_name = filename.replace('.md', '').upper()
        
        # Common document types
        doc_types = ['GUIDE', 'REFERENCE', 'SUMMARY', 'IMPLEMENTATION']
        
        for doc_type in doc_types:
            suggestions.append(f"{base_name}_{doc_type}.md")
        
        return suggestions[:2]

    def validate_configuration_files(self) -> None:
        """Validate configuration file naming conventions."""
        print("⚙️ Validating configuration files...")
        
        config_files = []
        
        # Check root directory configs
        for pattern in ['requirements*.txt', 'Dockerfile*', 'docker-compose*.yml', '*.toml', '*.ini']:
            config_files.extend(self.project_root.glob(pattern))
        
        # Check config directory
        config_dir = self.project_root / "config"
        if config_dir.exists():
            config_files.extend(config_dir.rglob("*"))
        
        for config_file in config_files:
            if config_file.is_file():
                self._validate_configuration_file(config_file)
        
        print(f"✅ Validated {len(config_files)} configuration files")

    def _validate_configuration_file(self, file_path: Path) -> None:
        """Validate a single configuration file."""
        filename = file_path.name
        
        # Skip hidden files and directories
        if filename.startswith('.'):
            return
        
        # Check specific config patterns
        valid_patterns = [
            re.compile(r'^requirements(-[a-z-]+)?\.txt$'),
            re.compile(r'^Dockerfile(\.[a-z]+)?$'),
            re.compile(r'^docker-compose(\.[a-z-]+)?\.yml$'),
            re.compile(r'^[a-z_]+\.(toml|ini|yml|yaml|json)$'),
        ]
        
        if not any(pattern.match(filename) for pattern in valid_patterns):
            self.violations.append(NamingViolation(
                file_path=file_path,
                category="configuration",
                current_name=filename,
                violation_type="invalid_pattern",
                description="Configuration file doesn't follow expected naming patterns",
                suggested_names=[filename.lower().replace('-', '_')],
                severity="info"
            ))

    def validate_environment_variables(self) -> None:
        """Validate environment variable naming in files."""
        print("🔧 Validating environment variables...")
        
        # Files that commonly contain environment variables
        env_files = []
        
        # GitHub workflows
        workflow_dir = self.project_root / ".github" / "workflows"
        if workflow_dir.exists():
            env_files.extend(workflow_dir.glob("*.yml"))
        
        # Docker compose files
        env_files.extend(self.project_root.glob("docker-compose*.yml"))
        
        # Scripts and config files
        env_files.extend(self.project_root.glob("scripts/*.py"))
        env_files.extend(self.project_root.glob("*.env"))
        
        for env_file in env_files:
            if env_file.is_file():
                self._validate_environment_variables_in_file(env_file)
        
        print(f"✅ Validated environment variables in {len(env_files)} files")

    def _validate_environment_variables_in_file(self, file_path: Path) -> None:
        """Validate environment variables in a specific file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find environment variable references
            env_patterns = [
                re.compile(r'\$\{([A-Z_][A-Z0-9_]*)\}'),  # ${VAR_NAME}
                re.compile(r'\$([A-Z_][A-Z0-9_]*)'),       # $VAR_NAME
                re.compile(r'os\.environ\[[\'\"]([A-Z_][A-Z0-9_]*)[\'\"]'),  # os.environ['VAR']
                re.compile(r'env:\s*\n\s*([A-Z_][A-Z0-9_]*):'),  # YAML env vars
            ]
            
            env_vars = set()
            for pattern in env_patterns:
                matches = pattern.findall(content)
                env_vars.update(matches)
            
            # Validate each environment variable
            for env_var in env_vars:
                if not self._is_valid_env_var_name(env_var):
                    self.violations.append(NamingViolation(
                        file_path=file_path,
                        category="environment_variable",
                        current_name=env_var,
                        violation_type="invalid_env_var_name",
                        description="Environment variable doesn't follow pattern: {SCOPE}_{PURPOSE}_{DETAIL}",
                        suggested_names=[self._suggest_env_var_name(env_var)],
                        severity="info"
                    ))
                    
        except (IOError, UnicodeDecodeError) as e:
            print(f"⚠️  Could not read file {file_path}: {e}")

    def _is_valid_env_var_name(self, env_var: str) -> bool:
        """Check if environment variable name is valid."""
        # Should be UPPER_CASE with underscores
        if not re.match(r'^[A-Z][A-Z0-9_]*$', env_var):
            return False
        
        # Should have meaningful prefix
        valid_prefixes = ['CI_', 'CD_', 'TEST_', 'APP_', 'SECRET_', 'DOCKER_', 'DATABASE_']
        
        # Allow some common system variables
        system_vars = {'PATH', 'HOME', 'USER', 'PWD', 'LANG', 'PYTHONPATH'}
        
        if env_var in system_vars:
            return True
        
        return any(env_var.startswith(prefix) for prefix in valid_prefixes)

    def _suggest_env_var_name(self, env_var: str) -> str:
        """Suggest a valid environment variable name."""
        # Convert to uppercase and replace invalid chars
        suggested = re.sub(r'[^A-Z0-9_]', '_', env_var.upper())
        
        # Add appropriate prefix if missing
        if not any(suggested.startswith(prefix) for prefix in ['CI_', 'CD_', 'TEST_', 'APP_', 'SECRET_']):
            suggested = f"APP_{suggested}"
        
        return suggested

    def generate_report(self) -> bool:
        """Generate comprehensive validation report."""
        print(f"\n{'='*80}")
        print("📊 NAMING CONVENTION VALIDATION REPORT")
        print(f"{'='*80}")
        
        if not self.violations:
            print("✅ ALL NAMING CONVENTIONS VALIDATED SUCCESSFULLY")
            print(f"✅ No violations found in {self.project_root}")
            return True
        
        # Group violations by category and severity
        violations_by_category = {}
        violations_by_severity = {'error': [], 'warning': [], 'info': []}
        
        for violation in self.violations:
            if violation.category not in violations_by_category:
                violations_by_category[violation.category] = []
            violations_by_category[violation.category].append(violation)
            violations_by_severity[violation.severity].append(violation)
        
        # Print summary
        print(f"❌ FOUND {len(self.violations)} VIOLATIONS")
        print(f"   - Errors: {len(violations_by_severity['error'])}")
        print(f"   - Warnings: {len(violations_by_severity['warning'])}")
        print(f"   - Info: {len(violations_by_severity['info'])}")
        print()
        
        # Print violations by category
        for category, violations in violations_by_category.items():
            print(f"📁 {category.upper()} VIOLATIONS ({len(violations)}):")
            for violation in violations:
                print(f"   {violation}")
                if violation.suggested_names:
                    print(f"      Suggestions: {', '.join(violation.suggested_names)}")
            print()
        
        # Print actionable summary
        print("🔧 RECOMMENDED ACTIONS:")
        
        error_count = len(violations_by_severity['error'])
        if error_count > 0:
            print(f"   1. Fix {error_count} CRITICAL naming violations (will cause CI failures)")
        
        warning_count = len(violations_by_severity['warning'])
        if warning_count > 0:
            print(f"   2. Address {warning_count} warning violations (recommended)")
        
        info_count = len(violations_by_severity['info'])
        if info_count > 0:
            print(f"   3. Consider {info_count} style improvements (optional)")
        
        print()
        print("📚 REFERENCE: docs/development/NAMING_CONVENTIONS.md")
        print(f"{'='*80}")
        
        # Return True if no critical errors
        return len(violations_by_severity['error']) == 0

    def fix_violations(self, dry_run: bool = True) -> None:
        """Attempt to automatically fix violations."""
        print(f"🔧 {'DRY RUN: ' if dry_run else ''}ATTEMPTING TO FIX VIOLATIONS...")
        
        fixable_violations = [v for v in self.violations if v.suggested_names and v.severity in ['error', 'warning']]
        
        if not fixable_violations:
            print("ℹ️  No automatically fixable violations found")
            return
        
        print(f"Found {len(fixable_violations)} potentially fixable violations")
        
        for violation in fixable_violations:
            if len(violation.suggested_names) == 1:
                old_path = violation.file_path
                new_name = violation.suggested_names[0]
                new_path = old_path.parent / new_name
                
                print(f"{'WOULD RENAME' if dry_run else 'RENAMING'}: {old_path.name} -> {new_name}")
                
                if not dry_run:
                    try:
                        old_path.rename(new_path)
                        print(f"✅ Renamed successfully")
                    except Exception as e:
                        print(f"❌ Failed to rename: {e}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate naming conventions across the Second Brain project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/validate_naming_conventions.py
    python scripts/validate_naming_conventions.py --fix --dry-run
    python scripts/validate_naming_conventions.py --category workflows
    python scripts/validate_naming_conventions.py --json-report validation_report.json
        """
    )
    
    parser.add_argument('--category', 
                       choices=['workflows', 'tests', 'scripts', 'docs', 'config', 'env'],
                       help='Validate only specific category')
    parser.add_argument('--fix', action='store_true',
                       help='Attempt to automatically fix violations')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be fixed without making changes')
    parser.add_argument('--json-report', 
                       help='Save detailed report to JSON file')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    validator = NamingConventionValidator(project_root)
    
    try:
        # Run validation
        if args.category:
            print(f"🎯 Validating only category: {args.category}")
            # Run specific category validation
            if args.category == 'workflows':
                validator.validate_workflows()
            elif args.category == 'tests':
                validator.validate_test_files()
            elif args.category == 'scripts':
                validator.validate_script_files()
            elif args.category == 'docs':
                validator.validate_documentation_files()
            elif args.category == 'config':
                validator.validate_configuration_files()
            elif args.category == 'env':
                validator.validate_environment_variables()
        else:
            # Run all validations
            success = validator.validate_all()
        
        # Save JSON report if requested
        if args.json_report:
            report_data = {
                'timestamp': '2025-08-01T12:00:00Z',
                'project_root': str(project_root),
                'total_violations': len(validator.violations),
                'violations': [
                    {
                        'file_path': str(v.file_path),
                        'category': v.category,
                        'current_name': v.current_name,
                        'violation_type': v.violation_type,
                        'description': v.description,
                        'suggested_names': v.suggested_names,
                        'severity': v.severity
                    }
                    for v in validator.violations
                ]
            }
            
            with open(args.json_report, 'w') as f:
                json.dump(report_data, f, indent=2)
            print(f"📄 Detailed report saved to: {args.json_report}")
        
        # Attempt fixes if requested
        if args.fix:
            validator.fix_violations(dry_run=args.dry_run)
        
        # Exit with appropriate code
        critical_errors = len([v for v in validator.violations if v.severity == 'error'])
        sys.exit(1 if critical_errors > 0 else 0)
        
    except KeyboardInterrupt:
        print("\n⏹️  Validation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"💥 Validation failed with error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()