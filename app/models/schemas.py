"""Pydantic models and schemas for LangGraph Agent Management System."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class AgentType(str, Enum):
    """Agent type enumeration."""
    MAIN = "main"
    CHILD = "child"

class AgentStatusEnum(str, Enum):
    """Agent status enumeration."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"

class WorkflowStatus(str, Enum):
    """Workflow status enumeration."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"

# LLM Configuration
class LLMConfig(BaseModel):
    """LLM configuration model."""
    provider: str = Field(..., description="LLM provider (openai, anthropic, etc.)")
    model: str = Field(..., description="Model name")
    api_key: Optional[str] = Field(None, description="API key for the LLM")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Temperature for LLM responses")
    max_tokens: int = Field(1000, gt=0, description="Maximum tokens for LLM responses")
    additional_config: Optional[Dict[str, Any]] = Field(None, description="Additional LLM configuration")

# MCP Server Configuration
class MCPConnection(BaseModel):
    """MCP server connection configuration."""
    server_name: str = Field(..., description="Name of the MCP server")
    server_url: str = Field(..., description="URL of the MCP server")
    auth_token: Optional[str] = Field(None, description="Authentication token")
    capabilities: List[str] = Field(default_factory=list, description="Available capabilities")

# Task models (for future use in task delegation)
class TaskCreate(BaseModel):
    """Task creation model for delegation."""
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")
    priority: int = Field(1, ge=1, le=5, description="Task priority (1=highest, 5=lowest)")
    status: str = Field("pending", description="Task status")

class Task(BaseModel):
    """Task model."""
    id: str = Field(..., description="Unique task identifier")
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")
    status: str = Field("pending", description="Task status")
    priority: int = Field(1, ge=1, le=5, description="Task priority (1=highest, 5=lowest)")
    created_at: datetime = Field(default_factory=datetime.now, description="Task creation timestamp")
    assigned_to: Optional[str] = Field(None, description="Agent ID assigned to this task")

# Agent models
class AgentBase(BaseModel):
    """Base agent model."""
    name: str = Field(..., description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    agent_type: AgentType = Field(AgentType.MAIN, description="Agent type")
    llm_config: LLMConfig = Field(..., description="LLM configuration")
    mcp_connections: List[MCPConnection] = Field(default_factory=list, description="MCP server connections")
    max_child_agents: int = Field(5, ge=0, description="Maximum number of child agents this agent can spawn")

class AgentCreate(AgentBase):
    """Agent creation model."""
    pass

class AgentResponse(AgentBase):
    """Agent response model."""
    id: str = Field(..., description="Unique agent identifier")
    workflow_id: str = Field(..., description="Workflow ID this agent belongs to")
    parent_agent_id: Optional[str] = Field(None, description="Parent agent ID (for child agents)")
    status: AgentStatusEnum = Field(AgentStatusEnum.IDLE, description="Agent status")
    status_description: str = Field("Agent is idle", description="Detailed description of current status")
    status_updated_at: datetime = Field(default_factory=datetime.now, description="When status was last updated")
    created_at: datetime = Field(default_factory=datetime.now, description="Agent creation timestamp")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")
    connected_agents: List[str] = Field(default_factory=list, description="List of connected agent IDs")
    child_agents: List[str] = Field(default_factory=list, description="List of child agent IDs")
    tasks: List[Task] = Field(default_factory=list, description="Assigned tasks (for future use)")

class AgentList(BaseModel):
    """Agent list response model."""
    agents: List[AgentResponse] = Field(..., description="List of agents")
    total: int = Field(..., description="Total number of agents")

class AgentConnection(BaseModel):
    """Agent connection model."""
    target_agent_id: str = Field(..., description="Target agent ID to connect to")
    connection_type: str = Field("delegation", description="Type of connection")

class TaskDelegation(BaseModel):
    """Task delegation model."""
    task_id: str = Field(..., description="ID of the task to delegate")
    target_agent_id: str = Field(..., description="ID of the target agent to delegate to")

class TaskCompletion(BaseModel):
    """Task completion notification model."""
    task_id: str = Field(..., description="ID of the completed task")
    result: Dict[str, Any] = Field(..., description="Task completion result")

class StatusBroadcast(BaseModel):
    """Status broadcast model."""
    status: AgentStatusEnum = Field(..., description="New agent status")
    message: str = Field("", description="Optional message about the status change")

class AgentStatusUpdate(BaseModel):
    """Agent status update model."""
    status: AgentStatusEnum = Field(..., description="New agent status")
    description: Optional[str] = Field(None, description="Detailed description of the status change")

class AgentStatus(BaseModel):
    """Agent status model."""
    agent_id: str = Field(..., description="Agent ID")
    status: AgentStatusEnum = Field(..., description="Current status")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")
    resource_usage: Dict[str, Any] = Field(default_factory=dict, description="Resource usage statistics")
    connected_agents: List[str] = Field(default_factory=list, description="Connected agent IDs")
    active_tasks: int = Field(0, description="Number of active tasks")
    completed_tasks: int = Field(0, description="Number of completed tasks")

# Workflow models
class WorkflowBase(BaseModel):
    """Base workflow model."""
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")

class WorkflowCreate(WorkflowBase):
    """Workflow creation model."""
    pass

class WorkflowResponse(WorkflowBase):
    """Workflow response model."""
    id: str = Field(..., description="Unique workflow identifier")
    status: WorkflowStatus = Field(WorkflowStatus.ACTIVE, description="Workflow status")
    created_at: datetime = Field(default_factory=datetime.now, description="Workflow creation timestamp")
    last_modified: datetime = Field(default_factory=datetime.now, description="Last modification timestamp")
    agent_count: int = Field(0, description="Number of agents in this workflow")
    agents: List[AgentResponse] = Field(default_factory=list, description="List of agents in this workflow")

class WorkflowList(BaseModel):
    """Workflow list response model."""
    workflows: List[WorkflowResponse] = Field(..., description="List of workflows")
    total: int = Field(..., description="Total number of workflows")

# Error models
class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp") 