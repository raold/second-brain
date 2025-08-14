"""
Platform and Environment Context Awareness Module

Provides intelligent detection of:
- Operating system (Windows, macOS, Linux, WSL)
- Development environment (local, CI/CD, Docker, GitHub Actions)
- Database configuration (mock, PostgreSQL, in-memory)
- Python environment (venv, conda, system)
- Available system resources
"""

import os
import sys
import platform
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import psutil
import socket


class PlatformType(Enum):
    """Supported platform types"""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    WSL = "wsl"
    DOCKER = "docker"
    UNKNOWN = "unknown"


class EnvironmentType(Enum):
    """Environment types"""
    LOCAL_DEV = "local_dev"
    CI_CD = "ci_cd"
    GITHUB_ACTIONS = "github_actions"
    DOCKER_CONTAINER = "docker_container"
    PRODUCTION = "production"
    TEST = "test"


class DatabaseType(Enum):
    """Database backend types"""
    MOCK = "mock"
    POSTGRESQL = "postgresql"
    IN_MEMORY = "in_memory"
    SQLITE = "sqlite"


@dataclass
class PlatformContext:
    """Complete platform and environment context"""
    # Platform info
    platform_type: PlatformType
    platform_version: str
    architecture: str
    processor: str
    
    # Environment info
    environment_type: EnvironmentType
    is_ci: bool
    is_docker: bool
    is_wsl: bool
    
    # Python info
    python_version: str
    python_implementation: str
    is_venv: bool
    venv_path: Optional[str]
    
    # Database info
    database_type: DatabaseType
    database_available: bool
    use_mock_database: bool
    
    # System resources
    cpu_count: int
    memory_gb: float
    disk_available_gb: float
    
    # Network info
    hostname: str
    has_internet: bool
    
    # File system info
    path_separator: str
    line_ending: str
    temp_dir: Path
    home_dir: Path
    
    # Development tools
    has_git: bool
    has_docker: bool
    has_make: bool
    has_wsl: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary"""
        return {
            "platform": {
                "type": self.platform_type.value,
                "version": self.platform_version,
                "architecture": self.architecture,
                "processor": self.processor
            },
            "environment": {
                "type": self.environment_type.value,
                "is_ci": self.is_ci,
                "is_docker": self.is_docker,
                "is_wsl": self.is_wsl
            },
            "python": {
                "version": self.python_version,
                "implementation": self.python_implementation,
                "is_venv": self.is_venv,
                "venv_path": str(self.venv_path) if self.venv_path else None
            },
            "database": {
                "type": self.database_type.value,
                "available": self.database_available,
                "use_mock": self.use_mock_database
            },
            "resources": {
                "cpu_count": self.cpu_count,
                "memory_gb": self.memory_gb,
                "disk_available_gb": self.disk_available_gb
            },
            "network": {
                "hostname": self.hostname,
                "has_internet": self.has_internet
            },
            "filesystem": {
                "path_separator": self.path_separator,
                "line_ending": self.line_ending,
                "temp_dir": str(self.temp_dir),
                "home_dir": str(self.home_dir)
            },
            "tools": {
                "git": self.has_git,
                "docker": self.has_docker,
                "make": self.has_make,
                "wsl": self.has_wsl
            }
        }


class PlatformDetector:
    """Intelligent platform and environment detection"""
    
    @staticmethod
    def detect_platform() -> PlatformType:
        """Detect the current platform"""
        system = platform.system().lower()
        
        # Check for Docker first
        if PlatformDetector._is_docker():
            return PlatformType.DOCKER
        
        # Check for WSL
        if system == "linux" and PlatformDetector._is_wsl():
            return PlatformType.WSL
        
        # Standard platforms
        if system == "windows":
            return PlatformType.WINDOWS
        elif system == "darwin":
            return PlatformType.MACOS
        elif system == "linux":
            return PlatformType.LINUX
        else:
            return PlatformType.UNKNOWN
    
    @staticmethod
    def detect_environment() -> EnvironmentType:
        """Detect the current environment type"""
        # Check environment variables
        if os.getenv("GITHUB_ACTIONS") == "true":
            return EnvironmentType.GITHUB_ACTIONS
        elif os.getenv("CI") == "true":
            return EnvironmentType.CI_CD
        elif PlatformDetector._is_docker():
            return EnvironmentType.DOCKER_CONTAINER
        elif os.getenv("ENVIRONMENT") == "test":
            return EnvironmentType.TEST
        elif os.getenv("ENVIRONMENT") == "production":
            return EnvironmentType.PRODUCTION
        else:
            return EnvironmentType.LOCAL_DEV
    
    @staticmethod
    def detect_database() -> Tuple[DatabaseType, bool, bool]:
        """Detect database configuration
        
        Returns:
            (database_type, is_available, use_mock)
        """
        # Check environment variables
        use_mock = os.getenv("USE_MOCK_DATABASE", "").lower() == "true"
        
        if use_mock:
            return DatabaseType.MOCK, True, True
        
        # Check for PostgreSQL
        if PlatformDetector._check_postgresql():
            return DatabaseType.POSTGRESQL, True, False
        
        # Check for SQLite
        if os.getenv("DATABASE_URL", "").startswith("sqlite"):
            return DatabaseType.SQLITE, True, False
        
        # Default to in-memory
        return DatabaseType.IN_MEMORY, True, False
    
    @staticmethod
    def _is_docker() -> bool:
        """Check if running in Docker container"""
        # Check for .dockerenv file
        if Path("/.dockerenv").exists():
            return True
        
        # Check cgroup for docker
        try:
            with open("/proc/self/cgroup", "r") as f:
                return "docker" in f.read()
        except:
            return False
    
    @staticmethod
    def _is_wsl() -> bool:
        """Check if running in WSL"""
        try:
            with open("/proc/version", "r") as f:
                return "microsoft" in f.read().lower()
        except:
            return False
    
    @staticmethod
    def _check_postgresql() -> bool:
        """Check if PostgreSQL is available"""
        try:
            import asyncpg
            # Check if we can import and if connection params exist
            host = os.getenv("POSTGRES_HOST", "localhost")
            port = os.getenv("POSTGRES_PORT", "5432")
            
            # Try to connect (with timeout)
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, int(port)))
            sock.close()
            return result == 0
        except:
            return False
    
    @staticmethod
    def _check_command(command: str) -> bool:
        """Check if a command is available"""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["where", command],
                    capture_output=True,
                    check=False
                )
            else:
                result = subprocess.run(
                    ["which", command],
                    capture_output=True,
                    check=False
                )
            return result.returncode == 0
        except:
            return False
    
    @staticmethod
    def _check_internet() -> bool:
        """Check if internet is available"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            # Try Google DNS
            result = sock.connect_ex(("8.8.8.8", 53))
            sock.close()
            return result == 0
        except:
            return False
    
    @classmethod
    def get_context(cls) -> PlatformContext:
        """Get complete platform context"""
        platform_type = cls.detect_platform()
        env_type = cls.detect_environment()
        db_type, db_available, use_mock = cls.detect_database()
        
        # Detect Python environment
        is_venv = hasattr(sys, 'real_prefix') or (
            hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
        )
        venv_path = None
        if is_venv:
            venv_path = Path(sys.prefix)
        
        # Get system resources
        memory_bytes = psutil.virtual_memory().total
        disk_stats = psutil.disk_usage('/')
        
        # Platform-specific settings
        if platform_type == PlatformType.WINDOWS:
            path_sep = "\\"
            line_ending = "\r\n"
        else:
            path_sep = "/"
            line_ending = "\n"
        
        return PlatformContext(
            # Platform
            platform_type=platform_type,
            platform_version=platform.version(),
            architecture=platform.machine(),
            processor=platform.processor(),
            
            # Environment
            environment_type=env_type,
            is_ci=env_type in [EnvironmentType.CI_CD, EnvironmentType.GITHUB_ACTIONS],
            is_docker=platform_type == PlatformType.DOCKER,
            is_wsl=platform_type == PlatformType.WSL,
            
            # Python
            python_version=platform.python_version(),
            python_implementation=platform.python_implementation(),
            is_venv=is_venv,
            venv_path=venv_path,
            
            # Database
            database_type=db_type,
            database_available=db_available,
            use_mock_database=use_mock,
            
            # Resources
            cpu_count=psutil.cpu_count(),
            memory_gb=round(memory_bytes / (1024**3), 2),
            disk_available_gb=round(disk_stats.free / (1024**3), 2),
            
            # Network
            hostname=socket.gethostname(),
            has_internet=cls._check_internet(),
            
            # Filesystem
            path_separator=path_sep,
            line_ending=line_ending,
            temp_dir=Path(os.environ.get('TEMP', '/tmp')),
            home_dir=Path.home(),
            
            # Tools
            has_git=cls._check_command("git"),
            has_docker=cls._check_command("docker"),
            has_make=cls._check_command("make"),
            has_wsl=cls._check_command("wsl") if platform_type == PlatformType.WINDOWS else False
        )


class PathHelper:
    """Cross-platform path handling utilities"""
    
    @staticmethod
    def normalize_path(path: str) -> Path:
        """Normalize path for current platform"""
        path_obj = Path(path)
        
        # Handle Windows paths on Unix and vice versa
        if "\\" in path and platform.system() != "Windows":
            path = path.replace("\\", "/")
        elif "/" in path and platform.system() == "Windows":
            path = path.replace("/", "\\")
        
        return Path(path).resolve()
    
    @staticmethod
    def get_project_root() -> Path:
        """Get project root directory reliably"""
        # Try multiple methods
        current_file = Path(__file__).resolve()
        
        # Method 1: Look for .git directory
        current = current_file.parent
        while current != current.parent:
            if (current / ".git").exists():
                return current
            current = current.parent
        
        # Method 2: Look for key project files
        current = current_file.parent
        while current != current.parent:
            if (current / "app.py").exists() or (current / "main.py").exists():
                return current
            current = current.parent
        
        # Method 3: Go up from utils directory
        # Assuming this file is in app/utils/
        return current_file.parent.parent.parent
    
    @staticmethod
    def get_test_data_dir() -> Path:
        """Get test data directory"""
        root = PathHelper.get_project_root()
        test_data = root / "tests" / "data"
        test_data.mkdir(parents=True, exist_ok=True)
        return test_data
    
    @staticmethod
    def get_temp_dir() -> Path:
        """Get platform-appropriate temp directory"""
        context = PlatformDetector.get_context()
        
        # For CI/CD, use a specific directory
        if context.is_ci:
            temp_dir = Path("/tmp/second-brain-ci")
        else:
            temp_dir = context.temp_dir / "second-brain"
        
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir


class EnvironmentManager:
    """Manage environment-specific configurations"""
    
    @staticmethod
    def setup_test_environment():
        """Setup test environment with platform awareness"""
        context = PlatformDetector.get_context()
        
        # Set test environment variables
        os.environ["ENVIRONMENT"] = "test"
        
        # Use mock database for CI/CD and when PostgreSQL not available
        if context.is_ci or not context.database_available:
            os.environ["USE_MOCK_DATABASE"] = "true"
        
        # Platform-specific settings
        if context.platform_type == PlatformType.WINDOWS:
            # Windows-specific test settings
            os.environ["PYTEST_TIMEOUT"] = "60"  # Longer timeout for Windows
        elif context.platform_type == PlatformType.MACOS:
            # macOS-specific settings
            os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"  # For multiprocessing
        
        # CI/CD specific settings
        if context.environment_type == EnvironmentType.GITHUB_ACTIONS:
            os.environ["LOG_LEVEL"] = "WARNING"  # Less verbose in CI
            os.environ["PYTEST_PARALLEL"] = "auto"  # Use all available cores
    
    @staticmethod
    def get_database_url() -> str:
        """Get database URL based on context"""
        context = PlatformDetector.get_context()
        
        if context.use_mock_database:
            return "mock://memory"
        
        if context.database_type == DatabaseType.POSTGRESQL:
            host = os.getenv("POSTGRES_HOST", "localhost")
            port = os.getenv("POSTGRES_PORT", "5432")
            user = os.getenv("POSTGRES_USER", "secondbrain")
            password = os.getenv("POSTGRES_PASSWORD", "changeme")
            database = os.getenv("POSTGRES_DB", "secondbrain")
            
            return f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        if context.database_type == DatabaseType.SQLITE:
            db_path = PathHelper.get_temp_dir() / "test.db"
            return f"sqlite:///{db_path}"
        
        return "memory://"
    
    @staticmethod
    def print_context():
        """Print current platform context for debugging"""
        context = PlatformDetector.get_context()
        
        print("=" * 60)
        print("PLATFORM CONTEXT")
        print("=" * 60)
        print(f"Platform: {context.platform_type.value} ({context.platform_version})")
        print(f"Architecture: {context.architecture}")
        print(f"Environment: {context.environment_type.value}")
        print(f"Python: {context.python_version} ({context.python_implementation})")
        print(f"Virtual Env: {context.is_venv} ({context.venv_path})")
        print(f"Database: {context.database_type.value} (available: {context.database_available})")
        print(f"Resources: {context.cpu_count} CPUs, {context.memory_gb}GB RAM")
        print(f"Network: {context.hostname} (internet: {context.has_internet})")
        print(f"Tools: git={context.has_git}, docker={context.has_docker}, make={context.has_make}")
        print("=" * 60)


# Global context instance (cached)
_context: Optional[PlatformContext] = None


def get_platform_context() -> PlatformContext:
    """Get cached platform context"""
    global _context
    if _context is None:
        _context = PlatformDetector.get_context()
    return _context


def invalidate_context():
    """Invalidate cached context (for testing)"""
    global _context
    _context = None


# Convenience functions
def is_windows() -> bool:
    """Check if running on Windows"""
    return get_platform_context().platform_type == PlatformType.WINDOWS


def is_macos() -> bool:
    """Check if running on macOS"""
    return get_platform_context().platform_type == PlatformType.MACOS


def is_linux() -> bool:
    """Check if running on Linux"""
    return get_platform_context().platform_type in [PlatformType.LINUX, PlatformType.WSL]


def is_ci() -> bool:
    """Check if running in CI/CD"""
    return get_platform_context().is_ci


def is_mock_database() -> bool:
    """Check if using mock database"""
    return get_platform_context().use_mock_database


def get_line_ending() -> str:
    """Get platform-appropriate line ending"""
    return get_platform_context().line_ending


def get_path_separator() -> str:
    """Get platform-appropriate path separator"""
    return get_platform_context().path_separator