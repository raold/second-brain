"""
Google Drive File Processor

Processes different file types from Google Drive and extracts content
for memory creation and embedding generation.
"""

import io
import json
import csv
from typing import Dict, Any, Optional, List
from pathlib import Path
import asyncio
import base64

# Document processing
import PyPDF2
try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

from app.utils.logging_config import get_logger
from app.services.memory_service import MemoryService
from app.docs import MemoryType

logger = get_logger(__name__)


class DriveFileProcessor:
    """
    Processes files streamed from Google Drive.
    
    Extracts text content, generates embeddings, and creates memories.
    Supports multiple file types including documents, images, and data files.
    """
    
    def __init__(self, memory_service: MemoryService):
        """
        Initialize the file processor.
        
        Args:
            memory_service: Service for creating memories
        """
        self.memory_service = memory_service
        
    async def process_file(
        self,
        file_data: Dict[str, Any],
        processing_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a file and create memories from its content.
        
        Args:
            file_data: File data including content and metadata
            processing_options: Optional processing configuration
            
        Returns:
            Processing results including created memories
        """
        file_name = file_data.get('file_name', 'Unknown')
        mime_type = file_data.get('mime_type', '')
        content = file_data.get('content', b'')
        
        # Default processing options
        options = processing_options or {}
        extract_text = options.get('extract_text', True)
        generate_embeddings = options.get('generate_embeddings', True)
        create_memories = options.get('create_memories', True)
        chunk_size = options.get('chunk_size', 1000)  # Characters per memory chunk
        
        logger.info(f"Processing file: {file_name} ({mime_type})")
        
        try:
            # Extract text based on file type
            extracted_text = await self._extract_text(content, mime_type)
            
            if not extracted_text:
                logger.warning(f"No text extracted from {file_name}")
                return {
                    'file_name': file_name,
                    'status': 'no_content',
                    'memories_created': 0
                }
            
            # Create memories if requested
            memories_created = []
            if create_memories:
                # Split text into chunks for memory creation
                chunks = self._split_text(extracted_text, chunk_size)
                
                for i, chunk in enumerate(chunks):
                    # Determine memory type based on content
                    memory_type = self._determine_memory_type(chunk, file_name)
                    
                    # Create memory
                    memory_data = {
                        'content': chunk,
                        'memory_type': memory_type,
                        'metadata': {
                            'source': 'google_drive',
                            'file_name': file_name,
                            'file_id': file_data.get('file_id'),
                            'chunk_index': i,
                            'total_chunks': len(chunks),
                            'mime_type': mime_type,
                            'modified_time': file_data.get('modified_time')
                        },
                        'tags': self._generate_tags(chunk, file_name),
                        'importance_score': self._calculate_importance(chunk, file_name)
                    }
                    
                    # Store memory
                    memory_id = await self.memory_service.store_memory(**memory_data)
                    memories_created.append(memory_id)
                    
                    logger.debug(f"Created memory {memory_id} from chunk {i+1}/{len(chunks)}")
            
            return {
                'file_name': file_name,
                'status': 'success',
                'text_extracted': len(extracted_text),
                'memories_created': len(memories_created),
                'memory_ids': memories_created
            }
            
        except Exception as e:
            logger.error(f"Error processing file {file_name}: {e}")
            return {
                'file_name': file_name,
                'status': 'error',
                'error': str(e)
            }
    
    async def _extract_text(self, content: bytes, mime_type: str) -> str:
        """
        Extract text from file content based on MIME type.
        
        Args:
            content: File content as bytes
            mime_type: MIME type of the file
            
        Returns:
            Extracted text
        """
        # Text files
        if mime_type in ['text/plain', 'text/markdown', 'text/csv']:
            return content.decode('utf-8', errors='ignore')
        
        # JSON files
        elif mime_type == 'application/json':
            try:
                data = json.loads(content.decode('utf-8'))
                return json.dumps(data, indent=2)
            except:
                return content.decode('utf-8', errors='ignore')
        
        # PDF files
        elif mime_type == 'application/pdf':
            return await self._extract_pdf_text(content)
        
        # CSV files (already exported from Google Sheets)
        elif 'csv' in mime_type:
            return await self._extract_csv_text(content)
        
        # Image files
        elif mime_type.startswith('image/'):
            return await self._extract_image_text(content)
        
        # Google Workspace exports (already in text format)
        elif mime_type in ['text/plain', 'text/csv']:
            return content.decode('utf-8', errors='ignore')
        
        else:
            logger.warning(f"Unsupported MIME type for text extraction: {mime_type}")
            return ""
    
    async def _extract_pdf_text(self, content: bytes) -> str:
        """
        Extract text from PDF content.
        
        Args:
            content: PDF file content
            
        Returns:
            Extracted text
        """
        try:
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text_parts = []
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return ""
    
    async def _extract_csv_text(self, content: bytes) -> str:
        """
        Extract and format CSV content.
        
        Args:
            content: CSV file content
            
        Returns:
            Formatted CSV text
        """
        try:
            csv_text = content.decode('utf-8', errors='ignore')
            csv_file = io.StringIO(csv_text)
            reader = csv.DictReader(csv_file)
            
            # Format as readable text
            rows = []
            for row in reader:
                row_text = ", ".join([f"{k}: {v}" for k, v in row.items() if v])
                rows.append(row_text)
            
            return "\n".join(rows)
            
        except Exception as e:
            logger.error(f"Error extracting CSV text: {e}")
            return content.decode('utf-8', errors='ignore')
    
    async def _extract_image_text(self, content: bytes) -> str:
        """
        Extract text from images using OCR.
        
        Args:
            content: Image file content
            
        Returns:
            Extracted text from OCR
        """
        if not OCR_AVAILABLE:
            logger.warning("OCR not available - pytesseract not installed")
            return "[Image file - OCR not available]"
            
        try:
            # Open image
            image = Image.open(io.BytesIO(content))
            
            # Perform OCR
            text = pytesseract.image_to_string(image)
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error extracting image text: {e}")
            return ""
    
    def _split_text(self, text: str, chunk_size: int) -> List[str]:
        """
        Split text into chunks for memory creation.
        
        Args:
            text: Text to split
            chunk_size: Maximum characters per chunk
            
        Returns:
            List of text chunks
        """
        # Clean text
        text = text.strip()
        
        if len(text) <= chunk_size:
            return [text]
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # If paragraph is too long, split by sentences
            if len(paragraph) > chunk_size:
                sentences = paragraph.split('. ')
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) < chunk_size:
                        current_chunk += sentence + ". "
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence + ". "
            else:
                # Add paragraph to current chunk if it fits
                if len(current_chunk) + len(paragraph) < chunk_size:
                    current_chunk += paragraph + "\n\n"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = paragraph + "\n\n"
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _determine_memory_type(self, text: str, file_name: str) -> MemoryType:
        """
        Determine the appropriate memory type for content.
        
        Args:
            text: Content text
            file_name: Source file name
            
        Returns:
            Memory type (semantic, episodic, or procedural)
        """
        text_lower = text.lower()
        file_lower = file_name.lower()
        
        # Check for procedural indicators
        procedural_keywords = [
            'how to', 'step ', 'procedure', 'instructions',
            'tutorial', 'guide', 'setup', 'install', 'configure'
        ]
        if any(keyword in text_lower for keyword in procedural_keywords):
            return MemoryType.PROCEDURAL
        
        # Check for episodic indicators
        episodic_keywords = [
            'meeting', 'discussion', 'talked', 'presented',
            'yesterday', 'today', 'last week', 'notes from'
        ]
        if any(keyword in text_lower for keyword in episodic_keywords):
            return MemoryType.EPISODIC
        
        # Check file name patterns
        if 'readme' in file_lower or 'doc' in file_lower:
            return MemoryType.PROCEDURAL
        elif 'meeting' in file_lower or 'notes' in file_lower:
            return MemoryType.EPISODIC
        
        # Default to semantic for factual content
        return MemoryType.SEMANTIC
    
    def _generate_tags(self, text: str, file_name: str) -> List[str]:
        """
        Generate tags for the content.
        
        Args:
            text: Content text
            file_name: Source file name
            
        Returns:
            List of relevant tags
        """
        tags = ['google_drive']
        
        # Add file type tag
        file_ext = Path(file_name).suffix.lower()
        if file_ext:
            tags.append(file_ext[1:])  # Remove the dot
        
        # Extract key terms (simple keyword extraction)
        keywords = [
            'python', 'javascript', 'api', 'database', 'docker',
            'kubernetes', 'aws', 'cloud', 'ai', 'ml', 'data',
            'security', 'testing', 'deployment', 'architecture'
        ]
        
        text_lower = text.lower()
        for keyword in keywords:
            if keyword in text_lower:
                tags.append(keyword)
        
        # Limit to 10 tags
        return tags[:10]
    
    def _calculate_importance(self, text: str, file_name: str) -> float:
        """
        Calculate importance score for content.
        
        Args:
            text: Content text
            file_name: Source file name
            
        Returns:
            Importance score between 0 and 1
        """
        score = 0.5  # Base score
        
        # Increase for documentation files
        if 'readme' in file_name.lower() or 'important' in file_name.lower():
            score += 0.2
        
        # Increase for procedural content
        if 'how to' in text.lower() or 'instructions' in text.lower():
            score += 0.1
        
        # Increase for recent meeting notes
        if 'meeting' in file_name.lower():
            score += 0.15
        
        # Cap at 1.0
        return min(score, 1.0)