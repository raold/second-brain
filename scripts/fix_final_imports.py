#!/usr/bin/env python3
"""
Final comprehensive fix for all remaining import issues.
"""

import re
from pathlib import Path

def fix_dependencies_imports():
    """Fix import issues in dependencies.py."""
    file_path = Path("app/core/dependencies.py")
    content = file_path.read_text(encoding='utf-8')
    
    # Remove redundant imports from line 3-4 since we redefine the functions
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        if line == "from app.database import get_database":
            new_lines.append("# " + line + " # Commented - redefined below")
        elif line == "from app.services.service_factory import get_health_service, get_memory_service, get_session_service":
            new_lines.append("# " + line + " # Commented - redefined below")
        else:
            new_lines.append(line)
    
    file_path.write_text('\n'.join(new_lines), encoding='utf-8')
    print(f"✓ Fixed {file_path}")

def fix_monitoring_imports():
    """Fix MetricsCollector redefinition."""
    file_path = Path("app/core/monitoring.py")
    content = file_path.read_text(encoding='utf-8')
    
    # Remove import of MetricsCollector since we define it here
    content = content.replace(
        "from app.services.monitoring.metrics_collector import MetricsCollector",
        "# from app.services.monitoring.metrics_collector import MetricsCollector  # Defined in this file"
    )
    
    file_path.write_text(content, encoding='utf-8')
    print(f"✓ Fixed {file_path}")

def fix_security_audit_imports():
    """Fix duplicate get_logger import."""
    file_path = Path("app/core/security_audit.py")
    content = file_path.read_text(encoding='utf-8')
    
    # Remove duplicate get_logger from line 17
    content = content.replace(
        "from app.core.logging import get_audit_logger, get_logger",
        "from app.core.logging import get_audit_logger"
    )
    
    file_path.write_text(content, encoding='utf-8')
    print(f"✓ Fixed {file_path}")

def fix_dependencies_file():
    """Fix app/dependencies.py."""
    file_path = Path("app/dependencies.py")
    if file_path.exists():
        content = file_path.read_text(encoding='utf-8')
        
        # Remove duplicate get_database import
        lines = content.split('\n')
        new_lines = []
        
        for line in lines:
            if "from app.database import get_database" in line and new_lines and "def get_database" in '\n'.join(new_lines[-5:]):
                new_lines.append("# " + line + " # Commented - redefined below")
            else:
                new_lines.append(line)
        
        file_path.write_text('\n'.join(new_lines), encoding='utf-8')
        print(f"✓ Fixed {file_path}")

def fix_docs_file():
    """Fix app/docs.py MemoryType redefinition."""
    file_path = Path("app/docs.py")
    if file_path.exists():
        content = file_path.read_text(encoding='utf-8')
        
        # Remove duplicate MemoryType class
        lines = content.split('\n')
        new_lines = []
        skip_class = False
        memory_type_count = 0
        
        for line in lines:
            if line.strip().startswith("class MemoryType"):
                memory_type_count += 1
                if memory_type_count > 1:
                    skip_class = True
                    continue
            
            if skip_class and line and not line[0].isspace():
                skip_class = False
                
            if not skip_class:
                new_lines.append(line)
        
        file_path.write_text('\n'.join(new_lines), encoding='utf-8')
        print(f"✓ Fixed {file_path}")

def fix_events_init():
    """Fix app/events/__init__.py."""
    file_path = Path("app/events/__init__.py")
    if file_path.exists():
        content = file_path.read_text(encoding='utf-8')
        
        # Remove duplicate event imports
        lines = content.split('\n')
        new_lines = []
        seen_imports = set()
        
        for line in lines:
            if "import" in line and "Event" in line:
                # Extract event name
                match = re.search(r'import\s+(\w+Event)', line)
                if match:
                    event_name = match.group(1)
                    if event_name in seen_imports:
                        new_lines.append("# " + line + " # Duplicate removed")
                        continue
                    seen_imports.add(event_name)
            new_lines.append(line)
        
        file_path.write_text('\n'.join(new_lines), encoding='utf-8')
        print(f"✓ Fixed {file_path}")

def fix_advanced_extractors():
    """Fix undefined names in advanced extractors."""
    # Fix advanced_structured_extractor.py
    file_path = Path("app/ingestion/advanced_structured_extractor.py")
    if file_path.exists():
        content = file_path.read_text(encoding='utf-8')
        
        # Add missing imports and definitions
        if "PANDAS_AVAILABLE = False" not in content:
            # Add after imports
            insert_after = "from app.utils.logging_config import get_logger"
            content = content.replace(insert_after, insert_after + """

# Optional dependencies
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

try:
    import xml.etree.ElementTree as ET
except ImportError:
    ET = None""")
        
        # Remove duplicate StructuredData import
        content = content.replace(
            "from app.models.intelligence.analytics_models import StructuredData",
            "# from app.models.intelligence.analytics_models import StructuredData  # Already imported"
        )
        
        file_path.write_text(content, encoding='utf-8')
        print(f"✓ Fixed {file_path}")
    
    # Fix advanced_topic_modeling.py
    file_path = Path("app/ingestion/advanced_topic_modeling.py")
    if file_path.exists():
        content = file_path.read_text(encoding='utf-8')
        
        # Add missing imports and flags
        if "BERTOPIC_AVAILABLE = False" not in content:
            insert_after = "from app.utils.logging_config import get_logger"
            content = content.replace(insert_after, insert_after + """

# Optional dependencies
try:
    from bertopic import BERTopic
    BERTOPIC_AVAILABLE = True
except ImportError:
    BERTOPIC_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import LatentDirichletAllocation
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

# Import TopicClassifier if available
try:
    from app.ingestion.topic_classifier import TopicClassifier
except ImportError:
    TopicClassifier = None""")
        
        file_path.write_text(content, encoding='utf-8')
        print(f"✓ Fixed {file_path}")

def main():
    """Fix all remaining import issues."""
    fix_dependencies_imports()
    fix_monitoring_imports()
    fix_security_audit_imports()
    fix_dependencies_file()
    fix_docs_file()
    fix_events_init()
    fix_advanced_extractors()
    
    print("\nFixed all remaining import issues")

if __name__ == "__main__":
    main()