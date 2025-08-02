#!/usr/bin/env python3
"""
Claude Code Startup Hook - Second Brain v4.0.0
Automatically loads context and provides session status when Claude Code starts.
Now with cross-platform support for Google Drive sync!
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import cross-platform utilities
try:
    from app.utils.cross_platform import get_platform_helper, setup_utf8_encoding
    setup_utf8_encoding()  # Fix encoding issues on Windows
    platform_helper = get_platform_helper()
except ImportError:
    platform_helper = None

# Colors for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RED = '\033[91m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_header():
    """Print session startup header."""
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}Second Brain v4.0.0 - Session Started{RESET}")
    if platform_helper:
        platform_name = "Windows" if platform_helper.is_windows else "macOS" if platform_helper.is_mac else "Linux"
        print(f"{BOLD}{BLUE}Platform: {platform_name} | Google Drive Sync Enabled{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")

def check_git_status():
    """Check and display git status."""
    print(f"{BOLD}📊 Git Status:{RESET}")
    try:
        result = subprocess.run(['git', 'status', '--short'], 
                              capture_output=True, text=True, check=True)
        if result.stdout:
            print(f"{YELLOW}  Uncommitted changes:{RESET}")
            for line in result.stdout.strip().split('\n'):
                print(f"    {line}")
        else:
            print(f"{GREEN}  ✓ Working directory clean{RESET}")
    except:
        print(f"{RED}  ✗ Not a git repository{RESET}")
    print()

def check_environment():
    """Check environment setup."""
    print(f"{BOLD}🔧 Environment Check:{RESET}")
    
    # Check for .env file
    env_exists = Path('.env').exists()
    if env_exists:
        print(f"{GREEN}  ✓ .env file exists{RESET}")
    else:
        print(f"{YELLOW}  ⚠ .env file missing - copy from .env.example{RESET}")
    
    # Check for critical env vars
    has_openai = bool(os.getenv('OPENAI_API_KEY'))
    if has_openai:
        print(f"{GREEN}  ✓ OpenAI API key configured{RESET}")
    else:
        print(f"{YELLOW}  ⚠ OpenAI API key not set{RESET}")
    
    print()

def run_security_check():
    """Run quick security check."""
    print(f"{BOLD}Security Check:{RESET}")
    try:
        # Use platform-specific Python
        python_cmd = platform_helper.get_venv_python() if platform_helper else 'python'
        result = subprocess.run([python_cmd, 'scripts/check_secrets.py'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"{GREEN}  ✓ No security issues detected{RESET}")
        else:
            print(f"{RED}  ✗ Security issues found - run: {python_cmd} scripts/check_secrets.py{RESET}")
    except:
        print(f"{YELLOW}  ⚠ Could not run security check{RESET}")
    print()

def show_test_status():
    """Show quick test status."""
    print(f"{BOLD}🧪 Test Status:{RESET}")
    print(f"  Last known: {GREEN}55 tests passing{RESET}")
    print(f"  Run tests: {BLUE}python -m pytest tests/unit/test_basic_functionality.py{RESET}")
    print()

def show_priority_todos():
    """Show priority TODO items."""
    print(f"{BOLD}📋 Priority TODOs:{RESET}")
    
    todos = [
        "🔴 CRITICAL: Rotate API keys if they were exposed",
        "1. Create .env from .env.example",
        "2. Add actual API keys to .env",
        "3. Set up production PostgreSQL (optional)",
        "4. Rename _new suffix files (technical debt)"
    ]
    
    for todo in todos:
        print(f"  {todo}")
    print()

def show_context_files():
    """Show important context files."""
    print(f"{BOLD}📚 Context Files (Auto-loaded):{RESET}")
    
    files = {
        "TODO.md": "Current tasks and priorities",
        "CLAUDE.md": "Project context and decisions",
        "DEVELOPMENT_CONTEXT.md": "Session history and details"
    }
    
    for file, desc in files.items():
        if Path(file).exists():
            print(f"  ✓ {file:<25} - {desc}")
        else:
            print(f"  ✗ {file:<25} - {RED}Missing{RESET}")
    print()

def show_quick_commands():
    """Show useful quick commands."""
    print(f"{BOLD}Quick Commands:{RESET}")
    
    # Platform-specific commands
    if platform_helper:
        python_cmd = platform_helper.get_venv_python()
        test_cmd = platform_helper.get_test_command()
        run_cmd = platform_helper.get_run_command()
        
        commands = [
            ("Start development", run_cmd),
            ("Run tests", test_cmd),
            ("Security check", f"{python_cmd} scripts/check_secrets.py"),
            ("Platform info", f"{python_cmd} -c \"from app.utils.cross_platform import get_platform_helper; get_platform_helper().print_platform_banner()\"")
        ]
    else:
        commands = [
            ("Start development", "make dev"),
            ("Run tests", "make test"),
            ("Security check", "python scripts/check_secrets.py"),
            ("Check config", "python -c 'from app.config import Config; print(Config.get_summary())'")
        ]
    
    for desc, cmd in commands:
        # Truncate long commands
        if len(cmd) > 50:
            cmd_display = cmd[:47] + "..."
        else:
            cmd_display = cmd
        print(f"  {desc:<20} → {BLUE}{cmd_display}{RESET}")
    print()

def show_platform_info():
    """Show platform-specific information."""
    if platform_helper:
        print(f"{BOLD}Platform Information:{RESET}")
        info = platform_helper.get_platform_info()
        
        # Show Google Drive sync status
        project_path = str(info['project_root'])
        if "GoogleDrive" in project_path or "Google Drive" in project_path or "My Drive" in project_path:
            print(f"{GREEN}  ✓ Google Drive sync detected{RESET}")
            print(f"  Path: {project_path[:60]}...")
        else:
            print(f"  Local development (not on Google Drive)")
        
        print(f"  System: {info['system']}")
        print(f"  Python: {platform_helper.get_venv_python()}")
        print(f"  Encoding: {info['encoding']} (File: {info['file_encoding']})")
        print()

def main():
    """Main startup hook."""
    print_header()
    
    # Change to project directory
    if platform_helper:
        project_dir = platform_helper.project_root
    else:
        project_dir = Path(__file__).parent.parent.parent
    os.chdir(project_dir)
    
    # Show platform info if available
    if platform_helper:
        show_platform_info()
    
    # Run checks
    check_git_status()
    check_environment()
    run_security_check()
    show_test_status()
    show_priority_todos()
    show_context_files()
    show_quick_commands()
    
    # Final message
    print(f"{BOLD}{GREEN}Ready to continue development!{RESET}")
    print(f"Session started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

if __name__ == "__main__":
    main()