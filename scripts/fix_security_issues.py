#!/usr/bin/env python3
"""
Fix security vulnerabilities in the codebase.
"""

import re
from pathlib import Path

# Fix bare except clauses
BARE_EXCEPT_FILES = {
    "app/routes/dashboard_routes.py": [
        (168, "except Exception as e:"),
        (428, "except Exception:"),
        (455, "except Exception:"),
    ],
    "app/routes/v2_unified_api.py": [
        (205, "except Exception as e:"),
        (445, "except Exception as e:"),
        (458, "except Exception as e:"),
    ],
}

# Fix hardcoded secrets and weak hashing
SECURITY_FIXES = {
    "app/config.py": [
        ('HOST: str = os.getenv("HOST", "0.0.0.0")',
         'HOST: str = os.getenv("HOST", "127.0.0.1")  # Changed from 0.0.0.0 for security'),
    ],
    "app/ingestion/embedding_generator.py": [
        ('text_hash = hashlib.md5(text.encode()).hexdigest()',
         'text_hash = hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()'),
        ('text_hash = hashlib.md5(text.encode()).hexdigest()[:8]',
         'text_hash = hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()[:8]'),
    ],
    "app/ingestion/engine.py": [
        ('hash_md5 = hashlib.md5()',
         'hash_md5 = hashlib.md5(usedforsecurity=False)'),
    ],
}

def fix_bare_excepts(file_path: Path, line_fixes: list) -> bool:
    """Fix bare except clauses in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        changed = False
        for line_num, replacement in line_fixes:
            # Adjust for 0-based indexing
            idx = line_num - 1
            if idx < len(lines):
                # Check if it's actually a bare except
                if 'except:' in lines[idx]:
                    # Preserve indentation
                    indent = len(lines[idx]) - len(lines[idx].lstrip())
                    lines[idx] = ' ' * indent + replacement + '\n'
                    changed = True
        
        if changed:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error fixing bare excepts in {file_path}: {e}")
        return False

def fix_security_issues(file_path: Path, fixes: list) -> bool:
    """Apply security fixes to a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        for old_pattern, new_pattern in fixes:
            content = content.replace(old_pattern, new_pattern)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error fixing security issues in {file_path}: {e}")
        return False

def fix_environment_syntax():
    """Fix syntax errors in environment.py file."""
    env_file = Path(__file__).parent.parent / "app" / "utils" / "environment.py"
    
    try:
        # Rewrite the environment.py file with proper syntax
        content = '''"""
Environment utilities for configuration and setup.
"""

import os
from pathlib import Path
from typing import Optional

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def get_env_var(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """
    Get environment variable with optional default and validation.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        required: Whether the variable is required
        
    Returns:
        Environment variable value or default
        
    Raises:
        ValueError: If required variable is not found
    """
    value = os.getenv(key, default)
    
    if required and value is None:
        raise ValueError(f"Required environment variable {key} not found")
    
    return value


def get_env_bool(key: str, default: bool = False) -> bool:
    """
    Get boolean environment variable.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        
    Returns:
        Boolean value
    """
    value = os.getenv(key, "").lower()
    
    if not value:
        return default
    
    return value in ("true", "1", "yes", "on")


def get_env_int(key: str, default: int = 0) -> int:
    """
    Get integer environment variable.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        
    Returns:
        Integer value
    """
    value = os.getenv(key)
    
    if not value:
        return default
    
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Invalid integer value for {key}: {value}, using default: {default}")
        return default


def get_project_root() -> Path:
    """Get the project root directory."""
    current = Path(__file__).resolve()
    
    # Walk up until we find a directory with key project files
    while current != current.parent:
        if (current / "pyproject.toml").exists() or (current / "setup.py").exists():
            return current
        current = current.parent
    
    # Fallback to 2 levels up from this file
    return Path(__file__).resolve().parent.parent.parent


def load_env_file(env_file: Optional[Path] = None) -> None:
    """
    Load environment variables from a .env file.
    
    Args:
        env_file: Path to .env file (defaults to project root/.env)
    """
    if env_file is None:
        env_file = get_project_root() / ".env"
    
    if not env_file.exists():
        logger.debug(f"Environment file not found: {env_file}")
        return
    
    try:
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    
                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value
                        logger.debug(f"Loaded {key} from {env_file}")
    
    except Exception as e:
        logger.error(f"Error loading environment file {env_file}: {e}")
'''
        
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("Fixed syntax errors in app/utils/environment.py")
        return True
        
    except Exception as e:
        print(f"Error fixing environment.py: {e}")
        return False

def main():
    """Main function to fix security issues."""
    project_root = Path(__file__).parent.parent
    fixed_count = 0
    
    print("🔒 Fixing security vulnerabilities...")
    
    # Fix bare except clauses
    print("\n📌 Fixing bare except clauses...")
    for file_path, line_fixes in BARE_EXCEPT_FILES.items():
        full_path = project_root / file_path
        if full_path.exists():
            if fix_bare_excepts(full_path, line_fixes):
                print(f"Fixed bare excepts in {file_path}")
                fixed_count += 1
    
    # Fix security issues
    print("\n🔐 Fixing security issues...")
    for file_path, fixes in SECURITY_FIXES.items():
        full_path = project_root / file_path
        if full_path.exists():
            if fix_security_issues(full_path, fixes):
                print(f"Fixed security issues in {file_path}")
                fixed_count += 1
    
    # Fix environment.py syntax
    if fix_environment_syntax():
        fixed_count += 1
    
    print(f"\n✅ Fixed {fixed_count} files")

if __name__ == "__main__":
    main()