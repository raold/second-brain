#!/usr/bin/env python3
"""
Centralized Context Cache Service
Provides shared context caching for all agents to prevent redundant file reads
"""

import hashlib
import json
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


class ContextCacheService:
    """Singleton service for context caching across agents"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.base_path = Path("/Users/dro/Documents/second-brain")
        self.cache_dir = self.base_path / ".claude" / "cache"
        self.cache_dir.mkdir(exist_ok=True)

        # In-memory cache
        self.cache = {}

        # Cache configuration
        self.cache_config = {
            "CLAUDE.md": {
                "ttl_seconds": 3600,      # 1 hour
                "sections": {
                    "principles": "FOUNDATIONAL DEVELOPMENT PRINCIPLES",
                    "architecture": "ARCHITECTURAL DESIGN PRINCIPLES",
                    "docker": "Docker-First Architecture"
                }
            },
            "TODO.md": {
                "ttl_seconds": 300,       # 5 minutes
                "sections": {
                    "critical": "Critical Issues",
                    "health": "Project Health Status",
                    "blockers": "Current Blockers"
                }
            },
            "DEVELOPMENT_CONTEXT.md": {
                "ttl_seconds": 60,        # 1 minute
                "sections": {
                    "recent": "Recent Decisions",
                    "focus": "Current Focus",
                    "session": "Session Notes"
                }
            }
        }

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("ContextCache")

        self._initialized = True

    def get_context(self, filename: str, force_refresh: bool = False) -> dict[str, Any] | None:
        """Get cached context for a file"""
        # Check if cache is valid
        if not force_refresh and self._is_cache_valid(filename):
            self.logger.info(f"Cache hit for {filename}")
            return self.cache[filename]

        # Load from file
        self.logger.info(f"Cache miss for {filename} - loading from disk")
        return self._load_and_cache(filename)

    def get_section(self, filename: str, section_name: str) -> str | None:
        """Get a specific section from cached context"""
        context = self.get_context(filename)
        if not context:
            return None

        sections = context.get("sections", {})
        return sections.get(section_name)

    def get_agent_context(self, agent_name: str) -> dict[str, Any]:
        """Get filtered context for a specific agent"""
        agent_context = {
            "project": "second-brain",
            "timestamp": datetime.now().isoformat()
        }

        # Agent-specific context mapping
        context_map = {
            "technical-debt-tracker": {
                "files": ["TODO.md"],
                "sections": ["critical", "blockers"]
            },
            "architecture-analyzer": {
                "files": ["CLAUDE.md"],
                "sections": ["architecture", "docker"]
            },
            "context-aware-orchestrator": {
                "files": ["TODO.md", "CLAUDE.md", "DEVELOPMENT_CONTEXT.md"],
                "sections": ["all"]
            }
        }

        # Get agent-specific requirements
        agent_config = context_map.get(agent_name, {
            "files": ["CLAUDE.md"],
            "sections": ["principles"]
        })

        # Build filtered context
        for filename in agent_config["files"]:
            file_context = self.get_context(filename)
            if file_context:
                if "all" in agent_config["sections"]:
                    agent_context[filename] = file_context["content"]
                else:
                    sections = {}
                    for section in agent_config["sections"]:
                        section_content = file_context.get("sections", {}).get(section)
                        if section_content:
                            sections[section] = section_content
                    if sections:
                        agent_context[filename] = sections

        return agent_context

    def invalidate_cache(self, filename: str | None = None):
        """Invalidate cache for a file or all files"""
        if filename:
            if filename in self.cache:
                del self.cache[filename]
                self.logger.info(f"Invalidated cache for {filename}")
        else:
            self.cache.clear()
            self.logger.info("Invalidated all cache entries")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics"""
        stats = {
            "entries": len(self.cache),
            "total_size_kb": 0,
            "files": {}
        }

        for filename, entry in self.cache.items():
            size_kb = len(entry.get("content", "")) / 1024
            stats["total_size_kb"] += size_kb
            stats["files"][filename] = {
                "size_kb": round(size_kb, 2),
                "age_seconds": (datetime.now() - entry["loaded_at"]).total_seconds(),
                "hash": entry.get("hash", "")[:8]
            }

        return stats

    def _is_cache_valid(self, filename: str) -> bool:
        """Check if cache entry is valid"""
        if filename not in self.cache:
            return False

        entry = self.cache[filename]
        config = self.cache_config.get(filename, {})
        ttl_seconds = config.get("ttl_seconds", 300)

        # Check TTL
        age = datetime.now() - entry["loaded_at"]
        if age > timedelta(seconds=ttl_seconds):
            return False

        # Check file hash
        filepath = self.base_path / filename
        if filepath.exists():
            current_hash = self._get_file_hash(filepath)
            if current_hash != entry.get("hash"):
                return False

        return True

    def _load_and_cache(self, filename: str) -> dict[str, Any] | None:
        """Load file and cache its content"""
        filepath = self.base_path / filename
        if not filepath.exists():
            self.logger.warning(f"File not found: {filepath}")
            return None

        try:
            content = filepath.read_text()
            file_hash = self._get_file_hash(filepath)

            # Create cache entry
            entry = {
                "content": content,
                "hash": file_hash,
                "loaded_at": datetime.now(),
                "size": len(content),
                "sections": {}
            }

            # Extract sections if configured
            config = self.cache_config.get(filename, {})
            sections_config = config.get("sections", {})

            for section_name, section_header in sections_config.items():
                section_content = self._extract_section(content, section_header)
                if section_content:
                    entry["sections"][section_name] = section_content

            # Cache the entry
            self.cache[filename] = entry

            # Persist to disk cache
            self._persist_cache_entry(filename, entry)

            return entry

        except Exception as e:
            self.logger.error(f"Failed to load {filename}: {e}")
            return None

    def _get_file_hash(self, filepath: Path) -> str:
        """Get hash of file content"""
        content = filepath.read_bytes()
        return hashlib.md5(content).hexdigest()

    def _extract_section(self, content: str, section_header: str) -> str | None:
        """Extract a section from content"""
        lines = content.split('\n')
        section_lines = []
        in_section = False

        for line in lines:
            if section_header in line:
                in_section = True
                continue

            if in_section:
                # Stop at next header (starts with #)
                if line.strip().startswith('#') and line.strip() != '#':
                    break
                section_lines.append(line)

        return '\n'.join(section_lines).strip() if section_lines else None

    def _persist_cache_entry(self, filename: str, entry: dict[str, Any]):
        """Persist cache entry to disk"""
        cache_file = self.cache_dir / f"{filename}.cache.json"

        # Create serializable version
        serializable = {
            "content": entry["content"][:1000],  # Store preview only
            "hash": entry["hash"],
            "loaded_at": entry["loaded_at"].isoformat(),
            "size": entry["size"],
            "sections": entry["sections"]
        }

        try:
            with open(cache_file, 'w') as f:
                json.dump(serializable, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to persist cache for {filename}: {e}")


# Global instance getter
def get_context_cache() -> ContextCacheService:
    """Get the global context cache instance"""
    return ContextCacheService()


# Agent helper functions
def get_agent_context(agent_name: str) -> dict[str, Any]:
    """Convenience function for agents to get their context"""
    cache = get_context_cache()
    return cache.get_agent_context(agent_name)


def invalidate_context(filename: str | None = None):
    """Convenience function to invalidate context cache"""
    cache = get_context_cache()
    cache.invalidate_cache(filename)


# CLI interface
if __name__ == "__main__":
    import sys

    cache = get_context_cache()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "stats":
            stats = cache.get_cache_stats()
            print(json.dumps(stats, indent=2))

        elif command == "get" and len(sys.argv) > 2:
            filename = sys.argv[2]
            context = cache.get_context(filename)
            if context:
                print(f"Cached content for {filename}:")
                print(f"Size: {context['size']} bytes")
                print(f"Sections: {list(context.get('sections', {}).keys())}")
            else:
                print(f"No cache entry for {filename}")

        elif command == "invalidate":
            filename = sys.argv[2] if len(sys.argv) > 2 else None
            cache.invalidate_cache(filename)
            print(f"Invalidated cache for: {filename or 'all files'}")

        elif command == "agent" and len(sys.argv) > 2:
            agent_name = sys.argv[2]
            context = cache.get_agent_context(agent_name)
            print(f"Context for {agent_name}:")
            print(json.dumps(context, indent=2, default=str))

        else:
            print("Usage:")
            print("  python context-cache.py stats")
            print("  python context-cache.py get <filename>")
            print("  python context-cache.py invalidate [filename]")
            print("  python context-cache.py agent <agent_name>")
    else:
        print("Context Cache Service")
        print("Use 'python context-cache.py stats' to see cache statistics")
