#!/usr/bin/env python3
"""
Test script for GitService
"""

import json

from app.services.git_service import GitService


def main():
    print('Testing GitService...')
    git_service = GitService()

    print('\n=== All Branches ===')
    branches = git_service.get_all_branches()
    print(json.dumps(branches, indent=2))

    print('\n=== Repository Status ===')
    repo_status = git_service.get_repository_status()
    print(f'Current branch: {repo_status.current_branch}')
    print(f'Total branches: {repo_status.total_branches}')
    print(f'Dirty: {repo_status.dirty}')

    print('\n=== Branch Details ===')
    for branch in repo_status.branches:
        print(f'{branch.name}: {branch.status}')

    print('\n=== Visualization Data ===')
    viz_data = git_service.get_d3_visualization_data()
    print(f'Nodes: {len(viz_data["nodes"])}')
    print(f'Links: {len(viz_data["links"])}')

if __name__ == "__main__":
    main()
