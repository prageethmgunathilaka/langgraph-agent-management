"""Agent service for managing LangGraph agents."""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.schemas import (
    AgentCreate, AgentResponse, AgentList, AgentStatus, 
    AgentType, AgentStatusEnum, Task, TaskCreate
)
from app.utils.logger import LoggerMixin, log_agent_event
from app.utils.config import get_settings
from app.utils.errors import (
    AgentNotFoundError,
    AgentAlreadyExistsError,
    AgentLimitExceededError,
    AgentConnectionError,
    AgentSpawnError,
    WorkflowNotFoundError,
    handle_service_error
)

class AgentService(LoggerMixin):
    """Service for managing LangGraph agents."""
    
    def __init__(self):
        # In-memory storage for MVP (would be replaced with database)
        self._agents: Dict[str, AgentResponse] = {}
        self._agent_connections: Dict[str, List[str]] = {}  # agent_id -> [connected_agent_ids]
        self._workflow_agents: Dict[str, List[str]] = {}  # workflow_id -> [agent_ids]
        self.settings = get_settings()
        self.logger.info("AgentService initialized")
    
    @handle_service_error
    async def create_agent(self, workflow_id: str, agent_data: AgentCreate) -> AgentResponse:
        """Create a new agent in a workflow."""
        agent_id = str(uuid.uuid4())
        
        # Check workflow agent limit
        current_agents = len(self._workflow_agents.get(workflow_id, []))
        if current_agents >= self.settings.max_agents_per_workflow:
            raise AgentLimitExceededError(
                "Workflow agents", 
                current_agents, 
                self.settings.max_agents_per_workflow
            )
        
        # Initialize empty tasks list for future use
        initial_tasks = []
        
        # Create new agent
        agent = AgentResponse(
            id=agent_id,
            workflow_id=workflow_id,
            parent_agent_id=None,  # Fixed: Added missing parameter
            name=agent_data.name,
            description=agent_data.description,
            agent_type=agent_data.agent_type,
            llm_config=agent_data.llm_config,
            mcp_connections=agent_data.mcp_connections,
            max_child_agents=agent_data.max_child_agents,
            status=AgentStatusEnum.IDLE,
            created_at=datetime.now(),
            last_activity=None,
            connected_agents=[],
            child_agents=[],
            tasks=initial_tasks
        )
        
        # Store agent
        self._agents[agent_id] = agent
        
        # Add to workflow
        if workflow_id not in self._workflow_agents:
            self._workflow_agents[workflow_id] = []
        self._workflow_agents[workflow_id].append(agent_id)
        
        # Initialize connections
        self._agent_connections[agent_id] = []
        
        log_agent_event(agent_id, "created", {
            "workflow_id": workflow_id,
            "name": agent.name,
            "type": agent.agent_type
        })
        
        self.logger.info(f"Created agent: {agent_id} in workflow: {workflow_id}")
        return agent
    
    @handle_service_error
    async def get_agent(self, agent_id: str) -> Optional[AgentResponse]:
        """Get an agent by ID."""
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        
        # Update connected agents list
        agent.connected_agents = self._agent_connections.get(agent_id, [])
        
        log_agent_event(agent_id, "retrieved")
        return agent
    
    @handle_service_error
    async def list_agents(self, workflow_id: str) -> AgentList:
        """List all agents in a workflow."""
        agent_ids = self._workflow_agents.get(workflow_id, [])
        agents = []
        
        for agent_id in agent_ids:
            agent = self._agents.get(agent_id)
            if agent:
                # Update connected agents list
                agent.connected_agents = self._agent_connections.get(agent_id, [])
                agents.append(agent)
        
        # Sort by creation date (newest first)
        agents.sort(key=lambda a: a.created_at, reverse=True)
        
        self.logger.info(f"Listed {len(agents)} agents in workflow: {workflow_id}")
        return AgentList(
            agents=agents,
            total=len(agents)
        )
    
    @handle_service_error
    async def update_agent(self, agent_id: str, updates: Dict[str, Any]) -> Optional[AgentResponse]:
        """Update an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        
        # Update fields
        for field, value in updates.items():
            if hasattr(agent, field):
                setattr(agent, field, value)
        
        # Update last activity
        agent.last_activity = datetime.now()
        
        log_agent_event(agent_id, "updated", updates)
        self.logger.info(f"Updated agent: {agent_id}")
        return agent
    
    @handle_service_error
    async def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        
        try:
            # Remove from workflow
            workflow_id = agent.workflow_id
            if workflow_id in self._workflow_agents:
                if agent_id in self._workflow_agents[workflow_id]:
                    self._workflow_agents[workflow_id].remove(agent_id)
            
            # Remove connections
            if agent_id in self._agent_connections:
                # Remove this agent from other agents' connection lists
                for other_agent_id, connections in self._agent_connections.items():
                    if agent_id in connections:
                        connections.remove(agent_id)
                
                # Remove this agent's connections
                del self._agent_connections[agent_id]
            
            # Delete child agents
            for child_id in agent.child_agents:
                await self.delete_agent(child_id)
            
            # Remove from storage
            del self._agents[agent_id]
            
            log_agent_event(agent_id, "deleted", {
                "workflow_id": workflow_id,
                "name": agent.name
            })
            
            self.logger.info(f"Deleted agent: {agent_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete agent {agent_id}: {str(e)}")
            return False
    
    @handle_service_error
    async def connect_agents(self, agent_id: str, target_agent_id: str) -> bool:
        """Connect two agents bidirectionally."""
        agent = self._agents.get(agent_id)
        target_agent = self._agents.get(target_agent_id)
        
        if not agent or not target_agent:
            return False
        
        # Check if agents are in the same workflow
        if agent.workflow_id != target_agent.workflow_id:
            raise AgentConnectionError(
                agent_id, 
                target_agent_id, 
                "Agents must be in the same workflow"
            )
        
        # Prevent self-connection
        if agent_id == target_agent_id:
            raise AgentConnectionError(
                agent_id, 
                target_agent_id, 
                "Agent cannot connect to itself"
            )
        
        # Add bidirectional connection
        if agent_id not in self._agent_connections:
            self._agent_connections[agent_id] = []
        if target_agent_id not in self._agent_connections:
            self._agent_connections[target_agent_id] = []
        
        # Add connections if not already present
        if target_agent_id not in self._agent_connections[agent_id]:
            self._agent_connections[agent_id].append(target_agent_id)
        if agent_id not in self._agent_connections[target_agent_id]:
            self._agent_connections[target_agent_id].append(agent_id)
        
        # Update both agents' connected_agents lists
        agent.connected_agents = self._agent_connections[agent_id]
        target_agent.connected_agents = self._agent_connections[target_agent_id]
        agent.last_activity = datetime.now()
        target_agent.last_activity = datetime.now()
        
        log_agent_event(agent_id, "connected", {
            "target_agent_id": target_agent_id,
            "workflow_id": agent.workflow_id
        })
        
        self.logger.info(f"Connected agents bidirectionally: {agent_id} <-> {target_agent_id}")
        return True
    
    @handle_service_error
    async def disconnect_agents(self, agent_id: str, target_agent_id: str) -> bool:
        """Disconnect two agents bidirectionally."""
        agent = self._agents.get(agent_id)
        target_agent = self._agents.get(target_agent_id)
        
        if not agent or not target_agent:
            return False
        
        # Remove bidirectional connection
        if agent_id in self._agent_connections:
            if target_agent_id in self._agent_connections[agent_id]:
                self._agent_connections[agent_id].remove(target_agent_id)
        
        if target_agent_id in self._agent_connections:
            if agent_id in self._agent_connections[target_agent_id]:
                self._agent_connections[target_agent_id].remove(agent_id)
        
        # Update both agents' connected_agents lists
        agent.connected_agents = self._agent_connections.get(agent_id, [])
        target_agent.connected_agents = self._agent_connections.get(target_agent_id, [])
        agent.last_activity = datetime.now()
        target_agent.last_activity = datetime.now()
        
        log_agent_event(agent_id, "disconnected", {
            "target_agent_id": target_agent_id,
            "workflow_id": agent.workflow_id
        })
        
        self.logger.info(f"Disconnected agents: {agent_id} <-> {target_agent_id}")
        return True
    
    @handle_service_error
    async def get_connected_agents(self, agent_id: str) -> List[AgentResponse]:
        """Get all agents connected to the specified agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return []
        
        connected_agent_ids = self._agent_connections.get(agent_id, [])
        connected_agents = []
        
        for connected_id in connected_agent_ids:
            connected_agent = self._agents.get(connected_id)
            if connected_agent:
                connected_agents.append(connected_agent)
        
        self.logger.info(f"Retrieved {len(connected_agents)} connected agents for: {agent_id}")
        return connected_agents
    
    @handle_service_error
    async def get_agent_status(self, agent_id: str) -> Optional[AgentStatus]:
        """Get agent status and details."""
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        
        # Calculate task statistics
        active_tasks = len([t for t in agent.tasks if t.status == "running"])
        completed_tasks = len([t for t in agent.tasks if t.status == "completed"])
        
        # Mock resource usage (in real implementation, would get actual metrics)
        resource_usage = {
            "cpu_percent": 25.5,
            "memory_mb": 128.7,
            "active_connections": len(agent.connected_agents),
            "uptime_seconds": (datetime.now() - agent.created_at).total_seconds()
        }
        
        status = AgentStatus(
            agent_id=agent_id,
            status=agent.status,
            last_activity=agent.last_activity,
            resource_usage=resource_usage,
            connected_agents=self._agent_connections.get(agent_id, []),
            active_tasks=active_tasks,
            completed_tasks=completed_tasks
        )
        
        return status
    
    @handle_service_error
    async def spawn_child_agent(self, parent_id: str, child_data: AgentCreate) -> AgentResponse:
        """Spawn a child agent from a parent agent."""
        parent = self._agents.get(parent_id)
        if not parent:
            raise AgentNotFoundError(parent_id)
        
        # Check child agent limit
        current_children = len(parent.child_agents)
        if current_children >= parent.max_child_agents:
            raise AgentLimitExceededError(
                "Child agents", 
                current_children, 
                parent.max_child_agents
            )
        
        # Create child agent
        child_data.agent_type = AgentType.CHILD
        child_agent = await self.create_agent(parent.workflow_id, child_data)
        
        # Set parent relationship
        child_agent.parent_agent_id = parent_id
        
        # Add to parent's child list
        parent.child_agents.append(child_agent.id)
        parent.last_activity = datetime.now()
        
        log_agent_event(parent_id, "spawned_child", {
            "child_agent_id": child_agent.id,
            "child_name": child_agent.name
        })
        
        self.logger.info(f"Spawned child agent: {child_agent.id} from parent: {parent_id}")
        return child_agent
    
    @handle_service_error
    async def update_agent_status(self, agent_id: str, status: AgentStatusEnum) -> bool:
        """Update agent status."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        
        old_status = agent.status
        agent.status = status
        agent.last_activity = datetime.now()
        
        log_agent_event(agent_id, "status_changed", {
            "old_status": old_status,
            "new_status": status
        })
        
        self.logger.info(f"Updated agent {agent_id} status: {old_status} -> {status}")
        return True
    
    @handle_service_error
    async def assign_task(self, agent_id: str, task: Task) -> bool:
        """Assign a task to an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        
        # Add task to agent
        agent.tasks.append(task)
        agent.last_activity = datetime.now()
        
        log_agent_event(agent_id, "task_assigned", {
            "task_id": task.id,
            "task_title": task.title
        })
        
        self.logger.info(f"Assigned task {task.id} to agent: {agent_id}")
        return True
    
    @handle_service_error
    async def delegate_task(self, from_agent_id: str, to_agent_id: str, task: Task) -> bool:
        """Delegate a task from one agent to another connected agent."""
        from_agent = self._agents.get(from_agent_id)
        to_agent = self._agents.get(to_agent_id)
        
        if not from_agent or not to_agent:
            return False
        
        # Check if agents are connected
        if to_agent_id not in self._agent_connections.get(from_agent_id, []):
            raise AgentConnectionError(
                from_agent_id, 
                to_agent_id, 
                "Agents must be connected to delegate tasks"
            )
        
        # Update task assignment
        task.assigned_to = to_agent_id
        task.status = "pending"
        
        # Add task to target agent
        to_agent.tasks.append(task)
        to_agent.last_activity = datetime.now()
        
        # Update source agent activity
        from_agent.last_activity = datetime.now()
        
        log_agent_event(from_agent_id, "task_delegated", {
            "task_id": task.id,
            "task_title": task.title,
            "to_agent_id": to_agent_id
        })
        
        log_agent_event(to_agent_id, "task_received", {
            "task_id": task.id,
            "task_title": task.title,
            "from_agent_id": from_agent_id
        })
        
        self.logger.info(f"Delegated task {task.id} from agent {from_agent_id} to agent {to_agent_id}")
        return True
    
    @handle_service_error
    async def spawn_child_task(self, parent_agent_id: str, child_agent_id: str, task_data: TaskCreate) -> bool:
        """Create a new task for a child agent."""
        parent_agent = self._agents.get(parent_agent_id)
        child_agent = self._agents.get(child_agent_id)
        
        if not parent_agent or not child_agent:
            return False
        
        # Check if child agent is actually a child of parent
        if child_agent_id not in parent_agent.child_agents:
            raise AgentConnectionError(
                parent_agent_id, 
                child_agent_id, 
                "Target agent must be a child of the parent agent"
            )
        
        # Create new task
        task = Task(
            id=str(uuid.uuid4()),
            title=task_data.title,
            description=task_data.description,
            status=task_data.status,
            priority=task_data.priority,
            created_at=datetime.now(),
            assigned_to=child_agent_id
        )
        
        # Add task to child agent
        child_agent.tasks.append(task)
        child_agent.last_activity = datetime.now()
        
        # Update parent agent activity
        parent_agent.last_activity = datetime.now()
        
        log_agent_event(parent_agent_id, "child_task_spawned", {
            "task_id": task.id,
            "task_title": task.title,
            "child_agent_id": child_agent_id
        })
        
        log_agent_event(child_agent_id, "task_spawned", {
            "task_id": task.id,
            "task_title": task.title,
            "parent_agent_id": parent_agent_id
        })
        
        self.logger.info(f"Spawned task {task.id} for child agent {child_agent_id} from parent {parent_agent_id}")
        return True
    
    @handle_service_error
    async def notify_task_completion(self, agent_id: str, task_id: str, result: Dict[str, Any]) -> bool:
        """Notify connected agents about task completion."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        
        # Find the task
        task = None
        for t in agent.tasks:
            if t.id == task_id:
                task = t
                break
        
        if not task:
            return False
        
        # Update task status
        task.status = "completed"
        agent.last_activity = datetime.now()
        
        # Notify connected agents
        connected_agent_ids = self._agent_connections.get(agent_id, [])
        for connected_id in connected_agent_ids:
            connected_agent = self._agents.get(connected_id)
            if connected_agent:
                connected_agent.last_activity = datetime.now()
                
                log_agent_event(connected_id, "task_completion_notified", {
                    "task_id": task_id,
                    "task_title": task.title,
                    "completing_agent_id": agent_id,
                    "result": result
                })
        
        # Notify parent agent if this is a child agent
        if agent.parent_agent_id:
            parent_agent = self._agents.get(agent.parent_agent_id)
            if parent_agent:
                parent_agent.last_activity = datetime.now()
                
                log_agent_event(agent.parent_agent_id, "child_task_completed", {
                    "task_id": task_id,
                    "task_title": task.title,
                    "child_agent_id": agent_id,
                    "result": result
                })
        
        log_agent_event(agent_id, "task_completed", {
            "task_id": task_id,
            "task_title": task.title,
            "result": result,
            "notified_agents": len(connected_agent_ids)
        })
        
        self.logger.info(f"Task {task_id} completed by agent {agent_id}, notified {len(connected_agent_ids)} connected agents")
        return True
    
    @handle_service_error
    async def broadcast_status_change(self, agent_id: str, status: AgentStatusEnum, message: str = "") -> bool:
        """Broadcast status change to all connected agents."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        
        # Update agent status
        old_status = agent.status
        agent.status = status
        agent.last_activity = datetime.now()
        
        # Broadcast to connected agents
        connected_agent_ids = self._agent_connections.get(agent_id, [])
        for connected_id in connected_agent_ids:
            connected_agent = self._agents.get(connected_id)
            if connected_agent:
                connected_agent.last_activity = datetime.now()
                
                log_agent_event(connected_id, "status_change_broadcast", {
                    "broadcasting_agent_id": agent_id,
                    "old_status": old_status,
                    "new_status": status,
                    "message": message
                })
        
        log_agent_event(agent_id, "status_broadcasted", {
            "old_status": old_status,
            "new_status": status,
            "message": message,
            "notified_agents": len(connected_agent_ids)
        })
        
        self.logger.info(f"Agent {agent_id} status changed from {old_status} to {status}, broadcasted to {len(connected_agent_ids)} connected agents")
        return True
    
    @handle_service_error
    async def get_workflow_agents(self, workflow_id: str) -> List[str]:
        """Get all agent IDs in a workflow."""
        return self._workflow_agents.get(workflow_id, [])
    
    # Helper methods
    def _validate_agent_data(self, agent_data: AgentCreate) -> None:
        """Validate agent data."""
        if not agent_data.name or not agent_data.name.strip():
            raise ValueError("Agent name is required")
        
        if len(agent_data.name) > 100:
            raise ValueError("Agent name must be less than 100 characters")
        
        if agent_data.max_child_agents < 0:
            raise ValueError("Max child agents must be non-negative")
        
        if agent_data.max_child_agents > self.settings.max_child_agents:
            raise ValueError(f"Max child agents cannot exceed {self.settings.max_child_agents}")
    
    def _validate_llm_config(self, llm_config) -> None:
        """Validate LLM configuration."""
        if not llm_config.provider:
            raise ValueError("LLM provider is required")
        
        if not llm_config.model:
            raise ValueError("LLM model is required")
        
        if llm_config.temperature < 0 or llm_config.temperature > 2:
            raise ValueError("Temperature must be between 0 and 2")
        
        if llm_config.max_tokens <= 0:
            raise ValueError("Max tokens must be positive") 