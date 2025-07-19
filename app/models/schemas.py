"""Pydantic models and schemas for LangGraph Agent Management System."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class AgentType(str, Enum):
    """Agent type enumeration."""

    MAIN = "main"
    CHILD = "child"
    API_AGENT = "api_agent"
    DATA_AGENT = "data_agent"
    FILE_AGENT = "file_agent"
    NOTIFICATION_AGENT = "notification_agent"
    GENERAL_AGENT = "general_agent"


class AgentStatusEnum(str, Enum):
    """Agent status enumeration."""

    IDLE = "idle"
    BUSY = "busy"
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


class TaskStatus(str, Enum):
    """Task status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IntelligenceLevel(str, Enum):
    """Intelligence level for task execution."""

    BASIC = "basic"  # No LLM access, predefined logic only
    ADAPTIVE = "adaptive"  # LLM access for error recovery only
    INTELLIGENT = "intelligent"  # LLM access for decisions and adaptations
    AUTONOMOUS = "autonomous"  # Full LLM access for planning and execution


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
    llm_config: Optional[LLMConfig] = Field(None, description="LLM configuration")
    mcp_connections: List[MCPConnection] = Field(default_factory=list, description="MCP server connections")
    max_child_agents: int = Field(5, ge=0, description="Maximum number of child agents this agent can spawn")


class AgentCreate(AgentBase):
    """Agent creation model."""

    capabilities: Optional[List[str]] = Field(default_factory=list, description="Agent capabilities")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Agent configuration")


class Agent(BaseModel):
    """Internal agent model for storage."""

    id: str = Field(..., description="Unique agent identifier")
    workflow_id: str = Field(..., description="Workflow ID this agent belongs to")
    name: str = Field(..., description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    agent_type: AgentType = Field(AgentType.MAIN, description="Agent type")
    status: AgentStatusEnum = Field(AgentStatusEnum.IDLE, description="Agent status")
    status_description: str = Field("Agent is idle", description="Detailed description of current status")
    status_updated_at: datetime = Field(default_factory=datetime.now, description="When status was last updated")
    created_at: datetime = Field(default_factory=datetime.now, description="Agent creation timestamp")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")
    tasks: List[Task] = Field(default_factory=list, description="Assigned tasks")
    child_agents: List[str] = Field(default_factory=list, description="List of child agent IDs")
    parent_agent_id: Optional[str] = Field(None, description="Parent agent ID (for child agents)")
    connected_agents: List[str] = Field(default_factory=list, description="List of connected agent IDs")
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    config: Dict[str, Any] = Field(default_factory=dict, description="Agent configuration")
    llm_config: Optional[LLMConfig] = Field(None, description="LLM configuration")
    max_child_agents: int = Field(5, ge=0, description="Maximum number of child agents this agent can spawn")


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
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    config: Dict[str, Any] = Field(default_factory=dict, description="Agent configuration")


class AgentList(BaseModel):
    """Agent list response model."""

    agents: List[AgentResponse] = Field(..., description="List of agents")
    total: int = Field(..., description="Total number of agents")


class AgentConnection(BaseModel):
    """Agent connection model."""

    target_agent_id: str = Field(..., description="Target agent ID to connect to")
    connection_type: str = Field("delegation", description="Type of connection")


# Task Update model
class TaskUpdate(BaseModel):
    """Task update model."""

    title: Optional[str] = Field(None, description="Updated task title")
    description: Optional[str] = Field(None, description="Updated task description")
    status: Optional[str] = Field(None, description="Updated task status")
    priority: Optional[int] = Field(None, ge=1, le=5, description="Updated task priority")


class TaskDelegation(BaseModel):
    """Task delegation model."""

    task_id: str = Field(..., description="ID of the task to delegate")
    target_agent_id: str = Field(..., description="ID of the target agent to delegate to")


# Enhanced Task Delegation Models for Workflow-Driven Delegation
class TaskDelegationRequest(BaseModel):
    """Request to delegate a task to another agent during workflow execution."""

    target_agent_id: str = Field(..., description="Agent to delegate to")
    task_title: str = Field(..., description="Title of the delegated task")
    task_description: str = Field(..., description="Description of the delegated task")
    task_inputs: Dict[str, Any] = Field(default_factory=dict, description="Input data for the task")
    priority: int = Field(1, ge=1, le=5, description="Task priority (1=highest, 5=lowest)")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context from delegating agent")
    dependencies: List[str] = Field(default_factory=list, description="Dependencies for this delegated task")


class TaskDelegationResult(BaseModel):
    """Result of task delegation."""

    delegated_task_id: str = Field(..., description="ID of the created delegated task")
    target_agent_id: str = Field(..., description="Agent that received the delegation")
    delegating_agent_id: str = Field(..., description="Agent that created the delegation")
    status: str = Field(..., description="Delegation status")
    created_at: datetime = Field(default_factory=datetime.now, description="Delegation creation time")


class DynamicWorkflowStep(BaseModel):
    """A dynamically created workflow step from agent delegation."""

    step_id: str = Field(..., description="Unique step identifier")
    parent_step_id: str = Field(..., description="ID of the step that created this one")
    delegating_agent_id: str = Field(..., description="Agent that created this step")
    target_agent_id: str = Field(..., description="Agent that will execute this step")
    action: str = Field(..., description="Action to perform")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Step inputs")
    context: Dict[str, Any] = Field(default_factory=dict, description="Execution context")
    status: str = Field("pending", description="Step status")
    dependencies: List[str] = Field(default_factory=list, description="Step dependencies")
    created_at: datetime = Field(default_factory=datetime.now, description="Step creation time")
    priority: int = Field(1, ge=1, le=5, description="Step priority")


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


# Task execution models for persistence
class TaskExecution(BaseModel):
    """Task execution data model."""

    task_id: str = Field(..., description="Task identifier")
    workflow_id: str = Field(..., description="Workflow identifier")
    agent_id: str = Field(..., description="Agent identifier")
    status: TaskStatus = Field(TaskStatus.PENDING, description="Task status")
    intelligence_level: IntelligenceLevel = Field(IntelligenceLevel.BASIC, description="Intelligence level")
    task_data: Dict[str, Any] = Field(default_factory=dict, description="Task data")
    result: Optional[Dict[str, Any]] = Field(None, description="Task result")
    error: Optional[str] = Field(None, description="Error message if failed")
    started_at: Optional[datetime] = Field(None, description="Task start time")
    completed_at: Optional[datetime] = Field(None, description="Task completion time")
    created_at: datetime = Field(default_factory=datetime.now, description="Task creation time")


class WorkflowPlan(BaseModel):
    """Workflow plan data model."""

    workflow_id: str = Field(..., description="Workflow identifier")
    title: str = Field(..., description="Workflow title")
    description: str = Field(..., description="Workflow description")
    steps: List[Dict[str, Any]] = Field(default_factory=list, description="Workflow steps")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.now, description="Plan creation time")
    last_modified: datetime = Field(default_factory=datetime.now, description="Last modification timestamp")
    agent_count: int = Field(0, description="Number of agents in this workflow")
    agents: List[AgentResponse] = Field(default_factory=list, description="List of agents in this workflow")


class WorkflowList(BaseModel):
    """Workflow list response model."""

    workflows: List[WorkflowResponse] = Field(..., description="List of workflows")
    total: int = Field(..., description="Total number of workflows")


# Agent Status History models
class AgentStatusHistory(BaseModel):
    """Agent status change history."""

    agent_id: str = Field(..., description="Agent ID")
    old_status: AgentStatusEnum = Field(..., description="Previous status")
    new_status: AgentStatusEnum = Field(..., description="New status")
    description: str = Field(..., description="Status change description")
    changed_at: datetime = Field(default_factory=datetime.now, description="When the status changed")
    changed_by: Optional[str] = Field(None, description="Who/what triggered the change")
    additional_context: Optional[Dict[str, Any]] = Field(None, description="Additional context about the change")


class AgentStatusHistoryResponse(BaseModel):
    """Response model for status history queries."""

    agent_id: str = Field(..., description="Agent ID")
    agent_name: str = Field(..., description="Agent name")
    history: List[AgentStatusHistory] = Field(..., description="Status change history")
    total_changes: int = Field(..., description="Total number of status changes")
    date_range: Dict[str, datetime] = Field(..., description="Date range of the history")


# Enhanced Status Response models
class WorkflowStatusSummary(BaseModel):
    """Workflow status summary response model."""

    workflow_id: str = Field(..., description="Workflow ID")
    total_agents: int = Field(..., description="Total number of agents in workflow")
    status_breakdown: Dict[str, int] = Field(..., description="Count of agents by status")
    agents: List[Dict[str, Any]] = Field(..., description="Agent status details")
    last_updated: str = Field(..., description="Last update timestamp")


class SystemStatusOverview(BaseModel):
    """System status overview response model."""

    system_health: str = Field(..., description="Overall system health")
    timestamp: str = Field(..., description="Report timestamp")
    totals: Dict[str, int] = Field(..., description="System totals")
    agent_status_breakdown: Dict[str, int] = Field(..., description="Agent status counts")
    workflow_distribution: Dict[str, int] = Field(..., description="Agents per workflow")
    problematic_agents: List[Dict[str, Any]] = Field(..., description="Agents needing attention")
    system_metrics: Dict[str, float] = Field(..., description="System performance metrics")


class AgentHealthCheck(BaseModel):
    """Agent health check response model."""

    agent_id: str = Field(..., description="Agent ID")
    health_status: str = Field(..., description="Health status (healthy, warning, critical)")
    health_issues: List[str] = Field(..., description="List of health issues")
    uptime_seconds: float = Field(..., description="Agent uptime in seconds")
    time_since_last_activity_seconds: float = Field(..., description="Time since last activity")
    current_status: str = Field(..., description="Current agent status")
    status_description: str = Field(..., description="Status description")
    resource_usage: Dict[str, float] = Field(..., description="Resource usage metrics")
    task_statistics: Dict[str, int] = Field(..., description="Task-related statistics")
    connection_statistics: Dict[str, Any] = Field(..., description="Connection-related statistics")
    last_health_check: str = Field(..., description="Health check timestamp")


# Error models
class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
