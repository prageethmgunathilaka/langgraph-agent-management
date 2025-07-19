"""
Test suite for PersistenceService
Tests the data storage and retrieval functionality
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from app.services.persistence_service import PersistenceService, PersistenceConfig
from app.services.task_service import TaskExecution, WorkflowPlan, TaskStatus, IntelligenceLevel
from app.models.schemas import Agent, AgentStatusEnum, AgentType


class TestPersistenceService:
    """Test suite for PersistenceService functionality"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def persistence_service(self, temp_dir):
        """Create PersistenceService instance with temporary database"""
        config = PersistenceConfig(
            database_path=f"{temp_dir}/test.db", backup_directory=f"{temp_dir}/backups", enable_file_backup=True
        )
        return PersistenceService(config)

    @pytest.mark.asyncio
    async def test_database_initialization(self, persistence_service):
        """Test that database initializes correctly"""
        # Database should be created during initialization
        assert persistence_service.db_path.exists()

        # Check health
        health = await persistence_service.health_check()
        assert health["status"] == "healthy"
        assert health["database_healthy"] is True

    @pytest.mark.asyncio
    async def test_task_execution_persistence(self, persistence_service):
        """Test saving and loading task executions"""
        # Create a task execution
        execution = TaskExecution(
            task_id="test-task-1",
            workflow_id="test-workflow-1",
            agent_id="test-agent-1",
            status=TaskStatus.COMPLETED,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            intelligence_level=IntelligenceLevel.BASIC,
            result={"output": "test result"},
            task_data={"request": "test", "response": "test"},
        )

        # Save execution
        success = await persistence_service.save_task_execution(execution)
        assert success is True

        # Load execution
        loaded_execution = await persistence_service.load_task_execution("test-task-1")
        assert loaded_execution is not None
        assert loaded_execution.task_id == "test-task-1"
        assert loaded_execution.agent_id == "test-agent-1"
        assert loaded_execution.status == TaskStatus.COMPLETED
        assert loaded_execution.result == {"output": "test result"}
        assert loaded_execution.task_data == {"request": "test", "response": "test"}

    @pytest.mark.asyncio
    async def test_workflow_plan_persistence(self, persistence_service):
        """Test saving and loading workflow plans"""
        # Create a workflow plan
        plan = WorkflowPlan(
            workflow_id="test-workflow-1",
            title="Test Workflow",
            description="A test workflow",
            steps=[
                {"id": "step-1", "type": "test", "parameters": {"test": "value"}},
                {"id": "step-2", "type": "test2", "parameters": {"test2": "value2"}},
            ],
            success_criteria="All steps completed",
            failure_handling="Retry on failure",
        )

        # Save plan
        success = await persistence_service.save_workflow_plan(plan)
        assert success is True

        # Load plan
        loaded_plan = await persistence_service.load_workflow_plan("test-workflow-1")
        assert loaded_plan is not None
        assert loaded_plan.workflow_id == "test-workflow-1"
        assert loaded_plan.title == "Test Workflow"
        assert len(loaded_plan.steps) == 2
        assert loaded_plan.steps[0]["type"] == "test"

    @pytest.mark.asyncio
    async def test_agent_state_persistence(self, persistence_service):
        """Test saving agent states"""
        # Create an agent
        agent = Agent(
            id="test-agent-1",
            workflow_id="test-workflow-1",
            name="Test Agent",
            agent_type=AgentType.GENERAL_AGENT,
            status=AgentStatusEnum.IDLE,
            capabilities=["test", "debug"],
            config={"setting": "value"},
        )

        # Save agent state
        success = await persistence_service.save_agent_state(agent)
        assert success is True

    @pytest.mark.asyncio
    async def test_tasks_by_status(self, persistence_service):
        """Test retrieving tasks by status"""
        # Create multiple task executions with different statuses
        executions = [
            TaskExecution(
                task_id="completed-task-1",
                workflow_id="test-workflow-1",
                agent_id="agent-1",
                status=TaskStatus.COMPLETED,
                started_at=datetime.now(),
                intelligence_level=IntelligenceLevel.BASIC,
            ),
            TaskExecution(
                task_id="running-task-1",
                workflow_id="test-workflow-1",
                agent_id="agent-1",
                status=TaskStatus.RUNNING,
                started_at=datetime.now(),
                intelligence_level=IntelligenceLevel.BASIC,
            ),
            TaskExecution(
                task_id="completed-task-2",
                workflow_id="test-workflow-1",
                agent_id="agent-2",
                status=TaskStatus.COMPLETED,
                started_at=datetime.now(),
                intelligence_level=IntelligenceLevel.BASIC,
            ),
        ]

        # Save all executions
        for execution in executions:
            await persistence_service.save_task_execution(execution)

        # Get completed tasks
        completed_tasks = await persistence_service.get_tasks_by_status(TaskStatus.COMPLETED)
        assert len(completed_tasks) == 2
        assert all(task.status == TaskStatus.COMPLETED for task in completed_tasks)

        # Get running tasks
        running_tasks = await persistence_service.get_tasks_by_status(TaskStatus.RUNNING)
        assert len(running_tasks) == 1
        assert running_tasks[0].status == TaskStatus.RUNNING

    @pytest.mark.asyncio
    async def test_metrics_recording(self, persistence_service):
        """Test recording and retrieving metrics"""
        # Record some metrics with slight delays to ensure ordering
        await persistence_service.record_metric("cpu_usage", 75.5, {"host": "test-host"})
        import asyncio
        await asyncio.sleep(0.01)  # Small delay to ensure different timestamps
        await persistence_service.record_metric("memory_usage", 60.2, {"host": "test-host"})
        await asyncio.sleep(0.01)  # Small delay to ensure different timestamps
        await persistence_service.record_metric("cpu_usage", 80.1, {"host": "test-host"})

        # Get CPU usage metrics
        cpu_metrics = await persistence_service.get_metrics("cpu_usage", limit=10)
        assert len(cpu_metrics) == 2
        assert cpu_metrics[0]["name"] == "cpu_usage"
        assert cpu_metrics[0]["value"] == 80.1  # Most recent first

        # Get memory usage metrics
        memory_metrics = await persistence_service.get_metrics("memory_usage", limit=10)
        assert len(memory_metrics) == 1
        assert memory_metrics[0]["value"] == 60.2

    @pytest.mark.asyncio
    async def test_database_stats(self, persistence_service):
        """Test database statistics"""
        # Add some test data
        execution = TaskExecution(
            task_id="stats-test-task",
            workflow_id="stats-test-workflow",
            agent_id="stats-test-agent",
            status=TaskStatus.COMPLETED,
            started_at=datetime.now(),
            intelligence_level=IntelligenceLevel.BASIC,
        )
        await persistence_service.save_task_execution(execution)

        plan = WorkflowPlan(
            workflow_id="stats-test-workflow",
            title="Stats Test",
            description="Test for stats",
            steps=[{"id": "step-1", "type": "test"}],
            success_criteria="Complete",
            failure_handling="Retry",
        )
        await persistence_service.save_workflow_plan(plan)

        # Get stats
        stats = await persistence_service.get_database_stats()
        assert "total_tasks" in stats
        assert "total_workflows" in stats
        assert "database_size" in stats
        assert stats["total_tasks"] >= 1
        assert stats["total_workflows"] >= 1

    @pytest.mark.asyncio
    async def test_backup_and_restore(self, persistence_service):
        """Test backup and restore functionality"""
        # Add some test data
        execution = TaskExecution(
            task_id="backup-test-task",
            workflow_id="backup-test-workflow",
            agent_id="backup-test-agent",
            status=TaskStatus.COMPLETED,
            started_at=datetime.now(),
            intelligence_level=IntelligenceLevel.BASIC,
        )
        await persistence_service.save_task_execution(execution)

        # Create backup
        backup_path = await persistence_service.create_backup()
        assert backup_path is not None
        assert Path(backup_path).exists()

        # Verify backup can be restored
        restore_success = await persistence_service.restore_from_backup(backup_path)
        assert restore_success is True

        # Verify data is still there after restore
        loaded_execution = await persistence_service.load_task_execution("backup-test-task")
        assert loaded_execution is not None
        assert loaded_execution.task_id == "backup-test-task"

    @pytest.mark.asyncio
    async def test_cleanup_old_data(self, persistence_service):
        """Test cleanup of old data"""
        # Add some test data
        execution = TaskExecution(
            task_id="cleanup-test-task",
            workflow_id="cleanup-test-workflow",
            agent_id="cleanup-test-agent",
            status=TaskStatus.COMPLETED,
            started_at=datetime.now(),
            intelligence_level=IntelligenceLevel.BASIC,
        )
        await persistence_service.save_task_execution(execution)

        # Cleanup with 0 days (should remove everything)
        success = await persistence_service.cleanup_old_data(days=0)
        assert success is True

        # Verify data was cleaned up
        loaded_execution = await persistence_service.load_task_execution("cleanup-test-task")
        assert loaded_execution is None  # Should be deleted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
