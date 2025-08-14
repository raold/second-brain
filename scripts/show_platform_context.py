#!/usr/bin/env python
"""
Display platform and environment context

This script shows the detected platform, environment, and configuration
to help debug platform-specific issues.
"""

import sys
import os
from pathlib import Path

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.platform_context import (
    PlatformDetector,
    EnvironmentManager,
    get_platform_context,
    PathHelper
)


def main():
    """Display platform context information"""
    print("\n" + "=" * 70)
    print("SECOND BRAIN - PLATFORM CONTEXT ANALYZER")
    print("=" * 70)
    
    # Get and display context
    context = get_platform_context()
    
    # Platform Information
    print("\n📱 PLATFORM INFORMATION")
    print("-" * 40)
    print(f"Operating System: {context.platform_type.value}")
    print(f"Version: {context.platform_version[:50]}...")
    print(f"Architecture: {context.architecture}")
    print(f"Processor: {context.processor[:50]}...")
    
    # Environment Information
    print("\n🌍 ENVIRONMENT INFORMATION")
    print("-" * 40)
    print(f"Environment Type: {context.environment_type.value}")
    print(f"Is CI/CD: {context.is_ci}")
    print(f"Is Docker: {context.is_docker}")
    print(f"Is WSL: {context.is_wsl}")
    
    # Python Information
    print("\n🐍 PYTHON INFORMATION")
    print("-" * 40)
    print(f"Python Version: {context.python_version}")
    print(f"Implementation: {context.python_implementation}")
    print(f"Virtual Environment: {context.is_venv}")
    if context.venv_path:
        print(f"Venv Path: {context.venv_path}")
    
    # Database Information
    print("\n🗄️ DATABASE INFORMATION")
    print("-" * 40)
    print(f"Database Type: {context.database_type.value}")
    print(f"Database Available: {context.database_available}")
    print(f"Use Mock Database: {context.use_mock_database}")
    print(f"Database URL: {EnvironmentManager.get_database_url()}")
    
    # System Resources
    print("\n💻 SYSTEM RESOURCES")
    print("-" * 40)
    print(f"CPU Cores: {context.cpu_count}")
    print(f"Memory: {context.memory_gb} GB")
    print(f"Disk Available: {context.disk_available_gb} GB")
    
    # Network Information
    print("\n🌐 NETWORK INFORMATION")
    print("-" * 40)
    print(f"Hostname: {context.hostname}")
    print(f"Internet Available: {context.has_internet}")
    
    # Development Tools
    print("\n🛠️ DEVELOPMENT TOOLS")
    print("-" * 40)
    print(f"Git Available: {context.has_git}")
    print(f"Docker Available: {context.has_docker}")
    print(f"Make Available: {context.has_make}")
    if context.platform_type.value == "windows":
        print(f"WSL Available: {context.has_wsl}")
    
    # File System Information
    print("\n📁 FILE SYSTEM INFORMATION")
    print("-" * 40)
    print(f"Path Separator: '{context.path_separator}'")
    print(f"Line Ending: {repr(context.line_ending)}")
    print(f"Temp Directory: {context.temp_dir}")
    print(f"Home Directory: {context.home_dir}")
    print(f"Project Root: {PathHelper.get_project_root()}")
    
    # Test Configuration
    print("\n🧪 TEST CONFIGURATION")
    print("-" * 40)
    print(f"ENVIRONMENT: {os.getenv('ENVIRONMENT', 'not set')}")
    print(f"USE_MOCK_DATABASE: {os.getenv('USE_MOCK_DATABASE', 'not set')}")
    print(f"OPENAI_API_KEY: {'set' if os.getenv('OPENAI_API_KEY') else 'not set'}")
    print(f"CI: {os.getenv('CI', 'not set')}")
    print(f"GITHUB_ACTIONS: {os.getenv('GITHUB_ACTIONS', 'not set')}")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS")
    print("-" * 40)
    
    if context.is_ci:
        print("✓ Running in CI/CD environment")
        print("  - Using mock database for tests")
        print("  - Reduced connection pools")
        print("  - Shorter timeouts")
    elif not context.database_available:
        print("⚠ No database detected")
        print("  - Will use mock database for tests")
        print("  - Consider starting PostgreSQL if needed")
    else:
        print("✓ Development environment ready")
        print(f"  - {context.database_type.value} database available")
        print(f"  - Running on {context.platform_type.value}")
    
    if context.platform_type.value == "windows" and not context.is_wsl:
        print("\n💡 Windows Development Tips:")
        print("  - Consider using WSL2 for Linux compatibility")
        print("  - Tests may run slower than on Unix systems")
        print("  - Path separators will be automatically handled")
    
    if not context.has_docker:
        print("\n⚠ Docker not available")
        print("  - Some integration tests may be skipped")
        print("  - Consider installing Docker for full test coverage")
    
    # Export as JSON option
    if "--json" in sys.argv:
        import json
        json_path = Path("platform_context.json")
        with open(json_path, "w") as f:
            json.dump(context.to_dict(), f, indent=2)
        print(f"\n✅ Context exported to {json_path}")
    
    print("\n" + "=" * 70)
    print("Analysis complete. Use --json to export as JSON.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()