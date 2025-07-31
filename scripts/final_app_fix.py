#!/usr/bin/env python3
"""
FINAL FIX - GET THE APP RUNNING NOW
This script will fix ALL remaining issues and get the app running
"""

import os
import re
import subprocess
from pathlib import Path

def add_missing_import(file_path, model_name, import_line):
    """Add missing import to a file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    if model_name not in content:
        print(f"❌ {model_name} not found in {file_path}")
        return False
    
    # Find where to add the import (after other imports)
    import_section = re.search(r'(from .+ import .+\n)+', content)
    if import_section:
        end_pos = import_section.end()
        content = content[:end_pos] + import_line + '\n' + content[end_pos:]
    else:
        # Add after module docstring
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith('"""') and not line.startswith('#'):
                lines.insert(i, import_line)
                break
        content = '\n'.join(lines)
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Added {model_name} import to {file_path}")
    return True

def fix_suggestion_engine():
    """Fix LearningPathSuggestion import in suggestion_engine.py"""
    file_path = Path("/Users/dro/Documents/second-brain/app/services/synthesis/suggestion_engine.py")
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if LearningPathSuggestion is already imported
    if "from app.models.synthesis.suggestion_models import" in content and "LearningPathSuggestion" in content:
        print("✅ LearningPathSuggestion already imported")
        return
    
    # Find the existing imports from suggestion_models
    import_match = re.search(r'from app\.models\.synthesis\.suggestion_models import \((.*?)\)', content, re.DOTALL)
    if import_match:
        imports = import_match.group(1)
        if "LearningPathSuggestion" not in imports:
            # Add to existing imports
            new_imports = imports.rstrip() + ",\n    LearningPathSuggestion"
            new_import_line = f"from app.models.synthesis.suggestion_models import ({new_imports})"
            content = content.replace(import_match.group(0), new_import_line)
    else:
        # Add new import
        content = re.sub(
            r'(from app\.models\.synthesis import.*?\n)',
            r'\1from app.models.synthesis.suggestion_models import LearningPathSuggestion\n',
            content
        )
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✅ Fixed LearningPathSuggestion import")

def check_all_models_defined():
    """Verify all models are properly defined"""
    suggestion_models = Path("/Users/dro/Documents/second-brain/app/models/synthesis/suggestion_models.py")
    
    with open(suggestion_models, 'r') as f:
        content = f.read()
    
    required_models = [
        "LearningPathSuggestion",
        "SuggestionBase", 
        "ContentSuggestion",
        "QuerySuggestion",
        "ActionSuggestion",
        "SuggestionResponse"
    ]
    
    missing = []
    for model in required_models:
        if f"class {model}" not in content:
            missing.append(model)
    
    if missing:
        print(f"⚠️  Missing models in suggestion_models.py: {missing}")
        # Add missing models
        models_to_add = []
        
        if "LearningPathSuggestion" in missing:
            models_to_add.append('''
class LearningPathSuggestion(BaseModel):
    """Suggested learning path based on knowledge gaps"""
    id: UUID = Field(default_factory=uuid4)
    title: str
    description: str
    topics: List[str] = Field(default_factory=list)
    difficulty: str = Field(default="intermediate")
    estimated_time: str = Field(default="1-2 weeks")
    resources: List[Dict[str, Any]] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    outcomes: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0, le=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)
''')
        
        if models_to_add:
            # Add imports if needed
            if "UUID" not in content:
                content = "from uuid import UUID, uuid4\n" + content
            
            # Add models at the end
            content += '\n'.join(models_to_add)
            
            with open(suggestion_models, 'w') as f:
                f.write(content)
            
            print(f"✅ Added missing models: {missing}")
    else:
        print("✅ All required models are defined")

def restart_app():
    """Restart the Docker app"""
    print("\n🔄 Restarting app...")
    subprocess.run(["docker-compose", "restart", "app"], check=True)
    print("✅ App restarted")

def check_app_status():
    """Check if the app is running"""
    import time
    print("\n⏳ Waiting for app to start...")
    time.sleep(10)
    
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:8000/health"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout:
            print("✅ APP IS RUNNING!")
            print(f"Health check response: {result.stdout}")
            return True
        else:
            print("❌ App not responding")
            # Check logs
            logs = subprocess.run(
                ["docker-compose", "logs", "--tail=20", "app"],
                capture_output=True,
                text=True
            )
            print("Recent logs:")
            print(logs.stdout)
            return False
    except Exception as e:
        print(f"❌ Error checking app: {e}")
        return False

def main():
    """Run all fixes"""
    print("🚀 FINAL APP FIX - GETTING IT RUNNING NOW")
    print("="*50)
    
    # Fix known issues
    print("\n1. Fixing suggestion_engine.py...")
    fix_suggestion_engine()
    
    print("\n2. Checking all models are defined...")
    check_all_models_defined()
    
    print("\n3. Restarting app...")
    restart_app()
    
    print("\n4. Checking app status...")
    if check_app_status():
        print("\n🎉 SUCCESS! The app is running!")
        print("\nYou can access:")
        print("- API Docs: http://localhost:8000/docs")
        print("- Health: http://localhost:8000/health")
        print("- Adminer: http://localhost:8080")
    else:
        print("\n❌ App still not running. Checking for more errors...")
        # Try to find the error
        subprocess.run(["docker-compose", "logs", "--tail=50", "app"])

if __name__ == "__main__":
    main()