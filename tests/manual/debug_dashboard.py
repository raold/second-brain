#!/usr/bin/env python3
"""Test script to debug the dashboard data structure"""


from development_status import get_development_status


def main():
    data = get_development_status()

    print('=== BRANCH DATA ===')
    if 'branches' in data:
        for branch in data['branches'][:3]:
            name = branch.get('name', 'Unknown')
            status = branch.get('status', {})
            print(f'{name}: {status}')
    else:
        print('No branches found')

    print('\n=== PR STATUS ===')
    if 'pr_status' in data:
        print(f'PR Status count: {len(data["pr_status"])}')
        if len(data['pr_status']) > 0:
            print(f'First PR item: {data["pr_status"][0]}')
    else:
        print('PR status not found')

    print('\n=== VERSION ROADMAP ===')
    if 'version_roadmap' in data:
        print(f'Roadmap versions: {list(data["version_roadmap"].keys())}')
        if data['version_roadmap']:
            first_version = list(data['version_roadmap'].keys())[0]
            print(f'First roadmap item: {data["version_roadmap"][first_version]}')
    else:
        print('Version roadmap not found')

if __name__ == '__main__':
    main()
