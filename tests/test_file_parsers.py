"""
Unit tests for file parsers
"""

from unittest.mock import MagicMock, patch

import pytest

# Import parsers conditionally to handle missing dependencies
try:
    from app.ingestion.parsers import (
        DocxParser,
        HTMLParser,
        ImageParser,
        MarkdownParser,
        PDFParser,
        SpreadsheetParser,
    )

    HAS_PARSERS = True
except ImportError:
    HAS_PARSERS = False


@pytest.mark.skipif(not HAS_PARSERS, reason="Parser dependencies not installed")
class TestPDFParser:
    """Test PDF parser"""

    @pytest.fixture
    def parser(self):
        """Create PDF parser instance"""
        with patch("app.ingestion.parsers.HAS_PDF", True):
            return PDFParser()

    def test_supports_pdf_types(self, parser):
        """Test PDF mime type support"""
        assert parser.supports("application/pdf")
        assert not parser.supports("text/plain")

    @pytest.mark.asyncio
    async def test_parse_pdf_with_pdfplumber(self, parser, tmp_path):
        """Test parsing PDF with pdfplumber"""
        # Create mock PDF
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"mock pdf content")

        # Mock pdfplumber
        with patch("app.ingestion.parsers.PDF") as MockPDF:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Page 1 content"
            mock_page.extract_tables.return_value = [["A", "B"], ["1", "2"]]
            mock_page.images = []
            mock_pdf.pages = [mock_page]
            MockPDF.open.return_value.__enter__.return_value = mock_pdf

            result = await parser.parse(pdf_path)

            assert "Page 1 content" in result["content"]
            assert result["metadata"]["pages"] == 1
            assert result["metadata"]["has_tables"] is True

    @pytest.mark.asyncio
    async def test_parse_pdf_fallback_pypdf2(self, parser, tmp_path):
        """Test PDF parsing fallback to PyPDF2"""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"mock pdf content")

        # Mock pdfplumber to fail
        with patch("app.ingestion.parsers.PDF") as MockPDF:
            MockPDF.open.side_effect = Exception("pdfplumber failed")

            # Mock PyPDF2
            with patch("app.ingestion.parsers.PyPDF2.PdfReader") as MockReader:
                mock_reader = MagicMock()
                mock_page = MagicMock()
                mock_page.extract_text.return_value = "PyPDF2 content"
                mock_reader.pages = [mock_page]
                MockReader.return_value = mock_reader

                result = await parser.parse(pdf_path)

                assert "PyPDF2 content" in result["content"]
                assert result["metadata"]["pages"] == 1

    def test_table_to_text_conversion(self):
        """Test table to text conversion"""
        table = [["Header 1", "Header 2"], ["Value 1", "Value 2"], ["Value 3", "Value 4"]]

        result = PDFParser._table_to_text(table)

        assert "Header 1" in result
        assert "Value 1" in result
        assert "|" in result  # Table formatting


@pytest.mark.skipif(not HAS_PARSERS, reason="Parser dependencies not installed")
class TestDocxParser:
    """Test DOCX parser"""

    @pytest.fixture
    def parser(self):
        """Create DOCX parser instance"""
        with patch("app.ingestion.parsers.HAS_DOCX", True):
            return DocxParser()

    def test_supports_docx_types(self, parser):
        """Test DOCX mime type support"""
        assert parser.supports(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert parser.supports("application/msword")
        assert not parser.supports("application/pdf")

    @pytest.mark.asyncio
    async def test_parse_docx(self, parser, tmp_path):
        """Test parsing DOCX file"""
        docx_path = tmp_path / "test.docx"
        docx_path.write_bytes(b"mock docx content")

        # Mock python-docx
        with patch("app.ingestion.parsers.Document") as MockDocument:
            mock_doc = MagicMock()

            # Mock paragraphs
            mock_para1 = MagicMock()
            mock_para1.text = "Paragraph 1"
            mock_para1.style.name = "Normal"

            mock_para2 = MagicMock()
            mock_para2.text = "List item"
            mock_para2.style.name = "List Paragraph"

            mock_doc.paragraphs = [mock_para1, mock_para2]

            # Mock tables
            mock_table = MagicMock()
            mock_row = MagicMock()
            mock_cell = MagicMock()
            mock_cell.text = "Cell content"
            mock_row.cells = [mock_cell]
            mock_table.rows = [mock_row]
            mock_doc.tables = [mock_table]

            # Mock relationships
            mock_doc.part.rels.values.return_value = []

            MockDocument.return_value = mock_doc

            result = await parser.parse(docx_path)

            assert "Paragraph 1" in result["content"]
            assert "List item" in result["content"]
            assert "[Table]" in result["content"]
            assert "Cell content" in result["content"]
            assert result["metadata"]["paragraphs"] == 2
            assert result["metadata"]["tables"] == 1
            assert result["metadata"]["lists"] == 1


@pytest.mark.skipif(not HAS_PARSERS, reason="Parser dependencies not installed")
class TestHTMLParser:
    """Test HTML parser"""

    @pytest.fixture
    def parser(self):
        """Create HTML parser instance"""
        with patch("app.ingestion.parsers.HAS_HTML", True):
            return HTMLParser()

    def test_supports_html_types(self, parser):
        """Test HTML mime type support"""
        assert parser.supports("text/html")
        assert parser.supports("application/xhtml+xml")
        assert not parser.supports("text/plain")

    @pytest.mark.asyncio
    async def test_parse_html(self, parser, tmp_path):
        """Test parsing HTML file"""
        html_content = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Header 1</h1>
            <h2>Header 2</h2>
            <p>Paragraph content</p>
            <a href="https://example.com">Link</a>
            <img src="image.jpg" alt="Test image">
        </body>
        </html>
        """

        html_path = tmp_path / "test.html"
        html_path.write_text(html_content)

        result = await parser.parse(html_path)

        # Check content conversion
        assert "Header 1" in result["content"]
        assert "Paragraph content" in result["content"]

        # Check metadata
        assert result["metadata"]["title"] == "Test Page"
        assert len(result["metadata"]["links"]) == 1
        assert result["metadata"]["links"][0]["href"] == "https://example.com"
        assert len(result["metadata"]["images"]) == 1
        assert result["metadata"]["headers"]["h1"] == 1
        assert result["metadata"]["headers"]["h2"] == 1


@pytest.mark.skipif(not HAS_PARSERS, reason="Parser dependencies not installed")
class TestImageParser:
    """Test image parser with OCR"""

    @pytest.fixture
    def parser(self):
        """Create image parser instance"""
        with patch("app.ingestion.parsers.HAS_OCR", True):
            return ImageParser()

    def test_supports_image_types(self, parser):
        """Test image mime type support"""
        assert parser.supports("image/jpeg")
        assert parser.supports("image/png")
        assert parser.supports("image/gif")
        assert not parser.supports("text/plain")

    @pytest.mark.asyncio
    async def test_parse_image_with_text(self, parser, tmp_path):
        """Test parsing image with OCR text"""
        # Create mock image
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"mock image content")

        # Mock PIL and pytesseract
        with (
            patch("app.ingestion.parsers.Image.open") as MockImage,
            patch("app.ingestion.parsers.pytesseract") as MockOCR,
        ):

            mock_img = MagicMock()
            mock_img.format = "JPEG"
            mock_img.size = (800, 600)
            mock_img.mode = "RGB"
            MockImage.return_value = mock_img

            MockOCR.image_to_string.return_value = "Extracted text from image"
            MockOCR.image_to_data.return_value = {"conf": [80, 90, 85, -1, 75]}

            result = await parser.parse(img_path)

            assert result["content"] == "Extracted text from image"
            assert result["metadata"]["format"] == "JPEG"
            assert result["metadata"]["size"] == (800, 600)
            assert result["metadata"]["has_text"] is True
            assert result["metadata"]["ocr_confidence"] == 82.5  # Average of valid scores

    @pytest.mark.asyncio
    async def test_parse_image_no_text(self, parser, tmp_path):
        """Test parsing image without text"""
        img_path = tmp_path / "test.png"
        img_path.write_bytes(b"mock image")

        with (
            patch("app.ingestion.parsers.Image.open") as MockImage,
            patch("app.ingestion.parsers.pytesseract") as MockOCR,
        ):

            mock_img = MagicMock()
            mock_img.format = "PNG"
            MockImage.return_value = mock_img

            MockOCR.image_to_string.return_value = ""

            result = await parser.parse(img_path)

            assert "[Image: test.png - No text detected]" in result["content"]
            assert result["metadata"]["has_text"] is False


@pytest.mark.skipif(not HAS_PARSERS, reason="Parser dependencies not installed")
class TestSpreadsheetParser:
    """Test spreadsheet parser"""

    @pytest.fixture
    def parser(self):
        """Create spreadsheet parser instance"""
        with patch("app.ingestion.parsers.HAS_SPREADSHEET", True):
            return SpreadsheetParser()

    def test_supports_spreadsheet_types(self, parser):
        """Test spreadsheet mime type support"""
        assert parser.supports("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        assert parser.supports("text/csv")
        assert not parser.supports("text/plain")

    @pytest.mark.asyncio
    async def test_parse_csv(self, parser, tmp_path):
        """Test parsing CSV file"""
        csv_content = "Name,Age,City\nJohn,30,NYC\nJane,25,LA"
        csv_path = tmp_path / "test.csv"
        csv_path.write_text(csv_content)

        with patch("app.ingestion.parsers.pd.read_csv") as MockReadCSV:
            mock_df = MagicMock()
            mock_df.__len__.return_value = 2
            mock_df.columns = ["Name", "Age", "City"]
            mock_df.to_string.return_value = csv_content
            MockReadCSV.return_value = mock_df

            result = await parser.parse(csv_path)

            assert "[Sheet1]" in result["content"]
            assert result["metadata"]["sheets"][0]["rows"] == 2
            assert result["metadata"]["sheets"][0]["columns"] == 3
            assert result["metadata"]["total_rows"] == 2

    @pytest.mark.asyncio
    async def test_parse_excel(self, parser, tmp_path):
        """Test parsing Excel file"""
        xlsx_path = tmp_path / "test.xlsx"
        xlsx_path.write_bytes(b"mock excel content")

        with (
            patch("app.ingestion.parsers.pd.ExcelFile") as MockExcel,
            patch("app.ingestion.parsers.pd.read_excel") as MockReadExcel,
        ):

            MockExcel.return_value.sheet_names = ["Sheet1", "Sheet2"]

            # Mock dataframes for each sheet
            mock_df1 = MagicMock()
            mock_df1.__len__.return_value = 10
            mock_df1.columns = ["A", "B"]
            mock_df1.to_string.return_value = "Sheet1 data"

            mock_df2 = MagicMock()
            mock_df2.__len__.return_value = 5
            mock_df2.columns = ["X", "Y", "Z"]
            mock_df2.to_string.return_value = "Sheet2 data"

            MockReadExcel.side_effect = [mock_df1, mock_df2]

            result = await parser.parse(xlsx_path)

            assert "[Sheet: Sheet1]" in result["content"]
            assert "[Sheet: Sheet2]" in result["content"]
            assert len(result["metadata"]["sheets"]) == 2
            assert result["metadata"]["total_rows"] == 15
            assert result["metadata"]["total_columns"] == 3


@pytest.mark.skipif(not HAS_PARSERS, reason="Parser dependencies not installed")
class TestMarkdownParser:
    """Test Markdown parser"""

    @pytest.fixture
    def parser(self):
        """Create Markdown parser instance"""
        return MarkdownParser()

    def test_supports_markdown_types(self, parser):
        """Test Markdown mime type support"""
        assert parser.supports("text/markdown")
        assert parser.supports("text/x-markdown")
        assert parser.supports("text/plain")  # Also handles plain text

    @pytest.mark.asyncio
    async def test_parse_markdown(self, parser, tmp_path):
        """Test parsing Markdown file"""
        md_content = """# Header 1
## Header 2
### Header 3

This is a paragraph with a [link](https://example.com).

![Image](image.png)

```python
code block
```
"""

        md_path = tmp_path / "test.md"
        md_path.write_text(md_content)

        result = await parser.parse(md_path)

        assert result["content"] == md_content
        assert result["metadata"]["headers"]["h1"] == 1
        assert result["metadata"]["headers"]["h2"] == 1
        assert result["metadata"]["headers"]["h3"] == 1
        assert result["metadata"]["links"] == 1
        assert result["metadata"]["images"] == 1
        assert result["metadata"]["code_blocks"] == 1

    @pytest.mark.asyncio
    async def test_parse_markdown_with_frontmatter(self, parser, tmp_path):
        """Test parsing Markdown with YAML frontmatter"""
        md_content = """---
title: Test Document
author: John Doe
tags: [test, markdown]
---

# Main Content

This is the content.
"""

        md_path = tmp_path / "test.md"
        md_path.write_text(md_content)

        with patch("yaml.safe_load") as MockYAML:
            MockYAML.return_value = {
                "title": "Test Document",
                "author": "John Doe",
                "tags": ["test", "markdown"],
            }

            result = await parser.parse(md_path)

            assert "# Main Content" in result["content"]
            assert result["metadata"]["frontmatter"]["title"] == "Test Document"
            assert result["metadata"]["frontmatter"]["author"] == "John Doe"


class TestParserErrors:
    """Test error handling in parsers"""

    @pytest.mark.asyncio
    async def test_parser_import_error(self):
        """Test parser initialization with missing dependencies"""
        with patch("app.ingestion.parsers.HAS_PDF", False):
            with pytest.raises(ImportError, match="PDF parsing libraries not installed"):
                PDFParser()

    @pytest.mark.asyncio
    async def test_parser_file_not_found(self, tmp_path):
        """Test parsing non-existent file"""
        parser = MarkdownParser()

        with pytest.raises(FileNotFoundError):
            await parser.parse(tmp_path / "nonexistent.md")
