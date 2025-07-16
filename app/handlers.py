import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.models import Payload
from app.storage.markdown_writer import write_markdown
from app.storage.qdrant_client import qdrant_upsert
from app.storage.shell_runner import run_shell_command
from app.utils.logger import get_logger

logger = get_logger()

def _write_to_markdown_file(filename: str, content: str, data_dir: str = None) -> bool:
    """
    Shared utility to write content to a markdown file.
    
    Args:
        filename: Name of the markdown file (e.g., "tasks.md")
        content: Content to append to the file
        data_dir: Optional data directory path
        
    Returns:
        True if successful, False otherwise
    """
    try:
        import os
        data_dir = data_dir or os.getenv("DATA_DIR", "./data")
        path = Path(data_dir) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with path.open("a", encoding="utf-8") as f:
            f.write(content)
        
        return True
    except Exception as e:
        logger.exception(f"Failed to write to {filename}: {str(e)}")
        return False

def dispatch_payload(payload: Payload) -> Optional[Dict[str, Any]]:
    """
    Dispatch payload to appropriate handler based on intent.
    
    Args:
        payload: Payload to dispatch
        
    Returns:
        Result dictionary or None if failed
    """
    try:
        logger.info(f"Dispatching {payload.type}:{payload.intent} to {payload.target}")
        
        if payload.intent == "store":
            return handle_store(payload)
        elif payload.intent == "execute":
            return handle_execute(payload)
        else:
            logger.warning(f"Unknown intent: {payload.intent}")
            return {"status": "error", "message": f"Unknown intent: {payload.intent}"}
            
    except Exception as e:
        logger.exception(f"Failed to dispatch payload {payload.id}: {str(e)}")
        return {"status": "error", "message": str(e)}

def handle_store(payload: Payload) -> Optional[Dict[str, Any]]:
    """
    Handle store intent for different target types.
    
    Args:
        payload: Payload to store
        
    Returns:
        Result dictionary or None if failed
    """
    try:
        target = payload.target
        
        if target in ("note", "memory"):
            # Store in both markdown and vector database
            markdown_success = write_markdown(payload)
            vector_success = qdrant_upsert(payload.model_dump())
            
            if markdown_success and vector_success:
                logger.info(f"Successfully stored {target}: {payload.id}")
                return {"status": "success", "type": target, "id": payload.id}
            else:
                logger.error(f"Failed to store {target}: {payload.id}")
                return {"status": "error", "message": "Storage failed"}
                
        elif target == "task":
            return store_task(payload)
        elif target == "bookmark":
            return store_bookmark(payload)
        elif target == "person":
            return store_contact(payload)
        else:
            logger.warning(f"Unknown store target: {target}")
            return {"status": "error", "message": f"Unknown target: {target}"}
            
    except Exception as e:
        logger.exception(f"Failed to handle store for payload {payload.id}: {str(e)}")
        return {"status": "error", "message": str(e)}

def handle_execute(payload: Payload) -> Optional[Dict[str, Any]]:
    """
    Handle execute intent for shell commands.
    
    Args:
        payload: Payload containing command to execute
        
    Returns:
        Result dictionary or None if failed
    """
    try:
        command = payload.data.get("command")
        if not command:
            logger.error("Missing command in execute payload")
            return {"status": "error", "message": "Missing command"}
        
        result = run_shell_command(command)
        if result:
            logger.info(f"Command executed successfully: {command}")
            return {
                "status": "success",
                "command": command,
                "returncode": result["returncode"],
                "stdout": result["stdout"],
                "stderr": result["stderr"]
            }
        else:
            logger.error(f"Command execution failed: {command}")
            return {"status": "error", "message": "Command execution failed"}
            
    except Exception as e:
        logger.exception(f"Failed to handle execute for payload {payload.id}: {str(e)}")
        return {"status": "error", "message": str(e)}

def store_task(payload: Payload) -> Optional[Dict[str, Any]]:
    """
    Store task in markdown file.
    
    Args:
        payload: Payload containing task data
        
    Returns:
        Result dictionary or None if failed
    """
    try:
        note = payload.data.get("note", "").strip()
        if not note:
            logger.error("Task payload missing note content")
            return {"status": "error", "message": "Missing task content"}
        
        timestamp = payload.data.get("timestamp", datetime.datetime.now().isoformat())
        task_line = f"- [ ] {note}  \n  – created: {timestamp}\n"

        success = _write_to_markdown_file("tasks.md", task_line)
        if success:
            logger.info(f"Task stored: {note}")
            return {"status": "success", "type": "task", "content": note}
        else:
            return {"status": "error", "message": "Failed to write task file"}
        
    except Exception as e:
        logger.exception(f"Failed to store task for payload {payload.id}: {str(e)}")
        return {"status": "error", "message": str(e)}

def store_bookmark(payload: Payload) -> Optional[Dict[str, Any]]:
    """
    Store bookmark in markdown file.
    
    Args:
        payload: Payload containing bookmark data
        
    Returns:
        Result dictionary or None if failed
    """
    try:
        note = payload.data.get("note", "").strip()
        url = payload.data.get("url", "").strip()
        
        if not note or not url:
            logger.error("Bookmark payload missing note or URL")
            return {"status": "error", "message": "Missing note or URL"}
        
        timestamp = payload.data.get("timestamp", datetime.datetime.now().isoformat())
        entry = f"- [{note}]({url})  \n  – saved: {timestamp}\n"

        success = _write_to_markdown_file("bookmarks.md", entry)
        if success:
            logger.info(f"Bookmark stored: {note} => {url}")
            return {"status": "success", "type": "bookmark", "note": note, "url": url}
        else:
            return {"status": "error", "message": "Failed to write bookmark file"}
        
    except Exception as e:
        logger.exception(f"Failed to store bookmark for payload {payload.id}: {str(e)}")
        return {"status": "error", "message": str(e)}

def store_contact(payload: Payload) -> Optional[Dict[str, Any]]:
    """
    Store contact information.
    
    Args:
        payload: Payload containing contact data
        
    Returns:
        Result dictionary or None if failed
    """
    try:
        contact_info = payload.data.get("contact_info", "Unknown Contact")
        logger.info(f"Contact stored: {contact_info}")
        return {"status": "success", "type": "contact", "info": contact_info}
        
    except Exception as e:
        logger.exception(f"Failed to store contact for payload {payload.id}: {str(e)}")
        return {"status": "error", "message": str(e)}

def categorize_payload(payload: Payload) -> Payload:
    """
    Automatically categorize payload based on content.
    
    Args:
        payload: Payload to categorize
        
    Returns:
        Modified payload with intent and target set
    """
    try:
        note = payload.data.get("note", "").lower()
        
        if "http" in note or "www" in note:
            payload.intent = "store"
            payload.target = "bookmark"
        elif "remind" in note or "todo" in note or "task" in note:
            payload.intent = "store"
            payload.target = "task"
        elif note.startswith("cmd:") or note.startswith("run ") or note.startswith("!"):
            payload.intent = "execute"
            payload.target = "shell"
            payload.data["command"] = note.replace("cmd:", "").strip()
        else:
            payload.intent = "store"
            payload.target = "note"
        
        logger.info(f"Payload categorized as {payload.intent}:{payload.target}")
        return payload
        
    except Exception as e:
        logger.exception(f"Failed to categorize payload {payload.id}: {str(e)}")
        # Default to note if categorization fails
        payload.intent = "store"
        payload.target = "note"
        return payload
