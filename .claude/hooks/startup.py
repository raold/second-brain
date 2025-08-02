#!/usr/bin/env python3
"""
Claude Code Startup Hook - Second Brain v4.0.0
Automatically loads context and provides session status when Claude Code starts.
"""

import os
import subprocess
from pathlib import Path
from datetime import datetime

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
    print(f"{BOLD}{BLUE}🧠 Second Brain v4.0.0 - Session Started{RESET}")
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
    print(f"{BOLD}🔒 Security Check:{RESET}")
    try:
        result = subprocess.run(['python', 'scripts/check_secrets.py'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"{GREEN}  ✓ No security issues detected{RESET}")
        else:
            print(f"{RED}  ✗ Security issues found - run: python scripts/check_secrets.py{RESET}")
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
    print(f"{BOLD}⚡ Quick Commands:{RESET}")
    commands = [
        ("Start development", "make dev"),
        ("Run tests", "make test"),
        ("Security check", "python scripts/check_secrets.py"),
        ("Check config", "python -c 'from app.config import Config; print(Config.get_summary())'")
    ]
    
    for desc, cmd in commands:
        print(f"  {desc:<20} → {BLUE}{cmd}{RESET}")
    print()

def main():
    """Main startup hook."""
    print_header()
    
    # Change to project directory
    project_dir = Path(__file__).parent.parent.parent
    os.chdir(project_dir)
    
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