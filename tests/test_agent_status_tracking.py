"""Tests for Agent Status Tracking with Rich Descriptions (Task 5)."""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from app.services.agent_service import AgentService
from app.services.workflow_service import WorkflowService
from app.models.schemas import (
    AgentCreate, AgentStatusUpdate, AgentStatusEnum,
    WorkflowCreate, LLMConfig, AgentType
)

class TestAgentStatusTracking:
    """Test suite for enhanced agent status tracking functionality."""
    
    @pytest.fixture
    def workflow_service(self):
        """Create a workflow service instance."""
        return WorkflowService()
    
    @pytest.fixture
    def agent_service(self):
        """Create an agent service instance."""
        return AgentService()
    
    @pytest_asyncio.fixture
    async def sample_workflow(self, workflow_service):
        """Create a sample workflow for testing."""
        workflow_data = WorkflowCreate(
            name="Status Test Workflow",
            description="Workflow for testing status tracking"
        )
        return await workflow_service.create_workflow(workflow_data)
    
    @pytest.fixture
    def sample_agent_data(self):
        """Create sample agent data."""
        return AgentCreate(
            name="Status Test Agent",
            description="Agent for testing status tracking",
            agent_type=AgentType.MAIN,
            llm_config=LLMConfig(
                provider="openai",
                model="gpt-4",
                api_key="test-key",
                temperature=0.7,
                max_tokens=1000
            ),
            mcp_connections=[],
            max_child_agents=5
        )
    
    @pytest_asyncio.fixture
    async def sample_agent(self, agent_service, sample_workflow, sample_agent_data):
        """Create a sample agent for testing."""
        return await agent_service.create_agent(sample_workflow.id, sample_agent_data)
    
    # Test 1: Agent Creation with Default Status
    @pytest.mark.asyncio
    async def test_agent_creation_default_status(self, agent_service, sample_workflow, sample_agent_data):
        """Test that agents are created with proper default status and description."""
        agent = await agent_service.create_agent(sample_workflow.id, sample_agent_data)
        
        assert agent is not None
        assert agent.status == AgentStatusEnum.IDLE
        assert agent.status_description == "Agent created and ready to receive tasks"
        assert agent.status_updated_at is not None
        assert isinstance(agent.status_updated_at, datetime)
    
    # Test 2: Update Status with Custom Description
    @pytest.mark.asyncio
    async def test_update_status_with_description(self, agent_service, sample_agent):
        """Test updating agent status with custom description."""
        # Capture original timestamp before update
        original_status_updated_at = sample_agent.status_updated_at
        
        # Small delay to ensure timestamp difference
        import asyncio
        await asyncio.sleep(0.001)
        
        custom_description = "Processing user authentication request"
        status_update = AgentStatusUpdate(
            status=AgentStatusEnum.RUNNING,
            description=custom_description
        )
        
        updated_agent = await agent_service.update_agent_status(sample_agent.id, status_update)
        
        assert updated_agent is not None
        assert updated_agent.status == AgentStatusEnum.RUNNING
        assert updated_agent.status_description == custom_description
        assert updated_agent.status_updated_at > original_status_updated_at
        assert updated_agent.last_activity is not None
    
    # Test 3: Update Status with Default Description
    @pytest.mark.asyncio
    async def test_update_status_with_default_description(self, agent_service, sample_agent):
        """Test updating agent status without custom description (uses default)."""
        # Capture original timestamp before update
        original_status_updated_at = sample_agent.status_updated_at
        
        # Small delay to ensure timestamp difference
        import asyncio
        await asyncio.sleep(0.001)
        
        status_update = AgentStatusUpdate(
            status=AgentStatusEnum.ERROR,
            description=None
        )
        
        updated_agent = await agent_service.update_agent_status(sample_agent.id, status_update)
        
        assert updated_agent is not None
        assert updated_agent.status == AgentStatusEnum.ERROR
        assert updated_agent.status_description == "Agent encountered an error"
        assert updated_agent.status_updated_at > original_status_updated_at
    
    # Test 4: Test All Status Transitions with Default Descriptions
    @pytest.mark.asyncio
    async def test_all_status_transitions(self, agent_service, sample_agent):
        """Test all possible status transitions and their default descriptions."""
        expected_descriptions = {
            AgentStatusEnum.IDLE: "Agent is idle and ready for tasks",
            AgentStatusEnum.RUNNING: "Agent is actively processing tasks",
            AgentStatusEnum.PAUSED: "Agent is paused and not processing tasks",
            AgentStatusEnum.ERROR: "Agent encountered an error",
            AgentStatusEnum.COMPLETED: "Agent has completed all assigned tasks"
        }
        
        for status, expected_desc in expected_descriptions.items():
            status_update = AgentStatusUpdate(status=status, description=None)
            updated_agent = await agent_service.update_agent_status(sample_agent.id, status_update)
            
            assert updated_agent.status == status
            assert updated_agent.status_description == expected_desc
            assert updated_agent.status_updated_at is not None
    
    # Test 5: Error Status with Detailed Description
    @pytest.mark.asyncio
    async def test_error_status_with_details(self, agent_service, sample_agent):
        """Test setting error status with detailed error information."""
        error_description = "Failed to connect to OpenAI API: Invalid API key provided (error code: 401)"
        status_update = AgentStatusUpdate(
            status=AgentStatusEnum.ERROR,
            description=error_description
        )
        
        updated_agent = await agent_service.update_agent_status(sample_agent.id, status_update)
        
        assert updated_agent.status == AgentStatusEnum.ERROR
        assert updated_agent.status_description == error_description
        assert "401" in updated_agent.status_description
        assert "OpenAI API" in updated_agent.status_description
    
    # Test 6: Completed Status with Summary
    @pytest.mark.asyncio
    async def test_completed_status_with_summary(self, agent_service, sample_agent):
        """Test setting completed status with task summary."""
        completion_summary = "Successfully processed 15 tasks: 12 completed, 3 delegated to child agents"
        status_update = AgentStatusUpdate(
            status=AgentStatusEnum.COMPLETED,
            description=completion_summary
        )
        
        updated_agent = await agent_service.update_agent_status(sample_agent.id, status_update)
        
        assert updated_agent.status == AgentStatusEnum.COMPLETED
        assert updated_agent.status_description == completion_summary
        assert "15 tasks" in updated_agent.status_description
        assert "12 completed" in updated_agent.status_description
    
    # Test 7: Running Status with Current Task
    @pytest.mark.asyncio
    async def test_running_status_with_current_task(self, agent_service, sample_agent):
        """Test setting running status with current task information."""
        task_description = "Analyzing customer feedback data using sentiment analysis model"
        status_update = AgentStatusUpdate(
            status=AgentStatusEnum.RUNNING,
            description=task_description
        )
        
        updated_agent = await agent_service.update_agent_status(sample_agent.id, status_update)
        
        assert updated_agent.status == AgentStatusEnum.RUNNING
        assert updated_agent.status_description == task_description
        assert "sentiment analysis" in updated_agent.status_description
    
    # Test 8: Paused Status with Reason
    @pytest.mark.asyncio
    async def test_paused_status_with_reason(self, agent_service, sample_agent):
        """Test setting paused status with reason."""
        pause_reason = "Paused due to rate limiting - resuming in 60 seconds"
        status_update = AgentStatusUpdate(
            status=AgentStatusEnum.PAUSED,
            description=pause_reason
        )
        
        updated_agent = await agent_service.update_agent_status(sample_agent.id, status_update)
        
        assert updated_agent.status == AgentStatusEnum.PAUSED
        assert updated_agent.status_description == pause_reason
        assert "rate limiting" in updated_agent.status_description
    
    # Test 9: Update Non-existent Agent
    @pytest.mark.asyncio
    async def test_update_nonexistent_agent_status(self, agent_service):
        """Test updating status of non-existent agent."""
        status_update = AgentStatusUpdate(
            status=AgentStatusEnum.RUNNING,
            description="This should fail"
        )
        
        result = await agent_service.update_agent_status("nonexistent-id", status_update)
        assert result is None
    
    # Test 10: Backward Compatibility Method
    @pytest.mark.asyncio
    async def test_backward_compatibility_method(self, agent_service, sample_agent):
        """Test the backward compatibility method for simple status updates."""
        result = await agent_service.update_agent_status_simple(
            sample_agent.id, 
            AgentStatusEnum.RUNNING
        )
        
        assert result is True
        
        # Verify the agent was updated
        updated_agent = await agent_service.get_agent(sample_agent.id)
        assert updated_agent.status == AgentStatusEnum.RUNNING
        assert updated_agent.status_description == "Agent is actively processing tasks"
    
    # Test 11: Status Timeline Tracking
    @pytest.mark.asyncio
    async def test_status_timeline_tracking(self, agent_service, sample_agent):
        """Test that status updates maintain proper timeline."""
        # First update
        status_update_1 = AgentStatusUpdate(
            status=AgentStatusEnum.RUNNING,
            description="Starting task processing"
        )
        agent_1 = await agent_service.update_agent_status(sample_agent.id, status_update_1)
        first_update_time = agent_1.status_updated_at
        
        # Small delay to ensure timestamp difference
        import asyncio
        await asyncio.sleep(0.01)
        
        # Second update
        status_update_2 = AgentStatusUpdate(
            status=AgentStatusEnum.COMPLETED,
            description="Task processing completed successfully"
        )
        agent_2 = await agent_service.update_agent_status(sample_agent.id, status_update_2)
        
        # Verify timeline
        assert agent_2.status_updated_at > first_update_time
        assert agent_2.last_activity > first_update_time
        assert agent_2.status == AgentStatusEnum.COMPLETED
        assert agent_2.status_description == "Task processing completed successfully"
    
    # Test 12: Status Persistence
    @pytest.mark.asyncio
    async def test_status_persistence(self, agent_service, sample_agent):
        """Test that status updates persist when retrieving agent."""
        status_update = AgentStatusUpdate(
            status=AgentStatusEnum.ERROR,
            description="Database connection timeout after 30 seconds"
        )
        
        await agent_service.update_agent_status(sample_agent.id, status_update)
        
        # Retrieve agent and verify status persisted
        retrieved_agent = await agent_service.get_agent(sample_agent.id)
        assert retrieved_agent.status == AgentStatusEnum.ERROR
        assert retrieved_agent.status_description == "Database connection timeout after 30 seconds"
        assert retrieved_agent.status_updated_at is not None
    
    # Test 13: Multiple Agents Status Independence
    @pytest.mark.asyncio
    async def test_multiple_agents_status_independence(self, agent_service, sample_workflow, sample_agent_data):
        """Test that status updates are independent between agents."""
        # Create two agents
        agent1 = await agent_service.create_agent(sample_workflow.id, sample_agent_data)
        agent2 = await agent_service.create_agent(sample_workflow.id, sample_agent_data)
        
        # Update agent1 status
        status_update_1 = AgentStatusUpdate(
            status=AgentStatusEnum.RUNNING,
            description="Agent 1 processing tasks"
        )
        await agent_service.update_agent_status(agent1.id, status_update_1)
        
        # Update agent2 status
        status_update_2 = AgentStatusUpdate(
            status=AgentStatusEnum.ERROR,
            description="Agent 2 encountered error"
        )
        await agent_service.update_agent_status(agent2.id, status_update_2)
        
        # Verify independence
        retrieved_agent1 = await agent_service.get_agent(agent1.id)
        retrieved_agent2 = await agent_service.get_agent(agent2.id)
        
        assert retrieved_agent1.status == AgentStatusEnum.RUNNING
        assert retrieved_agent1.status_description == "Agent 1 processing tasks"
        assert retrieved_agent2.status == AgentStatusEnum.ERROR
        assert retrieved_agent2.status_description == "Agent 2 encountered error" 