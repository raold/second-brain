#!/usr/bin/env python3
"""
Test script to verify OpenAI API key configuration.
Run this to check if your OpenAI API key is properly set and working.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_openai_key():
    """Test OpenAI API key configuration and functionality."""
    print("Testing OpenAI API Key Configuration...")
    print("-" * 50)
    
    # Check environment variable
    api_key = os.environ.get('OPENAI_API_KEY', '')
    
    if not api_key:
        print("[ERROR] OPENAI_API_KEY environment variable is not set")
        print("\nTo set it:")
        print("  Windows: set OPENAI_API_KEY=your-api-key-here")
        print("  Linux/Mac: export OPENAI_API_KEY=your-api-key-here")
        return False
    
    # Check key format
    if not api_key.startswith('sk-'):
        print(f"[WARNING] OPENAI_API_KEY has unexpected format: {api_key[:5]}...")
        print("   OpenAI API keys typically start with 'sk-'")
    else:
        print(f"[OK] OPENAI_API_KEY is set: {api_key[:7]}...{api_key[-4:]}")
    
    # Test the key with actual API call
    print("\nTesting API connection...")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # List models to verify the key works
        models = list(client.models.list())
        print(f"[OK] API key is valid! Found {len(models)} available models")
        
        # Test embedding creation
        print("\nTesting embedding creation...")
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input="Hello, this is a test"
        )
        embedding = response.data[0].embedding
        print(f"[OK] Successfully created embedding with {len(embedding)} dimensions")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] API test failed: {e}")
        return False

def test_app_integration():
    """Test OpenAI integration with the app."""
    print("\nTesting app integration...")
    
    try:
        from app.utils.openai_client import OpenAIClient
        from app.config import Config
        
        print(f"Config.OPENAI_API_KEY: {'Set' if Config.OPENAI_API_KEY else 'Not set'}")
        
        client = OpenAIClient()
        if client._client:
            print("[OK] OpenAIClient initialized successfully")
        else:
            print("[ERROR] OpenAIClient failed to initialize")
            
    except Exception as e:
        print(f"[ERROR] App integration test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("OpenAI API Key Test Script")
    print("=" * 50)
    
    # Test API key
    key_valid = test_openai_key()
    
    # Test app integration
    if key_valid:
        test_app_integration()
    
    print("\n" + "=" * 50)
    if key_valid:
        print("[OK] All tests passed! Your OpenAI API key is working.")
    else:
        print("[ERROR] Tests failed. Please check your OpenAI API key configuration.")
        sys.exit(1)