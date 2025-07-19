"""Tests for agent functionality."""

import pytest
from datetime import datetime
from app.models.schemas import (
    AgentCreate, AgentType, AgentStatusEnum, LLMConfig, MCPConnection,
    WorkflowCreate
)
from app.services.agent_service import AgentService
from app.services.workflow_service import WorkflowService

@pytest.fixture
def agent_service():
    """Create an agent service instance."""
    return AgentService()

@pytest.fixture
def workflow_service():
    """Create a workflow service instance."""
    return WorkflowService()

@pytest.fixture
async def sample_workflow(workflow_service):
    """Create a sample workflow."""
    workflow_data = WorkflowCreate(
        name="Test Workflow",
        description="A test workflow for agent testing"
    )
    return await workflow_service.create_workflow(workflow_data)

@pytest.fixture
def sample_llm_config():
    """Create sample LLM configuration."""
    return LLMConfig(
        provider="openai",
        model="gpt-4",
        temperature=0.7,
        max_tokens=1000
    )

@pytest.fixture
def sample_agent_data(sample_llm_config):
    """Create sample agent data."""
    return AgentCreate(
        name="Test Agent",
        description="A test agent for unit testing",
        agent_type=AgentType.MAIN,
        llm_config=sample_llm_config,
        mcp_connections=[],
        max_child_agents=5
    )

class TestAgentService:
    """Test agent service functionality."""
    
    @pytest.mark.asyncio
    async def test_create_agent(self, agent_service, sample_workflow, sample_agent_data):
        """Test agent creation."""
        agent = await agent_service.create_agent(sample_workflow.id, sample_agent_data)
        
        assert agent.id is not None
        assert agent.workflow_id == sample_workflow.id
        assert agent.name == sample_agent_data.name
        assert agent.description == sample_agent_data.description
        assert agent.agent_type == sample_agent_data.agent_type
        assert agent.status == AgentStatusEnum.IDLE
        assert agent.llm_config.provider == sample_agent_data.llm_config.provider
        assert agent.llm_config.model == sample_agent_data.llm_config.model
        assert agent.max_child_agents == sample_agent_data.max_child_agents
        assert len(agent.connected_agents) == 0
        assert len(agent.child_agents) == 0
        assert len(agent.tasks) == 0
        assert isinstance(agent.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_get_agent(self, agent_service, sample_workflow, sample_agent_data):
        """Test agent retrieval."""
        # Create an agent first
        created_agent = await agent_service.create_agent(sample_workflow.id, sample_agent_data)
        
        # Retrieve it
        retrieved_agent = await agent_service.get_agent(created_agent.id)
        
        assert retrieved_agent is not None
        assert retrieved_agent.id == created_agent.id
        assert retrieved_agent.name == created_agent.name
        assert retrieved_agent.workflow_id == created_agent.workflow_id
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_agent(self, agent_service):
        """Test retrieving a non-existent agent."""
        agent = await agent_service.get_agent("nonexistent-id")
        assert agent is None
    
    @pytest.mark.asyncio
    async def test_list_agents(self, agent_service, sample_workflow, sample_agent_data):
        """Test listing agents in a workflow."""
        # Initially empty
        agent_list = await agent_service.list_agents(sample_workflow.id)
        assert agent_list.total == 0
        assert len(agent_list.agents) == 0
        
        # Create an agent
        await agent_service.create_agent(sample_workflow.id, sample_agent_data)
        
        # List should now contain one agent
        agent_list = await agent_service.list_agents(sample_workflow.id)
        assert agent_list.total == 1
        assert len(agent_list.agents) == 1
        assert agent_list.agents[0].name == sample_agent_data.name
    
    @pytest.mark.asyncio
    async def test_update_agent(self, agent_service, sample_workflow, sample_agent_data):
        """Test agent update."""
        # Create an agent
        agent = await agent_service.create_agent(sample_workflow.id, sample_agent_data)
        
        # Update it
        updates = {"description": "Updated description"}
        updated_agent = await agent_service.update_agent(agent.id, updates)
        
        assert updated_agent is not None
        assert updated_agent.description == "Updated description"
        assert updated_agent.last_activity is not None
    
    @pytest.mark.asyncio
    async def test_delete_agent(self, agent_service, sample_workflow, sample_agent_data):
        """Test agent deletion."""
        # Create an agent
        agent = await agent_service.create_agent(sample_workflow.id, sample_agent_data)
        
        # Delete it
        result = await agent_service.delete_agent(agent.id)
        assert result is True
        
        # Verify it's gone
        retrieved_agent = await agent_service.get_agent(agent.id)
        assert retrieved_agent is None
    
    @pytest.mark.asyncio
    async def test_connect_agents(self, agent_service, sample_workflow, sample_agent_data):
        """Test connecting two agents."""
        # Create two agents
        agent1 = await agent_service.create_agent(sample_workflow.id, sample_agent_data)
        
        agent2_data = sample_agent_data.copy()
        agent2_data.name = "Test Agent 2"
        agent2 = await agent_service.create_agent(sample_workflow.id, agent2_data)
        
        # Connect them
        result = await agent_service.connect_agents(agent1.id, agent2.id)
        assert result is True
        
        # Verify connection
        updated_agent1 = await agent_service.get_agent(agent1.id)
        assert agent2.id in updated_agent1.connected_agents
    
    @pytest.mark.asyncio
    async def test_get_agent_status(self, agent_service, sample_workflow, sample_agent_data):
        """Test getting agent status."""
        # Create an agent
        agent = await agent_service.create_agent(sample_workflow.id, sample_agent_data)
        
        # Get status
        status = await agent_service.get_agent_status(agent.id)
        
        assert status is not None
        assert status.agent_id == agent.id
        assert status.status == AgentStatusEnum.IDLE
        assert isinstance(status.resource_usage, dict)
        assert status.active_tasks == 0
        assert status.completed_tasks == 0
    
    @pytest.mark.asyncio
    async def test_spawn_child_agent(self, agent_service, sample_workflow, sample_agent_data):
        """Test spawning a child agent."""
        # Create parent agent
        parent_agent = await agent_service.create_agent(sample_workflow.id, sample_agent_data)
        
        # Create child agent data
        child_data = sample_agent_data.copy()
        child_data.name = "Child Agent"
        
        # Spawn child
        child_agent = await agent_service.spawn_child_agent(parent_agent.id, child_data)
        
        assert child_agent is not None
        assert child_agent.agent_type == AgentType.CHILD
        assert child_agent.parent_agent_id == parent_agent.id
        assert child_agent.workflow_id == parent_agent.workflow_id
        
        # Verify parent has child in list
        updated_parent = await agent_service.get_agent(parent_agent.id)
        assert child_agent.id in updated_parent.child_agents
    
    @pytest.mark.asyncio
    async def test_update_agent_status(self, agent_service, sample_workflow, sample_agent_data):
        """Test updating agent status."""
        # Create an agent
        agent = await agent_service.create_agent(sample_workflow.id, sample_agent_data)
        
        # Update status
        result = await agent_service.update_agent_status(agent.id, AgentStatusEnum.RUNNING)
        assert result is True
        
        # Verify status changed
        updated_agent = await agent_service.get_agent(agent.id)
        assert updated_agent.status == AgentStatusEnum.RUNNING
    
    @pytest.mark.asyncio
    async def test_get_workflow_agents(self, agent_service, sample_workflow, sample_agent_data):
        """Test getting all agents in a workflow."""
        # Initially empty
        agent_ids = await agent_service.get_workflow_agents(sample_workflow.id)
        assert len(agent_ids) == 0
        
        # Create an agent
        agent = await agent_service.create_agent(sample_workflow.id, sample_agent_data)
        
        # Should now have one agent
        agent_ids = await agent_service.get_workflow_agents(sample_workflow.id)
        assert len(agent_ids) == 1
        assert agent.id in agent_ids 