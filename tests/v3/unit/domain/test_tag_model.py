"""
Unit tests for Tag domain model.
"""

import pytest
from datetime import datetime
from uuid import UUID, uuid4

from src.domain.models.tag import (
    Tag,
    TagId,
    TagHierarchy,
    TagFactory,
)


class TestTagId:
    """Tests for TagId value object."""
    
    def test_create_tag_id(self):
        """Test creating a TagId."""
        id_value = uuid4()
        tag_id = TagId(id_value)
        assert tag_id.value == id_value
    
    def test_tag_id_equality(self):
        """Test TagId equality."""
        id_value = uuid4()
        tag_id1 = TagId(id_value)
        tag_id2 = TagId(id_value)
        tag_id3 = TagId(uuid4())
        
        assert tag_id1 == tag_id2
        assert tag_id1 != tag_id3


class TestTag:
    """Tests for Tag aggregate."""
    
    def test_create_tag(self):
        """Test creating a tag."""
        tag_id = TagId(uuid4())
        user_id = uuid4()
        
        tag = Tag(
            id=tag_id,
            name="python",
            user_id=user_id,
        )
        
        assert tag.id == tag_id
        assert tag.name == "python"
        assert tag.user_id == user_id
        assert tag.parent_id is None
        assert tag.color is None
        assert tag.icon is None
        assert tag.description is None
        assert tag.usage_count == 0
    
    def test_tag_with_optional_fields(self):
        """Test creating tag with all optional fields."""
        parent_id = TagId(uuid4())
        tag = Tag(
            id=TagId(uuid4()),
            name="django",
            user_id=uuid4(),
            parent_id=parent_id,
            color="#FF5733",
            icon="🐍",
            description="Django web framework",
        )
        
        assert tag.parent_id == parent_id
        assert tag.color == "#FF5733"
        assert tag.icon == "🐍"
        assert tag.description == "Django web framework"
    
    def test_tag_timestamps(self):
        """Test tag timestamps."""
        tag = Tag(
            id=TagId(uuid4()),
            name="python",
            user_id=uuid4(),
        )
        
        assert isinstance(tag.created_at, datetime)
        assert isinstance(tag.updated_at, datetime)
        assert tag.last_used_at is None
    
    def test_tag_validation(self):
        """Test tag validation rules."""
        # Test empty name
        with pytest.raises(ValueError, match="Tag name cannot be empty"):
            Tag(
                id=TagId(uuid4()),
                name="",
                user_id=uuid4(),
            )
        
        # Test name too long
        with pytest.raises(ValueError, match="Tag name cannot exceed 100 characters"):
            Tag(
                id=TagId(uuid4()),
                name="a" * 101,
                user_id=uuid4(),
            )
        
        # Test invalid color format
        with pytest.raises(ValueError, match="Invalid color format"):
            Tag(
                id=TagId(uuid4()),
                name="python",
                user_id=uuid4(),
                color="invalid",
            )
        
        # Test invalid hex color
        with pytest.raises(ValueError, match="Invalid color format"):
            Tag(
                id=TagId(uuid4()),
                name="python",
                user_id=uuid4(),
                color="#GGGGGG",
            )
    
    def test_normalize_tag_name(self):
        """Test tag name normalization."""
        tag = Tag(
            id=TagId(uuid4()),
            name="  Python  ",
            user_id=uuid4(),
        )
        
        assert tag.name == "python"  # Should be lowercase and trimmed
        
        tag2 = Tag(
            id=TagId(uuid4()),
            name="Machine-Learning",
            user_id=uuid4(),
        )
        
        assert tag2.name == "machine-learning"
    
    def test_increment_usage_count(self):
        """Test incrementing usage count."""
        tag = Tag(
            id=TagId(uuid4()),
            name="python",
            user_id=uuid4(),
        )
        
        assert tag.usage_count == 0
        
        tag.increment_usage()
        assert tag.usage_count == 1
        assert tag.last_used_at is not None
        assert isinstance(tag.last_used_at, datetime)
        
        tag.increment_usage()
        assert tag.usage_count == 2
    
    def test_update_details(self):
        """Test updating tag details."""
        tag = Tag(
            id=TagId(uuid4()),
            name="python",
            user_id=uuid4(),
        )
        
        tag.update_details(
            color="#3776AB",
            icon="🐍",
            description="Python programming language",
        )
        
        assert tag.color == "#3776AB"
        assert tag.icon == "🐍"
        assert tag.description == "Python programming language"
    
    def test_set_parent(self):
        """Test setting parent tag."""
        tag = Tag(
            id=TagId(uuid4()),
            name="django",
            user_id=uuid4(),
        )
        
        parent_id = TagId(uuid4())
        tag.set_parent(parent_id)
        
        assert tag.parent_id == parent_id
    
    def test_remove_parent(self):
        """Test removing parent tag."""
        parent_id = TagId(uuid4())
        tag = Tag(
            id=TagId(uuid4()),
            name="django",
            user_id=uuid4(),
            parent_id=parent_id,
        )
        
        assert tag.parent_id == parent_id
        
        tag.remove_parent()
        assert tag.parent_id is None
    
    def test_is_child_of(self):
        """Test checking if tag is child of another."""
        parent_id = TagId(uuid4())
        tag = Tag(
            id=TagId(uuid4()),
            name="django",
            user_id=uuid4(),
            parent_id=parent_id,
        )
        
        assert tag.is_child_of(parent_id) is True
        assert tag.is_child_of(TagId(uuid4())) is False
        
        # Test tag without parent
        tag2 = Tag(
            id=TagId(uuid4()),
            name="python",
            user_id=uuid4(),
        )
        assert tag2.is_child_of(parent_id) is False


class TestTagHierarchy:
    """Tests for TagHierarchy value object."""
    
    def test_create_hierarchy(self):
        """Test creating tag hierarchy."""
        root_id = TagId(uuid4())
        child1_id = TagId(uuid4())
        child2_id = TagId(uuid4())
        grandchild_id = TagId(uuid4())
        
        hierarchy = TagHierarchy(
            root_id=root_id,
            children={
                root_id: [child1_id, child2_id],
                child1_id: [grandchild_id],
                child2_id: [],
                grandchild_id: [],
            }
        )
        
        assert hierarchy.root_id == root_id
        assert len(hierarchy.children[root_id]) == 2
        assert child1_id in hierarchy.children[root_id]
        assert child2_id in hierarchy.children[root_id]
        assert grandchild_id in hierarchy.children[child1_id]
    
    def test_get_depth(self):
        """Test getting depth of hierarchy."""
        root_id = TagId(uuid4())
        child_id = TagId(uuid4())
        grandchild_id = TagId(uuid4())
        
        hierarchy = TagHierarchy(
            root_id=root_id,
            children={
                root_id: [child_id],
                child_id: [grandchild_id],
                grandchild_id: [],
            }
        )
        
        assert hierarchy.get_depth() == 3
        
        # Test single node
        single_hierarchy = TagHierarchy(
            root_id=root_id,
            children={root_id: []}
        )
        assert single_hierarchy.get_depth() == 1
    
    def test_get_all_descendants(self):
        """Test getting all descendants of a tag."""
        root_id = TagId(uuid4())
        child1_id = TagId(uuid4())
        child2_id = TagId(uuid4())
        grandchild_id = TagId(uuid4())
        
        hierarchy = TagHierarchy(
            root_id=root_id,
            children={
                root_id: [child1_id, child2_id],
                child1_id: [grandchild_id],
                child2_id: [],
                grandchild_id: [],
            }
        )
        
        descendants = hierarchy.get_all_descendants(root_id)
        assert len(descendants) == 3
        assert child1_id in descendants
        assert child2_id in descendants
        assert grandchild_id in descendants
        
        # Test leaf node
        leaf_descendants = hierarchy.get_all_descendants(grandchild_id)
        assert len(leaf_descendants) == 0
    
    def test_get_path_to_root(self):
        """Test getting path from tag to root."""
        root_id = TagId(uuid4())
        child_id = TagId(uuid4())
        grandchild_id = TagId(uuid4())
        
        hierarchy = TagHierarchy(
            root_id=root_id,
            children={
                root_id: [child_id],
                child_id: [grandchild_id],
                grandchild_id: [],
            }
        )
        
        # Build parent mapping
        parents = {
            child_id: root_id,
            grandchild_id: child_id,
        }
        
        path = hierarchy.get_path_to_root(grandchild_id, parents)
        assert path == [grandchild_id, child_id, root_id]
        
        # Test root node
        root_path = hierarchy.get_path_to_root(root_id, parents)
        assert root_path == [root_id]


class TestTagFactory:
    """Tests for TagFactory."""
    
    def test_create_simple_tag(self):
        """Test creating a simple tag."""
        user_id = uuid4()
        tag = TagFactory.create_simple_tag(
            user_id=user_id,
            name="python",
        )
        
        assert tag.name == "python"
        assert tag.user_id == user_id
        assert tag.parent_id is None
        assert tag.color is None
        assert tag.icon is None
    
    def test_create_colored_tag(self):
        """Test creating a colored tag."""
        user_id = uuid4()
        tag = TagFactory.create_colored_tag(
            user_id=user_id,
            name="urgent",
            color="#FF0000",
            icon="🔴",
        )
        
        assert tag.name == "urgent"
        assert tag.color == "#FF0000"
        assert tag.icon == "🔴"
    
    def test_create_hierarchical_tag(self):
        """Test creating a hierarchical tag."""
        user_id = uuid4()
        parent_id = TagId(uuid4())
        
        tag = TagFactory.create_hierarchical_tag(
            user_id=user_id,
            name="django",
            parent_id=parent_id,
            description="Django web framework",
        )
        
        assert tag.name == "django"
        assert tag.parent_id == parent_id
        assert tag.description == "Django web framework"
    
    def test_create_category_tag(self):
        """Test creating a category tag."""
        user_id = uuid4()
        tag = TagFactory.create_category_tag(
            user_id=user_id,
            name="Programming Languages",
            color="#0066CC",
            icon="💻",
        )
        
        assert tag.name == "programming-languages"  # Should be normalized
        assert tag.color == "#0066CC"
        assert tag.icon == "💻"
        assert tag.parent_id is None  # Categories are top-level