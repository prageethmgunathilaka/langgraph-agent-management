"""API routes for LangGraph Agent Management System."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from app.models.schemas import (
    WorkflowCreate, WorkflowResponse, WorkflowList,
    AgentCreate, AgentResponse, AgentList,
    AgentConnection, AgentStatus, AgentStatusUpdate, TaskDelegation, TaskCompletion, StatusBroadcast, TaskCreate
)
from app.services.workflow_service import WorkflowService
from app.services.agent_service import AgentService

router = APIRouter()

# Initialize services
workflow_service = WorkflowService()
agent_service = AgentService()

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
async def delegate_task(agent_id: str, delegation: TaskDelegation):
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
            id=delegation.task_id,
            title="Delegated Task",
            description="Task delegated between agents",
            status="pending",
            priority=1,
            created_at=datetime.now(),
            assigned_to=delegation.target_agent_id
        )
        
        result = await agent_service.delegate_task(agent_id, delegation.target_agent_id, mock_task)
        if not result:
            raise HTTPException(status_code=404, detail="One or both agents not found")
        return {"message": f"Task {delegation.task_id} delegated from {agent_id} to {delegation.target_agent_id}"}
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
async def complete_task(agent_id: str, completion: TaskCompletion):
    """Mark a task as completed and notify connected agents."""
    try:
        result = await agent_service.notify_task_completion(agent_id, completion.task_id, completion.result)
        if not result:
            raise HTTPException(status_code=404, detail="Agent or task not found")
        return {"message": f"Task {completion.task_id} completed by agent {agent_id}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents/{agent_id}/broadcast-status", tags=["Agents"])
async def broadcast_status(agent_id: str, status_broadcast: StatusBroadcast):
    """Broadcast status change to all connected agents."""
    try:
        result = await agent_service.broadcast_status_change(agent_id, status_broadcast.status, status_broadcast.message)
        if not result:
            raise HTTPException(status_code=404, detail="Agent not found")
        return {"message": f"Status change broadcasted by agent {agent_id}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 