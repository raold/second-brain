#!/usr/bin/env python3
"""
Bulletproof Virtual Environment Setup
Automatically creates and validates .venv with all required dependencies
"""

import os
import sys
import subprocess
import platform
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple


class BulletproofVenv:
    """Creates and validates bulletproof virtual environments"""
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.venv_path = self.project_root / ".venv"
        self.is_windows = platform.system() == "Windows"
        self.python_exe = self._get_python_executable()
        self.pip_exe = self._get_pip_executable()
        
    def _get_python_executable(self) -> Optional[str]:
        """Get the Python executable path in venv"""
        if self.is_windows:
            exe_path = self.venv_path / "Scripts" / "python.exe"
        else:
            exe_path = self.venv_path / "bin" / "python"
        return str(exe_path) if exe_path.exists() else None
    
    def _get_pip_executable(self) -> Optional[str]:
        """Get the pip executable path in venv"""
        if self.is_windows:
            exe_path = self.venv_path / "Scripts" / "pip.exe"
        else:
            exe_path = self.venv_path / "bin" / "pip"
        return str(exe_path) if exe_path.exists() else None
    
    def _run_command(self, cmd: List[str], description: str) -> Tuple[bool, str]:
        """Run a command and return success status and output"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                cwd=self.project_root
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            error_msg = f"{description} failed: {e.stderr}"
            return False, error_msg
        except FileNotFoundError as e:
            error_msg = f"{description} failed: Command not found - {e}"
            return False, error_msg
    
    def check_prerequisites(self) -> bool:
        """Check if required tools are available"""
        print("🔍 Checking prerequisites...")
        
        # Check Python
        try:
            result = subprocess.run([sys.executable, "--version"], capture_output=True, text=True)
            python_version = result.stdout.strip()
            print(f"   ✅ Python: {python_version}")
        except Exception as e:
            print(f"   ❌ Python check failed: {e}")
            return False
        
        # Check pip
        try:
            result = subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True, text=True)
            pip_version = result.stdout.strip()
            print(f"   ✅ Pip: {pip_version}")
        except Exception as e:
            print(f"   ❌ Pip check failed: {e}")
            return False
        
        # Check venv module
        try:
            subprocess.run([sys.executable, "-m", "venv", "--help"], capture_output=True, check=True)
            print("   ✅ Venv module available")
        except Exception as e:
            print(f"   ❌ Venv module check failed: {e}")
            return False
        
        return True
    
    def create_venv(self, force: bool = False) -> bool:
        """Create virtual environment"""
        if self.venv_path.exists() and not force:
            print(f"📦 Virtual environment already exists: {self.venv_path}")
            return True
        
        if force and self.venv_path.exists():
            print(f"🗑️  Removing existing venv: {self.venv_path}")
            shutil.rmtree(self.venv_path)
        
        print(f"📦 Creating virtual environment: {self.venv_path}")
        
        success, output = self._run_command(
            [sys.executable, "-m", "venv", str(self.venv_path)],
            "Virtual environment creation"
        )
        
        if not success:
            print(f"❌ {output}")
            return False
        
        print("   ✅ Virtual environment created")
        
        # Update executable paths
        self.python_exe = self._get_python_executable()
        self.pip_exe = self._get_pip_executable()
        
        if not self.python_exe or not self.pip_exe:
            print("❌ Failed to locate venv executables")
            return False
        
        return True
    
    def upgrade_pip(self) -> bool:
        """Upgrade pip to latest version"""
        print("📦 Upgrading pip...")
        
        success, output = self._run_command(
            [self.python_exe, "-m", "pip", "install", "--upgrade", "pip"],
            "Pip upgrade"
        )
        
        if not success:
            print(f"❌ {output}")
            return False
        
        print("   ✅ Pip upgraded")
        return True
    
    def install_requirements(self) -> bool:
        """Install all requirements files"""
        requirements_files = [
            self.project_root / "requirements.txt",
            self.project_root / "config" / "requirements-production.txt",
            self.project_root / "config" / "requirements-ci.txt"
        ]
        
        for req_file in requirements_files:
            if not req_file.exists():
                print(f"⚠️  Requirements file not found: {req_file}")
                continue
            
            print(f"📦 Installing {req_file.name}...")
            
            success, output = self._run_command(
                [self.pip_exe, "install", "-r", str(req_file)],
                f"Installation of {req_file.name}"
            )
            
            if not success:
                print(f"❌ {output}")
                return False
            
            print(f"   ✅ {req_file.name} installed")
        
        return True
    
    def validate_installation(self) -> bool:
        """Validate the virtual environment installation"""
        print("🔍 Validating installation...")
        
        # Check Python version
        success, output = self._run_command(
            [self.python_exe, "--version"],
            "Python version check"
        )
        
        if not success:
            print(f"❌ {output}")
            return False
        
        print(f"   ✅ Python: {output.strip()}")
        
        # Check critical packages
        critical_packages = ["fastapi", "uvicorn", "pydantic", "pytest"]
        
        for package in critical_packages:
            success, output = self._run_command(
                [self.pip_exe, "show", package],
                f"Package check: {package}"
            )
            
            if not success:
                print(f"   ❌ Missing package: {package}")
                return False
            
            # Extract version
            for line in output.split("\\n"):
                if line.startswith("Version:"):
                    version = line.split(":", 1)[1].strip()
                    print(f"   ✅ {package}: {version}")
                    break
        
        return True
    
    def run_health_check(self) -> bool:
        """Run a health check on the application"""
        print("🏥 Running health check...")
        
        # Try to import main modules
        test_script = '''
import sys
sys.path.insert(0, ".")

try:
    from app.app import app
    print("✅ App import successful")
except Exception as e:
    print(f"❌ App import failed: {e}")
    sys.exit(1)

try:
    from app.database import get_database
    print("✅ Database module import successful")
except Exception as e:
    print(f"❌ Database import failed: {e}")
    sys.exit(1)

print("✅ All critical imports successful")
'''
        
        # Write test script to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            temp_script = f.name
        
        try:
            success, output = self._run_command(
                [self.python_exe, temp_script],
                "Health check"
            )
            
            if success:
                print("   " + output.replace("\\n", "\\n   "))
                return True
            else:
                print(f"❌ Health check failed: {output}")
                return False
        
        finally:
            os.unlink(temp_script)
    
    def generate_activation_script(self) -> None:
        """Generate convenient activation scripts"""
        print("📝 Generating activation scripts...")
        
        # Windows batch script
        if self.is_windows:
            activate_bat = self.project_root / "activate-venv.bat"
            with open(activate_bat, 'w') as f:
                f.write(f"""@echo off
echo Activating Second Brain virtual environment...
call "{self.venv_path}\\Scripts\\activate.bat"
echo ✅ Virtual environment activated
echo.
echo Available commands:
echo   python main.py                    - Start application
echo   python scripts/test_runner.py     - Run tests
echo   python -m uvicorn main:app --reload - Start with reload
echo.
cmd /k
""")
            print(f"   ✅ Created {activate_bat}")
        
        # Unix shell script
        activate_sh = self.project_root / "activate-venv.sh"
        with open(activate_sh, 'w') as f:
            f.write(f"""#!/bin/bash
echo "Activating Second Brain virtual environment..."
source "{self.venv_path}/bin/activate"
echo "✅ Virtual environment activated"
echo ""
echo "Available commands:"
echo "  python main.py                    - Start application"
echo "  python scripts/test_runner.py     - Run tests"
echo "  python -m uvicorn main:app --reload - Start with reload"
echo ""
exec bash
""")
        
        # Make shell script executable
        try:
            os.chmod(activate_sh, 0o755)
            print(f"   ✅ Created {activate_sh}")
        except Exception as e:
            print(f"   ⚠️  Created {activate_sh} but failed to make executable: {e}")
    
    def setup_complete(self) -> bool:
        """Complete setup process"""
        print("\\n" + "=" * 60)
        print("🎉 BULLETPROOF VIRTUAL ENVIRONMENT SETUP COMPLETE")
        print("=" * 60)
        
        print(f"📁 Project Root: {self.project_root}")
        print(f"🐍 Python Executable: {self.python_exe}")
        print(f"📦 Pip Executable: {self.pip_exe}")
        
        print("\\n🚀 Quick Start Commands:")
        if self.is_windows:
            print(f"   {self.python_exe} main.py")
            print(f"   {self.python_exe} scripts/test_runner.py --validation")
            print("   activate-venv.bat  # For interactive development")
        else:
            print(f"   {self.python_exe} main.py")
            print(f"   {self.python_exe} scripts/test_runner.py --validation")
            print("   ./activate-venv.sh  # For interactive development")
        
        print("\\n💡 Remember: Always use the .venv Python for this project!")
        return True


def main():
    """Main setup function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Bulletproof Virtual Environment Setup")
    parser.add_argument("--force", action="store_true", help="Force recreate venv")
    parser.add_argument("--skip-health-check", action="store_true", help="Skip application health check")
    
    args = parser.parse_args()
    
    print("🔧 Second Brain - Bulletproof Virtual Environment Setup")
    print("=" * 60)
    
    venv_setup = BulletproofVenv()
    
    # Check prerequisites
    if not venv_setup.check_prerequisites():
        print("❌ Prerequisites check failed")
        sys.exit(1)
    
    # Create virtual environment
    if not venv_setup.create_venv(force=args.force):
        print("❌ Virtual environment creation failed")
        sys.exit(1)
    
    # Upgrade pip
    if not venv_setup.upgrade_pip():
        print("❌ Pip upgrade failed")
        sys.exit(1)
    
    # Install requirements
    if not venv_setup.install_requirements():
        print("❌ Requirements installation failed")
        sys.exit(1)
    
    # Validate installation
    if not venv_setup.validate_installation():
        print("❌ Installation validation failed")
        sys.exit(1)
    
    # Health check (optional)
    if not args.skip_health_check:
        if not venv_setup.run_health_check():
            print("⚠️  Health check failed, but installation may still be valid")
    
    # Generate activation scripts
    venv_setup.generate_activation_script()
    
    # Complete setup
    venv_setup.setup_complete()
    
    print("\\n✅ Setup completed successfully!")


if __name__ == "__main__":
    main()