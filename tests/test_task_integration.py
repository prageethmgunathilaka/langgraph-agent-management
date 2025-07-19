"""
Integration tests for Task 6 Hybrid Intelligence Architecture flows.

This module tests all the new Task 6 endpoints and flows including:
- Workflow planning and execution
- Task management with intelligence levels
- System metrics and monitoring
- LLM usage tracking
- Persistence service operations
- Full end-to-end workflow execution
"""

import pytest
import json
import time
from fastapi.testclient import TestClient
from app.main import app
from app.services.task_service import IntelligenceLevel

# Test client
client = TestClient(app)


class TestTask6Integration:
    """Integration tests for Task 6 hybrid intelligence flows."""

    def setup_method(self):
        """Setup before each test method."""
        # Clear services for clean state
        from app.api.routes import workflow_service, agent_service, task_service, persistence_service

        workflow_service._workflows.clear()
        agent_service._agents.clear()
        agent_service._agent_connections.clear()
        agent_service._workflow_agents.clear()
        task_service.task_executions.clear()
        task_service.workflow_plans.clear()
        task_service.task_dependencies.clear()
        task_service.running_tasks.clear()
        # Note: persistence_service uses disk storage, so it persists between tests

    def teardown_method(self):
        """Cleanup after each test method."""
        # Clear services after test
        from app.api.routes import workflow_service, agent_service, task_service

        workflow_service._workflows.clear()
        agent_service._agents.clear()
        agent_service._agent_connections.clear()
        agent_service._workflow_agents.clear()
        task_service.task_executions.clear()
        task_service.workflow_plans.clear()
        task_service.task_dependencies.clear()
        task_service.running_tasks.clear()

    # Workflow Planning Tests
    def test_workflow_planning_endpoint_exists(self):
        """Test that workflow planning endpoint exists and handles requests."""
        request_data = {"request": "Simple test request", "intelligence_level": "BASIC"}

        response = client.post("/workflows/plan", json=request_data)

        # Should either succeed or fail with known error (not 404)
        assert response.status_code != 404
        assert response.status_code in [200, 422, 500]

        # If it's a 500, it should be the expected LLM service error
        if response.status_code == 500:
            assert "LLM service not available" in response.text or "Failed to create workflow plan" in response.text

    def test_workflow_planning_basic(self):
        """Test basic workflow planning from text request."""
        request_data = {"request": "Create a simple API endpoint that returns user data", "intelligence_level": "BASIC"}

        response = client.post("/workflows/plan", json=request_data)

        # Handle case where LLM service is not available (no API keys in test environment)
        if response.status_code == 500 and "LLM service not available" in response.text:
            pytest.skip("LLM service not available - API keys not configured for testing")

        if response.status_code != 200:
            print(f"Error response: {response.status_code}")
            print(f"Error details: {response.text}")
        assert response.status_code == 200

        plan = response.json()
        assert "workflow_id" in plan
        assert "plan" in plan
        assert "tasks" in plan["plan"]
        assert "estimated_duration" in plan["plan"]
        assert "intelligence_level" in plan["plan"]
        assert plan["plan"]["intelligence_level"] == "BASIC"

        # Verify plan structure
        tasks = plan["plan"]["tasks"]
        assert len(tasks) > 0
        for task in tasks:
            assert "id" in task
            assert "title" in task
            assert "agent_type" in task
            assert "estimated_duration" in task

    def test_workflow_planning_with_intelligence_levels(self):
        """Test workflow planning with different intelligence levels."""
        request_data = {"request": "Build a user authentication system with JWT tokens", "intelligence_level": "INTELLIGENT"}

        response = client.post("/workflows/plan", json=request_data)

        # Handle case where LLM service is not available
        if response.status_code == 500 and "LLM service not available" in response.text:
            pytest.skip("LLM service not available - API keys not configured for testing")

        assert response.status_code == 200

        plan = response.json()
        assert plan["plan"]["intelligence_level"] == "INTELLIGENT"

        # Intelligent plans should have more detailed tasks
        tasks = plan["plan"]["tasks"]
        assert len(tasks) >= 3  # Should break down into multiple tasks

        # Test with AUTONOMOUS level
        request_data["intelligence_level"] = "AUTONOMOUS"
        response = client.post("/workflows/plan", json=request_data)
        assert response.status_code == 200

        autonomous_plan = response.json()
        assert autonomous_plan["plan"]["intelligence_level"] == "AUTONOMOUS"

    def test_workflow_planning_validation(self):
        """Test workflow planning validation and error handling."""
        # Test missing request
        response = client.post("/workflows/plan", json={})
        assert response.status_code == 422

        # Test invalid intelligence level
        request_data = {"request": "Test request", "intelligence_level": "INVALID_LEVEL"}
        response = client.post("/workflows/plan", json=request_data)
        assert response.status_code == 422

        # Test empty request
        request_data = {"request": "", "intelligence_level": "BASIC"}
        response = client.post("/workflows/plan", json=request_data)
        assert response.status_code == 422

    # Workflow Execution Tests
    def test_workflow_execution_basic(self):
        """Test basic workflow execution."""
        # First create a workflow plan
        request_data = {"request": "Create a simple greeting API endpoint", "intelligence_level": "BASIC"}

        plan_response = client.post("/workflows/plan", json=request_data)
        assert plan_response.status_code == 200
        workflow_id = plan_response.json()["workflow_id"]

        # Execute the workflow
        execution_data = {"intelligence_level": "BASIC"}

        response = client.post(f"/workflows/{workflow_id}/execute", json=execution_data)
        assert response.status_code == 200

        execution = response.json()
        assert "execution_id" in execution
        assert "status" in execution
        assert "started_at" in execution
        assert execution["status"] in ["running", "completed"]

    def test_workflow_execution_with_different_intelligence(self):
        """Test workflow execution with different intelligence levels."""
        # Create plan with BASIC level
        request_data = {"request": "Process user registration data", "intelligence_level": "BASIC"}

        plan_response = client.post("/workflows/plan", json=request_data)
        workflow_id = plan_response.json()["workflow_id"]

        # Execute with INTELLIGENT level (higher than planned)
        execution_data = {"intelligence_level": "INTELLIGENT"}

        response = client.post(f"/workflows/{workflow_id}/execute", json=execution_data)
        assert response.status_code == 200

        execution = response.json()
        assert "execution_id" in execution
        assert "intelligence_level" in execution
        # Should use the execution level, not the plan level

    def test_workflow_execution_nonexistent(self):
        """Test workflow execution with non-existent workflow."""
        execution_data = {"intelligence_level": "BASIC"}

        response = client.post("/workflows/non-existent-id/execute", json=execution_data)
        assert response.status_code == 404

    # Workflow Status Tests
    def test_workflow_status_tracking(self):
        """Test workflow status tracking throughout execution."""
        # Create and execute workflow
        request_data = {"request": "Create a data validation function", "intelligence_level": "BASIC"}

        plan_response = client.post("/workflows/plan", json=request_data)
        workflow_id = plan_response.json()["workflow_id"]

        execution_data = {"intelligence_level": "BASIC"}
        exec_response = client.post(f"/workflows/{workflow_id}/execute", json=execution_data)
        assert exec_response.status_code == 200

        # Check workflow status
        response = client.get(f"/workflows/{workflow_id}/status")
        assert response.status_code == 200

        status = response.json()
        assert "workflow_id" in status
        assert "status" in status
        assert "tasks" in status
        assert "progress" in status
        assert "started_at" in status

        # Verify task status structure
        tasks = status["tasks"]
        for task in tasks:
            assert "id" in task
            assert "status" in task
            assert "agent_type" in task

    def test_workflow_status_nonexistent(self):
        """Test workflow status for non-existent workflow."""
        response = client.get("/workflows/non-existent-id/status")
        assert response.status_code == 404

    # Task Status Tests
    def test_task_status_tracking(self):
        """Test individual task status tracking."""
        # Create and execute workflow to get tasks
        request_data = {"request": "Create a simple calculator function", "intelligence_level": "BASIC"}

        plan_response = client.post("/workflows/plan", json=request_data)
        workflow_id = plan_response.json()["workflow_id"]

        execution_data = {"intelligence_level": "BASIC"}
        exec_response = client.post(f"/workflows/{workflow_id}/execute", json=execution_data)

        # Get workflow status to find task IDs
        status_response = client.get(f"/workflows/{workflow_id}/status")
        tasks = status_response.json()["tasks"]

        if tasks:
            task_id = tasks[0]["id"]

            # Check individual task status
            response = client.get(f"/tasks/{task_id}/status")
            assert response.status_code == 200

            task_status = response.json()
            assert "task_id" in task_status
            assert "status" in task_status
            assert "agent_type" in task_status
            assert "started_at" in task_status

    def test_task_status_nonexistent(self):
        """Test task status for non-existent task."""
        response = client.get("/tasks/non-existent-id/status")
        assert response.status_code == 404

    # Task Cancellation Tests
    def test_task_cancellation(self):
        """Test task cancellation functionality."""
        # Create and execute workflow
        request_data = {"request": "Create a long-running data processing task", "intelligence_level": "BASIC"}

        plan_response = client.post("/workflows/plan", json=request_data)
        workflow_id = plan_response.json()["workflow_id"]

        execution_data = {"intelligence_level": "BASIC"}
        exec_response = client.post(f"/workflows/{workflow_id}/execute", json=execution_data)

        # Get task ID
        status_response = client.get(f"/workflows/{workflow_id}/status")
        tasks = status_response.json()["tasks"]

        if tasks:
            task_id = tasks[0]["id"]

            # Cancel the task
            response = client.delete(f"/tasks/{task_id}")
            assert response.status_code == 200

            cancel_result = response.json()
            assert "task_id" in cancel_result
            assert "status" in cancel_result
            assert cancel_result["status"] == "cancelled"

    def test_task_cancellation_nonexistent(self):
        """Test task cancellation for non-existent task."""
        response = client.delete("/tasks/non-existent-id")
        assert response.status_code == 404

    # System Metrics Tests
    def test_system_metrics_endpoint_exists(self):
        """Test that system metrics endpoint exists and returns data."""
        response = client.get("/system/metrics")
        assert response.status_code == 200

        # Should return JSON with metrics structure
        metrics = response.json()
        assert isinstance(metrics, dict)
        # Basic structure should exist even if values are zero
        expected_keys = ["total_workflows", "total_executions", "running_tasks", "completed_tasks", "failed_tasks"]
        for key in expected_keys:
            assert key in metrics

        # Should also have LLM usage info
        assert "llm_usage" in metrics

    def test_system_metrics(self):
        """Test system metrics endpoint."""
        response = client.get("/system/metrics")
        assert response.status_code == 200

        metrics = response.json()
        assert "active_workflows" in metrics
        assert "total_tasks" in metrics
        assert "completed_tasks" in metrics
        assert "failed_tasks" in metrics
        assert "system_load" in metrics
        assert "memory_usage" in metrics
        assert "uptime" in metrics

        # Verify metric types
        assert isinstance(metrics["active_workflows"], int)
        assert isinstance(metrics["total_tasks"], int)
        assert isinstance(metrics["completed_tasks"], int)
        assert isinstance(metrics["failed_tasks"], int)
        assert isinstance(metrics["uptime"], (int, float))

    def test_system_metrics_after_workflow_execution(self):
        """Test system metrics after executing workflows."""
        # Get initial metrics
        initial_response = client.get("/system/metrics")
        initial_metrics = initial_response.json()

        # Execute a workflow
        request_data = {"request": "Create a test function", "intelligence_level": "BASIC"}

        plan_response = client.post("/workflows/plan", json=request_data)
        workflow_id = plan_response.json()["workflow_id"]

        execution_data = {"intelligence_level": "BASIC"}
        exec_response = client.post(f"/workflows/{workflow_id}/execute", json=execution_data)

        # Get updated metrics
        updated_response = client.get("/system/metrics")
        updated_metrics = updated_response.json()

        # Verify metrics changed
        assert updated_metrics["active_workflows"] >= initial_metrics["active_workflows"]
        assert updated_metrics["total_tasks"] >= initial_metrics["total_tasks"]

    # LLM Usage Tests
    def test_llm_usage_tracking(self):
        """Test LLM usage statistics tracking."""
        response = client.get("/llm/usage")
        assert response.status_code == 200

        usage = response.json()
        assert "total_requests" in usage
        assert "total_tokens" in usage
        assert "total_cost" in usage
        assert "requests_by_provider" in usage
        assert "average_response_time" in usage
        assert "cache_hit_rate" in usage

        # Verify usage structure
        assert isinstance(usage["total_requests"], int)
        assert isinstance(usage["total_tokens"], int)
        assert isinstance(usage["total_cost"], (int, float))
        assert isinstance(usage["requests_by_provider"], dict)

    def test_llm_usage_after_intelligent_workflow(self):
        """Test LLM usage tracking after executing intelligent workflows."""
        # Get initial usage
        initial_response = client.get("/llm/usage")
        initial_usage = initial_response.json()

        # Execute workflow with INTELLIGENT level (should use LLM)
        request_data = {"request": "Create a complex data analysis system", "intelligence_level": "INTELLIGENT"}

        plan_response = client.post("/workflows/plan", json=request_data)
        workflow_id = plan_response.json()["workflow_id"]

        execution_data = {"intelligence_level": "INTELLIGENT"}
        exec_response = client.post(f"/workflows/{workflow_id}/execute", json=execution_data)

        # Get updated usage - allow some time for processing
        time.sleep(0.1)
        updated_response = client.get("/llm/usage")
        updated_usage = updated_response.json()

        # Usage should have increased (or at least not decreased)
        assert updated_usage["total_requests"] >= initial_usage["total_requests"]

    # Persistence Service Tests
    def test_persistence_health(self):
        """Test persistence service health endpoint."""
        response = client.get("/persistence/health")
        assert response.status_code == 200

        health = response.json()
        assert "status" in health
        assert "database_healthy" in health
        assert "backup_healthy" in health
        assert "last_backup" in health
        assert "disk_usage" in health

        assert health["status"] in ["healthy", "degraded", "unhealthy"]
        assert isinstance(health["database_healthy"], bool)
        assert isinstance(health["backup_healthy"], bool)

    def test_persistence_stats(self):
        """Test persistence service statistics."""
        response = client.get("/persistence/stats")
        assert response.status_code == 200

        stats = response.json()
        assert "total_tasks" in stats
        assert "total_workflows" in stats
        assert "database_size" in stats
        assert "tasks_by_status" in stats
        assert "total_agents" in stats
        assert "total_metrics" in stats

        # Verify stat types
        assert isinstance(stats["total_tasks"], int)
        assert isinstance(stats["total_workflows"], int)
        assert isinstance(stats["database_size"], (int, float))
        assert isinstance(stats["tasks_by_status"], dict)
        assert isinstance(stats["total_agents"], int)
        assert isinstance(stats["total_metrics"], int)

    def test_persistence_backup_restore(self):
        """Test persistence backup and restore functionality."""
        # Create a backup
        backup_response = client.post("/persistence/backup")
        assert backup_response.status_code == 200

        backup_result = backup_response.json()
        assert "backup_file" in backup_result
        assert "created_at" in backup_result
        assert "size" in backup_result

        backup_file = backup_result["backup_file"]

        # Test restore
        restore_data = {"backup_file": backup_file}
        restore_response = client.post("/persistence/restore", json=restore_data)
        assert restore_response.status_code == 200

        restore_result = restore_response.json()
        assert "restored_at" in restore_result
        assert "records_restored" in restore_result

    def test_persistence_cleanup(self):
        """Test persistence cleanup functionality."""
        # Test cleanup with default settings
        response = client.delete("/persistence/cleanup")
        assert response.status_code == 200

        cleanup_result = response.json()
        assert "cleaned_up" in cleanup_result
        assert "records_removed" in cleanup_result
        assert "space_freed" in cleanup_result

        # Test cleanup with parameters
        cleanup_data = {"older_than_days": 30}
        response = client.delete("/persistence/cleanup", json=cleanup_data)
        assert response.status_code == 200

    def test_persistence_metrics_recording(self):
        """Test persistence metrics recording and retrieval."""
        # Record a metric
        metric_data = {"name": "test_metric", "value": 42.5, "timestamp": "2024-01-01T12:00:00Z"}

        response = client.post("/persistence/metrics", json=metric_data)
        assert response.status_code == 200

        # Retrieve the metric
        response = client.get("/persistence/metrics/test_metric")
        assert response.status_code == 200

        retrieved_metrics = response.json()
        assert "metrics" in retrieved_metrics
        assert "metric_name" in retrieved_metrics
        assert retrieved_metrics["metric_name"] == "test_metric"

    def test_persistence_metrics_nonexistent(self):
        """Test retrieving non-existent metrics."""
        response = client.get("/persistence/metrics/nonexistent_metric")
        assert response.status_code == 404

    # End-to-End Integration Tests
    def test_complete_workflow_lifecycle(self):
        """Test complete workflow lifecycle from planning to completion."""
        # Step 1: Plan workflow
        request_data = {"request": "Create a user registration API with validation", "intelligence_level": "INTELLIGENT"}

        plan_response = client.post("/workflows/plan", json=request_data)
        assert plan_response.status_code == 200
        workflow_id = plan_response.json()["workflow_id"]

        # Step 2: Execute workflow
        execution_data = {"intelligence_level": "INTELLIGENT"}
        exec_response = client.post(f"/workflows/{workflow_id}/execute", json=execution_data)
        assert exec_response.status_code == 200

        # Step 3: Monitor progress
        status_response = client.get(f"/workflows/{workflow_id}/status")
        assert status_response.status_code == 200

        # Step 4: Check system metrics
        metrics_response = client.get("/system/metrics")
        assert metrics_response.status_code == 200

        # Step 5: Check LLM usage
        usage_response = client.get("/llm/usage")
        assert usage_response.status_code == 200

        # Step 6: Verify persistence
        health_response = client.get("/persistence/health")
        assert health_response.status_code == 200

    def test_multiple_concurrent_workflows(self):
        """Test handling multiple concurrent workflows."""
        workflow_ids = []

        # Create multiple workflows
        for i in range(3):
            request_data = {"request": f"Create test function {i}", "intelligence_level": "BASIC"}

            plan_response = client.post("/workflows/plan", json=request_data)
            assert plan_response.status_code == 200
            workflow_ids.append(plan_response.json()["workflow_id"])

        # Execute all workflows
        for workflow_id in workflow_ids:
            execution_data = {"intelligence_level": "BASIC"}
            exec_response = client.post(f"/workflows/{workflow_id}/execute", json=execution_data)
            assert exec_response.status_code == 200

        # Check all workflow statuses
        for workflow_id in workflow_ids:
            status_response = client.get(f"/workflows/{workflow_id}/status")
            assert status_response.status_code == 200

        # Verify system metrics reflect multiple workflows
        metrics_response = client.get("/system/metrics")
        assert metrics_response.status_code == 200
        metrics = metrics_response.json()
        assert metrics["active_workflows"] >= 3

    def test_error_handling_and_recovery(self):
        """Test error handling and recovery mechanisms."""
        # Test invalid workflow execution
        execution_data = {"intelligence_level": "INVALID"}
        response = client.post("/workflows/invalid-id/execute", json=execution_data)
        assert response.status_code in [404, 422]

        # Test invalid task cancellation
        response = client.delete("/tasks/invalid-id")
        assert response.status_code == 404

        # Test invalid backup restore
        restore_data = {"backup_file": "nonexistent.db"}
        response = client.post("/persistence/restore", json=restore_data)
        assert response.status_code in [400, 404]

        # Verify system remains healthy after errors
        health_response = client.get("/persistence/health")
        assert health_response.status_code == 200

        metrics_response = client.get("/system/metrics")
        assert metrics_response.status_code == 200


# Utility functions for running tests
def run_task6_tests():
    """Run all Task 6 integration tests."""
    pytest.main(["tests/test_task_integration.py", "-v"])


def run_quick_task6_tests():
    """Run quick subset of Task 6 tests."""
    pytest.main(
        [
            "tests/test_task_integration.py::TestTask6Integration::test_workflow_planning_basic",
            "tests/test_task_integration.py::TestTask6Integration::test_workflow_execution_basic",
            "tests/test_task_integration.py::TestTask6Integration::test_system_metrics",
            "tests/test_task_integration.py::TestTask6Integration::test_persistence_health",
            "-v",
        ]
    )


if __name__ == "__main__":
    # Run quick tests by default
    run_quick_task6_tests()
