import datetime
import os
import re
from pathlib import Path

from app.models import Payload
from app.utils.logger import get_logger

logger = get_logger()

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and invalid characters."""
    # Remove path traversal attempts
    filename = re.sub(r'[./\\]', '_', filename)
    # Remove other potentially dangerous characters
    filename = re.sub(r'[<>:"|?*]', '_', filename)
    # Limit length
    return filename[:100]

def write_markdown(payload: Payload) -> bool:
    """
    Write payload to markdown file.
    
    Args:
        payload: Payload to write
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Validate payload
        if not payload or not payload.id:
            raise ValueError("Invalid payload or missing ID")
        
        # Sanitize filename
        safe_filename = sanitize_filename(payload.id)
        
        # Create directory structure - use relative path for CI compatibility
        data_dir = os.getenv("DATA_DIR", "./data/memories")
        path = Path(data_dir)
        path.mkdir(parents=True, exist_ok=True)
        
        # Create file path
        file = path / f"{safe_filename}.md"
        
        # Prepare content
        title = payload.target.title() if payload.target else 'Note'
        timestamp = datetime.datetime.now().isoformat()
        tags = payload.data.get('tags', [])
        note_content = payload.data.get('note', '')
        
        # Escape markdown content to prevent injection
        note_content = note_content.replace('```', '\\```')
        
        content = f"""# {title} Entry

**ID**: {payload.id}  
**Type**: {payload.type}  
**Timestamp**: {timestamp}  
**Priority**: {payload.priority}  
**Tags**: {', '.join(tags) if tags else 'None'}  

## Note:
{note_content}

## Metadata:
- **Context**: {payload.context}
- **TTL**: {payload.ttl}
- **Intent**: {payload.intent or 'None'}
- **Target**: {payload.target or 'None'}
"""
        
        # Write file
        file.write_text(content, encoding='utf-8')
        
        logger.info(f"Successfully wrote markdown file: {file}")
        return True
        
    except Exception as e:
        logger.exception(f"Failed to write markdown for payload {payload.id if payload else 'unknown'}: {str(e)}")
        return False
