#!/usr/bin/env python3
"""
Simple test to verify the storage handler is working correctly.
"""
import asyncio
from app.storage.storage_handler import get_storage_handler

async def test_storage():
    try:
        handler = await get_storage_handler()
        print('✅ Storage handler created successfully')
        print(f'Storage handler type: {type(handler)}')
        print(f'Has store_memory: {hasattr(handler, "store_memory")}')
        print(f'Has search_memories: {hasattr(handler, "search_memories")}')
        print(f'Has get_memory: {hasattr(handler, "get_memory")}')
        return True
    except Exception as e:
        print(f'❌ Error: {e}')
        return False

if __name__ == "__main__":
    success = asyncio.run(test_storage())
    if success:
        print('\n✅ Storage handler test passed!')
    else:
        print('\n❌ Storage handler test failed!')
