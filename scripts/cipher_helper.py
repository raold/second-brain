#!/usr/bin/env python3
"""
Cipher Helper - Simple commands to use Cipher effectively
"""

import sys
import subprocess
import json
from datetime import datetime
import argparse

def run_cipher_command(cmd_parts):
    """Run a cipher command and return output"""
    try:
        result = subprocess.run(
            ["cipher"] + cmd_parts,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return f"Error: {e}"

def add_memory(content, tags=None):
    """Add a memory to Cipher"""
    # For now, we'll store it in a local file since Cipher CLI is interactive
    memories_file = "/Users/dro/.cipher/memories_local.json"
    
    try:
        # Load existing memories
        try:
            with open(memories_file, 'r') as f:
                memories = json.load(f)
        except:
            memories = []
        
        # Add new memory
        memory = {
            "id": f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "content": content,
            "tags": tags.split(',') if tags else [],
            "created": datetime.now().isoformat(),
            "source": "manual"
        }
        memories.append(memory)
        
        # Save memories
        with open(memories_file, 'w') as f:
            json.dump(memories, f, indent=2)
        
        print(f"✅ Memory added: {memory['id']}")
        return memory['id']
        
    except Exception as e:
        print(f"❌ Failed to add memory: {e}")
        return None

def search_memories(query):
    """Search memories"""
    memories_file = "/Users/dro/.cipher/memories_local.json"
    
    try:
        with open(memories_file, 'r') as f:
            memories = json.load(f)
        
        # Simple text search
        results = []
        query_lower = query.lower()
        for memory in memories:
            if query_lower in memory['content'].lower():
                results.append(memory)
        
        if results:
            print(f"\n📝 Found {len(results)} memories:\n")
            for mem in results:
                print(f"[{mem['created'][:10]}] {mem['content'][:100]}...")
                if mem.get('tags'):
                    print(f"  Tags: {', '.join(mem['tags'])}")
                print()
        else:
            print(f"No memories found for '{query}'")
            
    except FileNotFoundError:
        print("No memories stored yet. Add some first!")
    except Exception as e:
        print(f"Error searching: {e}")

def list_recent_memories(limit=10):
    """List recent memories"""
    memories_file = "/Users/dro/.cipher/memories_local.json"
    
    try:
        with open(memories_file, 'r') as f:
            memories = json.load(f)
        
        # Sort by date and get recent
        memories.sort(key=lambda x: x['created'], reverse=True)
        recent = memories[:limit]
        
        print(f"\n📚 Recent {len(recent)} memories:\n")
        for mem in recent:
            print(f"[{mem['created'][:16]}]")
            print(f"  {mem['content'][:150]}")
            if mem.get('tags'):
                print(f"  🏷️  {', '.join(mem['tags'])}")
            print()
            
    except FileNotFoundError:
        print("No memories stored yet. Add some first!")
    except Exception as e:
        print(f"Error listing: {e}")

def export_memories(format='json'):
    """Export all memories"""
    memories_file = "/Users/dro/.cipher/memories_local.json"
    
    try:
        with open(memories_file, 'r') as f:
            memories = json.load(f)
        
        if format == 'json':
            print(json.dumps(memories, indent=2))
        elif format == 'markdown':
            print("# Cipher Memories\n")
            for mem in memories:
                print(f"## {mem['created'][:10]}")
                print(f"\n{mem['content']}\n")
                if mem.get('tags'):
                    print(f"**Tags:** {', '.join(mem['tags'])}\n")
                print("---\n")
        
    except FileNotFoundError:
        print("No memories stored yet.")
    except Exception as e:
        print(f"Error exporting: {e}")

def main():
    parser = argparse.ArgumentParser(description='Cipher Memory Helper')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Add memory command
    add_parser = subparsers.add_parser('add', help='Add a memory')
    add_parser.add_argument('content', help='Memory content')
    add_parser.add_argument('--tags', help='Comma-separated tags')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search memories')
    search_parser.add_argument('query', help='Search query')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List recent memories')
    list_parser.add_argument('--limit', type=int, default=10, help='Number of memories')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export memories')
    export_parser.add_argument('--format', choices=['json', 'markdown'], default='json')
    
    args = parser.parse_args()
    
    if args.command == 'add':
        add_memory(args.content, args.tags)
    elif args.command == 'search':
        search_memories(args.query)
    elif args.command == 'list':
        list_recent_memories(args.limit)
    elif args.command == 'export':
        export_memories(args.format)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()