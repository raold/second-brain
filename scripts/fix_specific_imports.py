#!/usr/bin/env python3
"""
Fix specific undefined names found in the codebase.
"""

import os
from pathlib import Path

# Specific fixes for each file
FILE_FIXES = {
    "app/events/event_handlers.py": [
        ("# Add missing event import", 
         "from app.events.domain_events import ImportanceUpdatedEvent")
    ],
    "app/ingestion/advanced_structured_extractor.py": [
        ("# Add availability flags",
         """# Check library availability
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

import xml.etree.ElementTree as ET""")
    ],
    "app/ingestion/advanced_topic_modeling.py": [
        ("# Add availability flags and imports",
         """# Check library availability
try:
    from bertopic import BERTopic
    BERTOPIC_AVAILABLE = True
except ImportError:
    BERTOPIC_AVAILABLE = False

try:
    from sklearn.cluster import AgglomerativeClustering
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from app.ingestion.models import Topic
from app.ingestion.topic_classifier import TopicClassifier""")
    ],
    "app/ingestion/content_classifier.py": [
        ("# Add missing imports",
         """from app.ingestion.models import ProcessedContent, ContentQuality, IntentType""")
    ],
    "app/ingestion/core_extraction_pipeline.py": [
        ("# Add missing imports",
         """from app.ingestion.models import ExtractedData, ProcessingResult
from app.services.monitoring.metrics_collector import MetricsCollector""")
    ],
    "app/ingestion/domain_classifier.py": [
        ("# Add missing imports",
         """from app.ingestion.models import Domain, DomainClassification""")
    ],
    "app/ingestion/embedding_generator.py": [
        ("# Add tiktoken import",
         """try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    tiktoken = None""")
    ],
    "app/ingestion/entity_extractor.py": [
        ("# Add missing imports",
         """from app.ingestion.models import Entity, EntityType
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    spacy = None""")
    ],
    "app/ingestion/intent_recognizer.py": [
        ("# Add missing imports",
         """from app.ingestion.models import Intent, IntentType""")
    ],
    "app/ingestion/multimedia_parsers.py": [
        ("# Add missing imports",
         """try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    AudioSegment = None

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    sr = None

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    Image = None
    pytesseract = None

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None""")
    ],
    "app/ingestion/parsers.py": [
        ("# Add missing imports",
         """import aiofiles
from bs4 import BeautifulSoup
import markdown
import PyPDF2
from docx import Document
import pandas as pd""")
    ],
    "app/ingestion/relationship_detector.py": [
        ("# Add missing imports",
         """from app.ingestion.models import Relationship, RelationshipType, Entity""")
    ],
    "app/ingestion/topic_classifier.py": [
        ("# Add missing imports",
         """from app.ingestion.models import Topic, TopicClassification""")
    ],
    "app/visualization/relationship_graph.py": [
        ("# Add NetworkX availability check at the top",
         """# Check library availability
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None

try:
    from sklearn.cluster import SpectralClustering
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    SpectralClustering = None

try:
    import matplotlib.pyplot as plt
    from matplotlib import cm
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    cm = None

import math
from app.ingestion.models import Entity, Relationship""")
    ],
    "app/services/synthesis/consolidation_engine.py": [
        ("# Add missing imports", 
         """from app.events.domain_events import MemoryConsolidatedEvent, ConsolidationEvent""")
    ],
    "app/services/synthesis/websocket_service.py": [
        ("# Add missing imports",
         """from app.events.domain_events import SystemHealthEvent""")
    ],
    "app/services/memory_deduplication_engine.py": [
        ("# Add missing imports",
         """from app.events.domain_events import DuplicatesDetectedEvent""")
    ],
    "app/services/knowledge_graph_builder.py": [
        ("# Add NetworkX import",
         """try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None""")
    ],
    "app/services/reasoning_engine.py": [
        ("# Add NetworkX import", 
         """try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None""")
    ],
}

def fix_imports_in_file(file_path: str, fixes: list) -> bool:
    """Apply specific import fixes to a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        for comment, import_block in fixes:
            # Check if the imports are already there
            if any(line in content for line in import_block.split('\n') if line.strip() and not line.startswith('#')):
                continue
            
            # Find where to insert the imports
            lines = content.split('\n')
            insert_pos = 0
            
            # Find the end of existing imports
            for i, line in enumerate(lines):
                if line.strip().startswith(('import ', 'from ')):
                    insert_pos = i + 1
                elif line.strip() and not line.strip().startswith('#') and insert_pos > 0:
                    break
            
            # Insert the new imports
            import_lines = import_block.split('\n')
            for j, import_line in enumerate(import_lines):
                lines.insert(insert_pos + j, import_line)
            
            # Add blank line after imports if needed
            if insert_pos + len(import_lines) < len(lines):
                if lines[insert_pos + len(import_lines)].strip() and not lines[insert_pos + len(import_lines) - 1].strip():
                    pass
                else:
                    lines.insert(insert_pos + len(import_lines), '')
            
            content = '\n'.join(lines)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Main function to apply specific fixes."""
    project_root = Path(__file__).parent.parent
    fixed_count = 0
    
    print("🔧 Applying specific import fixes...")
    
    for file_path, fixes in FILE_FIXES.items():
        full_path = project_root / file_path
        if full_path.exists():
            if fix_imports_in_file(full_path, fixes):
                print(f"Fixed imports in {file_path}")
                fixed_count += 1
        else:
            print(f"Warning: {file_path} not found")
    
    print(f"\n✅ Fixed {fixed_count} files")

if __name__ == "__main__":
    main()