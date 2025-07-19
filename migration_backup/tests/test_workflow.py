"""Tests for workflow functionality."""

import pytest
from datetime import datetime
from app.models.schemas import WorkflowCreate, WorkflowStatus
from app.services.workflow_service import WorkflowService

@pytest.fixture
def workflow_service():
    """Create a workflow service instance."""
    return WorkflowService()

@pytest.fixture
def sample_workflow_data():
    """Create sample workflow data."""
    return WorkflowCreate(
        name="Test Workflow",
        description="A test workflow for unit testing"
    )

class TestWorkflowService:
    """Test workflow service functionality."""
    
    @pytest.mark.asyncio
    async def test_create_workflow(self, workflow_service, sample_workflow_data):
        """Test workflow creation."""
        workflow = await workflow_service.create_workflow(sample_workflow_data)
        
        assert workflow.id is not None
        assert workflow.name == sample_workflow_data.name
        assert workflow.description == sample_workflow_data.description
        assert workflow.status == WorkflowStatus.ACTIVE
        assert workflow.agent_count == 0
        assert len(workflow.agents) == 0
        assert isinstance(workflow.created_at, datetime)
        assert isinstance(workflow.last_modified, datetime)
    
    @pytest.mark.asyncio
    async def test_get_workflow(self, workflow_service, sample_workflow_data):
        """Test workflow retrieval."""
        # Create a workflow first
        created_workflow = await workflow_service.create_workflow(sample_workflow_data)
        
        # Retrieve it
        retrieved_workflow = await workflow_service.get_workflow(created_workflow.id)
        
        assert retrieved_workflow is not None
        assert retrieved_workflow.id == created_workflow.id
        assert retrieved_workflow.name == created_workflow.name
        assert retrieved_workflow.description == created_workflow.description
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_workflow(self, workflow_service):
        """Test retrieving a non-existent workflow."""
        workflow = await workflow_service.get_workflow("nonexistent-id")
        assert workflow is None
    
    @pytest.mark.asyncio
    async def test_list_workflows(self, workflow_service, sample_workflow_data):
        """Test listing workflows."""
        # Initially empty
        workflow_list = await workflow_service.list_workflows()
        assert workflow_list.total == 0
        assert len(workflow_list.workflows) == 0
        
        # Create a workflow
        await workflow_service.create_workflow(sample_workflow_data)
        
        # List should now contain one workflow
        workflow_list = await workflow_service.list_workflows()
        assert workflow_list.total == 1
        assert len(workflow_list.workflows) == 1
        assert workflow_list.workflows[0].name == sample_workflow_data.name
    
    @pytest.mark.asyncio
    async def test_update_workflow(self, workflow_service, sample_workflow_data):
        """Test workflow update."""
        # Create a workflow
        workflow = await workflow_service.create_workflow(sample_workflow_data)
        original_modified = workflow.last_modified
        
        # Update it
        updates = {"description": "Updated description"}
        updated_workflow = await workflow_service.update_workflow(workflow.id, updates)
        
        assert updated_workflow is not None
        assert updated_workflow.description == "Updated description"
        assert updated_workflow.last_modified > original_modified
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_workflow(self, workflow_service):
        """Test updating a non-existent workflow."""
        updates = {"description": "Updated description"}
        result = await workflow_service.update_workflow("nonexistent-id", updates)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_workflow(self, workflow_service, sample_workflow_data):
        """Test workflow deletion."""
        # Create a workflow
        workflow = await workflow_service.create_workflow(sample_workflow_data)
        
        # Delete it
        result = await workflow_service.delete_workflow(workflow.id)
        assert result is True
        
        # Verify it's gone
        retrieved_workflow = await workflow_service.get_workflow(workflow.id)
        assert retrieved_workflow is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_workflow(self, workflow_service):
        """Test deleting a non-existent workflow."""
        result = await workflow_service.delete_workflow("nonexistent-id")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_workflow_stats(self, workflow_service, sample_workflow_data):
        """Test getting workflow statistics."""
        # Create a workflow
        workflow = await workflow_service.create_workflow(sample_workflow_data)
        
        # Get stats
        stats = await workflow_service.get_workflow_stats(workflow.id)
        
        assert stats is not None
        assert stats["workflow_id"] == workflow.id
        assert stats["name"] == workflow.name
        assert stats["status"] == workflow.status
        assert stats["agent_count"] == 0
        assert stats["active_agents"] == 0
        assert stats["idle_agents"] == 0
        assert stats["error_agents"] == 0
    
    @pytest.mark.asyncio
    async def test_update_workflow_status(self, workflow_service, sample_workflow_data):
        """Test updating workflow status."""
        # Create a workflow
        workflow = await workflow_service.create_workflow(sample_workflow_data)
        
        # Update status
        result = await workflow_service.update_workflow_status(workflow.id, WorkflowStatus.PAUSED)
        assert result is True
        
        # Verify status changed
        updated_workflow = await workflow_service.get_workflow(workflow.id)
        assert updated_workflow.status == WorkflowStatus.PAUSED
    
    @pytest.mark.asyncio
    async def test_duplicate_workflow_name(self, workflow_service, sample_workflow_data):
        """Test creating workflows with duplicate names."""
        # Create first workflow
        await workflow_service.create_workflow(sample_workflow_data)
        
        # Try to create another with same name - should raise exception
        with pytest.raises(Exception):  # WorkflowAlreadyExistsError
            await workflow_service.create_workflow(sample_workflow_data) 