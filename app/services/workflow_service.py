"""Workflow service for managing LangGraph workflows."""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.schemas import WorkflowCreate, WorkflowResponse, WorkflowList, WorkflowStatus
from app.utils.logger import LoggerMixin, log_workflow_event
from app.utils.errors import (
    WorkflowNotFoundError,
    WorkflowAlreadyExistsError,
    WorkflowDeletionError,
    handle_service_error
)

class WorkflowService(LoggerMixin):
    """Service for managing workflows."""
    
    def __init__(self):
        # In-memory storage for MVP (would be replaced with database)
        self._workflows: Dict[str, WorkflowResponse] = {}
        self.logger.info("WorkflowService initialized")
    
    @handle_service_error
    async def create_workflow(self, workflow_data: WorkflowCreate) -> WorkflowResponse:
        """Create a new workflow."""
        workflow_id = str(uuid.uuid4())
        
        # Check if workflow with same name already exists
        existing = self._find_workflow_by_name(workflow_data.name)
        if existing:
            from app.utils.errors import ValidationError
            raise ValidationError("name", workflow_data.name, "Workflow name already exists")
        
        # Create new workflow
        workflow = WorkflowResponse(
            id=workflow_id,
            name=workflow_data.name,
            description=workflow_data.description,
            status=WorkflowStatus.ACTIVE,
            created_at=datetime.now(),
            last_modified=datetime.now(),
            agent_count=0,
            agents=[]
        )
        
        # Store workflow
        self._workflows[workflow_id] = workflow
        
        log_workflow_event(workflow_id, "created", {
            "name": workflow.name,
            "description": workflow.description
        })
        
        self.logger.info(f"Created workflow: {workflow_id}")
        return workflow
    
    @handle_service_error
    async def get_workflow(self, workflow_id: str) -> Optional[WorkflowResponse]:
        """Get a workflow by ID."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None
        
        log_workflow_event(workflow_id, "retrieved")
        return workflow
    
    @handle_service_error
    async def list_workflows(self) -> WorkflowList:
        """List all workflows."""
        workflows = list(self._workflows.values())
        
        # Sort by creation date (newest first)
        workflows.sort(key=lambda w: w.created_at, reverse=True)
        
        self.logger.info(f"Listed {len(workflows)} workflows")
        return WorkflowList(
            workflows=workflows,
            total=len(workflows)
        )
    
    @handle_service_error
    async def update_workflow(self, workflow_id: str, updates: Dict[str, Any]) -> Optional[WorkflowResponse]:
        """Update a workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None
        
        # Update fields
        for field, value in updates.items():
            if hasattr(workflow, field):
                setattr(workflow, field, value)
        
        # Update last modified timestamp
        workflow.last_modified = datetime.now()
        
        log_workflow_event(workflow_id, "updated", updates)
        self.logger.info(f"Updated workflow: {workflow_id}")
        return workflow
    
    @handle_service_error
    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow and all its agents."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False
        
        try:
            # In a real implementation, this would also delete all associated agents
            # For now, we'll just remove the workflow
            del self._workflows[workflow_id]
            
            log_workflow_event(workflow_id, "deleted", {
                "name": workflow.name,
                "agent_count": workflow.agent_count
            })
            
            self.logger.info(f"Deleted workflow: {workflow_id}")
            return True
            
        except Exception as e:
            raise WorkflowDeletionError(workflow_id, str(e))
    
    @handle_service_error
    async def get_workflow_stats(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow statistics."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None
        
        stats = {
            "workflow_id": workflow_id,
            "name": workflow.name,
            "status": workflow.status,
            "created_at": workflow.created_at,
            "last_modified": workflow.last_modified,
            "agent_count": workflow.agent_count,
            "active_agents": len([a for a in workflow.agents if a.status == "running"]),
            "idle_agents": len([a for a in workflow.agents if a.status == "idle"]),
            "error_agents": len([a for a in workflow.agents if a.status == "error"])
        }
        
        return stats
    
    @handle_service_error
    async def update_workflow_status(self, workflow_id: str, status: WorkflowStatus) -> bool:
        """Update workflow status."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False
        
        old_status = workflow.status
        workflow.status = status
        workflow.last_modified = datetime.now()
        
        log_workflow_event(workflow_id, "status_changed", {
            "old_status": old_status,
            "new_status": status
        })
        
        self.logger.info(f"Updated workflow {workflow_id} status: {old_status} -> {status}")
        return True
    
    # Helper methods
    def _find_workflow_by_name(self, name: str) -> Optional[WorkflowResponse]:
        """Find workflow by name."""
        for workflow in self._workflows.values():
            if workflow.name == name:
                return workflow
        return None
    
    def _validate_workflow_data(self, workflow_data: WorkflowCreate) -> None:
        """Validate workflow data."""
        if not workflow_data.name or not workflow_data.name.strip():
            raise ValueError("Workflow name is required")
        
        if len(workflow_data.name) > 100:
            raise ValueError("Workflow name must be less than 100 characters")
    
    # Internal methods for agent service integration
    async def _add_agent_to_workflow(self, workflow_id: str, agent_id: str) -> bool:
        """Add an agent to a workflow (called by agent service)."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False
        
        workflow.agent_count += 1
        workflow.last_modified = datetime.now()
        
        log_workflow_event(workflow_id, "agent_added", {"agent_id": agent_id})
        return True
    
    async def _remove_agent_from_workflow(self, workflow_id: str, agent_id: str) -> bool:
        """Remove an agent from a workflow (called by agent service)."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False
        
        workflow.agent_count = max(0, workflow.agent_count - 1)
        workflow.last_modified = datetime.now()
        
        log_workflow_event(workflow_id, "agent_removed", {"agent_id": agent_id})
        return True 