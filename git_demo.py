#!/usr/bin/env python3
"""
Git Visualization Demo - Shows git branch information directly
"""

import subprocess
import json
import os
from datetime import datetime

def run_git_command(command):
    """Run a git command and return output."""
    try:
        result = subprocess.run(
            ['git'] + command,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            timeout=10,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"Git command failed: {' '.join(command)} - {result.stderr}")
            return None
    except Exception as e:
        print(f"Error running git command {command}: {e}")
        return None

def get_simple_branch_info():
    """Get simplified branch information."""
    # Get current branch
    current_branch = run_git_command(['branch', '--show-current'])
    
    # Get all branches
    branch_output = run_git_command(['branch', '-a'])
    branches = []
    
    if branch_output:
        for line in branch_output.split('\n'):
            line = line.strip()
            if line:
                is_current = line.startswith('*')
                branch_name = line.replace('*', '').strip()
                if branch_name.startswith('remotes/'):
                    branch_name = branch_name[8:]  # Remove 'remotes/'
                
                # Get simple commit info
                commit_info = run_git_command(['log', '-1', '--oneline', branch_name])
                
                branches.append({
                    'name': branch_name,
                    'is_current': is_current,
                    'is_remote': 'origin/' in branch_name,
                    'commit_info': commit_info or 'No commit info',
                    'status': 'main' if branch_name in ['main', 'master'] else 'active',
                    'features': get_branch_features(branch_name)
                })
    
    # Check if repo is dirty
    status_output = run_git_command(['status', '--porcelain'])
    is_dirty = bool(status_output and status_output.strip())
    
    return {
        'current_branch': current_branch,
        'total_branches': len(branches),
        'dirty': is_dirty,
        'branches': branches
    }

def get_branch_features(branch_name):
    """Extract features from branch name."""
    features = []
    name_lower = branch_name.lower()
    
    if 'feature' in name_lower:
        features.append('feature')
    if 'testing' in name_lower or 'test' in name_lower:
        features.append('testing')
    if 'develop' in name_lower:
        features.append('development')
    if 'alpha' in name_lower:
        features.append('alpha')
    
    return features

def create_visualization_data(repo_info):
    """Create D3.js visualization data."""
    nodes = []
    links = []
    
    main_branches = [b for b in repo_info['branches'] if b['status'] == 'main']
    
    for i, branch in enumerate(repo_info['branches']):
        # Create node
        node = {
            'id': branch['name'],
            'name': branch['name'].split('/')[-1],
            'full_name': branch['name'],
            'group': get_branch_group(branch),
            'status': branch['status'],
            'is_current': branch['is_current'],
            'features': branch['features'],
            'commit_info': branch['commit_info']
        }
        nodes.append(node)
        
        # Create links to main branch
        if branch['status'] != 'main' and main_branches:
            main_branch = main_branches[0]
            link = {
                'source': main_branch['name'],
                'target': branch['name'],
                'distance': 50,
                'type': 'branch'
            }
            links.append(link)
    
    return {
        'nodes': nodes,
        'links': links,
        'repository': repo_info
    }

def get_branch_group(branch):
    """Get group number for branch visualization."""
    if branch['status'] == 'main':
        return 1
    elif branch['features'] and 'feature' in branch['features']:
        return 2
    elif branch['features'] and 'testing' in branch['features']:
        return 4
    elif branch['features'] and 'development' in branch['features']:
        return 3
    else:
        return 6

def main():
    print("🌿 Git Repository Visualization Demo")
    print("=" * 50)
    
    # Get repository info
    repo_info = get_simple_branch_info()
    
    print(f"\n📊 Repository Overview:")
    print(f"Current Branch: {repo_info['current_branch']}")
    print(f"Total Branches: {repo_info['total_branches']}")
    print(f"Has Uncommitted Changes: {repo_info['dirty']}")
    
    print(f"\n🌲 Branch Details:")
    for branch in repo_info['branches']:
        status_indicator = "👑" if branch['is_current'] else "🌿" if branch['status'] == 'main' else "🔧"
        features_str = ', '.join(branch['features']) if branch['features'] else 'none'
        print(f"{status_indicator} {branch['name']}: {branch['status']} (features: {features_str})")
        print(f"   Last commit: {branch['commit_info']}")
    
    # Create visualization data
    viz_data = create_visualization_data(repo_info)
    
    print(f"\n🎨 Visualization Data:")
    print(f"Nodes: {len(viz_data['nodes'])}")
    print(f"Links: {len(viz_data['links'])}")
    
    # Save data as JSON for the dashboard
    with open('dashboard_data/git_data.json', 'w') as f:
        json.dump(viz_data, f, indent=2, default=str)
    
    print(f"\n✅ Git visualization data saved to dashboard_data/git_data.json")
    print(f"This data can be used by the dashboard's git visualization!")

if __name__ == "__main__":
    main()
