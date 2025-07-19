#!/usr/bin/env python3
# Test script to directly call the API and print JSON response

import requests
import json
import pprint

try:
    print("Testing Dashboard API...")
    response = requests.get('http://localhost:8000/dashboard/development/status', timeout=5)
    print(f"Status Code: {response.status_code}")
    
    if response.ok:
        data = response.json()
        print("\n=== FULL API RESPONSE ===")
        pprint.pprint(data, width=120)
        
        print(f"\n=== KEY STATS ===")
        print(f"PR Status items: {len(data.get('pr_status', []))}")
        print(f"Version roadmap keys: {list(data.get('version_roadmap', {}).keys())}")
        print(f"Summary data: {data.get('summary', {})}")
        
        # Show first PR status item
        if data.get('pr_status'):
            print(f"\n=== FIRST PR STATUS ITEM ===")
            pprint.pprint(data['pr_status'][0])
            
        # Show first roadmap item  
        if data.get('version_roadmap'):
            first_version = list(data['version_roadmap'].keys())[0]
            print(f"\n=== FIRST ROADMAP ITEM ({first_version}) ===")
            pprint.pprint(data['version_roadmap'][first_version])
    else:
        print(f"Error: {response.status_code} - {response.text}")
        
except Exception as e:
    print(f"Connection error: {e}")
