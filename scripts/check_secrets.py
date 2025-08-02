#!/usr/bin/env python3
"""
Security check script to validate environment configuration and detect exposed secrets.
Run this before commits and in CI/CD pipelines.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict
import json

# Color codes for terminal output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

# Patterns for detecting secrets
SECRET_PATTERNS = {
    'openai_api_key': (r'sk-proj-[A-Za-z0-9\-_]{100,}', 'OpenAI API Key'),
    'anthropic_api_key': (r'sk-ant-[A-Za-z0-9\-_]{50,}', 'Anthropic API Key'),
    'aws_access_key': (r'AKIA[0-9A-Z]{16}', 'AWS Access Key'),
    'aws_secret_key': (r'[A-Za-z0-9/+=]{40}', 'AWS Secret Key (potential)'),
    'github_token': (r'ghp_[A-Za-z0-9]{36}', 'GitHub Personal Access Token'),
    'github_oauth': (r'gho_[A-Za-z0-9]{36}', 'GitHub OAuth Token'),
    'slack_token': (r'xox[baprs]-[0-9]{10,12}-[0-9]{10,12}-[a-zA-Z0-9]{24}', 'Slack Token'),
    'stripe_key': (r'sk_live_[A-Za-z0-9]{24,}', 'Stripe Live Key'),
    'private_key': (r'-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----', 'Private Key'),
}

# Files to exclude from scanning
EXCLUDE_PATTERNS = [
    '*.pyc',
    '__pycache__',
    '.git',
    '.venv',
    'venv',
    'node_modules',
    '*.log',
    '.pytest_cache',
]

# Safe example patterns (won't trigger alerts)
SAFE_EXAMPLES = [
    'your_openai_api_key_here',
    'your_anthropic_api_key_here',
    'sk-...your_actual_key_here...',
    'test-key-mock',
    'changeme',
    'your_.*_here',
]


def is_safe_example(value: str) -> bool:
    """Check if a value is a safe example/placeholder."""
    value_lower = value.lower()
    for safe_pattern in SAFE_EXAMPLES:
        if re.search(safe_pattern, value_lower):
            return True
    return False


def check_file_for_secrets(filepath: Path) -> List[Tuple[int, str, str]]:
    """Check a single file for exposed secrets."""
    findings = []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                # Skip comments and empty lines
                if line.strip().startswith('#') or not line.strip():
                    continue
                    
                for secret_type, (pattern, description) in SECRET_PATTERNS.items():
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        secret_value = match.group()
                        if not is_safe_example(secret_value):
                            findings.append((line_num, description, secret_value[:20] + '...'))
                            
    except Exception as e:
        print(f"{YELLOW}Warning: Could not read {filepath}: {e}{RESET}")
        
    return findings


def check_git_tracked_env_files() -> List[str]:
    """Check if any .env files are tracked in git."""
    import subprocess
    
    tracked_env_files = []
    try:
        result = subprocess.run(
            ['git', 'ls-files'],
            capture_output=True,
            text=True,
            check=True
        )
        
        for file in result.stdout.split('\n'):
            if '.env' in file and file != '.env.example' and file != '.env.local.template':
                tracked_env_files.append(file)
                
    except subprocess.CalledProcessError:
        print(f"{YELLOW}Warning: Not a git repository or git not available{RESET}")
        
    return tracked_env_files


def check_gitignore() -> bool:
    """Verify .gitignore properly excludes sensitive files."""
    gitignore_path = Path('.gitignore')
    if not gitignore_path.exists():
        return False
        
    required_patterns = [
        '.env',
        '.env.local',
        '.env.production',
        '*.pem',
        '*.key',
        '*.cert',
    ]
    
    with open(gitignore_path, 'r') as f:
        gitignore_content = f.read()
        
    missing = []
    for pattern in required_patterns:
        if pattern not in gitignore_content:
            missing.append(pattern)
            
    if missing:
        print(f"{YELLOW}Missing from .gitignore: {', '.join(missing)}{RESET}")
        return False
        
    return True


def validate_env_file(env_file: Path) -> Dict[str, List[str]]:
    """Validate an environment file for security issues."""
    issues = {
        'weak_passwords': [],
        'exposed_secrets': [],
        'missing_required': [],
    }
    
    if not env_file.exists():
        return issues
        
    # Check for weak passwords
    weak_password_patterns = ['password', 'changeme', 'admin', 'test', '123456']
    
    # Required environment variables
    required_vars = ['JWT_SECRET_KEY', 'DATABASE_URL']
    found_vars = set()
    
    with open(env_file, 'r') as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.strip().split('=', 1)
                found_vars.add(key)
                
                # Check for weak passwords
                for weak_pattern in weak_password_patterns:
                    if weak_pattern in value.lower() and 'example' not in str(env_file):
                        issues['weak_passwords'].append(f"{key}={value[:20]}...")
                        
    # Check for missing required variables
    for req_var in required_vars:
        if req_var not in found_vars and '.template' not in str(env_file):
            issues['missing_required'].append(req_var)
            
    return issues


def main():
    """Main security check function."""
    print(f"{BOLD}{BLUE}🔒 Second Brain Security Check{RESET}\n")
    
    project_root = Path.cwd()
    has_issues = False
    
    # 1. Check for tracked .env files in git
    print(f"{BOLD}1. Checking Git Tracked Files...{RESET}")
    tracked_env = check_git_tracked_env_files()
    if tracked_env:
        has_issues = True
        print(f"{RED}❌ CRITICAL: Environment files tracked in git:{RESET}")
        for file in tracked_env:
            print(f"   - {file}")
        print(f"{YELLOW}   Run: git rm --cached {' '.join(tracked_env)}{RESET}")
    else:
        print(f"{GREEN}✅ No .env files tracked in git{RESET}")
    
    # 2. Check .gitignore
    print(f"\n{BOLD}2. Checking .gitignore...{RESET}")
    if check_gitignore():
        print(f"{GREEN}✅ .gitignore properly configured{RESET}")
    else:
        has_issues = True
        print(f"{RED}❌ .gitignore needs updates{RESET}")
    
    # 3. Scan for exposed secrets in code
    print(f"\n{BOLD}3. Scanning for Exposed Secrets...{RESET}")
    
    files_to_check = []
    for pattern in ['*.py', '*.js', '*.ts', '*.yml', '*.yaml', '*.json', '*.md']:
        files_to_check.extend(project_root.rglob(pattern))
    
    # Add all .env files
    files_to_check.extend(project_root.glob('.env*'))
    
    total_findings = 0
    files_with_secrets = {}
    
    for filepath in files_to_check:
        # Skip excluded paths
        skip = False
        for exclude in EXCLUDE_PATTERNS:
            if exclude in str(filepath):
                skip = True
                break
        if skip:
            continue
            
        findings = check_file_for_secrets(filepath)
        if findings:
            files_with_secrets[filepath] = findings
            total_findings += len(findings)
    
    if files_with_secrets:
        has_issues = True
        print(f"{RED}❌ Found {total_findings} potential secrets in {len(files_with_secrets)} files:{RESET}")
        for filepath, findings in files_with_secrets.items():
            print(f"\n   {filepath}:")
            for line_num, description, preview in findings:
                print(f"      Line {line_num}: {description} - {preview}")
    else:
        print(f"{GREEN}✅ No exposed secrets found{RESET}")
    
    # 4. Validate environment files
    print(f"\n{BOLD}4. Validating Environment Files...{RESET}")
    
    env_files_to_check = ['.env', '.env.local', '.env.development', '.env.production']
    
    for env_file_name in env_files_to_check:
        env_file = project_root / env_file_name
        if env_file.exists():
            issues = validate_env_file(env_file)
            
            if any(issues.values()):
                has_issues = True
                print(f"\n   {env_file_name}:")
                
                if issues['weak_passwords']:
                    print(f"      {YELLOW}⚠️  Weak passwords detected:{RESET}")
                    for pwd in issues['weak_passwords']:
                        print(f"         - {pwd}")
                        
                if issues['exposed_secrets']:
                    print(f"      {RED}❌ Exposed secrets:{RESET}")
                    for secret in issues['exposed_secrets']:
                        print(f"         - {secret}")
                        
                if issues['missing_required']:
                    print(f"      {YELLOW}⚠️  Missing required variables:{RESET}")
                    for var in issues['missing_required']:
                        print(f"         - {var}")
            else:
                print(f"   {env_file_name}: {GREEN}✅ OK{RESET}")
    
    # 5. Final summary
    print(f"\n{BOLD}{'='*60}{RESET}")
    if has_issues:
        print(f"{RED}❌ SECURITY ISSUES DETECTED!{RESET}")
        print(f"\n{BOLD}Recommended Actions:{RESET}")
        print("1. Remove any tracked .env files from git")
        print("2. Rotate any exposed API keys immediately")
        print("3. Use .env.local for local development (not tracked)")
        print("4. Update weak passwords before deployment")
        print("5. Run 'git filter-branch' to remove secrets from history")
        sys.exit(1)
    else:
        print(f"{GREEN}✅ All security checks passed!{RESET}")
        print("\nRemember:")
        print("- Never commit real API keys")
        print("- Use environment variables for secrets")
        print("- Rotate keys regularly")
        print("- Use .env.local for local development")
        sys.exit(0)


if __name__ == "__main__":
    main()