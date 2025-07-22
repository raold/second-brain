"""
Tests for the graph query parser
"""

import pytest
from app.services.graph_query_parser import (
    GraphQueryParser,
    QueryType,
    ParsedQuery
)


class TestGraphQueryParser:
    """Test the graph query parser functionality"""
    
    @pytest.fixture
    def parser(self):
        """Create a query parser instance"""
        return GraphQueryParser()
    
    def test_connection_query_parsing(self, parser):
        """Test parsing connection queries"""
        queries = [
            "Show connections between Python and machine learning",
            "What connects AI to neural networks?",
            "Display the relationship between data science and statistics",
            "How is Python connected to web development?"
        ]
        
        for query in queries:
            parsed = parser.parse(query)
            assert parsed.query_type == QueryType.CONNECTION
            assert len(parsed.entities) >= 2
            assert parsed.filters is None or len(parsed.filters) == 0
    
    def test_related_query_parsing(self, parser):
        """Test parsing related queries"""
        queries = [
            "What is related to machine learning?",
            "Show everything connected to Python",
            "Find related concepts to artificial intelligence",
            "Display items associated with data science"
        ]
        
        for query in queries:
            parsed = parser.parse(query)
            assert parsed.query_type == QueryType.RELATED
            assert len(parsed.entities) >= 1
            assert parsed.operation_params.get("max_depth", 1) > 0
    
    def test_filter_query_parsing(self, parser):
        """Test parsing filter queries"""
        queries = [
            "Show all people",
            "Display all organizations",
            "List all technologies",
            "Find all concepts"
        ]
        
        for query in queries:
            parsed = parser.parse(query)
            assert parsed.query_type == QueryType.FILTER
            assert len(parsed.filters) > 0
            assert "type" in parsed.filters
    
    def test_analysis_query_parsing(self, parser):
        """Test parsing analysis queries"""
        queries = [
            "Tell me about machine learning",
            "Analyze the relationship between Python and AI",
            "What can you tell me about neural networks?",
            "Explain data science concepts"
        ]
        
        for query in queries:
            parsed = parser.parse(query)
            assert parsed.query_type == QueryType.ANALYSIS
            assert len(parsed.entities) >= 1
    
    def test_entity_extraction(self, parser):
        """Test entity extraction from queries"""
        test_cases = [
            ("connections between Python and JavaScript", ["Python", "JavaScript"]),
            ("related to machine learning and deep learning", ["machine learning", "deep learning"]),
            ("show all people in San Francisco", ["San Francisco"]),
            ("analyze OpenAI and ChatGPT relationship", ["OpenAI", "ChatGPT"])
        ]
        
        for query, expected_entities in test_cases:
            parsed = parser.parse(query)
            extracted_entities = [e.lower() for e in parsed.entities]
            for expected in expected_entities:
                assert expected.lower() in extracted_entities
    
    def test_complex_entity_extraction(self, parser):
        """Test extraction of complex multi-word entities"""
        query = "Show connections between New York City and San Francisco Bay Area"
        parsed = parser.parse(query)
        
        entities_lower = [e.lower() for e in parsed.entities]
        assert "new york city" in entities_lower or "new york" in entities_lower
        assert "san francisco" in entities_lower or "san francisco bay area" in entities_lower
    
    def test_filter_extraction(self, parser):
        """Test extraction of filters from queries"""
        test_cases = [
            ("show all people", {"type": "person"}),
            ("display technology entities", {"type": "technology"}),
            ("list important concepts", {"type": "concept", "importance": "high"}),
            ("find recent events", {"type": "event", "time": "recent"})
        ]
        
        for query, expected_filters in test_cases:
            parsed = parser.parse(query)
            for key, value in expected_filters.items():
                if key in parsed.filters:
                    assert parsed.filters[key] == value
    
    def test_operation_parameters(self, parser):
        """Test extraction of operation parameters"""
        # Test depth parameters
        query = "Show related items within 3 hops"
        parsed = parser.parse(query)
        assert parsed.operation_params.get("max_depth") == 3
        
        # Test limit parameters
        query2 = "Show top 10 connections"
        parsed2 = parser.parse(query2)
        assert parsed2.operation_params.get("limit") == 10
    
    def test_query_suggestions(self, parser):
        """Test query suggestion generation"""
        partial_query = "Show connections"
        suggestions = parser.get_suggestions(partial_query)
        
        assert len(suggestions) > 0
        assert all("connections" in s.lower() for s in suggestions)
        
        # Test entity-based suggestions
        partial_with_entity = "Python"
        suggestions2 = parser.get_suggestions(partial_with_entity)
        assert len(suggestions2) > 0
        assert any("Python" in s for s in suggestions2)
    
    def test_query_validation(self, parser):
        """Test query validation"""
        # Valid queries
        valid_queries = [
            "Show connections between A and B",
            "What is related to X?",
            "Display all people",
            "Analyze concept Y"
        ]
        
        for query in valid_queries:
            result = parser.validate_query(query)
            assert result["valid"] is True
            assert "error" not in result
        
        # Invalid queries
        invalid_queries = [
            "",  # Empty
            "xyz",  # Too short/unclear
            "show",  # Incomplete
        ]
        
        for query in invalid_queries:
            result = parser.validate_query(query)
            assert result["valid"] is False
            assert "error" in result
    
    def test_ambiguous_query_handling(self, parser):
        """Test handling of ambiguous queries"""
        ambiguous_queries = [
            "python",  # Could be asking about the language or searching for it
            "connections",  # Missing entities
            "show all",  # Missing what to show
        ]
        
        for query in ambiguous_queries:
            parsed = parser.parse(query)
            # Should either provide a default interpretation or mark as ambiguous
            assert parsed.query_type is not None
            assert parsed.confidence < 1.0  # Lower confidence for ambiguous
    
    def test_case_insensitivity(self, parser):
        """Test case insensitive parsing"""
        queries = [
            ("SHOW CONNECTIONS BETWEEN python AND java", "Show connections between Python and Java"),
            ("what is RELATED to AI?", "What is related to AI?"),
            ("Display ALL PEOPLE", "display all people")
        ]
        
        for query1, query2 in queries:
            parsed1 = parser.parse(query1)
            parsed2 = parser.parse(query2)
            
            assert parsed1.query_type == parsed2.query_type
            # Entities might differ in case but should be equivalent
            assert len(parsed1.entities) == len(parsed2.entities)
    
    def test_special_characters_handling(self, parser):
        """Test handling of special characters"""
        queries_with_special = [
            "Show connections between C++ and C#",
            "What is related to Node.js?",
            "Find all .NET developers",
            "Analyze AWS S3 usage"
        ]
        
        for query in queries_with_special:
            parsed = parser.parse(query)
            assert parsed is not None
            assert parsed.query_type is not None
            assert len(parsed.entities) > 0
    
    def test_compound_query_parsing(self, parser):
        """Test parsing of compound queries"""
        compound_query = "Show connections between Python and Java in technology entities"
        parsed = parser.parse(compound_query)
        
        assert parsed.query_type == QueryType.CONNECTION
        assert "Python" in parsed.entities
        assert "Java" in parsed.entities
        assert parsed.filters.get("type") == "technology"
    
    def test_temporal_query_parsing(self, parser):
        """Test parsing of temporal queries"""
        temporal_queries = [
            "Show recent connections",
            "What happened last week?",
            "Find events from 2024",
            "Display today's activities"
        ]
        
        for query in temporal_queries:
            parsed = parser.parse(query)
            assert parsed is not None
            assert any(key in parsed.operation_params for key in ["time_range", "date", "recency"])
    
    def test_query_intent_classification(self, parser):
        """Test accurate intent classification"""
        test_cases = [
            # (query, expected_type)
            ("How are X and Y connected?", QueryType.CONNECTION),
            ("What relates to Z?", QueryType.RELATED),
            ("Show me all people", QueryType.FILTER),
            ("Explain concept A", QueryType.ANALYSIS),
            ("Find path from B to C", QueryType.CONNECTION),
            ("Everything about topic D", QueryType.ANALYSIS),
            ("List organizations", QueryType.FILTER),
            ("Connected items for E", QueryType.RELATED)
        ]
        
        for query, expected_type in test_cases:
            parsed = parser.parse(query)
            assert parsed.query_type == expected_type, f"Failed for query: {query}"
    
    def test_performance_with_long_queries(self, parser):
        """Test parser performance with long queries"""
        long_query = "Show all connections between " + " and ".join([f"Entity{i}" for i in range(20)])
        
        parsed = parser.parse(long_query)
        assert parsed is not None
        assert parsed.query_type == QueryType.CONNECTION
        assert len(parsed.entities) > 10  # Should extract multiple entities
    
    def test_error_recovery(self, parser):
        """Test parser error recovery"""
        malformed_queries = [
            "Show connections between and",  # Missing entities
            "What is related to ?",  # Missing entity
            "Display all",  # Incomplete filter
            ">>><<<",  # Gibberish
        ]
        
        for query in malformed_queries:
            # Should not raise exception
            try:
                parsed = parser.parse(query)
                assert parsed is not None
                # Should have low confidence or be marked as invalid
                assert parsed.confidence < 0.5 or not parsed.valid
            except Exception as e:
                pytest.fail(f"Parser should handle malformed query gracefully: {query}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])