#!/usr/bin/env python3
"""
Setup Qdrant collections for Cipher integration
Creates dual collections for knowledge and reflection memory
"""

import requests
import json
import sys

QDRANT_URL = "http://localhost:6333"

def create_collection(name, size=1536):
    """Create a Qdrant collection with OpenAI embedding dimensions"""
    
    payload = {
        "vectors": {
            "size": size,
            "distance": "Cosine"
        },
        "optimizers_config": {
            "default_segment_number": 2
        },
        "replication_factor": 1
    }
    
    try:
        # Check if collection exists
        response = requests.get(f"{QDRANT_URL}/collections/{name}")
        if response.status_code == 200:
            print(f"✓ Collection '{name}' already exists")
            return True
            
        # Create collection
        response = requests.put(
            f"{QDRANT_URL}/collections/{name}",
            json=payload
        )
        
        if response.status_code == 200:
            print(f"✅ Created collection '{name}'")
            return True
        else:
            print(f"❌ Failed to create '{name}': {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error connecting to Qdrant: {e}")
        return False

def main():
    print("🚀 Setting up Qdrant collections for Cipher")
    print("=" * 50)
    
    # Check Qdrant connection
    try:
        response = requests.get(f"{QDRANT_URL}/collections")
        response.raise_for_status()
        print(f"✓ Connected to Qdrant at {QDRANT_URL}")
    except:
        print(f"❌ Cannot connect to Qdrant at {QDRANT_URL}")
        print("Make sure Qdrant is running: docker-compose up -d qdrant")
        sys.exit(1)
    
    # Create Cipher collections
    collections = [
        "cipher_knowledge",      # System 1: Programming concepts
        "cipher_reflection",     # System 2: Reasoning chains
        "second_brain_memory",   # Shared memory for second-brain
    ]
    
    print("\nCreating collections...")
    for collection in collections:
        create_collection(collection)
    
    # List all collections
    print("\n📊 Current Qdrant collections:")
    response = requests.get(f"{QDRANT_URL}/collections")
    data = response.json()
    
    for col in data["result"]["collections"]:
        # Get collection info
        info_response = requests.get(f"{QDRANT_URL}/collections/{col['name']}")
        info = info_response.json()
        
        if info["status"] == "ok":
            points_count = info["result"]["points_count"]
            vectors_count = info["result"]["vectors_count"]
            print(f"  - {col['name']}: {points_count} points, {vectors_count} vectors")
        else:
            print(f"  - {col['name']}")
    
    print("\n✅ Qdrant setup complete!")
    print("\nCipher will now use Qdrant for:")
    print("  • Knowledge memory (concepts, patterns)")
    print("  • Reflection memory (reasoning chains)")
    print("  • Shared memory with second-brain")

if __name__ == "__main__":
    main()