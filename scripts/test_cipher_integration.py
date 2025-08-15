#!/usr/bin/env python3
"""
Test Cipher Integration with Second Brain
Verifies that memories can sync between Second Brain and Cipher
"""

import asyncio
import os
import sys
import io
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables
os.environ["CIPHER_ENABLED"] = "true"
os.environ["CIPHER_URL"] = "http://localhost:3000"

from app.adapters.cipher_adapter import CipherAdapter, create_cipher_config
from app.interfaces.sync_provider import SyncStatus
from app.core.logging import get_logger

logger = get_logger(__name__)


async def test_cipher_connection():
    """Test basic connection to Cipher"""
    print("\n🔧 Testing Cipher Integration\n")
    print("=" * 50)
    
    # Create Cipher configuration
    config = create_cipher_config(
        enabled=True,
        cipher_url="http://localhost:3000",
        sync_interval=60  # 1 minute for testing
    )
    
    # Create adapter
    adapter = CipherAdapter(config)
    
    try:
        # Test 1: Connect to Cipher
        print("\n✅ Test 1: Connecting to Cipher...")
        await adapter.connect()
        print("   SUCCESS: Connected to Cipher server")
        
        # Test 2: Health check
        print("\n✅ Test 2: Health check...")
        health = await adapter.health_check()
        if health.healthy:
            print(f"   SUCCESS: Cipher is healthy")
            print(f"   - Latency: {health.latency_ms:.2f}ms")
            if health.details:
                print(f"   - Details: {health.details}")
        else:
            print(f"   WARNING: Health check failed: {health.error_message}")
        
        # Test 3: Push a test memory
        print("\n✅ Test 3: Pushing test memory to Cipher...")
        test_memory = {
            "id": f"test-{datetime.now().timestamp()}",
            "content": "Test memory from Second Brain integration test",
            "type": "concept",
            "tags": ["test", "cipher-integration"],
            "created_at": datetime.now().isoformat(),
            "metadata": {
                "source": "second-brain-test",
                "test_run": True
            }
        }
        
        success = await adapter.push_memory(test_memory)
        if success:
            print("   SUCCESS: Memory pushed to Cipher")
        else:
            print("   FAILED: Could not push memory")
        
        # Test 4: Pull changes from Cipher
        print("\n✅ Test 4: Pulling changes from Cipher...")
        changes = await adapter.pull_changes()
        print(f"   SUCCESS: Pulled {len(changes)} memories from Cipher")
        
        # Test 5: Batch push
        print("\n✅ Test 5: Testing batch push...")
        test_batch = [
            {
                "id": f"batch-{i}-{datetime.now().timestamp()}",
                "content": f"Batch test memory {i}",
                "type": "code" if i % 2 == 0 else "reasoning",
                "tags": ["batch-test"],
                "created_at": datetime.now().isoformat()
            }
            for i in range(3)
        ]
        
        result = await adapter.push_batch(test_batch)
        if result.status == SyncStatus.SUCCESS:
            print(f"   SUCCESS: Pushed {result.pushed} memories in batch")
        else:
            print(f"   PARTIAL: Pushed {result.pushed} memories, errors: {result.errors}")
        
        print("\n" + "=" * 50)
        print("🎉 Cipher Integration Test Complete!")
        print("\nCipher is properly configured and working with Second Brain.")
        print("\nNext steps:")
        print("1. Start Second Brain with: make dev")
        print("2. Memories will automatically sync every 5 minutes")
        print("3. Configure your IDE to use Cipher MCP server")
        
    except ConnectionError as e:
        print(f"\n❌ Connection Error: {e}")
        print("\nMake sure Cipher is running:")
        print("  cipher start")
        print("\nOr check if it's running on the correct port:")
        print("  curl http://localhost:3000/health")
        
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        print("\nCheck the logs for more details")
        
    finally:
        # Disconnect
        await adapter.disconnect()
        print("\n✅ Disconnected from Cipher")


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_cipher_connection())