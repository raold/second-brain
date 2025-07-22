"""
API routes for automation control and monitoring.

Provides endpoints for:
- Viewing automation status
- Controlling scheduled tasks
- Monitoring trigger states
- Manual task execution
- Automation configuration
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.auth import verify_token
from app.services.automation_service import automation_service

router = APIRouter(prefix="/automation", tags=["automation"])


# Pydantic models for API

class TaskStatusResponse(BaseModel):
    """Response model for task status"""
    id: str
    name: str
    status: str
    enabled: bool
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    error_count: int
    is_running: bool


class TriggerStatusResponse(BaseModel):
    """Response model for trigger status"""
    id: str
    name: str
    enabled: bool
    last_triggered: Optional[datetime]
    trigger_count: int


class AutomationStatusResponse(BaseModel):
    """Response model for overall automation status"""
    initialized: bool
    scheduler_running: bool
    scheduled_tasks: List[TaskStatusResponse]
    active_triggers: List[TriggerStatusResponse]
    system_health: Dict[str, Any]


class TaskControlRequest(BaseModel):
    """Request model for task control operations"""
    task_id: str = Field(..., description="ID of the task to control")
    action: str = Field(..., description="Action to perform: enable, disable, trigger")


class ManualTriggerRequest(BaseModel):
    """Request model for manual task triggering"""
    task_id: str = Field(..., description="ID of the task to trigger")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata for the task")


class EventRecordRequest(BaseModel):
    """Request model for recording events"""
    event_type: str = Field(..., description="Type of event to record")
    event_data: Dict[str, Any] = Field(..., description="Event data payload")


@router.get("/status", response_model=AutomationStatusResponse)
async def get_automation_status(
    api_key: str = Depends(verify_token)
) -> AutomationStatusResponse:
    """
    Get comprehensive automation system status.
    
    Returns:
    - Scheduler status
    - All scheduled tasks with their states
    - Active triggers and their states
    - System health metrics
    """
    try:
        status = automation_service.get_automation_status()
        
        # Add system health metrics
        import psutil
        status["system_health"] = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "timestamp": datetime.now().isoformat()
        }
        
        return AutomationStatusResponse(**status)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get automation status: {str(e)}"
        )


@router.get("/tasks", response_model=List[TaskStatusResponse])
async def list_scheduled_tasks(
    api_key: str = Depends(verify_token)
) -> List[TaskStatusResponse]:
    """
    List all scheduled tasks with their current status.
    
    Returns:
    - List of all registered scheduled tasks
    - Current status, last run time, next run time
    - Error counts and running state
    """
    try:
        tasks = automation_service.scheduler.get_all_tasks()
        return [TaskStatusResponse(**task) for task in tasks]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tasks: {str(e)}"
        )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    api_key: str = Depends(verify_token)
) -> TaskStatusResponse:
    """
    Get detailed status of a specific scheduled task.
    
    Args:
        task_id: ID of the task to query
        
    Returns:
        Detailed task status including execution history
    """
    try:
        task_status = automation_service.scheduler.get_task_status(task_id)
        
        if not task_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        
        return TaskStatusResponse(**task_status)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}"
        )


@router.post("/tasks/control")
async def control_task(
    request: TaskControlRequest,
    api_key: str = Depends(verify_token)
) -> Dict[str, Any]:
    """
    Control a scheduled task (enable, disable, or trigger).
    
    Args:
        request: Task control request with task ID and action
        
    Returns:
        Result of the control operation
    """
    try:
        if request.action == "enable":
            automation_service.enable_task(request.task_id)
            return {"status": "success", "message": f"Task {request.task_id} enabled"}
            
        elif request.action == "disable":
            automation_service.disable_task(request.task_id)
            return {"status": "success", "message": f"Task {request.task_id} disabled"}
            
        elif request.action == "trigger":
            manual_task_id = automation_service.trigger_task(request.task_id)
            if not manual_task_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Task {request.task_id} not found"
                )
            return {
                "status": "success",
                "message": f"Task {request.task_id} triggered manually",
                "manual_task_id": manual_task_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {request.action}. Must be enable, disable, or trigger"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to control task: {str(e)}"
        )


@router.post("/tasks/trigger/{task_id}")
async def trigger_task_now(
    task_id: str,
    request: Optional[ManualTriggerRequest] = None,
    api_key: str = Depends(verify_token)
) -> Dict[str, Any]:
    """
    Manually trigger a scheduled task for immediate execution.
    
    Args:
        task_id: ID of the task to trigger
        request: Optional metadata for the task execution
        
    Returns:
        ID of the created manual execution task
    """
    try:
        manual_task_id = automation_service.trigger_task(task_id)
        
        if not manual_task_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        
        return {
            "status": "success",
            "message": f"Task {task_id} triggered for immediate execution",
            "manual_task_id": manual_task_id,
            "triggered_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger task: {str(e)}"
        )


@router.get("/triggers", response_model=List[TriggerStatusResponse])
async def list_triggers(
    api_key: str = Depends(verify_token)
) -> List[TriggerStatusResponse]:
    """
    List all active automation triggers.
    
    Returns:
        List of configured triggers with their status
    """
    try:
        from app.scheduler.triggers import trigger_manager
        
        triggers = []
        for trigger in trigger_manager.triggers.values():
            triggers.append({
                "id": trigger.trigger_id,
                "name": trigger.name,
                "enabled": trigger.enabled,
                "last_triggered": trigger.last_triggered,
                "trigger_count": trigger.trigger_count
            })
        
        return [TriggerStatusResponse(**t) for t in triggers]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list triggers: {str(e)}"
        )


@router.post("/events/record")
async def record_event(
    request: EventRecordRequest,
    api_key: str = Depends(verify_token)
) -> Dict[str, Any]:
    """
    Record an event for trigger processing.
    
    This allows external systems to notify the automation system
    of events that may trigger automated actions.
    
    Args:
        request: Event type and data
        
    Returns:
        Confirmation of event recording
    """
    try:
        automation_service.record_event(
            event_type=request.event_type,
            event_data=request.event_data
        )
        
        return {
            "status": "success",
            "message": f"Event {request.event_type} recorded",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record event: {str(e)}"
        )


@router.post("/consolidation/immediate")
async def trigger_immediate_consolidation(
    api_key: str = Depends(verify_token)
) -> Dict[str, Any]:
    """
    Trigger immediate memory consolidation.
    
    This bypasses scheduled timing and runs consolidation now.
    Useful for manual maintenance or after large imports.
    
    Returns:
        Task ID for tracking the consolidation process
    """
    try:
        manual_task_id = automation_service.trigger_task("daily_consolidation")
        
        if not manual_task_id:
            # Task doesn't exist, create a one-off
            from app.scheduler import ScheduledTask, TaskPriority
            task = ScheduledTask(
                id=f"manual_consolidation_{datetime.now().timestamp()}",
                name="Manual Consolidation",
                function=automation_service.consolidation_worker.run_consolidation,
                schedule="once",
                priority=TaskPriority.HIGH,
                timeout=7200
            )
            automation_service.scheduler.register_task(task)
            manual_task_id = task.id
        
        return {
            "status": "success",
            "message": "Consolidation triggered",
            "task_id": manual_task_id,
            "estimated_duration": "15-30 minutes depending on data size"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger consolidation: {str(e)}"
        )


@router.post("/cleanup/immediate")
async def trigger_immediate_cleanup(
    retention_days: Optional[int] = 90,
    api_key: str = Depends(verify_token)
) -> Dict[str, Any]:
    """
    Trigger immediate cleanup of old data.
    
    Args:
        retention_days: Number of days of data to retain (default: 90)
        
    Returns:
        Task ID for tracking the cleanup process
    """
    try:
        # Update retention if specified
        if retention_days:
            automation_service.cleanup_worker.retention_days = retention_days
        
        manual_task_id = automation_service.trigger_task("daily_cleanup")
        
        return {
            "status": "success",
            "message": "Cleanup triggered",
            "task_id": manual_task_id,
            "retention_days": retention_days,
            "estimated_duration": "5-15 minutes"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger cleanup: {str(e)}"
        )


@router.get("/health")
async def automation_health_check() -> Dict[str, Any]:
    """
    Quick health check for the automation system.
    
    Returns:
        Simple health status
    """
    try:
        is_healthy = (
            automation_service.is_initialized and
            automation_service.scheduler._running
        )
        
        return {
            "healthy": is_healthy,
            "initialized": automation_service.is_initialized,
            "scheduler_running": automation_service.scheduler._running,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }