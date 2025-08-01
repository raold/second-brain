#!/usr/bin/env python3
"""
Configuration Files Validator for Second Brain CI/CD System

This script validates configuration file consistency, format, and completeness
across the entire project ecosystem.

Features:
- GitHub Actions workflow validation
- Docker configuration validation
- Python configuration validation (pyproject.toml, pytest.ini)
- Requirements files validation
- Environment configuration validation
- Configuration cross-consistency checks

Usage:
    python scripts/validate_configurations.py
    python scripts/validate_configurations.py --fix-format
    python scripts/validate_configurations.py --check-security
"""

import argparse
import json
import re
import sys
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@dataclass
class ConfigurationIssue:
    """A configuration consistency or format issue."""
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

class ConfigurationValidator:
    """Comprehensive configuration files validator."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.issues: List[ConfigurationIssue] = []
        
        # Required configuration files
        self.required_configs = {
            'pyproject.toml': 'Project configuration',
            'pytest.ini': 'Test configuration',
            'docker-compose.yml': 'Development orchestration',
            'Dockerfile': 'Container definition',
            'requirements.txt': 'Core dependencies',
            '.github/workflows/ci-smoke-tests.yml': 'Smoke test pipeline',
        }
        
        # Security-sensitive configurations
        self.security_patterns = {
            'hardcoded_secrets': [
                re.compile(r'password\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
                re.compile(r'api_key\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
                re.compile(r'secret\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
                re.compile(r'token\s*=\s*["\'][^"\']+["\']', re.IGNORECASE),
            ],
            'insecure_settings': [
                re.compile(r'debug\s*=\s*true', re.IGNORECASE),
                re.compile(r'ssl_verify\s*=\s*false', re.IGNORECASE),
                re.compile(r'insecure\s*=\s*true', re.IGNORECASE),
            ]
        }

    def validate_all(self) -> bool:
        """Run all configuration validations."""
        print("⚙️ Starting comprehensive configuration validation...")
        print(f"Project root: {self.project_root}")
        print()
        
        # Run all validation categories
        self.validate_required_configurations()
        self.validate_workflow_configurations()
        self.validate_docker_configurations()
        self.validate_python_configurations()
        self.validate_requirements_files()
        self.validate_security_configurations()
        self.validate_configuration_consistency()
        
        # Generate report
        return self.generate_report()

    def validate_required_configurations(self) -> None:
        """Validate that all required configuration files exist."""
        print("📋 Validating required configuration files...")
        
        missing_configs = []
        for config_file, description in self.required_configs.items():
            config_path = self.project_root / config_file
            if not config_path.exists():
                missing_configs.append((config_file, description))
                self.issues.append(ConfigurationIssue(
                    file_path=config_path,
                    issue_type="missing_required_config",
                    description=f"Required configuration file is missing: {description}",
                    severity="error"
                ))
        
        if missing_configs:
            print(f"❌ Found {len(missing_configs)} missing required configurations")
        else:
            print("✅ All required configuration files present")

    def validate_workflow_configurations(self) -> None:
        """Validate GitHub Actions workflow configurations."""
        print("🔄 Validating GitHub Actions workflows...")
        
        workflows_dir = self.project_root / ".github" / "workflows"
        if not workflows_dir.exists():
            self.issues.append(ConfigurationIssue(
                file_path=workflows_dir,
                issue_type="missing_workflows_dir",
                description="GitHub Actions workflows directory is missing",
                severity="error"
            ))
            return
        
        workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
        
        for workflow_file in workflow_files:
            self._validate_workflow_file(workflow_file)
        
        print(f"✅ Validated {len(workflow_files)} workflow configurations")

    def _validate_workflow_file(self, file_path: Path) -> None:
        """Validate a single GitHub Actions workflow file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                workflow_content = yaml.safe_load(f)
        except yaml.YAMLError as e:
            self.issues.append(ConfigurationIssue(
                file_path=file_path,
                issue_type="invalid_yaml",
                description=f"Invalid YAML syntax: {e}",
                severity="error"
            ))
            return
        except (IOError, UnicodeDecodeError) as e:
            self.issues.append(ConfigurationIssue(
                file_path=file_path,
                issue_type="read_error",
                description=f"Could not read workflow file: {e}",
                severity="error"
            ))
            return
        
        # Validate workflow structure
        self._validate_workflow_structure(file_path, workflow_content)
        
        # Check for security issues
        self._validate_workflow_security(file_path, workflow_content)

    def _validate_workflow_structure(self, file_path: Path, workflow: Dict[str, Any]) -> None:
        """Validate GitHub Actions workflow structure."""
        required_fields = ['name', 'on', 'jobs']
        
        for field in required_fields:
            if field not in workflow:
                self.issues.append(ConfigurationIssue(
                    file_path=file_path,
                    issue_type="missing_workflow_field",
                    description=f"Required workflow field '{field}' is missing",
                    severity="error"
                ))
        
        # Validate jobs structure
        if 'jobs' in workflow:
            jobs = workflow['jobs']
            if not isinstance(jobs, dict) or not jobs:
                self.issues.append(ConfigurationIssue(
                    file_path=file_path,
                    issue_type="invalid_jobs_structure",
                    description="Workflow must have at least one job",
                    severity="error"
                ))
            else:
                for job_name, job_config in jobs.items():
                    self._validate_job_structure(file_path, job_name, job_config)

    def _validate_job_structure(self, file_path: Path, job_name: str, job_config: Dict[str, Any]) -> None:
        """Validate individual job structure."""
        required_job_fields = ['runs-on', 'steps']
        
        for field in required_job_fields:
            if field not in job_config:
                self.issues.append(ConfigurationIssue(
                    file_path=file_path,
                    issue_type="missing_job_field",
                    description=f"Job '{job_name}' missing required field '{field}'",
                    severity="error"
                ))
        
        # Validate steps
        if 'steps' in job_config:
            steps = job_config['steps']
            if not isinstance(steps, list) or not steps:
                self.issues.append(ConfigurationIssue(
                    file_path=file_path,
                    issue_type="invalid_steps_structure",
                    description=f"Job '{job_name}' must have at least one step",
                    severity="error"
                ))

    def _validate_workflow_security(self, file_path: Path, workflow: Dict[str, Any]) -> None:
        """Validate workflow security configurations."""
        # Check for pinned action versions
        workflow_str = yaml.dump(workflow)
        
        # Find action uses
        action_pattern = re.compile(r'uses:\s*([^@\s]+)@?([^\s]*)')
        actions = action_pattern.findall(workflow_str)
        
        for action_name, version in actions:
            if not version or version in ['latest', 'main', 'master']:
                self.issues.append(ConfigurationIssue(
                    file_path=file_path,
                    issue_type="unpinned_action_version",
                    description=f"Action '{action_name}' should use pinned version for security",
                    suggested_fix="Use specific version or commit hash",
                    severity="warning"
                ))

    def validate_docker_configurations(self) -> None:
        """Validate Docker-related configurations."""
        print("🐳 Validating Docker configurations...")
        
        docker_files = [
            self.project_root / "Dockerfile",
            self.project_root / "Dockerfile.multimodal",
            self.project_root / "docker-compose.yml",
            self.project_root / "docker-compose.production.yml",
        ]
        
        validated_count = 0
        for docker_file in docker_files:
            if docker_file.exists():
                self._validate_docker_file(docker_file)
                validated_count += 1
        
        print(f"✅ Validated {validated_count} Docker configuration files")

    def _validate_docker_file(self, file_path: Path) -> None:
        """Validate a Docker configuration file."""
        if file_path.name.startswith("Dockerfile"):
            self._validate_dockerfile(file_path)
        elif file_path.name.startswith("docker-compose"):
            self._validate_docker_compose(file_path)

    def _validate_dockerfile(self, file_path: Path) -> None:
        """Validate Dockerfile."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (IOError, UnicodeDecodeError) as e:
            self.issues.append(ConfigurationIssue(
                file_path=file_path,
                issue_type="read_error",
                description=f"Could not read Dockerfile: {e}",
                severity="error"
            ))
            return
        
        lines = content.split('\n')
        
        # Check for FROM instruction
        has_from = any(line.strip().upper().startswith('FROM') for line in lines)
        if not has_from:
            self.issues.append(ConfigurationIssue(
                file_path=file_path,
                issue_type="missing_from_instruction",
                description="Dockerfile must start with FROM instruction",
                severity="error"
            ))
        
        # Check for security best practices
        self._validate_dockerfile_security(file_path, content)

    def _validate_dockerfile_security(self, file_path: Path, content: str) -> None:
        """Validate Dockerfile security practices."""
        lines = content.split('\n')
        
        # Check for running as root
        has_user_instruction = any('USER' in line.upper() for line in lines)
        if not has_user_instruction:
            self.issues.append(ConfigurationIssue(
                file_path=file_path,
                issue_type="dockerfile_security_risk",
                description="Dockerfile should specify USER instruction (avoid running as root)",
                suggested_fix="Add USER instruction to run as non-root user",
                severity="warning"
            ))
        
        # Check for .dockerignore reference
        dockerignore_path = file_path.parent / ".dockerignore"
        if not dockerignore_path.exists():
            self.issues.append(ConfigurationIssue(
                file_path=file_path,
                issue_type="missing_dockerignore",
                description="Missing .dockerignore file for build context optimization",
                suggested_fix="Create .dockerignore file to exclude unnecessary files",
                severity="info"
            ))

    def _validate_docker_compose(self, file_path: Path) -> None:
        """Validate docker-compose.yml file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                compose_content = yaml.safe_load(f)
        except yaml.YAMLError as e:
            self.issues.append(ConfigurationIssue(
                file_path=file_path,
                issue_type="invalid_yaml",
                description=f"Invalid YAML syntax: {e}",
                severity="error"
            ))
            return
        except (IOError, UnicodeDecodeError) as e:
            self.issues.append(ConfigurationIssue(
                file_path=file_path,
                issue_type="read_error",
                description=f"Could not read docker-compose file: {e}",
                severity="error"
            ))
            return
        
        # Validate compose structure
        if 'version' not in compose_content:
            self.issues.append(ConfigurationIssue(
                file_path=file_path,
                issue_type="missing_compose_version",
                description="docker-compose.yml should specify version",
                severity="warning"
            ))
        
        if 'services' not in compose_content or not compose_content['services']:
            self.issues.append(ConfigurationIssue(
                file_path=file_path,
                issue_type="missing_services",
                description="docker-compose.yml must define at least one service",
                severity="error"
            ))

    def validate_python_configurations(self) -> None:
        """Validate Python-specific configuration files."""
        print("🐍 Validating Python configurations...")
        
        python_configs = [
            (self.project_root / "pyproject.toml", self._validate_pyproject_toml),
            (self.project_root / "pytest.ini", self._validate_pytest_ini),
            (self.project_root / "ruff.toml", self._validate_ruff_config),
        ]
        
        validated_count = 0
        for config_path, validator_func in python_configs:
            if config_path.exists():
                validator_func(config_path)
                validated_count += 1
        
        print(f"✅ Validated {validated_count} Python configuration files")

    def _validate_pyproject_toml(self, file_path: Path) -> None:
        """Validate pyproject.toml configuration."""
        try:
            import tomli
            with open(file_path, 'rb') as f:
                config = tomli.load(f)
        except ImportError:
            self.issues.append(ConfigurationIssue(
                file_path=file_path,
                issue_type="missing_dependency",
                description="tomli package required to validate pyproject.toml",
                suggested_fix="Install tomli: pip install tomli",
                severity="warning"
            ))
            return
        except Exception as e:
            self.issues.append(ConfigurationIssue(
                file_path=file_path,
                issue_type="invalid_toml",
                description=f"Invalid TOML syntax: {e}",
                severity="error"
            ))
            return
        
        # Validate project metadata
        if 'project' in config:
            project = config['project']
            required_fields = ['name', 'version', 'description']
            
            for field in required_fields:
                if field not in project:
                    self.issues.append(ConfigurationIssue(
                        file_path=file_path,
                        issue_type="missing_project_metadata",
                        description=f"Project metadata missing required field: {field}",
                        severity="warning"
                    ))

    def _validate_pytest_ini(self, file_path: Path) -> None:
        """Validate pytest.ini configuration."""
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read(file_path)
        except Exception as e:
            self.issues.append(ConfigurationIssue(
                file_path=file_path,
                issue_type="invalid_ini",
                description=f"Invalid INI format: {e}",
                severity="error"
            ))
            return
        
        # Check for pytest section
        if 'tool:pytest' not in config and 'pytest' not in config:
            self.issues.append(ConfigurationIssue(
                file_path=file_path,
                issue_type="missing_pytest_section",
                description="pytest.ini should contain [tool:pytest] or [pytest] section",
                severity="warning"
            ))

    def _validate_ruff_config(self, file_path: Path) -> None:
        """Validate ruff.toml configuration."""
        try:
            import tomli
            with open(file_path, 'rb') as f:
                config = tomli.load(f)
        except ImportError:
            return  # Skip if tomli not available
        except Exception as e:
            self.issues.append(ConfigurationIssue(
                file_path=file_path,
                issue_type="invalid_toml",
                description=f"Invalid TOML syntax in ruff config: {e}",
                severity="error"
            ))

    def validate_requirements_files(self) -> None:
        """Validate requirements files."""
        print("📦 Validating requirements files...")
        
        requirements_files = list(self.project_root.glob("requirements*.txt"))
        config_dir = self.project_root / "config"
        if config_dir.exists():
            requirements_files.extend(config_dir.glob("requirements*.txt"))
        
        for req_file in requirements_files:
            self._validate_requirements_file(req_file)
        
        print(f"✅ Validated {len(requirements_files)} requirements files")

    def _validate_requirements_file(self, file_path: Path) -> None:
        """Validate a requirements.txt file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except (IOError, UnicodeDecodeError) as e:
            self.issues.append(ConfigurationIssue(
                file_path=file_path,
                issue_type="read_error",
                description=f"Could not read requirements file: {e}",
                severity="error"
            ))
            return
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Basic format validation
            if not self._is_valid_requirement_line(line):
                self.issues.append(ConfigurationIssue(
                    file_path=file_path,
                    issue_type="invalid_requirement_format",
                    description=f"Invalid requirement format: {line}",
                    line_number=line_num,
                    severity="warning"
                ))

    def _is_valid_requirement_line(self, line: str) -> bool:
        """Check if a requirements line is valid."""
        # Basic regex for package requirements
        requirement_pattern = re.compile(r'^[a-zA-Z0-9_.-]+([><=!~]+[0-9.]+)?$')
        return bool(requirement_pattern.match(line.split()[0]))

    def validate_security_configurations(self) -> None:
        """Validate security-related configurations."""
        print("🔒 Validating security configurations...")
        
        # Find all configuration files
        config_files = []
        config_files.extend(self.project_root.glob("*.yml"))
        config_files.extend(self.project_root.glob("*.yaml"))
        config_files.extend(self.project_root.glob("*.toml"))
        config_files.extend(self.project_root.glob("*.ini"))
        config_files.extend(self.project_root.glob("*.env"))
        
        # Add workflow files
        workflows_dir = self.project_root / ".github" / "workflows"
        if workflows_dir.exists():
            config_files.extend(workflows_dir.glob("*.yml"))
        
        security_issues_found = 0
        for config_file in config_files:
            if config_file.is_file():
                issues_in_file = self._validate_security_in_file(config_file)
                security_issues_found += issues_in_file
        
        if security_issues_found > 0:
            print(f"⚠️  Found {security_issues_found} potential security issues")
        else:
            print("✅ No security issues detected in configurations")

    def _validate_security_in_file(self, file_path: Path) -> int:
        """Validate security in a configuration file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (IOError, UnicodeDecodeError):
            return 0
        
        issues_found = 0
        
        # Check for hardcoded secrets
        for pattern in self.security_patterns['hardcoded_secrets']:
            matches = pattern.findall(content)
            for match in matches:
                self.issues.append(ConfigurationIssue(
                    file_path=file_path,
                    issue_type="hardcoded_secret",
                    description=f"Potential hardcoded secret detected",
                    suggested_fix="Use environment variables or secrets management",
                    severity="error"
                ))
                issues_found += 1
        
        # Check for insecure settings
        for pattern in self.security_patterns['insecure_settings']:
            if pattern.search(content):
                self.issues.append(ConfigurationIssue(
                    file_path=file_path,
                    issue_type="insecure_setting",
                    description="Potentially insecure configuration setting",
                    suggested_fix="Review security implications",
                    severity="warning"
                ))
                issues_found += 1
        
        return issues_found

    def validate_configuration_consistency(self) -> None:
        """Validate consistency across configuration files."""
        print("🔄 Validating configuration consistency...")
        
        # Check Python version consistency
        self._validate_python_version_consistency()
        
        # Check dependency consistency
        self._validate_dependency_consistency()
        
        print("✅ Configuration consistency validation completed")

    def _validate_python_version_consistency(self) -> None:
        """Validate Python version consistency across configurations."""
        python_versions = {}
        
        # Check pyproject.toml
        pyproject_path = self.project_root / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomli
                with open(pyproject_path, 'rb') as f:
                    config = tomli.load(f)
                
                if 'project' in config and 'requires-python' in config['project']:
                    python_versions['pyproject.toml'] = config['project']['requires-python']
            except:
                pass
        
        # Check workflows
        workflows_dir = self.project_root / ".github" / "workflows"
        if workflows_dir.exists():
            for workflow_file in workflows_dir.glob("*.yml"):
                try:
                    with open(workflow_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Look for Python version in workflows
                    version_match = re.search(r'python-version:\s*["\']([^"\']+)["\']', content)
                    if version_match:
                        python_versions[f'workflow:{workflow_file.name}'] = version_match.group(1)
                except:
                    pass
        
        # Check for inconsistencies
        if len(set(python_versions.values())) > 1:
            self.issues.append(ConfigurationIssue(
                file_path=self.project_root,
                issue_type="inconsistent_python_version",
                description=f"Inconsistent Python versions across configurations: {python_versions}",
                suggested_fix="Standardize Python version across all configuration files",
                severity="warning"
            ))

    def _validate_dependency_consistency(self) -> None:
        """Validate dependency consistency across requirements files."""
        requirements_files = list(self.project_root.glob("requirements*.txt"))
        config_dir = self.project_root / "config"
        if config_dir.exists():
            requirements_files.extend(config_dir.glob("requirements*.txt"))
        
        all_dependencies = {}
        
        for req_file in requirements_files:
            try:
                with open(req_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        package_name = line.split('==')[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0]
                        if package_name not in all_dependencies:
                            all_dependencies[package_name] = {}
                        all_dependencies[package_name][req_file.name] = line
            except:
                continue
        
        # Check for conflicting versions
        for package, file_versions in all_dependencies.items():
            if len(file_versions) > 1:
                versions = list(file_versions.values())
                if len(set(versions)) > 1:
                    self.issues.append(ConfigurationIssue(
                        file_path=self.project_root,
                        issue_type="conflicting_dependency_versions",
                        description=f"Package '{package}' has conflicting versions: {file_versions}",
                        suggested_fix="Standardize package versions across requirements files",
                        severity="warning"
                    ))

    def generate_report(self) -> bool:
        """Generate comprehensive configuration validation report."""
        print(f"\n{'='*80}")
        print("📊 CONFIGURATION VALIDATION REPORT")
        print(f"{'='*80}")
        
        if not self.issues:
            print("✅ ALL CONFIGURATION VALIDATIONS PASSED")
            print(f"✅ No issues found in configurations at {self.project_root}")
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
        print(f"❌ FOUND {len(self.issues)} CONFIGURATION ISSUES")
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
            print(f"   1. Fix {error_count} CRITICAL configuration issues (will cause CI failures)")
        
        warning_count = len(issues_by_severity['warning'])
        if warning_count > 0:
            print(f"   2. Address {warning_count} configuration warnings (recommended)")
        
        info_count = len(issues_by_severity['info'])
        if info_count > 0:
            print(f"   3. Consider {info_count} configuration improvements (optional)")
        
        print()
        print("📚 REFERENCE: docs/development/NAMING_CONVENTIONS.md")
        print(f"{'='*80}")
        
        # Return True if no critical errors
        return len(issues_by_severity['error']) == 0

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate configuration files across the Second Brain project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/validate_configurations.py
    python scripts/validate_configurations.py --check-security
    python scripts/validate_configurations.py --json-report config_validation.json
        """
    )
    
    parser.add_argument('--check-security', action='store_true',
                       help='Enable enhanced security checks')
    parser.add_argument('--fix-format', action='store_true',
                       help='Attempt to fix formatting issues')
    parser.add_argument('--json-report', 
                       help='Save detailed report to JSON file')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    validator = ConfigurationValidator(project_root)
    
    try:
        # Run validation
        success = validator.validate_all()
        
        # Save JSON report if requested
        if args.json_report:
            import json
            from datetime import datetime
            
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
        print("\n⏹️  Configuration validation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"💥 Configuration validation failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()