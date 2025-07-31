#!/usr/bin/env python
"""
Comprehensive virtual environment validation script.
Follows PEP8 and Pythonic best practices.
"""

import json

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class VirtualEnvironmentValidator:
    """Validates Python virtual environment setup and dependencies."""

    def __init__(self, venv_path: Optional[Path] = None):
        """Initialize validator with virtual environment path."""
        self.venv_path = venv_path or Path('.venv')
        self.python_exe = self._get_python_executable()
        self.issues: List[Dict[str, str]] = []
        self.warnings: List[Dict[str, str]] = []

    def _get_python_executable(self) -> Path:
        """Get the correct Python executable path based on OS."""
        if platform.system() == 'Windows':
            python_path = self.venv_path / 'Scripts' / 'python.exe'
        else:
            python_path = self.venv_path / 'bin' / 'python'

        if not python_path.exists():
            logger.error(f"Python executable not found at {python_path}")
            raise FileNotFoundError(f"Python executable not found at {python_path}")

        return python_path

    def validate_all(self) -> bool:
        """Run all validation checks."""
        logger.info("Starting comprehensive virtual environment validation")

        checks = [
            self.check_venv_structure,
            self.check_python_version,
            self.check_pip_version,
            self.check_installed_packages,
            self.check_dependency_conflicts,
            self.check_requirements_files,
            self.check_import_availability,
            self.check_pep8_tools,
        ]

        all_passed = True
        for check in checks:
            try:
                if not check():
                    all_passed = False
            except Exception as e:
                logger.error(f"Check {check.__name__} failed with error: {e}")
                self.issues.append({
                    'check': check.__name__,
                    'severity': 'ERROR',
                    'message': str(e)
                })
                all_passed = False

        self._generate_report()
        return all_passed

    def check_venv_structure(self) -> bool:
        """Validate virtual environment directory structure."""
        logger.info("Checking virtual environment structure...")

        required_dirs = ['Scripts' if platform.system() == 'Windows' else 'bin', 'lib', 'include']
        missing_dirs = []

        for dir_name in required_dirs:
            dir_path = self.venv_path / dir_name
            if not dir_path.exists():
                missing_dirs.append(dir_name)

        if missing_dirs:
            self.issues.append({
                'check': 'venv_structure',
                'severity': 'ERROR',
                'message': f"Missing required directories: {', '.join(missing_dirs)}"
            })
            return False

        # Check pyvenv.cfg
        pyvenv_cfg = self.venv_path / 'pyvenv.cfg'
        if not pyvenv_cfg.exists():
            self.issues.append({
                'check': 'venv_structure',
                'severity': 'ERROR',
                'message': "Missing pyvenv.cfg file"
            })
            return False

        # Parse pyvenv.cfg
        with open(pyvenv_cfg) as f:
            config = {}
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    config[key.strip()] = value.strip()

        logger.debug(f"pyvenv.cfg contents: {config}")

        # Check for hardcoded paths
        if 'home' in config:
            home_path = config['home']
            if 'dro.LAB' in home_path or 'AppData\\Local\\Programs' in home_path:
                self.warnings.append({
                    'check': 'venv_structure',
                    'severity': 'WARNING',
                    'message': f"Virtual environment created with hardcoded path: {home_path}"
                })

        return True

    def check_python_version(self) -> bool:
        """Check Python version compatibility."""
        logger.info("Checking Python version...")

        result = subprocess.run(
            [str(self.python_exe), '--version'],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            self.issues.append({
                'check': 'python_version',
                'severity': 'ERROR',
                'message': f"Failed to get Python version: {result.stderr}"
            })
            return False

        version_str = result.stdout.strip()
        logger.info(f"Python version: {version_str}")

        # Extract version numbers
        import re
        match = re.search(r'Python (\d+)\.(\d+)\.(\d+)', version_str)
        if match:
            major, minor, patch = map(int, match.groups())
            if major < 3 or (major == 3 and minor < 8):
                self.issues.append({
                    'check': 'python_version',
                    'severity': 'ERROR',
                    'message': f"Python {major}.{minor}.{patch} is too old. Requires Python 3.8+"
                })
                return False

        return True

    def check_pip_version(self) -> bool:
        """Check pip version and upgrade if needed."""
        logger.info("Checking pip version...")

        result = subprocess.run(
            [str(self.python_exe), '-m', 'pip', '--version'],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            self.issues.append({
                'check': 'pip_version',
                'severity': 'ERROR',
                'message': f"Failed to get pip version: {result.stderr}"
            })
            return False

        logger.info(f"Pip version: {result.stdout.strip()}")
        return True

    def check_installed_packages(self) -> bool:
        """List all installed packages and their versions."""
        logger.info("Checking installed packages...")

        result = subprocess.run(
            [str(self.python_exe), '-m', 'pip', 'list', '--format=json'],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            self.issues.append({
                'check': 'installed_packages',
                'severity': 'ERROR',
                'message': f"Failed to list packages: {result.stderr}"
            })
            return False

        packages = json.loads(result.stdout)
        logger.info(f"Found {len(packages)} installed packages")

        # Log package details
        for pkg in packages:
            logger.debug(f"  {pkg['name']}=={pkg['version']}")

        return True

    def check_dependency_conflicts(self) -> bool:
        """Check for dependency conflicts using pip check."""
        logger.info("Checking for dependency conflicts...")

        result = subprocess.run(
            [str(self.python_exe), '-m', 'pip', 'check'],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            self.issues.append({
                'check': 'dependency_conflicts',
                'severity': 'ERROR',
                'message': f"Dependency conflicts found:\n{result.stdout}"
            })
            logger.error(f"Dependency conflicts:\n{result.stdout}")
            return False

        logger.info("No dependency conflicts found")
        return True

    def check_requirements_files(self) -> bool:
        """Validate requirements files for conflicts and duplicates."""
        logger.info("Checking requirements files...")

        req_files = ['requirements.txt', 'requirements-dev.txt', 'requirements-v3.txt']
        all_requirements = defaultdict(list)

        for req_file in req_files:
            if not Path(req_file).exists():
                logger.debug(f"Requirements file {req_file} not found, skipping")
                continue

            logger.info(f"Parsing {req_file}...")
            with open(req_file) as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    # Parse package name and version
                    if '==' in line:
                        pkg_name, version = line.split('==', 1)
                        pkg_name = pkg_name.split('[')[0]  # Remove extras
                        all_requirements[pkg_name].append({
                            'file': req_file,
                            'line': line_num,
                            'version': version
                        })

        # Check for conflicts
        conflicts_found = False
        for pkg_name, specs in all_requirements.items():
            if len(specs) > 1:
                versions = set(spec['version'] for spec in specs)
                if len(versions) > 1:
                    conflicts_found = True
                    conflict_msg = f"Package '{pkg_name}' has conflicting versions:\n"
                    for spec in specs:
                        conflict_msg += f"  - {spec['version']} in {spec['file']}:{spec['line']}\n"

                    self.issues.append({
                        'check': 'requirements_files',
                        'severity': 'ERROR',
                        'message': conflict_msg
                    })

        return not conflicts_found

    def check_import_availability(self) -> bool:
        """Check if critical imports are available."""
        logger.info("Checking critical imports...")

        critical_imports = [
            'fastapi',
            'uvicorn',
            'pydantic',
            'sqlalchemy',
            'pytest',
            'httpx'
        ]

        import_script = """
import sys
import importlib

packages = {packages}
failed = []

for package in packages:
    try:
        importlib.import_module(package)
    except ImportError as e:
        failed.append((package, str(e)))

if failed:
    for pkg, err in failed:
        print(f"FAILED: {{pkg}} - {{err}}")
    sys.exit(1)
else:
    print("All imports successful")
"""

        result = subprocess.run(
            [str(self.python_exe), '-c', import_script.format(packages=critical_imports)],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            self.issues.append({
                'check': 'import_availability',
                'severity': 'ERROR',
                'message': f"Failed to import critical packages:\n{result.stdout}"
            })
            return False

        logger.info("All critical imports are available")
        return True

    def check_pep8_tools(self) -> bool:
        """Check if PEP8/linting tools are installed."""
        logger.info("Checking PEP8 and linting tools...")

        linting_tools = ['ruff', 'black', 'mypy', 'pylint', 'flake8']
        installed_tools = []
        missing_tools = []

        for tool in linting_tools:
            result = subprocess.run(
                [str(self.python_exe), '-m', tool, '--version'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                installed_tools.append(tool)
                logger.debug(f"{tool} is installed")
            else:
                missing_tools.append(tool)

        if missing_tools:
            self.warnings.append({
                'check': 'pep8_tools',
                'severity': 'WARNING',
                'message': f"Recommended linting tools not installed: {', '.join(missing_tools)}"
            })

        if installed_tools:
            logger.info(f"Installed linting tools: {', '.join(installed_tools)}")

        return True

    def _generate_report(self) -> None:
        """Generate a comprehensive validation report."""
        logger.info("\n" + "="*60)
        logger.info("VIRTUAL ENVIRONMENT VALIDATION REPORT")
        logger.info("="*60)

        if not self.issues and not self.warnings:
            logger.info("✅ All checks passed! Virtual environment is properly configured.")
        else:
            if self.issues:
                logger.error(f"\n❌ Found {len(self.issues)} issues:")
                for issue in self.issues:
                    logger.error(f"  [{issue['severity']}] {issue['check']}: {issue['message']}")

            if self.warnings:
                logger.warning(f"\n⚠️  Found {len(self.warnings)} warnings:")
                for warning in self.warnings:
                    logger.warning(f"  [{warning['severity']}] {warning['check']}: {warning['message']}")

        logger.info("="*60)


def main():
    """Main entry point."""
    validator = VirtualEnvironmentValidator()
    success = validator.validate_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
