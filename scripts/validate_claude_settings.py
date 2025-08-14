#!/usr/bin/env python
"""Validate Claude Code settings configuration."""

import json
import os
import sys
from pathlib import Path

# Handle Unicode output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def validate_settings():
    """Validate Claude settings files."""
    issues = []
    warnings = []
    
    # Check settings.json
    settings_path = Path(".claude/settings.json")
    if settings_path.exists():
        with open(settings_path) as f:
            settings = json.load(f)
        
        # Check permissions
        if "permissions" in settings:
            allow = settings["permissions"].get("allow", [])
            deny = settings["permissions"].get("deny", [])
            
            # Check for overly broad permissions
            if "Bash(*)" in allow:
                warnings.append("⚠ 'Bash(*)' allows all bash commands - consider being more specific")
            
            # Check for dangerous denies
            good_denies = ["Bash(rm -rf /)", "Bash(rm -rf ~)"]
            for deny_cmd in good_denies:
                if deny_cmd not in deny:
                    warnings.append(f"⚠ Consider adding '{deny_cmd}' to deny list for safety")
        
        # Check hooks
        if "hooks" in settings:
            hooks = settings.get("hooks", {})
            if "PostToolUse" in hooks:
                for hook in hooks["PostToolUse"]:
                    if "matcher" not in hook:
                        issues.append("✗ Hook missing 'matcher' field")
                    if "hooks" not in hook:
                        issues.append("✗ Hook missing 'hooks' field")
        
        print("✓ settings.json loaded successfully")
    else:
        issues.append("✗ settings.json not found")
    
    # Check settings.local.json
    local_path = Path(".claude/settings.local.json")
    if local_path.exists():
        with open(local_path) as f:
            local_settings = json.load(f)
        
        # Check for cleanupPeriod vs cleanupPeriodDays
        if "cleanupPeriod" in local_settings:
            warnings.append("⚠ 'cleanupPeriod' in settings.local.json should be 'cleanupPeriodDays'")
        
        print("✓ settings.local.json loaded successfully")
    
    # Check for CLAUDE.md
    claude_md = Path("CLAUDE.md")
    if claude_md.exists():
        print("✓ CLAUDE.md found - project instructions available")
    else:
        warnings.append("⚠ No CLAUDE.md file - consider adding project instructions")
    
    # Summary
    print("\n=== Validation Summary ===")
    if not issues and not warnings:
        print("✅ All settings are valid!")
    else:
        if issues:
            print("\n❌ Issues found:")
            for issue in issues:
                print(f"  {issue}")
        if warnings:
            print("\n⚠ Warnings:")
            for warning in warnings:
                print(f"  {warning}")
    
    return len(issues) == 0

if __name__ == "__main__":
    is_valid = validate_settings()
    exit(0 if is_valid else 1)