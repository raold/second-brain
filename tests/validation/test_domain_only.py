#!/usr/bin/env python3
"""
Test domain models directly without pytest conftest complications.
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_memory_domain():
    """Test Memory domain model."""
    print("Testing Memory domain model...")
    
    try:
        from uuid import UUID, uuid4
        from src.domain.models.memory import Memory, MemoryId, MemoryType, MemoryStatus
        
        # Test MemoryId generation
        id1 = MemoryId.generate()
        id2 = MemoryId.generate()
        assert id1 != id2
        assert isinstance(id1.value, UUID)
        print("[OK] MemoryId generation works")
        
        # Test Memory creation
        memory_data = {
            "id": MemoryId.generate(),
            "user_id": uuid4(),
            "title": "Test Memory",
            "content": "This is a test memory content.",
            "memory_type": MemoryType.SEMANTIC,
        }
        
        memory = Memory(**memory_data)
        assert memory.title == "Test Memory"
        assert memory.content == "This is a test memory content."
        assert memory.memory_type == MemoryType.SEMANTIC
        assert memory.status == MemoryStatus.ACTIVE
        print("[OK] Memory creation works")
        
        # Test Memory content update
        old_updated_at = memory.updated_at
        time.sleep(0.001)  # Ensure timestamp difference
        memory.update_content("New Title", "New content")
        assert memory.title == "New Title"
        assert memory.content == "New content"
        assert memory.updated_at > old_updated_at
        print("[OK] Memory update works")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Memory domain test: {e}")
        return False

def test_user_domain():
    """Test User domain model."""
    print("\nTesting User domain model...")
    
    try:
        from uuid import UUID, uuid4
        from src.domain.models.user import User, UserId, UserRole
        
        # Test UserId generation
        id1 = UserId.generate()
        id2 = UserId.generate()
        assert id1 != id2
        assert isinstance(id1.value, UUID)
        print("[OK] UserId generation works")
        
        # Test User creation
        user_data = {
            "id": UserId.generate(),
            "email": "test@example.com",
            "username": "testuser",
        }
        
        user = User(**user_data)
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.role == UserRole.USER
        assert user.is_active is True
        assert user.is_verified is False
        print("[OK] User creation works")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] User domain test: {e}")
        return False

def main():
    """Run all domain tests."""
    print("=== Domain Layer Validation ===")
    
    success = True
    
    if not test_memory_domain():
        success = False
        
    if not test_user_domain():
        success = False
    
    print("\n=== Domain Test Summary ===")
    if success:
        print("[SUCCESS] All domain tests passed!")
        print("Domain layer is working correctly.")
    else:
        print("[FAILURE] Some domain tests failed.")
        
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)