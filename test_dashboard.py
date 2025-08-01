#!/usr/bin/env python3
"""Test dashboard routes directly"""

import requests
import json

# Test different endpoints
base_url = "http://localhost:8000"
api_key = "test-token-for-development"

endpoints = [
    "/api/v1/dashboard/status",
    "/api/v1/dashboard/metrics", 
    "/api/v1/dashboard/todos",
    "/api/v1/dashboard/docker",
    "/api/v1/dashboard/activity",
    "/api/v1/dashboard/analytics",
]

print("Testing dashboard endpoints...")
print(f"Using API key: {api_key}")
print("-" * 50)

for endpoint in endpoints:
    url = f"{base_url}{endpoint}"
    params = {"api_key": api_key}
    
    try:
        response = requests.get(url, params=params)
        print(f"\n{endpoint}:")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Response: {json.dumps(data, indent=2)[:200]}...")
        else:
            print(f"  Error: {response.text}")
    except Exception as e:
        print(f"  Exception: {e}")

# Also test what routes are actually available
print("\n" + "-" * 50)
print("Checking OpenAPI spec for available routes...")
try:
    response = requests.get(f"{base_url}/openapi.json")
    if response.status_code == 200:
        data = response.json()
        paths = list(data.get('paths', {}).keys())
        print(f"Total routes: {len(paths)}")
        dashboard_routes = [p for p in paths if 'dashboard' in p]
        if dashboard_routes:
            print("Dashboard routes found:")
            for route in dashboard_routes:
                print(f"  {route}")
        else:
            print("No dashboard routes found in OpenAPI spec")
except Exception as e:
    print(f"Error fetching OpenAPI spec: {e}")