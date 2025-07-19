#!/usr/bin/env python3
"""
Git Visualization Demo - Shows git branch information with commit activity metrics
"""

import subprocess
import json
import os
from datetime import datetime, timedelta

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

def get_commit_metrics(branch_name, days):
    """Get commit metrics for a branch within specified days."""
    try:
        since_date = datetime.now() - timedelta(days=days)
        since_str = since_date.strftime('%Y-%m-%d')
        
        # Get commit count
        commit_count_cmd = ['rev-list', '--count', f'--since={since_str}', branch_name]
        commit_count_output = run_git_command(commit_count_cmd)
        commit_count = int(commit_count_output) if commit_count_output and commit_count_output.isdigit() else 0
        
        if commit_count == 0:
            return {
                'commit_count': 0,
                'lines_added': 0,
                'lines_deleted': 0,
                'files_changed': 0,
                'authors': []
            }
        
        # Get stats (lines added/deleted, files changed)
        stat_cmd = ['log', f'--since={since_str}', '--pretty=format:', '--numstat', branch_name]
        stat_output = run_git_command(stat_cmd)
        
        lines_added = 0
        lines_deleted = 0
        files_changed = set()
        
        if stat_output:
            for line in stat_output.split('\n'):
                line = line.strip()
                if line and '\t' in line:
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        try:
                            added = int(parts[0]) if parts[0] != '-' else 0
                            deleted = int(parts[1]) if parts[1] != '-' else 0
                            filename = parts[2]
                            
                            lines_added += added
                            lines_deleted += deleted
                            files_changed.add(filename)
                        except ValueError:
                            continue
        
        # Get unique authors
        authors_cmd = ['log', f'--since={since_str}', '--pretty=format:%an', branch_name]
        authors_output = run_git_command(authors_cmd)
        authors = list(set(authors_output.split('\n'))) if authors_output else []
        authors = [a.strip() for a in authors if a.strip()]
        
        return {
            'commit_count': commit_count,
            'lines_added': lines_added,
            'lines_deleted': lines_deleted,
            'files_changed': len(files_changed),
            'authors': authors
        }
        
    except Exception as e:
        print(f"Error getting commit metrics for {branch_name} ({days}d): {e}")
        return {
            'commit_count': 0,
            'lines_added': 0,
            'lines_deleted': 0,
            'files_changed': 0,
            'authors': []
        }

def get_simple_branch_info():
    """Get simplified branch information with commit metrics."""
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
                
                # Skip duplicate entries and invalid branch names
                if '->' in branch_name:
                    continue
                
                # Get simple commit info
                commit_info = run_git_command(['log', '-1', '--oneline', branch_name])
                
                # Get commit metrics for different periods
                metrics_24h = get_commit_metrics(branch_name, 1)
                metrics_7d = get_commit_metrics(branch_name, 7)
                metrics_30d = get_commit_metrics(branch_name, 30)
                
                branches.append({
                    'name': branch_name,
                    'is_current': is_current,
                    'is_remote': 'origin/' in branch_name,
                    'commit_info': commit_info or 'No commit info',
                    'status': 'main' if branch_name in ['main', 'master'] else 'active',
                    'features': get_branch_features(branch_name),
                    'metrics_24h': metrics_24h,
                    'metrics_7d': metrics_7d,
                    'metrics_30d': metrics_30d
                })
    
    # Check if repo is dirty
    status_output = run_git_command(['status', '--porcelain'])
    is_dirty = bool(status_output and status_output.strip())
    
    # Calculate aggregate metrics
    total_commits_24h = sum(b['metrics_24h']['commit_count'] for b in branches)
    total_commits_7d = sum(b['metrics_7d']['commit_count'] for b in branches)
    total_commits_30d = sum(b['metrics_30d']['commit_count'] for b in branches)
    total_lines_24h = sum(b['metrics_24h']['lines_added'] for b in branches)
    total_lines_7d = sum(b['metrics_7d']['lines_added'] for b in branches)
    total_lines_30d = sum(b['metrics_30d']['lines_added'] for b in branches)
    
    return {
        'current_branch': current_branch,
        'total_branches': len(branches),
        'dirty': is_dirty,
        'branches': branches,
        'total_commits_24h': total_commits_24h,
        'total_commits_7d': total_commits_7d,
        'total_commits_30d': total_commits_30d,
        'total_lines_added_24h': total_lines_24h,
        'total_lines_added_7d': total_lines_7d,
        'total_lines_added_30d': total_lines_30d
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
            'commit_info': branch['commit_info'],
            'metrics_24h': branch['metrics_24h'],
            'metrics_7d': branch['metrics_7d'],
            'metrics_30d': branch['metrics_30d']
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
    print("🌿 Git Repository Visualization Demo with Commit Activity Metrics")
    print("=" * 70)
    
    # Get repository info
    repo_info = get_simple_branch_info()
    
    print(f"\n📊 Repository Overview:")
    print(f"Current Branch: {repo_info['current_branch']}")
    print(f"Total Branches: {repo_info['total_branches']}")
    print(f"Has Uncommitted Changes: {repo_info['dirty']}")
    
    print(f"\n📈 Commit Activity Summary:")
    print(f"Commits in last 24h: {repo_info['total_commits_24h']}")
    print(f"Commits in last 7d:  {repo_info['total_commits_7d']}")
    print(f"Commits in last 30d: {repo_info['total_commits_30d']}")
    print(f"Lines added in last 24h: {repo_info['total_lines_added_24h']}")
    print(f"Lines added in last 7d:  {repo_info['total_lines_added_7d']}")
    print(f"Lines added in last 30d: {repo_info['total_lines_added_30d']}")
    
    print(f"\n🌲 Branch Details with Commit Metrics:")
    
    # Sort branches by recent activity
    active_branches = [b for b in repo_info['branches'] if b['metrics_24h']['commit_count'] > 0 or b['metrics_7d']['commit_count'] > 0]
    active_branches.sort(key=lambda x: x['metrics_24h']['commit_count'] + x['metrics_7d']['commit_count'], reverse=True)
    
    # Show most active branches first
    for branch in active_branches[:10]:  # Top 10 active branches
        status_indicator = "👑" if branch['is_current'] else "🌿" if branch['status'] == 'main' else "🔧"
        features_str = ', '.join(branch['features']) if branch['features'] else 'none'
        
        print(f"\n{status_indicator} {branch['name']}: {branch['status']} (features: {features_str})")
        print(f"   Last commit: {branch['commit_info']}")
        print(f"   📈 Activity: 24h={branch['metrics_24h']['commit_count']}c/{branch['metrics_24h']['lines_added']}+, " +
              f"7d={branch['metrics_7d']['commit_count']}c/{branch['metrics_7d']['lines_added']}+, " +
              f"30d={branch['metrics_30d']['commit_count']}c/{branch['metrics_30d']['lines_added']}+")
        if branch['metrics_24h']['authors']:
            print(f"   👥 Recent authors: {', '.join(branch['metrics_24h']['authors'][:3])}")
    
    # Show inactive branches summary
    inactive_branches = [b for b in repo_info['branches'] if b['metrics_7d']['commit_count'] == 0]
    if inactive_branches:
        print(f"\n💤 {len(inactive_branches)} inactive branches (no commits in 7 days)")
    
    # Create visualization data with metrics
    viz_data = create_visualization_data(repo_info)
    
    print(f"\n🎨 Visualization Data:")
    print(f"Nodes: {len(viz_data['nodes'])}")
    print(f"Links: {len(viz_data['links'])}")
    
    # Save data as JSON for the dashboard
    with open('dashboard_data/git_data.json', 'w') as f:
        json.dump(viz_data, f, indent=2, default=str)
    
    print(f"\n✅ Git visualization data with commit metrics saved to dashboard_data/git_data.json")
    print(f"🚀 Dashboard can now show commit activity for the past 24h, 7d, and 30d!")

if __name__ == "__main__":
    main()
