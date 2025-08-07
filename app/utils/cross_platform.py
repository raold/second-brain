"""
Cross-platform utilities for Second Brain development.
Handles differences between Windows, macOS, and Linux environments.
"""

import os
import sys
import platform
from pathlib import Path
from typing import Optional, Union

class PlatformHelper:
    """Helper for cross-platform development with Google Drive sync."""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.is_windows = self.system == 'windows'
        self.is_mac = self.system == 'darwin'
        self.is_linux = self.system == 'linux'
        self.project_root = self._find_project_root()
        
    def _find_project_root(self) -> Path:
        """Find project root regardless of platform or Google Drive location."""
        # Known Google Drive paths for the project
        possible_paths = [
            # Windows
            Path("G:/My Drive/projects/second-brain"),
            Path("G:\\My Drive\\projects\\second-brain"),
            # macOS
            Path("/Users/dro/Library/CloudStorage/GoogleDrive-dro@lynchburgsmiles.com/My Drive/projects/second-brain"),
            # Linux (common Google Drive mount points)
            Path.home() / "GoogleDrive/My Drive/projects/second-brain",
            Path.home() / "Google Drive/My Drive/projects/second-brain",
            Path("/mnt/googledrive/My Drive/projects/second-brain"),  # WSL2
            # Fallback to current directory
            Path.cwd()
        ]
        
        # Check each possible path
        for path in possible_paths:
            if path.exists() and (path / "app").exists():
                return path
                
        # If not found, use current directory
        return Path.cwd()
    
    def get_venv_python(self) -> str:
        """Get the correct Python executable path for the virtual environment."""
        venv_path = self.project_root / ".venv"
        
        if self.is_windows:
            python_exe = venv_path / "Scripts" / "python.exe"
            if python_exe.exists():
                return str(python_exe)
            # Fallback for Windows
            return "python"
        else:
            # macOS and Linux
            python_exe = venv_path / "bin" / "python"
            if python_exe.exists():
                return str(python_exe)
            # Fallback
            return "python3"
    
    def get_venv_pip(self) -> str:
        """Get the correct pip executable path for the virtual environment."""
        venv_path = self.project_root / ".venv"
        
        if self.is_windows:
            pip_exe = venv_path / "Scripts" / "pip.exe"
            if pip_exe.exists():
                return str(pip_exe)
            return "pip"
        else:
            pip_exe = venv_path / "bin" / "pip"
            if pip_exe.exists():
                return str(pip_exe)
            return "pip3"
    
    def normalize_path(self, path: Union[str, Path]) -> Path:
        """Normalize path for current platform."""
        path = Path(path)
        
        # Handle Google Drive paths
        if str(path).startswith("G:\\") or str(path).startswith("G:/"):
            if not self.is_windows:
                # Convert Windows Google Drive path to macOS/Linux
                relative = str(path).replace("G:\\My Drive", "").replace("G:/My Drive", "")
                if self.is_mac:
                    return Path("/Users/dro/Library/CloudStorage/GoogleDrive-dro@lynchburgsmiles.com/My Drive") / relative.lstrip("/\\")
                else:
                    return Path.home() / "GoogleDrive/My Drive" / relative.lstrip("/\\")
        
        elif "/GoogleDrive" in str(path) or "/CloudStorage" in str(path):
            if self.is_windows:
                # Convert macOS/Linux Google Drive path to Windows
                if "My Drive/projects/second-brain" in str(path):
                    return Path("G:/My Drive/projects/second-brain")
        
        return path
    
    def get_platform_info(self) -> dict:
        """Get detailed platform information."""
        return {
            "system": platform.system(),
            "platform": platform.platform(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": sys.version,
            "is_windows": self.is_windows,
            "is_mac": self.is_mac,
            "is_linux": self.is_linux,
            "project_root": str(self.project_root),
            "venv_python": self.get_venv_python(),
            "encoding": sys.getdefaultencoding(),
            "file_encoding": sys.getfilesystemencoding()
        }
    
    def fix_encoding(self, text: str) -> str:
        """Fix encoding issues, especially on Windows."""
        if self.is_windows:
            # Windows often has issues with UTF-8
            try:
                # Try to encode and decode to fix issues
                return text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
            except:
                # Fallback to ASCII
                return text.encode('ascii', errors='ignore').decode('ascii', errors='ignore')
        return text
    
    def get_line_ending(self) -> str:
        """Get appropriate line ending for platform."""
        return '\r\n' if self.is_windows else '\n'
    
    def get_path_separator(self) -> str:
        """Get platform-specific path separator."""
        return '\\' if self.is_windows else '/'
    
    def make_executable(self, script_path: Union[str, Path]) -> None:
        """Make a script executable (Unix-like systems only)."""
        if not self.is_windows:
            import stat
            path = Path(script_path)
            if path.exists():
                path.chmod(path.stat().st_mode | stat.S_IEXEC)
    
    def get_shell_command(self, command: str) -> str:
        """Adapt shell commands for the platform."""
        if self.is_windows:
            # Windows-specific adaptations
            command = command.replace('python3', 'python')
            command = command.replace('pip3', 'pip')
            command = command.replace('source .venv/bin/activate', '.venv\\Scripts\\activate')
            command = command.replace('.venv/bin/', '.venv\\Scripts\\')
            command = command.replace('/', '\\')
        else:
            # Unix-like adaptations
            command = command.replace('.venv\\Scripts\\', '.venv/bin/')
            command = command.replace('\\', '/')
            
        return command
    
    def get_test_command(self, test_path: str = "tests/unit") -> str:
        """Get platform-appropriate test command."""
        python = self.get_venv_python()
        return f'"{python}" -m pytest {test_path} -v --tb=short'
    
    def get_run_command(self) -> str:
        """Get platform-appropriate run command for the app."""
        python = self.get_venv_python()
        return f'"{python}" -m uvicorn app.app:app --reload --host 0.0.0.0 --port 8000'
    
    def print_platform_banner(self):
        """Print a nice platform-specific banner."""
        info = self.get_platform_info()
        
        # Platform-specific emoji (ASCII fallback for Windows)
        emoji = "[WIN]" if self.is_windows else "[MAC]" if self.is_mac else "[LNX]"
        
        # Truncate project root if too long
        project_root = str(info['project_root'])
        if len(project_root) > 45:
            project_root = "..." + project_root[-42:]
        
        print(f"""
╔════════════════════════════════════════════════════════════╗
║  {emoji} Second Brain v4.0.0 - Cross-Platform Development   ║
╠════════════════════════════════════════════════════════════╣
║  Platform: {info['system']:<47} ║
║  Project:  {project_root:<47} ║
║  Python:   {info['python_version'].split()[0]:<47} ║
║  Encoding: {info['encoding']:<47} ║
╚════════════════════════════════════════════════════════════╝
        """)


# Global instance
_platform_helper: Optional[PlatformHelper] = None

def get_platform_helper() -> PlatformHelper:
    """Get global platform helper instance."""
    global _platform_helper
    if _platform_helper is None:
        _platform_helper = PlatformHelper()
    return _platform_helper

# Convenience functions
def is_windows() -> bool:
    """Check if running on Windows."""
    return get_platform_helper().is_windows

def is_mac() -> bool:
    """Check if running on macOS."""
    return get_platform_helper().is_mac

def is_linux() -> bool:
    """Check if running on Linux."""
    return get_platform_helper().is_linux

def get_project_root() -> Path:
    """Get project root path."""
    return get_platform_helper().project_root

def get_venv_python() -> str:
    """Get virtual environment Python executable."""
    return get_platform_helper().get_venv_python()

def normalize_path(path: Union[str, Path]) -> Path:
    """Normalize path for current platform."""
    return get_platform_helper().normalize_path(path)

def setup_utf8_encoding():
    """Set up UTF-8 encoding for all platforms (especially Windows)."""
    if platform.system() == 'Windows':
        # Fix Windows console encoding
        import locale
        locale.setlocale(locale.LC_ALL, '')
        
        # Set environment variables for UTF-8
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        
        # Fix console output on Windows
        if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')

def get_google_drive_status() -> dict:
    """Check Google Drive sync status."""
    helper = get_platform_helper()
    project_root = helper.project_root
    
    return {
        "platform": helper.system,
        "project_root": str(project_root),
        "is_google_drive": "GoogleDrive" in str(project_root) or "Google Drive" in str(project_root) or "My Drive" in str(project_root),
        "root_exists": project_root.exists(),
        "app_exists": (project_root / "app").exists(),
        "venv_exists": (project_root / ".venv").exists()
    }