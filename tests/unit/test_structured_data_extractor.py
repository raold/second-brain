"""
Unit tests for StructuredDataExtractor service
Tests comprehensive structured data extraction with pattern matching and AI enhancement
"""

import json
from unittest.mock import MagicMock, patch

import pytest
pytestmark = pytest.mark.unit

from app.services.structured_data_extractor import (
    ExtractedCodeBlock,
    ExtractedEntity,
    ExtractedList,
    ExtractedTable,
    StructuredDataContainer,
    StructuredDataExtractor,
)


class TestStructuredDataExtractor:
    """Test the StructuredDataExtractor service"""

    def setup_method(self):
        """Set up test fixtures"""
        self.extractor = StructuredDataExtractor(use_ai=False)  # Disable AI for unit tests

    def test_extractor_initialization(self):
        """Test extractor initializes correctly"""
        extractor = StructuredDataExtractor()
        assert extractor.config == {}
        assert extractor.min_confidence == 0.5
        assert extractor.extract_entities is True
        assert extractor.extract_relationships is True

    def test_extractor_initialization_with_config(self):
        """Test extractor initialization with custom config"""
        config = {
            "min_confidence": 0.8,
            "extract_entities": False,
            "extract_relationships": False,
            "use_ai": False
        }
        extractor = StructuredDataExtractor(**config)
        assert extractor.min_confidence == 0.8
        assert extractor.extract_entities is False
        assert extractor.extract_relationships is False
        assert extractor.use_ai is False

    def test_extract_key_value_pairs_basic(self):
        """Test extracting basic key-value pairs"""
        content = """
        Name: John Doe
        Age: 30
        Email: john@example.com
        Status: Active
        """
        
        result = self.extractor.extract_structured_data(content)
        
        assert "Name" in result.key_value_pairs
        assert "Age" in result.key_value_pairs
        assert "Email" in result.key_value_pairs
        assert "Status" in result.key_value_pairs
        
        assert result.key_value_pairs["Name"] == "John Doe"
        assert result.key_value_pairs["Age"] == 30
        assert result.key_value_pairs["Email"] == "john@example.com"
        assert result.key_value_pairs["Status"] == "Active"

    def test_extract_key_value_pairs_different_patterns(self):
        """Test extracting key-value pairs with different patterns"""
        content = """
        Name: John Doe
        Age = 30
        Country -> USA
        **Status**: Active
        Temperature is 25.5
        Location means New York
        """
        
        result = self.extractor.extract_structured_data(content)
        
        assert result.key_value_pairs["Name"] == "John Doe"
        assert result.key_value_pairs["Age"] == 30
        assert result.key_value_pairs["Country"] == "USA"
        assert result.key_value_pairs["Status"] == "Active"
        assert result.key_value_pairs["Temperature"] == 25.5

    def test_extract_lists_bullet_points(self):
        """Test extracting bullet point lists"""
        content = """
        Shopping List:
        - Apples
        - Bananas
        - Milk
        - Bread
        
        Another list:
        * Item 1
        * Item 2
        + Item 3
        """
        
        result = self.extractor.extract_structured_data(content)
        
        assert len(result.lists) >= 1
        
        # Find the shopping list
        shopping_list = None
        for lst in result.lists:
            if lst.title == "Shopping List":
                shopping_list = lst
                break
        
        assert shopping_list is not None
        assert shopping_list.list_type == "bullet"
        assert "Apples" in shopping_list.items
        assert "Bananas" in shopping_list.items
        assert "Milk" in shopping_list.items
        assert "Bread" in shopping_list.items

    def test_extract_lists_numbered(self):
        """Test extracting numbered lists"""
        content = """
        Steps:
        1. First step
        2. Second step
        3. Third step
        
        Another format:
        a) Option A
        b) Option B
        c) Option C
        """
        
        result = self.extractor.extract_structured_data(content)
        
        assert len(result.lists) >= 1
        
        # Find numbered list
        numbered_list = None
        for lst in result.lists:
            if lst.title == "Steps":
                numbered_list = lst
                break
        
        assert numbered_list is not None
        assert numbered_list.list_type == "numbered"
        assert "First step" in numbered_list.items
        assert "Second step" in numbered_list.items
        assert "Third step" in numbered_list.items

    def test_extract_markdown_tables(self):
        """Test extracting markdown tables"""
        content = """
        | Name    | Age | City      |
        |---------|-----|-----------|
        | Alice   | 25  | New York  |
        | Bob     | 30  | Boston    |
        | Charlie | 35  | Chicago   |
        """
        
        result = self.extractor.extract_structured_data(content)
        
        assert len(result.tables) == 1
        table = result.tables[0]
        
        assert table.headers == ["Name", "Age", "City"]
        assert len(table.rows) == 3
        assert table.rows[0] == ["Alice", "25", "New York"]
        assert table.rows[1] == ["Bob", "30", "Boston"]
        assert table.rows[2] == ["Charlie", "35", "Chicago"]

    def test_extract_code_blocks_markdown(self):
        """Test extracting markdown code blocks"""
        content = """
        Here's some Python code:
        ```python
        def hello_world():
            print("Hello, World!")
            return True
        
        class MyClass:
            def __init__(self):
                self.value = 42
        ```
        
        And some JavaScript:
        ```javascript
        function greet(name) {
            console.log(`Hello, ${name}!`);
        }
        ```
        """
        
        result = self.extractor.extract_structured_data(content)
        
        assert len(result.code_snippets) == 2
        
        python_block = result.code_snippets[0]
        assert python_block.language == "python"
        assert "def hello_world():" in python_block.code
        assert "hello_world" in python_block.functions
        assert "MyClass" in python_block.classes
        
        js_block = result.code_snippets[1]
        assert js_block.language == "javascript"
        assert "function greet(name)" in js_block.code

    def test_extract_entities_dates(self):
        """Test extracting date entities"""
        content = """
        The meeting is scheduled for 2024-01-15.
        Another important date is January 20, 2024.
        Don't forget about 12/25/2023.
        """
        
        result = self.extractor.extract_structured_data(content)
        
        date_entities = [e for e in result.entities if e.entity_type == "date"]
        assert len(date_entities) >= 2  # At least 2 dates should be found

    def test_extract_entities_emails_urls(self):
        """Test extracting email and URL entities"""
        content = """
        Contact us at support@example.com or visit https://example.com.
        You can also reach john.doe@company.org.
        Check out our blog at http://blog.example.com/posts.
        """
        
        result = self.extractor.extract_structured_data(content)
        
        email_entities = [e for e in result.entities if e.entity_type == "email"]
        url_entities = [e for e in result.entities if e.entity_type == "url"]
        
        assert len(email_entities) >= 2
        assert len(url_entities) >= 2

    def test_extract_entities_phone_money(self):
        """Test extracting phone and money entities"""
        content = """
        Call me at (555) 123-4567 or 555-987-6543.
        The price is $1,299.99 or 500 USD.
        Budget: $50,000.00
        """
        
        result = self.extractor.extract_structured_data(content)
        
        phone_entities = [e for e in result.entities if e.entity_type == "phone"]
        money_entities = [e for e in result.entities if e.entity_type == "money"]
        
        assert len(phone_entities) >= 1
        assert len(money_entities) >= 2

    def test_extract_metadata_statistics(self):
        """Test extracting metadata and statistics"""
        content = """
        This is a sample document with multiple paragraphs.
        
        It contains various types of information including:
        - URLs like https://example.com
        - Email addresses like test@example.com
        - File references like document.pdf and data.csv
        
        This helps test the metadata extraction functionality.
        """
        
        result = self.extractor.extract_structured_data(content)
        
        assert "statistics" in result.metadata_fields
        stats = result.metadata_fields["statistics"]
        
        assert "word_count" in stats
        assert "line_count" in stats
        assert "character_count" in stats
        assert "paragraph_count" in stats
        
        assert stats["word_count"] > 0
        assert stats["line_count"] > 0
        assert stats["character_count"] > 0

    def test_get_extraction_statistics(self):
        """Test getting extraction statistics"""
        content = """
        Name: John Doe
        Age: 30
        
        Tasks:
        - Task 1
        - Task 2
        - Task 3
        
        | Item | Count |
        |------|-------|
        | A    | 10    |
        | B    | 20    |
        
        ```python
        def test():
            pass
        ```
        """
        
        result = self.extractor.extract_structured_data(content)
        stats = self.extractor.get_extraction_statistics(result)
        
        assert "total_structured_elements" in stats
        assert "key_value_pairs" in stats
        assert "lists" in stats
        assert "tables" in stats
        assert "code_snippets" in stats
        assert "entities" in stats
        
        assert stats["key_value_pairs"]["count"] >= 2
        assert stats["lists"]["count"] >= 1
        assert stats["tables"]["count"] >= 1
        assert stats["code_snippets"]["count"] >= 1

    def test_extract_topics_headers(self):
        """Test extracting topics from headers"""
        content = """
        # Introduction
        This is the introduction section.
        
        ## Methods
        This describes the methods used.
        
        ### Data Collection
        Details about data collection.
        
        ## Results
        The results are presented here.
        """
        
        topics = self.extractor.extract_topics(content)
        
        assert len(topics) >= 4
        
        # Check for section topics
        section_topics = [t for t in topics if t["type"] == "section"]
        assert len(section_topics) >= 4
        
        titles = [t["title"] for t in section_topics]
        assert "Introduction" in titles
        assert "Methods" in titles
        assert "Data Collection" in titles
        assert "Results" in titles

    def test_extract_topics_definitions(self):
        """Test extracting definition topics"""
        content = """
        Machine Learning: A method of data analysis that automates analytical model building.
        
        Deep Learning: A subset of machine learning based on artificial neural networks.
        
        Neural Network: A computing system inspired by biological neural networks.
        """
        
        topics = self.extractor.extract_topics(content)
        
        definition_topics = [t for t in topics if t["type"] == "definition"]
        assert len(definition_topics) >= 3
        
        terms = [t["term"] for t in definition_topics]
        assert "Machine Learning" in terms
        assert "Deep Learning" in terms
        assert "Neural Network" in terms

    def test_classify_domain_technical(self):
        """Test domain classification for technical content"""
        content = """
        ```python
        import numpy as np
        
        def algorithm(data):
            return np.mean(data)
        ```
        
        This function implements a statistical algorithm using the NumPy library.
        The API endpoint accepts parameters and returns processed data.
        """
        
        result = self.extractor.classify_domain(content)
        
        assert "domains" in result
        assert "primary_domain" in result
        
        # Should detect technical domain
        domain_names = [d["name"] for d in result["domains"]]
        assert "technical" in domain_names or result["primary_domain"] == "technical"

    def test_classify_domain_business(self):
        """Test domain classification for business content"""
        content = """
        Our quarterly revenue increased by 15% to $2.5 million.
        The ROI on our marketing investment was 300%.
        Key performance indicators show strong growth in customer acquisition.
        Market analysis indicates continued expansion opportunities.
        """
        
        result = self.extractor.classify_domain(content)
        
        assert "domains" in result
        assert "primary_domain" in result
        
        # Should detect business domain
        domain_names = [d["name"] for d in result["domains"]]
        assert "business" in domain_names or result["primary_domain"] == "business"

    def test_classify_domain_academic(self):
        """Test domain classification for academic content"""
        content = """
        Abstract: This study examines the relationship between variables.
        
        Introduction: Previous research has shown [1] that...
        
        Methodology: We conducted a controlled experiment with...
        
        Results: The findings indicate significant correlation (Smith & Jones, 2020).
        
        Discussion: These results support the hypothesis...
        
        References:
        [1] Author, A. (2019). Title of paper. Journal Name.
        """
        
        result = self.extractor.classify_domain(content)
        
        assert "domains" in result
        assert "primary_domain" in result
        
        # Should detect academic domain
        domain_names = [d["name"] for d in result["domains"]]
        assert "academic" in domain_names or result["primary_domain"] == "academic"

    def test_advanced_structured_data_extraction(self):
        """Test advanced extraction with multiple formats"""
        content = """
        # Project Report
        
        **Project Name**: Advanced Data Processing
        **Status**: In Progress
        **Budget**: $50,000
        
        ## Features
        - Data ingestion pipeline
        - Real-time processing
        - Analytics dashboard
        
        ## Technical Stack
        | Component | Technology |
        |-----------|------------|
        | Backend   | Python     |
        | Database  | PostgreSQL |
        | Frontend  | React      |
        
        ```python
        # Core processing function
        def process_data(input_data):
            # Implementation here
            return processed_data
        ```
        
        Contact: admin@project.com
        Deadline: 2024-06-15
        """
        
        result = self.extractor.extract_advanced_structured_data(content)
        
        # Should extract key-value pairs
        assert len(result.key_value_pairs) >= 3
        assert "Project Name" in result.key_value_pairs
        assert "Status" in result.key_value_pairs
        assert "Budget" in result.key_value_pairs
        
        # Should extract lists
        assert len(result.lists) >= 1
        
        # Should extract tables
        assert len(result.tables) >= 1
        
        # Should extract code blocks
        assert len(result.code_snippets) >= 1
        
        # Should extract entities
        email_entities = [e for e in result.entities if e.entity_type == "email"]
        date_entities = [e for e in result.entities if e.entity_type == "date"]
        assert len(email_entities) >= 1
        assert len(date_entities) >= 1


class TestStructuredDataExtractorEdgeCases:
    """Test edge cases and error conditions"""

    def setup_method(self):
        """Set up test fixtures"""
        self.extractor = StructuredDataExtractor(use_ai=False)

    def test_empty_content(self):
        """Test extraction with empty content"""
        result = self.extractor.extract_structured_data("")
        
        assert len(result.key_value_pairs) == 0
        assert len(result.lists) == 0
        assert len(result.tables) == 0
        assert len(result.code_snippets) == 0

    def test_malformed_table(self):
        """Test extraction with malformed table"""
        content = """
        | Name | Age |
        | Alice | 25 | Extra column |
        | Bob |
        """
        
        result = self.extractor.extract_structured_data(content)
        
        # Should handle malformed table gracefully
        # Either extract what it can or skip the table
        assert isinstance(result.tables, list)

    def test_mixed_list_types(self):
        """Test extraction with mixed list types"""
        content = """
        Mixed list:
        - Bullet item
        1. Numbered item
        * Another bullet
        2. Another number
        """
        
        result = self.extractor.extract_structured_data(content)
        
        # Should handle mixed list types
        assert isinstance(result.lists, list)

    def test_very_long_content(self):
        """Test extraction with very long content"""
        # Create content with 10,000 lines
        long_content = "\n".join([f"Line {i}: This is line number {i}" for i in range(10000)])
        
        result = self.extractor.extract_structured_data(long_content)
        
        # Should handle long content without crashing
        assert isinstance(result, StructuredDataContainer)
        assert "statistics" in result.metadata_fields

    def test_unicode_content(self):
        """Test extraction with Unicode characters"""
        content = """
        名前: 田中太郎
        年齢: 30
        
        Список покупок:
        - Хлеб
        - Молоко
        
        العنوان: البيانات المنظمة
        """
        
        result = self.extractor.extract_structured_data(content)
        
        # Should handle Unicode content
        assert isinstance(result, StructuredDataContainer)

    def test_special_characters(self):
        """Test extraction with special characters"""
        content = """
        Key with spaces: Value with "quotes" and 'apostrophes'
        Special chars: !@#$%^&*()_+-=[]{}|;:'"<>?,./
        HTML tags: <script>alert('test')</script>
        """
        
        result = self.extractor.extract_structured_data(content)
        
        # Should handle special characters safely
        assert isinstance(result, StructuredDataContainer)

    def test_nested_structures(self):
        """Test extraction with nested structures"""
        content = """
        ```python
        # Code with nested structures
        data = {
            "users": [
                {"name": "Alice", "age": 25},
                {"name": "Bob", "age": 30}
            ],
            "config": {
                "debug": True,
                "port": 8080
            }
        }
        ```
        """
        
        result = self.extractor.extract_structured_data(content)
        
        # Should extract the code block
        assert len(result.code_snippets) >= 1
        code_block = result.code_snippets[0]
        assert "data = {" in code_block.code

    def test_invalid_regex_patterns(self):
        """Test that invalid regex patterns don't crash the extractor"""
        # This tests internal robustness
        result = self.extractor.extract_structured_data("Normal content with no special patterns")
        assert isinstance(result, StructuredDataContainer)

    def test_memory_usage_with_large_input(self):
        """Test memory usage doesn't explode with large input"""
        import sys
        
        # Create a large content string (1MB)
        large_content = "Sample text. " * (1024 * 1024 // 13)  # ~1MB
        
        # Monitor memory usage (simplified)
        initial_size = sys.getsizeof(large_content)
        
        result = self.extractor.extract_structured_data(large_content)
        
        # Should complete without excessive memory usage
        assert isinstance(result, StructuredDataContainer)
        assert sys.getsizeof(result) < initial_size * 2  # Shouldn't double memory usage


class TestStructuredDataExtractorAI:
    """Test AI enhancement functionality"""

    @patch('app.services.structured_data_extractor.get_openai_client')
    def test_ai_enhancement_enabled(self, mock_openai):
        """Test AI enhancement when enabled"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        extractor = StructuredDataExtractor(use_ai=True)
        assert extractor.use_ai is True
        assert extractor.openai_client == mock_client

    @patch('app.services.structured_data_extractor.get_openai_client')
    def test_ai_enhancement_fails_gracefully(self, mock_openai):
        """Test AI enhancement fails gracefully"""
        mock_openai.side_effect = Exception("OpenAI not available")
        
        extractor = StructuredDataExtractor(use_ai=True)
        assert extractor.use_ai is False  # Should fallback to pattern-based

    def test_extraction_without_ai(self):
        """Test that extraction works without AI"""
        content = """
        Name: Test User
        Email: test@example.com
        
        - Item 1
        - Item 2
        """
        
        extractor = StructuredDataExtractor(use_ai=False)
        result = extractor.extract_structured_data(content)
        
        assert len(result.key_value_pairs) >= 2
        assert len(result.lists) >= 1


class TestDataModels:
    """Test the data model classes"""

    def test_extracted_table_model(self):
        """Test ExtractedTable data model"""
        table = ExtractedTable(
            headers=["Name", "Age"],
            rows=[["Alice", "25"], ["Bob", "30"]],
            caption="User Data",
            table_type="data",
            confidence=0.9
        )
        
        assert table.headers == ["Name", "Age"]
        assert len(table.rows) == 2
        assert table.caption == "User Data"
        assert table.table_type == "data"
        assert table.confidence == 0.9

    def test_extracted_list_model(self):
        """Test ExtractedList data model"""
        list_obj = ExtractedList(
            items=["Item 1", "Item 2", "Item 3"],
            list_type="unordered",
            title="Shopping List"
        )
        
        assert len(list_obj.items) == 3
        assert list_obj.list_type == "unordered"
        assert list_obj.title == "Shopping List"

    def test_extracted_code_block_model(self):
        """Test ExtractedCodeBlock data model"""
        code_block = ExtractedCodeBlock(
            code="def hello():\n    print('Hello')",
            language="python",
            line_count=2,
            description="Simple greeting function",
            functions=["hello"],
            classes=[]
        )
        
        assert "def hello():" in code_block.code
        assert code_block.language == "python"
        assert code_block.line_count == 2
        assert "hello" in code_block.functions
        assert len(code_block.classes) == 0

    def test_extracted_entity_model(self):
        """Test ExtractedEntity data model"""
        entity = ExtractedEntity(
            text="john@example.com",
            entity_type="email",
            context="Contact john@example.com for more info",
            confidence=0.95
        )
        
        assert entity.text == "john@example.com"
        assert entity.entity_type == "email"
        assert "john@example.com" in entity.context
        assert entity.confidence == 0.95

    def test_structured_data_container_model(self):
        """Test StructuredDataContainer data model"""
        container = StructuredDataContainer()
        
        # Test default values
        assert isinstance(container.key_value_pairs, dict)
        assert isinstance(container.lists, list)
        assert isinstance(container.tables, list)
        assert isinstance(container.code_snippets, list)
        assert isinstance(container.metadata_fields, dict)
        assert isinstance(container.entities, list)
        assert isinstance(container.relationships, list)
        
        # Test adding data
        container.key_value_pairs["test"] = "value"
        container.lists.append(ExtractedList(items=["test"], list_type="bullet"))
        
        assert container.key_value_pairs["test"] == "value"
        assert len(container.lists) == 1