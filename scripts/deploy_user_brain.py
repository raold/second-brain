#!/usr/bin/env python3
"""
Deploy a single user's brain container to Kubernetes.
This script would be called by the management API when a user signs up.
"""

import os
import sys
import uuid
import base64
import subprocess
from typing import Dict, Any
from pathlib import Path


# User tier configurations
TIER_CONFIGS = {
    "free": {
        "memory_request": "512Mi",
        "memory_limit": "1Gi",
        "cpu_request": "0.25",
        "cpu_limit": "0.5",
        "storage_size": "1Gi",
        "max_replicas": 1
    },
    "pro": {
        "memory_request": "2Gi",
        "memory_limit": "4Gi",
        "cpu_request": "1",
        "cpu_limit": "2",
        "storage_size": "10Gi",
        "max_replicas": 3
    },
    "enterprise": {
        "memory_request": "8Gi",
        "memory_limit": "16Gi",
        "cpu_request": "4",
        "cpu_limit": "8",
        "storage_size": "100Gi",
        "max_replicas": 10
    }
}


def generate_api_key() -> str:
    """Generate a unique API key for the user's container."""
    return str(uuid.uuid4())


def deploy_user_brain(user_id: str, tier: str = "free", email: str = None) -> Dict[str, Any]:
    """
    Deploy a new brain container for a user.
    
    Args:
        user_id: Unique user identifier
        tier: User's subscription tier (free, pro, enterprise)
        email: User's email (optional, for notifications)
    
    Returns:
        Deployment information including API endpoint and key
    """
    if tier not in TIER_CONFIGS:
        raise ValueError(f"Invalid tier: {tier}")
    
    config = TIER_CONFIGS[tier]
    api_key = generate_api_key()
    api_key_b64 = base64.b64encode(api_key.encode()).decode()
    
    # Read the template
    template_path = Path(__file__).parent.parent / "k8s" / "single-user-deployment.yaml"
    with open(template_path, 'r') as f:
        template = f.read()
    
    # Replace variables
    deployment_yaml = template.replace("${USER_ID}", user_id)
    deployment_yaml = deployment_yaml.replace("${USER_TIER}", tier)
    deployment_yaml = deployment_yaml.replace("${USER_API_KEY_BASE64}", api_key_b64)
    deployment_yaml = deployment_yaml.replace("${MEMORY_REQUEST}", config["memory_request"])
    deployment_yaml = deployment_yaml.replace("${MEMORY_LIMIT}", config["memory_limit"])
    deployment_yaml = deployment_yaml.replace("${CPU_REQUEST}", config["cpu_request"])
    deployment_yaml = deployment_yaml.replace("${CPU_LIMIT}", config["cpu_limit"])
    deployment_yaml = deployment_yaml.replace("${STORAGE_SIZE}", config["storage_size"])
    deployment_yaml = deployment_yaml.replace("${MAX_REPLICAS}", str(config["max_replicas"]))
    
    # Save the customized YAML
    output_path = f"/tmp/brain-{user_id}.yaml"
    with open(output_path, 'w') as f:
        f.write(deployment_yaml)
    
    # Apply to Kubernetes
    try:
        result = subprocess.run(
            ["kubectl", "apply", "-f", output_path],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✅ Deployed brain for user {user_id}")
        
        # Get the service endpoint
        service_name = f"brain-{user_id}-svc"
        endpoint = f"http://{service_name}.second-brain-users.svc.cluster.local"
        
        return {
            "success": True,
            "user_id": user_id,
            "tier": tier,
            "api_key": api_key,
            "endpoint": endpoint,
            "message": f"Brain deployed successfully for user {user_id}"
        }
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to deploy brain for user {user_id}: {e.stderr}")
        return {
            "success": False,
            "error": str(e),
            "stderr": e.stderr
        }
    finally:
        # Clean up temp file
        if os.path.exists(output_path):
            os.remove(output_path)


def delete_user_brain(user_id: str) -> bool:
    """
    Delete a user's brain container and associated resources.
    
    Args:
        user_id: User identifier
    
    Returns:
        Success status
    """
    resources = [
        f"deployment/brain-{user_id}",
        f"service/brain-{user_id}-svc",
        f"secret/brain-{user_id}-secret",
        f"pvc/brain-{user_id}-pvc",
        f"hpa/brain-{user_id}-hpa"
    ]
    
    success = True
    for resource in resources:
        try:
            subprocess.run(
                ["kubectl", "delete", resource, "-n", "second-brain-users"],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"✅ Deleted {resource}")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Failed to delete {resource}: {e.stderr}")
            success = False
    
    return success


def upgrade_user_tier(user_id: str, new_tier: str) -> bool:
    """
    Upgrade a user's brain to a new tier.
    
    Args:
        user_id: User identifier
        new_tier: New subscription tier
    
    Returns:
        Success status
    """
    if new_tier not in TIER_CONFIGS:
        raise ValueError(f"Invalid tier: {new_tier}")
    
    config = TIER_CONFIGS[new_tier]
    
    # Update deployment resources
    patches = [
        {
            "resource": f"deployment/brain-{user_id}",
            "patch": {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [{
                                "name": "second-brain",
                                "resources": {
                                    "requests": {
                                        "memory": config["memory_request"],
                                        "cpu": config["cpu_request"]
                                    },
                                    "limits": {
                                        "memory": config["memory_limit"],
                                        "cpu": config["cpu_limit"]
                                    }
                                }
                            }]
                        }
                    }
                }
            }
        },
        {
            "resource": f"hpa/brain-{user_id}-hpa",
            "patch": {
                "spec": {
                    "maxReplicas": config["max_replicas"]
                }
            }
        }
    ]
    
    success = True
    for patch_config in patches:
        try:
            import json
            patch_json = json.dumps(patch_config["patch"])
            subprocess.run(
                ["kubectl", "patch", patch_config["resource"], "-n", "second-brain-users",
                 "--type", "merge", "-p", patch_json],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"✅ Updated {patch_config['resource']}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to update {patch_config['resource']}: {e.stderr}")
            success = False
    
    return success


def list_user_brains() -> list:
    """List all deployed user brains."""
    try:
        result = subprocess.run(
            ["kubectl", "get", "deployments", "-n", "second-brain-users",
             "-o", "jsonpath={.items[*].metadata.name}"],
            capture_output=True,
            text=True,
            check=True
        )
        deployments = result.stdout.strip().split()
        return [d.replace("brain-", "") for d in deployments if d.startswith("brain-")]
    except subprocess.CalledProcessError:
        return []


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage user brain deployments")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Deploy command
    deploy_parser = subparsers.add_parser("deploy", help="Deploy a new user brain")
    deploy_parser.add_argument("user_id", help="User ID")
    deploy_parser.add_argument("--tier", default="free", choices=["free", "pro", "enterprise"])
    deploy_parser.add_argument("--email", help="User email")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a user brain")
    delete_parser.add_argument("user_id", help="User ID")
    
    # Upgrade command
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade user tier")
    upgrade_parser.add_argument("user_id", help="User ID")
    upgrade_parser.add_argument("tier", choices=["free", "pro", "enterprise"])
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all user brains")
    
    args = parser.parse_args()
    
    if args.command == "deploy":
        result = deploy_user_brain(args.user_id, args.tier, args.email)
        print(result)
    elif args.command == "delete":
        success = delete_user_brain(args.user_id)
        print("Success" if success else "Failed")
    elif args.command == "upgrade":
        success = upgrade_user_tier(args.user_id, args.tier)
        print("Success" if success else "Failed")
    elif args.command == "list":
        users = list_user_brains()
        print(f"Active user brains: {users}")
    else:
        parser.print_help()