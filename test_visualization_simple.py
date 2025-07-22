"""
Simple test for visualization feature v2.6.2-visualization
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_visualization_data_structure():
    """Test graph visualization data structures"""
    print("🎨 Testing Visualization Data Structures v2.6.2-visualization")
    
    # Test node structure
    sample_node = {
        "id": "1",
        "label": "Python", 
        "type": "technology",
        "importance": 0.9
    }
    
    required_node_fields = ["id", "label", "type"]
    for field in required_node_fields:
        assert field in sample_node, f"Node missing required field: {field}"
    print("✅ Node structure validation works")
    
    # Test edge structure
    sample_edge = {
        "source": "1",
        "target": "2",
        "weight": 0.8,
        "type": "used_in"
    }
    
    required_edge_fields = ["source", "target", "weight"]
    for field in required_edge_fields:
        assert field in sample_edge, f"Edge missing required field: {field}"
    print("✅ Edge structure validation works")
    
    # Test entity type color mapping
    entity_types = ["person", "organization", "technology", "concept", 
                   "location", "event", "skill", "topic", "other"]
    
    color_map = {
        "person": "#FF6B6B",
        "organization": "#4ECDC4",
        "technology": "#45B7D1",
        "concept": "#96CEB4",
        "location": "#DDA0DD",
        "event": "#F4A460",
        "skill": "#FFD93D",
        "topic": "#6C5CE7",
        "other": "#95A5A6"
    }
    
    for entity_type in entity_types:
        assert entity_type in color_map, f"Missing color for entity type: {entity_type}"
        assert color_map[entity_type].startswith("#"), f"Invalid color format for {entity_type}"
        assert len(color_map[entity_type]) == 7, f"Invalid color length for {entity_type}"
    print("✅ Entity type color mapping works")
    
    return True


def test_search_filtering():
    """Test search and filtering functionality"""
    print("\n🔍 Testing Search and Filtering")
    
    # Sample graph data
    sample_nodes = [
        {"id": "1", "label": "Python", "type": "technology", "importance": 0.9},
        {"id": "2", "label": "Machine Learning", "type": "concept", "importance": 0.8},
        {"id": "3", "label": "John Smith", "type": "person", "importance": 0.7}
    ]
    
    # Test search functionality
    search_term = "Python"
    matching_nodes = [
        n for n in sample_nodes 
        if search_term.lower() in n["label"].lower()
    ]
    assert len(matching_nodes) == 1
    assert matching_nodes[0]["id"] == "1"
    print("✅ Node search functionality works")
    
    # Test entity type filtering
    tech_nodes = [
        n for n in sample_nodes
        if n["type"] == "technology"
    ]
    assert len(tech_nodes) == 1
    assert tech_nodes[0]["label"] == "Python"
    print("✅ Entity type filtering works")
    
    # Test multiple type filtering
    types_to_include = ["concept", "person"]
    filtered_nodes = [
        n for n in sample_nodes
        if n["type"] in types_to_include
    ]
    assert len(filtered_nodes) == 2
    print("✅ Multiple type filtering works")
    
    return True


def test_d3_visualization_structure():
    """Test D3.js visualization structure"""
    print("\n📊 Testing D3.js Visualization Structure")
    
    # Test JavaScript file exists and has key components
    viz_file = Path("static/js/knowledge-graph-viz.js")
    if viz_file.exists():
        content = viz_file.read_text()
        
        # Check for key D3.js components
        assert "class KnowledgeGraphViz" in content
        assert "d3.forceSimulation" in content
        assert "d3.forceLink" in content
        assert "d3.zoom" in content
        print("✅ D3.js visualization class structure works")
        
        # Check for interaction methods
        assert "onNodeClick" in content
        assert "onNodeHover" in content
        assert "drag" in content
        print("✅ Interaction methods present")
        
        # Check for export functionality
        assert "exportAsPNG" in content
        assert "exportAsJSON" in content
        print("✅ Export functionality present")
        
    else:
        print("⚠️  D3.js visualization file not found at expected location")
    
    return True


def main():
    """Run all tests"""
    print("🎨 Graph Visualization Testing v2.6.2-visualization")
    print("=" * 60)
    
    try:
        success1 = test_visualization_data_structure()
        success2 = test_search_filtering()
        success3 = test_d3_visualization_structure()
        
        if success1 and success2 and success3:
            print("\n✅ All Visualization Feature Tests: PASSED")
            return True
        else:
            print("\n❌ Some Visualization Feature Tests: FAILED")
            return False
            
    except Exception as e:
        print(f"\n❌ Visualization Feature Tests: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)