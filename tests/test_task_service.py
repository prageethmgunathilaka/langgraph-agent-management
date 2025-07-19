"""
Test suite for TaskService - Hybrid Intelligence Task Management
Tests the core functionality that actually exists in the implementation.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from app.services.task_service import TaskService, IntelligenceLevel, TaskStatus, WorkflowPlan, TaskExecution
from app.services.agent_service import AgentService
from app.services.llm_service import LLMService


class TestTaskService:
    """Test suite for TaskService functionality"""

    @pytest.fixture
    def mock_agent_service(self):
        """Mock agent service for testing"""
        mock_service = Mock(spec=AgentService)
        mock_service.create_agent = AsyncMock()
        mock_service.execute_task = AsyncMock()
        return mock_service

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service for testing"""
        mock_service = Mock(spec=LLMService)
        mock_service.plan_workflow = AsyncMock()
        mock_service.get_usage_stats = Mock()
        return mock_service

    @pytest.fixture
    def task_service(self, mock_agent_service, mock_llm_service):
        """Create TaskService instance with mocked dependencies"""
        return TaskService(mock_agent_service, mock_llm_service)

    def test_task_service_initialization(self, task_service):
        """Test TaskService initializes correctly"""
        assert task_service.agent_service is not None
        assert task_service.llm_service is not None
        assert isinstance(task_service.task_executions, dict)
        assert isinstance(task_service.workflow_plans, dict)
        assert isinstance(task_service.task_dependencies, dict)
        assert isinstance(task_service.running_tasks, set)

    @pytest.mark.asyncio
    async def test_workflow_creation_from_string_request(self, task_service, mock_llm_service):
        """Test creating a workflow from a string request"""
        # Setup
        request = "Process user data and send notification"

        # Mock LLM response
        mock_response = Mock()
        mock_response.content = json.dumps(
            {
                "workflow_id": "workflow-1",
                "title": "Data Processing Workflow",
                "description": "Process user data and send notification",
                "steps": [
                    {
                        "step_id": "step-1",
                        "type": "validate_data",
                        "parameters": {"schema": "user_schema"},
                        "agent_type": "data_agent",
                    }
                ],
                "success_criteria": "All steps completed successfully",
                "failure_handling": "Retry failed steps up to 3 times",
            }
        )

        mock_llm_service.generate_planning_workflow.return_value = mock_response

        # Execute
        result = await task_service.create_workflow_from_request(request)

        # Verify
        assert result.workflow_id == "workflow-1"
        assert result.title == "Data Processing Workflow"
        assert len(result.steps) == 1
        assert result.steps[0]["type"] == "validate_data"

        # Verify LLM service was called
        mock_llm_service.generate_planning_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_task_status_retrieval(self, task_service):
        """Test retrieving task status"""
        # Setup
        task_id = "task-123"

        # Add task execution to internal tracking
        task_service.task_executions[task_id] = TaskExecution(
            task_id=task_id,
            workflow_id="workflow-123",
            agent_id="agent-1",
            status=TaskStatus.RUNNING,
            intelligence_level=IntelligenceLevel.BASIC,
            task_data={"type": "test_task"},
            started_at=datetime.now(),
        )

        # Execute
        status = await task_service.get_task_status(task_id)

        # Verify
        assert status["task_id"] == task_id
        assert status["status"] == TaskStatus.RUNNING.value
        assert status["agent_id"] == "agent-1"
        assert "start_time" in status

    @pytest.mark.asyncio
    async def test_task_status_not_found(self, task_service):
        """Test retrieving status for non-existent task"""
        # Execute
        status = await task_service.get_task_status("non-existent-task")

        # Verify
        assert status["task_id"] == "non-existent-task"
        assert status["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_task_cancellation(self, task_service):
        """Test task cancellation"""
        # Setup
        task_id = "task-cancel-test"

        # Add running task
        task_service.task_executions[task_id] = TaskExecution(
            task_id=task_id,
            workflow_id="workflow-cancel-test",
            agent_id="agent-1",
            status=TaskStatus.RUNNING,
            intelligence_level=IntelligenceLevel.BASIC,
            task_data={"type": "test_task"},
            started_at=datetime.now(),
        )
        task_service.running_tasks.add(task_id)

        # Execute
        result = await task_service.cancel_task(task_id)

        # Verify
        assert result is True
        assert task_service.task_executions[task_id].status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_task_cancellation_not_found(self, task_service):
        """Test cancelling non-existent task"""
        # Execute
        result = await task_service.cancel_task("non-existent-task")

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_workflow_status_calculation(self, task_service):
        """Test workflow status calculation"""
        # Setup
        workflow_id = "workflow-status-test"

        # Add workflow plan
        task_service.workflow_plans[workflow_id] = WorkflowPlan(
            workflow_id=workflow_id,
            title="Test Workflow",
            description="Test workflow for status calculation",
            steps=[
                {"step_id": "step-1", "type": "task1"},
                {"step_id": "step-2", "type": "task2"},
                {"step_id": "step-3", "type": "task3"},
            ],
            metadata={"success_criteria": "All steps completed", "failure_handling": "Stop on failure"},
        )

        # Add some task executions
        task_service.task_executions["step-1"] = TaskExecution(
            task_id="step-1",
            workflow_id=workflow_id,
            agent_id="agent-1",
            status=TaskStatus.COMPLETED,
            intelligence_level=IntelligenceLevel.BASIC,
            task_data={"type": "task1"},
            started_at=datetime.now(),
        )

        task_service.task_executions["step-2"] = TaskExecution(
            task_id="step-2",
            workflow_id=workflow_id,
            agent_id="agent-2",
            status=TaskStatus.RUNNING,
            intelligence_level=IntelligenceLevel.BASIC,
            task_data={"type": "task2"},
            started_at=datetime.now(),
        )

        # Execute
        status = await task_service.get_workflow_status(workflow_id)

        # Verify
        assert status["workflow_id"] == workflow_id
        assert status["overall_status"] == "running"  # Should be running since step-2 is running
        assert "steps" in status
        assert len(status["steps"]) == 3  # All steps are included
        assert status["steps"]["step-1"]["status"] == "completed"
        assert status["steps"]["step-2"]["status"] == "running"
        assert status["steps"]["step-3"]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_workflow_status_not_found(self, task_service):
        """Test workflow status for non-existent workflow"""
        # Execute
        status = await task_service.get_workflow_status("non-existent-workflow")

        # Verify
        assert status["status"] == "not_found"

    def test_llm_usage_stats(self, task_service, mock_llm_service):
        """Test LLM usage statistics retrieval"""
        # Setup mock LLM usage stats
        mock_llm_service.get_usage_stats.return_value = {
            "total_requests": 5,
            "total_tokens": 1500,
            "total_cost": 0.025,
            "cache_hit_rate": 0.4,
        }

        # Execute
        stats = task_service.get_llm_usage_stats()

        # Verify
        assert stats["total_requests"] == 5
        assert stats["total_tokens"] == 1500
        assert stats["total_cost"] == 0.025
        assert stats["cache_hit_rate"] == 0.4

        # Verify LLM service was called
        mock_llm_service.get_usage_stats.assert_called_once()

    def test_llm_usage_stats_no_service(self, mock_agent_service):
        """Test LLM usage stats when no LLM service is available"""
        # Create TaskService without LLM service
        task_service = TaskService(mock_agent_service, None)
        task_service.llm_service = None  # Explicitly set to None to bypass initialization

        # Execute
        stats = task_service.get_llm_usage_stats()

        # Verify
        assert stats["llm_service"] == "not_available"

    @pytest.mark.asyncio
    async def test_system_metrics_collection(self, task_service):
        """Test system metrics collection"""
        # Setup some mock data
        task_service.task_executions["task-1"] = TaskExecution(
            task_id="task-1",
            workflow_id="workflow-metrics-test",
            agent_id="agent-1",
            status=TaskStatus.COMPLETED,
            intelligence_level=IntelligenceLevel.BASIC,
            task_data={"type": "task1"},
            started_at=datetime.now(),
        )

        task_service.task_executions["task-2"] = TaskExecution(
            task_id="task-2",
            workflow_id="workflow-metrics-test",
            agent_id="agent-2",
            status=TaskStatus.RUNNING,
            intelligence_level=IntelligenceLevel.BASIC,
            task_data={"type": "task2"},
            started_at=datetime.now(),
        )

        # Execute
        metrics = await task_service.get_system_metrics()

        # Verify
        assert "total_executions" in metrics
        assert "completed_tasks" in metrics
        assert "failed_tasks" in metrics
        assert metrics["total_executions"] == 2
        assert metrics["completed_tasks"] == 1
        assert metrics["failed_tasks"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
