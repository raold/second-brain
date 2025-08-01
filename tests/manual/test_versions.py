#!/usr/bin/env python3
"""Test script to show the new branch version assignments"""


from development_status import get_development_status


def main():
    status = get_development_status()

    print("=== BRANCH VERSION ASSIGNMENTS ===")
    for branch in status["branches"]:
        if branch["name"] in ["main", "testing", "develop"]:
            name = branch["name"]
            version = branch["status"]["version"]
            feature = branch["status"]["feature"]
            stat = branch["status"]["status"]
            print(f"{name:>10}: {version} - {feature} ({stat})")

    print("\n=== VERSION ROADMAP ===")
    for version, details in status["version_roadmap"].items():
        if version in ["v2.4.3", "v2.5.0", "v2.6.0"]:
            focus = details["focus"]
            stat = details["status"]
            branch = details.get("branch", "N/A")
            print(f"{version}: {focus} - {stat} ({branch} branch)")

    print("\n=== CURRENT VERSIONS ===")
    versions = status["versions"]
    print(f'Stable: {versions["current_stable"]}')
    print(f'Testing: {versions.get("testing_version", "N/A")}')
    print(f'Development: {versions["current_development"]}')


if __name__ == "__main__":
    main()
