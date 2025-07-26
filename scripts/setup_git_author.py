#!/usr/bin/env python3
"""
Set up git configuration for proper commit attribution
"""
import subprocess
import sys

def run_git_command(args):
    """Run a git command and return output"""
    try:
        result = subprocess.run(['git'] + args, capture_output=True, text=True)
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)

def main():
    print("Setting up Git configuration for future commits...")
    print("="*60)
    
    # Get current configuration
    success, current_name = run_git_command(['config', 'user.name'])
    if success and current_name:
        print(f"Current name: {current_name}")
    
    success, current_email = run_git_command(['config', 'user.email'])
    if success and current_email:
        print(f"Current email: {current_email}")
    
    print("\nTo ensure future commits show your name (not Claude):")
    print("Run these commands in your terminal:\n")
    
    print("git config user.name \"Your Name\"")
    print("git config user.email \"your.email@example.com\"")
    
    print("\nFor this repository only (recommended):")
    print("git config --local user.name \"Your Name\"") 
    print("git config --local user.email \"your.email@example.com\"")
    
    print("\nNote: Past commits will still show Claude as co-author,")
    print("but all future commits will be attributed only to you.")
    
    print("\nThe 30 existing commits from Claude are preserved in the git history.")

if __name__ == "__main__":
    main()