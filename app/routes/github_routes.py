"""
GitHub Routes - Provides repository structure and information.
"""

import logging
import os
from typing import Dict, List, Any
from pathlib import Path

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/github", tags=["GitHub"])


def get_directory_tree(path: Path, prefix: str = "", max_depth: int = 3, current_depth: int = 0) -> List[Dict[str, Any]]:
    """Get directory tree structure"""
    if current_depth >= max_depth:
        return []
    
    items = []
    try:
        # Get all items in directory
        dir_items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
        
        for item in dir_items:
            # Skip hidden files and common ignore patterns
            if item.name.startswith('.') or item.name in ['__pycache__', 'node_modules', '.git', '.venv', 'htmlcov']:
                continue
            
            if item.is_dir():
                # Directory
                dir_data = {
                    "name": item.name,
                    "type": "folder",
                    "path": str(item.relative_to(Path.cwd())),
                    "children": get_directory_tree(item, prefix + "  ", max_depth, current_depth + 1)
                }
                items.append(dir_data)
            else:
                # File
                file_data = {
                    "name": item.name,
                    "type": "file",
                    "path": str(item.relative_to(Path.cwd())),
                    "size": item.stat().st_size,
                    "extension": item.suffix
                }
                items.append(file_data)
                
    except PermissionError:
        logger.warning(f"Permission denied accessing {path}")
    
    return items


@router.get("/tree")
async def get_repository_tree(max_depth: int = 3):
    """Get repository file tree structure"""
    try:
        # Get project root
        root_path = Path.cwd()
        
        # Get tree structure
        tree = {
            "name": root_path.name,
            "type": "folder",
            "path": ".",
            "children": get_directory_tree(root_path, max_depth=max_depth)
        }
        
        return {
            "status": "success",
            "tree": tree,
            "stats": {
                "total_files": sum(1 for _ in root_path.rglob("*") if _.is_file()),
                "total_folders": sum(1 for _ in root_path.rglob("*") if _.is_dir())
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get repository tree: {e}")
        raise HTTPException(status_code=500, detail="Failed to get repository tree")


@router.get("/info")
async def get_repository_info():
    """Get repository information"""
    try:
        # Get git info if available
        git_info = {}
        
        # Try to get current branch
        try:
            with open(".git/HEAD", "r") as f:
                ref = f.read().strip()
                if ref.startswith("ref: refs/heads/"):
                    git_info["branch"] = ref.replace("ref: refs/heads/", "")
        except:
            git_info["branch"] = "unknown"
        
        # Get repository stats
        root_path = Path.cwd()
        
        # Count files by extension
        file_stats = {}
        for file in root_path.rglob("*"):
            if file.is_file() and not any(part.startswith('.') for part in file.parts):
                ext = file.suffix or "no_extension"
                file_stats[ext] = file_stats.get(ext, 0) + 1
        
        # Get top languages
        language_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".html": "HTML",
            ".css": "CSS",
            ".json": "JSON",
            ".md": "Markdown",
            ".yml": "YAML",
            ".yaml": "YAML"
        }
        
        languages = {}
        for ext, count in file_stats.items():
            lang = language_map.get(ext, ext)
            languages[lang] = languages.get(lang, 0) + count
        
        # Sort languages by count
        top_languages = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "status": "success",
            "repository": {
                "name": root_path.name,
                "path": str(root_path),
                "git": git_info
            },
            "statistics": {
                "total_files": sum(file_stats.values()),
                "file_types": len(file_stats),
                "top_languages": [{"language": lang, "files": count} for lang, count in top_languages]
            },
            "structure": {
                "main_directories": [
                    d.name for d in root_path.iterdir() 
                    if d.is_dir() and not d.name.startswith('.')
                ][:10]
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get repository info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get repository info") 