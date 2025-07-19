"""API routes for LangGraph Agent Management System."""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional, Dict, Any
from app.models.schemas import (
    WorkflowCreate, WorkflowResponse, WorkflowList,
    AgentCreate, AgentResponse, AgentList, AgentConnection, AgentStatusUpdate, AgentStatus,
    TaskCreate, Task, TaskUpdate
)
from app.services.workflow_service import WorkflowService
from app.services.agent_service import AgentService
from app.services.task_service import TaskService, IntelligenceLevel
from app.services.persistence_service import PersistenceService

router = APIRouter()

# Initialize services
workflow_service = WorkflowService()
agent_service = AgentService(workflow_service=workflow_service)
persistence_service = PersistenceService()
task_service = TaskService(agent_service=agent_service, persistence_service=persistence_service)

# Root endpoint
@router.get("/", tags=["System"])
async def root():
    """Root endpoint providing basic system information."""
    return {
        "message": "LangGraph Agent Management System",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "workflows": "/workflows",
            "agents": "/agents", 
            "health": "/health",
            "docs": "/docs"
        }
    }

# Workflow endpoints
@router.post("/workflows", response_model=WorkflowResponse, tags=["Workflows"])
async def create_workflow(workflow: WorkflowCreate):
    """Create a new workflow."""
    try:
        return await workflow_service.create_workflow(workflow)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workflows", response_model=WorkflowList, tags=["Workflows"])
async def list_workflows():
    """List all workflows."""
    try:
        return await workflow_service.list_workflows()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse, tags=["Workflows"])
async def get_workflow(workflow_id: str):
    """Get a specific workflow by ID."""
    try:
        workflow = await workflow_service.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return workflow
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/workflows/{workflow_id}", tags=["Workflows"])
async def delete_workflow(workflow_id: str):
    """Delete a workflow and all its agents."""
    try:
        result = await workflow_service.delete_workflow(workflow_id, agent_service)
        if not result:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return {"message": f"Workflow {workflow_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Agent endpoints
@router.post("/workflows/{workflow_id}/agents", response_model=AgentResponse, tags=["Agents"])
async def create_agent(workflow_id: str, agent: AgentCreate):
    """Create a new agent in a workflow."""
    try:
        return await agent_service.create_agent(workflow_id, agent)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workflows/{workflow_id}/agents", response_model=AgentList, tags=["Agents"])
async def list_agents(workflow_id: str):
    """List all agents in a workflow."""
    try:
        return await agent_service.list_agents(workflow_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/{agent_id}", response_model=AgentResponse, tags=["Agents"])
async def get_agent(agent_id: str):
    """Get a specific agent by ID."""
    try:
        agent = await agent_service.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/agents/{agent_id}", tags=["Agents"])
async def delete_agent(agent_id: str):
    """Delete an agent."""
    try:
        result = await agent_service.delete_agent(agent_id)
        if not result:
            raise HTTPException(status_code=404, detail="Agent not found")
        return {"message": f"Agent {agent_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents/{agent_id}/connect", tags=["Agents"])
async def connect_agents(agent_id: str, connection: AgentConnection):
    """Connect two agents bidirectionally."""
    try:
        result = await agent_service.connect_agents(agent_id, connection.target_agent_id)
        if not result:
            raise HTTPException(status_code=404, detail="One or both agents not found")
        return {"message": f"Agents {agent_id} and {connection.target_agent_id} connected successfully"}
    except HTTPException:
        raise
    except Exception as e:
        # Import here to avoid circular imports
        from app.utils.errors import AgentConnectionError
        if isinstance(e, AgentConnectionError):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents/{agent_id}/disconnect", tags=["Agents"])
async def disconnect_agents(agent_id: str, connection: AgentConnection):
    """Disconnect two agents bidirectionally."""
    try:
        result = await agent_service.disconnect_agents(agent_id, connection.target_agent_id)
        if not result:
            raise HTTPException(status_code=404, detail="One or both agents not found")
        return {"message": f"Agents {agent_id} and {connection.target_agent_id} disconnected successfully"}
    except HTTPException:
        raise
    except Exception as e:
        # Import here to avoid circular imports
        from app.utils.errors import AgentConnectionError
        if isinstance(e, AgentConnectionError):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/{agent_id}/connections", response_model=List[AgentResponse], tags=["Agents"])
async def get_agent_connections(agent_id: str):
    """Get all agents connected to the specified agent."""
    try:
        connections = await agent_service.get_connected_agents(agent_id)
        return connections
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/{agent_id}/status", response_model=AgentStatus, tags=["Agents"])
async def get_agent_status(agent_id: str):
    """Get agent status and details."""
    try:
        status = await agent_service.get_agent_status(agent_id)
        if not status:
            raise HTTPException(status_code=404, detail="Agent not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/agents/{agent_id}/status", response_model=AgentResponse, tags=["Agents"])
async def update_agent_status(agent_id: str, status_update: AgentStatusUpdate):
    """Update agent status with description."""
    try:
        agent = await agent_service.update_agent_status(agent_id, status_update)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents/{agent_id}/spawn", response_model=AgentResponse, tags=["Agents"])
async def spawn_child_agent(agent_id: str, child_agent: AgentCreate):
    """Spawn a child agent from a main agent."""
    try:
        return await agent_service.spawn_child_agent(agent_id, child_agent)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents/{agent_id}/delegate", tags=["Agents"])
async def delegate_task(agent_id: str, delegation: Dict[str, Any]):
    """Delegate a task from one agent to another connected agent."""
    try:
        # For this endpoint, we need to find the task first
        # In a real implementation, you'd have a task service
        # For now, we'll create a mock task for demonstration
        from app.models.schemas import Task
        import uuid
        from datetime import datetime
        
        # This is a simplified implementation - in production you'd retrieve the actual task
        mock_task = Task(
            id=delegation.get("task_id", ""),
            title="Delegated Task",
            description="Task delegated between agents",
            status="pending",
            priority=1,
            created_at=datetime.now(),
            assigned_to=delegation.get("target_agent_id", "")
        )
        
        result = await agent_service.delegate_task(agent_id, delegation.get("target_agent_id", ""), mock_task)
        if not result:
            raise HTTPException(status_code=404, detail="One or both agents not found")
        return {"message": f"Task {delegation.get('task_id', '')} delegated from {agent_id} to {delegation.get('target_agent_id', '')}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents/{agent_id}/spawn-task", tags=["Agents"])
async def spawn_child_task(agent_id: str, child_agent_id: str, task: TaskCreate):
    """Create a new task for a child agent."""
    try:
        result = await agent_service.spawn_child_task(agent_id, child_agent_id, task)
        if not result:
            raise HTTPException(status_code=404, detail="One or both agents not found")
        return {"message": f"Task '{task.title}' spawned for child agent {child_agent_id}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents/{agent_id}/complete-task", tags=["Agents"])
async def complete_task(agent_id: str, completion: Dict[str, Any]):
    """Mark a task as completed and notify connected agents."""
    try:
        result = await agent_service.notify_task_completion(agent_id, completion.get("task_id", ""), completion.get("result", ""))
        if not result:
            raise HTTPException(status_code=404, detail="Agent or task not found")
        return {"message": f"Task {completion.get('task_id', '')} completed by agent {agent_id}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents/{agent_id}/broadcast-status", tags=["Agents"])
async def broadcast_status(agent_id: str, status_broadcast: Dict[str, Any]):
    """Broadcast status change to all connected agents."""
    try:
        result = await agent_service.broadcast_status_change(agent_id, status_broadcast.get("status", ""), status_broadcast.get("message", ""))
        if not result:
            raise HTTPException(status_code=404, detail="Agent not found")
        return {"message": f"Status change broadcasted by agent {agent_id}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 

# Task Management and Workflow Planning Endpoints

@router.post("/workflows/plan", response_model=Dict[str, Any])
async def create_workflow_plan(
    request_data: Dict[str, Any],
    task_service: TaskService = Depends(lambda: task_service)
):
    """Create a structured workflow plan from a complex request using LLM."""
    try:
        request_text = request_data.get("request", "")
        context = request_data.get("context", {})
        
        if not request_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request text is required"
            )
        
        workflow_plan = await task_service.create_workflow_from_request(request_text, context)
        
        return {
            "workflow_id": workflow_plan.workflow_id,
            "title": workflow_plan.title,
            "description": workflow_plan.description,
            "steps": workflow_plan.steps,
            "success_criteria": workflow_plan.metadata.get("success_criteria", ""),
            "failure_handling": workflow_plan.metadata.get("failure_handling", ""),
            "estimated_duration": workflow_plan.metadata.get("estimated_duration", 0),
            "created_at": workflow_plan.created_at.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workflow plan: {str(e)}"
        )

@router.post("/workflows/{workflow_id}/execute", response_model=Dict[str, Any])
async def execute_workflow(
    workflow_id: str,
    execution_params: Dict[str, Any],
    task_service: TaskService = Depends(lambda: task_service)
):
    """Execute a workflow plan with specified intelligence level."""
    try:
        intelligence_level_str = execution_params.get("intelligence_level", "basic")
        
        # Convert string to enum
        intelligence_level = IntelligenceLevel(intelligence_level_str)
        
        result = await task_service.execute_workflow(workflow_id, intelligence_level)
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameters: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute workflow: {str(e)}"
        )

@router.get("/workflows/{workflow_id}/status", response_model=Dict[str, Any])
async def get_workflow_status(
    workflow_id: str,
    task_service: TaskService = Depends(lambda: task_service)
):
    """Get detailed workflow execution status."""
    try:
        status_info = await task_service.get_workflow_status(workflow_id)
        
        if status_info.get("status") == "not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow status: {str(e)}"
        )

@router.get("/tasks/{task_id}/status", response_model=Dict[str, Any])
async def get_task_status(
    task_id: str,
    task_service: TaskService = Depends(lambda: task_service)
):
    """Get detailed task execution status."""
    try:
        status_info = await task_service.get_task_status(task_id)
        
        if status_info.get("status") == "not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}"
        )

@router.delete("/tasks/{task_id}", response_model=Dict[str, Any])
async def cancel_task(
    task_id: str,
    task_service: TaskService = Depends(lambda: task_service)
):
    """Cancel a running task."""
    try:
        success = await task_service.cancel_task(task_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found or not running"
            )
        
        return {"message": f"Task {task_id} cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel task: {str(e)}"
        )

@router.get("/system/metrics", response_model=Dict[str, Any])
async def get_system_metrics(
    task_service: TaskService = Depends(lambda: task_service)
):
    """Get system performance metrics including LLM usage."""
    try:
        metrics = await task_service.get_system_metrics()
        return metrics
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system metrics: {str(e)}"
        )

@router.get("/llm/usage", response_model=Dict[str, Any])
async def get_llm_usage_stats(
    task_service: TaskService = Depends(lambda: task_service)
):
    """Get LLM usage statistics and costs."""
    try:
        stats = task_service.get_llm_usage_stats()
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get LLM usage stats: {str(e)}"
        )


# Persistence Management Endpoints

@router.get("/persistence/health")
async def get_persistence_health():
    """Get persistence service health status."""
    try:
        health = await persistence_service.health_check()
        return health
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check persistence health: {str(e)}"
        )


@router.get("/persistence/stats")
async def get_persistence_stats():
    """Get database statistics."""
    try:
        stats = await persistence_service.get_database_stats()
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get persistence stats: {str(e)}"
        )


@router.post("/persistence/backup")
async def create_backup():
    """Create a database backup."""
    try:
        backup_path = await persistence_service.create_backup()
        if backup_path:
            return {"status": "success", "backup_path": backup_path}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create backup"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create backup: {str(e)}"
        )


@router.post("/persistence/restore")
async def restore_backup(backup_path: str):
    """Restore database from backup."""
    try:
        success = await persistence_service.restore_from_backup(backup_path)
        if success:
            return {"status": "success", "message": "Database restored successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to restore from backup"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore backup: {str(e)}"
        )


@router.delete("/persistence/cleanup")
async def cleanup_old_data(days: int = 30):
    """Clean up old data older than specified days."""
    try:
        success = await persistence_service.cleanup_old_data(days)
        if success:
            return {"status": "success", "message": f"Cleaned up data older than {days} days"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cleanup old data"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup old data: {str(e)}"
        )


@router.get("/persistence/metrics/{metric_name}")
async def get_metrics(metric_name: str, limit: int = 100):
    """Get system metrics by name."""
    try:
        metrics = await persistence_service.get_metrics(metric_name, limit=limit)
        return metrics
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )


@router.post("/persistence/metrics")
async def record_metric(metric_name: str, metric_value: float, metadata: Optional[Dict[str, Any]] = None):
    """Record a system metric."""
    try:
        success = await persistence_service.record_metric(metric_name, metric_value, metadata)
        if success:
            return {"status": "success", "message": "Metric recorded successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to record metric"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record metric: {str(e)}"
        ) 