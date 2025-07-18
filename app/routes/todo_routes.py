"""
TODO Routes - Manages project TODOs and task tracking.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime
import json
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/todos", tags=["TODOs"])


class TodoItem(BaseModel):
    """Model for a TODO item"""
    id: str = Field(..., description="Unique identifier")
    content: str = Field(..., description="TODO content")
    status: str = Field(..., description="Status: pending, in_progress, completed, cancelled")
    priority: str = Field(default="medium", description="Priority: critical, high, medium, low")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    assignee: str | None = Field(default=None, description="Assigned to")
    tags: List[str] = Field(default_factory=list, description="Tags")
    due_date: datetime | None = Field(default=None, description="Due date")


# In-memory storage for now (should be moved to database)
TODOS_FILE = "todos.json"


def load_todos() -> List[Dict[str, Any]]:
    """Load TODOs from file or return defaults"""
    if os.path.exists(TODOS_FILE):
        try:
            with open(TODOS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    
    # Return default TODOs for the project
    return [
        {
            "id": "todo_001",
            "content": "🔒 Implement Authentication System - OAuth2/JWT integration",
            "status": "in_progress",
            "priority": "critical",
            "assignee": "Security Team",
            "tags": ["security", "authentication"],
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-17T14:30:00Z"
        },
        {
            "id": "todo_002",
            "content": "📊 Performance Optimization - Implement caching layer with Redis",
            "status": "pending",
            "priority": "high",
            "tags": ["performance", "infrastructure"],
            "created_at": "2024-01-16T09:00:00Z",
            "updated_at": "2024-01-16T09:00:00Z"
        },
        {
            "id": "todo_003",
            "content": "🧪 Unit Test Coverage - Achieve 90% test coverage",
            "status": "in_progress",
            "priority": "high",
            "assignee": "QA Team",
            "tags": ["testing", "quality"],
            "created_at": "2024-01-14T11:00:00Z",
            "updated_at": "2024-01-17T10:00:00Z"
        },
        {
            "id": "todo_004",
            "content": "📝 API Documentation - Complete OpenAPI documentation",
            "status": "completed",
            "priority": "medium",
            "tags": ["documentation"],
            "created_at": "2024-01-10T08:00:00Z",
            "updated_at": "2024-01-16T16:00:00Z"
        },
        {
            "id": "todo_005",
            "content": "🚀 CI/CD Pipeline - GitHub Actions workflow optimization",
            "status": "completed",
            "priority": "high",
            "tags": ["devops", "automation"],
            "created_at": "2024-01-12T13:00:00Z",
            "updated_at": "2024-01-15T17:00:00Z"
        },
        {
            "id": "todo_006",
            "content": "🎨 UI/UX Improvements - Dashboard redesign",
            "status": "completed",
            "priority": "medium",
            "assignee": "Frontend Team",
            "tags": ["ui", "frontend"],
            "created_at": "2024-01-13T10:00:00Z",
            "updated_at": "2024-01-17T15:00:00Z"
        },
        {
            "id": "todo_007",
            "content": "🔍 Search Enhancement - Implement fuzzy search",
            "status": "pending",
            "priority": "medium",
            "tags": ["feature", "search"],
            "created_at": "2024-01-17T09:00:00Z",
            "updated_at": "2024-01-17T09:00:00Z"
        },
        {
            "id": "todo_008",
            "content": "📱 Mobile Responsiveness - Optimize for mobile devices",
            "status": "pending",
            "priority": "low",
            "tags": ["mobile", "ui"],
            "created_at": "2024-01-17T11:00:00Z",
            "updated_at": "2024-01-17T11:00:00Z"
        },
        {
            "id": "todo_009",
            "content": "🌍 Internationalization - Add multi-language support",
            "status": "pending",
            "priority": "low",
            "tags": ["i18n", "feature"],
            "created_at": "2024-01-16T14:00:00Z",
            "updated_at": "2024-01-16T14:00:00Z"
        },
        {
            "id": "todo_010",
            "content": "⚡ WebSocket Implementation - Real-time updates",
            "status": "pending",
            "priority": "medium",
            "tags": ["feature", "realtime"],
            "created_at": "2024-01-17T12:00:00Z",
            "updated_at": "2024-01-17T12:00:00Z"
        }
    ]


def save_todos(todos: List[Dict[str, Any]]):
    """Save TODOs to file"""
    try:
        with open(TODOS_FILE, "w") as f:
            json.dump(todos, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to save TODOs: {e}")


@router.get("/")
async def get_todos(
    status: str | None = None,
    priority: str | None = None,
    assignee: str | None = None
):
    """Get all TODOs with optional filtering"""
    todos = load_todos()
    
    # Apply filters
    if status:
        todos = [t for t in todos if t.get("status") == status]
    if priority:
        todos = [t for t in todos if t.get("priority") == priority]
    if assignee:
        todos = [t for t in todos if t.get("assignee") == assignee]
    
    return todos


@router.get("/stats")
async def get_todo_stats():
    """Get TODO statistics"""
    todos = load_todos()
    
    stats = {
        "total": len(todos),
        "by_status": {},
        "by_priority": {},
        "by_assignee": {},
        "completion_rate": 0
    }
    
    # Count by status
    for todo in todos:
        status = todo.get("status", "pending")
        stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
        
        priority = todo.get("priority", "medium")
        stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1
        
        assignee = todo.get("assignee", "Unassigned")
        stats["by_assignee"][assignee] = stats["by_assignee"].get(assignee, 0) + 1
    
    # Calculate completion rate
    completed = stats["by_status"].get("completed", 0)
    if stats["total"] > 0:
        stats["completion_rate"] = round((completed / stats["total"]) * 100, 1)
    
    return stats


@router.post("/")
async def create_todo(todo: TodoItem):
    """Create a new TODO"""
    todos = load_todos()
    
    new_todo = todo.dict()
    new_todo["id"] = f"todo_{len(todos) + 1:03d}"
    new_todo["created_at"] = datetime.utcnow().isoformat()
    new_todo["updated_at"] = datetime.utcnow().isoformat()
    
    todos.append(new_todo)
    save_todos(todos)
    
    return new_todo


@router.put("/{todo_id}")
async def update_todo(todo_id: str, updates: Dict[str, Any]):
    """Update a TODO"""
    todos = load_todos()
    
    for i, todo in enumerate(todos):
        if todo["id"] == todo_id:
            todos[i].update(updates)
            todos[i]["updated_at"] = datetime.utcnow().isoformat()
            save_todos(todos)
            return todos[i]
    
    raise HTTPException(status_code=404, detail="TODO not found")


@router.delete("/{todo_id}")
async def delete_todo(todo_id: str):
    """Delete a TODO"""
    todos = load_todos()
    
    for i, todo in enumerate(todos):
        if todo["id"] == todo_id:
            deleted = todos.pop(i)
            save_todos(todos)
            return {"status": "success", "deleted": deleted}
    
    raise HTTPException(status_code=404, detail="TODO not found") 