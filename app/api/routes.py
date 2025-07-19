"""API routes for LangGraph Agent Management System."""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional, Dict, Any
from app.models.schemas import (
    WorkflowCreate,
    WorkflowResponse,
    WorkflowList,
    AgentCreate,
    AgentResponse,
    AgentList,
    AgentConnection,
    AgentStatusUpdate,
    AgentStatus,
    TaskCreate,
    Task,
    TaskUpdate,
    AgentStatusHistoryResponse,
    WorkflowStatusSummary,
    SystemStatusOverview,
    AgentHealthCheck,
    TaskDelegationRequest,
    TaskDelegationResult,
    DynamicWorkflowStep,
)
from app.services.workflow_service import WorkflowService
from app.services.agent_service import AgentService
from app.services.task_service import TaskService, IntelligenceLevel
from app.services.persistence_service import PersistenceService

router = APIRouter()

# Initialize services
workflow_service = WorkflowService()
persistence_service = PersistenceService()

# Initialize agent_service first without task_service
agent_service = AgentService(workflow_service=workflow_service)

# Initialize task_service with agent_service
task_service = TaskService(agent_service=agent_service, persistence_service=persistence_service)

# Now update agent_service with task_service reference for delegation support
agent_service.task_service = task_service


# Root endpoint
@router.get("/", tags=["System"])
async def root():
    """Root endpoint providing basic system information."""
    return {
        "message": "LangGraph Agent Management System",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {"workflows": "/workflows", "agents": "/agents", "health": "/health", "docs": "/docs"},
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


# Specific agent routes must come before parameterized routes to avoid conflicts
@router.get("/agents/problematic", tags=["Agent Status"])
async def get_problematic_agents():
    """Get agents that might need attention."""
    try:
        problematic_agents = await agent_service.find_problematic_agents()
        return {"problematic_agents": problematic_agents, "count": len(problematic_agents)}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get problematic agents: {str(e)}"
        )


@router.get("/agents/status/all", tags=["Agent Status"])
async def get_all_agents_status(status_filter: Optional[str] = None, workflow_id: Optional[str] = None):
    """Get status for all agents with optional filtering."""
    try:
        agents_status = await agent_service.get_all_agents_status(status_filter=status_filter, workflow_id=workflow_id)
        return agents_status

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get agents status: {str(e)}")


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
            assigned_to=delegation.get("target_agent_id", ""),
        )

        result = await agent_service.delegate_task(agent_id, delegation.get("target_agent_id", ""), mock_task)
        if not result:
            raise HTTPException(status_code=404, detail="One or both agents not found")
        return {
            "message": f"Task {delegation.get('task_id', '')} delegated from {agent_id} to {delegation.get('target_agent_id', '')}"
        }
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
        result = await agent_service.notify_task_completion(
            agent_id, completion.get("task_id", ""), completion.get("result", "")
        )
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
        result = await agent_service.broadcast_status_change(
            agent_id, status_broadcast.get("status", ""), status_broadcast.get("message", "")
        )
        if not result:
            raise HTTPException(status_code=404, detail="Agent not found")
        return {"message": f"Status change broadcasted by agent {agent_id}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Task Management and Workflow Planning Endpoints


@router.post("/workflows/plan", response_model=Dict[str, Any])
async def create_workflow_plan(request_data: Dict[str, Any], task_service: TaskService = Depends(lambda: task_service)):
    """Create a structured workflow plan from a complex request using LLM."""
    try:
        request_text = request_data.get("request", "")
        context = request_data.get("context", {})

        if not request_text:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request text is required")

        workflow_plan = await task_service.create_workflow_from_request(request_text, context)

        return {
            "workflow_id": workflow_plan.workflow_id,
            "title": workflow_plan.title,
            "description": workflow_plan.description,
            "steps": workflow_plan.steps,
            "success_criteria": workflow_plan.metadata.get("success_criteria", ""),
            "failure_handling": workflow_plan.metadata.get("failure_handling", ""),
            "estimated_duration": workflow_plan.metadata.get("estimated_duration", 0),
            "created_at": workflow_plan.created_at.isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create workflow plan: {str(e)}"
        )


@router.post("/workflows/{workflow_id}/execute", response_model=Dict[str, Any])
async def execute_workflow(
    workflow_id: str, execution_params: Dict[str, Any], task_service: TaskService = Depends(lambda: task_service)
):
    """Execute a workflow plan with specified intelligence level."""
    try:
        intelligence_level_str = execution_params.get("intelligence_level", "basic")

        # Convert string to enum
        intelligence_level = IntelligenceLevel(intelligence_level_str)

        result = await task_service.execute_workflow(workflow_id, intelligence_level)

        return result

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid parameters: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to execute workflow: {str(e)}")


@router.get("/workflows/{workflow_id}/status", response_model=Dict[str, Any])
async def get_workflow_status(workflow_id: str, task_service: TaskService = Depends(lambda: task_service)):
    """Get detailed workflow execution status."""
    try:
        status_info = await task_service.get_workflow_status(workflow_id)

        if status_info.get("status") == "not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Workflow {workflow_id} not found")

        return status_info

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get workflow status: {str(e)}"
        )


@router.get("/tasks/{task_id}/status", response_model=Dict[str, Any])
async def get_task_status(task_id: str, task_service: TaskService = Depends(lambda: task_service)):
    """Get detailed task execution status."""
    try:
        status_info = await task_service.get_task_status(task_id)

        if status_info.get("status") == "not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found")

        return status_info

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get task status: {str(e)}")


@router.delete("/tasks/{task_id}", response_model=Dict[str, Any])
async def cancel_task(task_id: str, task_service: TaskService = Depends(lambda: task_service)):
    """Cancel a running task."""
    try:
        success = await task_service.cancel_task(task_id)

        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found or not running")

        return {"message": f"Task {task_id} cancelled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to cancel task: {str(e)}")


# Enhanced Agent Status Tracking Endpoints


@router.get("/workflows/{workflow_id}/agents/status", tags=["Agent Status"])
async def get_workflow_agents_status(workflow_id: str):
    """Get status summary for all agents in a workflow."""
    try:
        status_summary = await agent_service.get_workflow_status_summary(workflow_id)
        return status_summary

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get workflow agents status: {str(e)}"
        )


@router.post("/agents/{agent_id}/status/broadcast", tags=["Agent Status"])
async def broadcast_status_change(agent_id: str, broadcast_data: Dict[str, Any]):
    """Broadcast status change to all connected agents."""
    try:
        status_str = broadcast_data.get("status")
        message = broadcast_data.get("message", "")

        if not status_str:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status is required")

        # Convert string to AgentStatusEnum
        try:
            from app.models.schemas import AgentStatusEnum

            status_enum = AgentStatusEnum(status_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_str}. Valid options: {[e.value for e in AgentStatusEnum]}",
            )

        success = await agent_service.broadcast_status_change(agent_id, status_enum, message)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")

        return {"message": f"Status broadcast sent successfully to connected agents"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to broadcast status change: {str(e)}"
        )


@router.get("/agents/{agent_id}/health", tags=["Agent Status"])
async def check_agent_health(agent_id: str):
    """Perform comprehensive health check on an agent."""
    try:
        health_status = await agent_service.check_agent_health(agent_id)
        if not health_status:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")
        return health_status

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to check agent health: {str(e)}"
        )


@router.get("/system/status/overview", tags=["Agent Status"])
async def get_system_status_overview():
    """Get system-wide status overview with metrics."""
    try:
        overview = await agent_service.get_system_status_overview()
        return overview

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get system status overview: {str(e)}"
        )


@router.put("/agents/status/batch", tags=["Agent Status"])
async def update_multiple_agents_status(update_data: Dict[str, Any]):
    """Update status for multiple agents."""
    try:
        agent_ids = update_data.get("agent_ids", [])
        new_status_str = update_data.get("status")

        if not agent_ids or not new_status_str:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="agent_ids and status are required")

        # Convert string to AgentStatusEnum
        try:
            from app.models.schemas import AgentStatusEnum

            new_status = AgentStatusEnum(new_status_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {new_status_str}. Valid options: {[e.value for e in AgentStatusEnum]}",
            )

        results = await agent_service.update_multiple_agent_status(agent_ids, new_status)
        return {"results": results}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update multiple agents status: {str(e)}"
        )


@router.get("/agents/{agent_id}/status/history", response_model=AgentStatusHistoryResponse, tags=["Agent Status"])
async def get_agent_status_history(agent_id: str, limit: int = 50):
    """Get status change history for an agent."""
    try:
        history = await agent_service.get_agent_status_history(agent_id, limit=limit)
        if not history:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")
        return history

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get agent status history: {str(e)}"
        )


@router.get("/system/metrics", response_model=Dict[str, Any])
async def get_system_metrics(task_service: TaskService = Depends(lambda: task_service)):
    """Get system performance metrics including LLM usage."""
    try:
        metrics = await task_service.get_system_metrics()
        return metrics

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get system metrics: {str(e)}"
        )


@router.get("/llm/usage", response_model=Dict[str, Any])
async def get_llm_usage_stats(task_service: TaskService = Depends(lambda: task_service)):
    """Get LLM usage statistics and costs."""
    try:
        stats = task_service.get_llm_usage_stats()
        return stats

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get LLM usage stats: {str(e)}"
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to check persistence health: {str(e)}"
        )


@router.get("/persistence/stats")
async def get_persistence_stats():
    """Get database statistics."""
    try:
        stats = await persistence_service.get_database_stats()
        return stats

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get persistence stats: {str(e)}"
        )


@router.post("/persistence/backup")
async def create_backup():
    """Create a database backup."""
    try:
        backup_path = await persistence_service.create_backup()
        if backup_path:
            return {"status": "success", "backup_path": backup_path}
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create backup")

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create backup: {str(e)}")


@router.post("/persistence/restore")
async def restore_backup(backup_path: str):
    """Restore database from backup."""
    try:
        success = await persistence_service.restore_from_backup(backup_path)
        if success:
            return {"status": "success", "message": "Database restored successfully"}
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to restore from backup")

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to restore backup: {str(e)}")


@router.delete("/persistence/cleanup")
async def cleanup_old_data(days: int = 30):
    """Clean up old data older than specified days."""
    try:
        success = await persistence_service.cleanup_old_data(days)
        if success:
            return {"status": "success", "message": f"Cleaned up data older than {days} days"}
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to cleanup old data")

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to cleanup old data: {str(e)}")


@router.get("/persistence/metrics/{metric_name}")
async def get_metrics(metric_name: str, limit: int = 100):
    """Get system metrics by name."""
    try:
        metrics = await persistence_service.get_metrics(metric_name, limit=limit)
        return metrics

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get metrics: {str(e)}")


@router.post("/persistence/metrics")
async def record_metric(metric_name: str, metric_value: float, metadata: Optional[Dict[str, Any]] = None):
    """Record a system metric."""
    try:
        success = await persistence_service.record_metric(metric_name, metric_value, metadata)
        if success:
            return {"status": "success", "message": "Metric recorded successfully"}
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to record metric")

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to record metric: {str(e)}")


# Enhanced Task Delegation Endpoints


@router.post("/workflows/{workflow_id}/execute-with-delegation", response_model=Dict[str, Any], tags=["Workflow Delegation"])
async def execute_workflow_with_delegation(workflow_id: str, execution_params: Dict[str, Any]):
    """Execute a workflow with support for dynamic task delegation."""
    try:
        intelligence_level_str = execution_params.get("intelligence_level", "basic")
        intelligence_level = IntelligenceLevel(intelligence_level_str)

        result = await task_service.execute_workflow_with_delegation(workflow_id, intelligence_level)
        return result

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid parameters: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to execute workflow with delegation: {str(e)}"
        )


@router.post("/agents/{agent_id}/delegate-task", response_model=TaskDelegationResult, tags=["Task Delegation"])
async def delegate_task_to_agent(agent_id: str, delegation_request: TaskDelegationRequest, current_context: Dict[str, Any]):
    """Delegate a task from one agent to another during execution."""
    try:
        result = await agent_service.delegate_task_during_execution(agent_id, delegation_request, current_context)
        return result

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid delegation request: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delegate task: {str(e)}")


@router.get("/workflows/{workflow_id}/dynamic-steps", response_model=List[Dict[str, Any]], tags=["Workflow Delegation"])
async def get_dynamic_steps(workflow_id: str):
    """Get dynamically created steps for a workflow."""
    try:
        dynamic_steps = await agent_service.get_dynamic_steps(workflow_id)
        return dynamic_steps

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get dynamic steps: {str(e)}")


@router.delete("/workflows/{workflow_id}/dynamic-steps", tags=["Workflow Delegation"])
async def clear_dynamic_steps(workflow_id: str):
    """Clear dynamically created steps for a workflow."""
    try:
        success = await agent_service.clear_dynamic_steps(workflow_id)
        if success:
            return {"status": "success", "message": f"Cleared dynamic steps for workflow {workflow_id}"}
        else:
            return {"status": "no_action", "message": f"No dynamic steps found for workflow {workflow_id}"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to clear dynamic steps: {str(e)}"
        )


@router.get("/workflows/{workflow_id}/delegation-status", response_model=Dict[str, Any], tags=["Workflow Delegation"])
async def get_workflow_delegation_status(workflow_id: str):
    """Get delegation status and statistics for a workflow."""
    try:
        # Get dynamic steps
        dynamic_steps = await agent_service.get_dynamic_steps(workflow_id)

        # Get workflow status from task service
        workflow_status = await task_service.get_workflow_status(workflow_id)

        # Calculate delegation statistics
        total_delegations = len(dynamic_steps)
        pending_delegations = len([s for s in dynamic_steps if s.get("status") == "pending"])
        completed_delegations = len([s for s in dynamic_steps if s.get("status") == "completed"])

        return {
            "workflow_id": workflow_id,
            "delegation_stats": {
                "total_delegations": total_delegations,
                "pending_delegations": pending_delegations,
                "completed_delegations": completed_delegations,
                "delegation_rate": (completed_delegations / total_delegations * 100) if total_delegations > 0 else 0,
            },
            "dynamic_steps": dynamic_steps,
            "workflow_status": workflow_status,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get delegation status: {str(e)}"
        )
