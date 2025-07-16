"""
Comprehensive tests for Agent Connection Management (Task 4).

This module tests all aspects of agent-to-agent connections including:
- Connection establishment and validation
- Bidirectional connection behavior
- Error handling and edge cases
- Connection cleanup and management
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.workflow_service import WorkflowService
from app.services.agent_service import AgentService

# Test client
client = TestClient(app)

class TestAgentConnections:
    """Test suite for agent connection functionality."""
    
    def setup_method(self):
        """Setup before each test method."""
        # Clear services for clean state
        from app.api.routes import workflow_service, agent_service
        workflow_service._workflows.clear()
        agent_service._agents.clear()
        agent_service._agent_connections.clear()
        agent_service._workflow_agents.clear()
    
    def teardown_method(self):
        """Cleanup after each test method."""
        # Clear services after test
        from app.api.routes import workflow_service, agent_service
        workflow_service._workflows.clear()
        agent_service._agents.clear()
        agent_service._agent_connections.clear()
        agent_service._workflow_agents.clear()
    
    def create_test_workflow(self, name="Test Workflow"):
        """Helper to create a test workflow."""
        workflow_data = {
            "name": name,
            "description": "Test workflow for agent connections"
        }
        response = client.post("/workflows", json=workflow_data)
        assert response.status_code == 200
        return response.json()["id"]
    
    def create_test_agent(self, workflow_id, name="Test Agent"):
        """Helper to create a test agent."""
        agent_data = {
            "name": name,
            "description": "Test agent for connections",
            "agent_type": "main",
            "llm_config": {
                "provider": "openai",
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 1000
            }
        }
        response = client.post(f"/workflows/{workflow_id}/agents", json=agent_data)
        assert response.status_code == 200
        return response.json()["id"]
    
    # === BASIC CONNECTION TESTS ===
    
    def test_connect_two_agents_success(self):
        """Test successful connection between two agents."""
        # Setup
        workflow_id = self.create_test_workflow()
        agent1_id = self.create_test_agent(workflow_id, "Agent 1")
        agent2_id = self.create_test_agent(workflow_id, "Agent 2")
        
        # Connect agents
        connection_data = {"target_agent_id": agent2_id}
        response = client.post(f"/agents/{agent1_id}/connect", json=connection_data)
        
        # Verify connection
        assert response.status_code == 200
        assert "connected successfully" in response.json()["message"]
        
        # Verify bidirectional connection
        response1 = client.get(f"/agents/{agent1_id}/connections")
        response2 = client.get(f"/agents/{agent2_id}/connections")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        connections1 = response1.json()
        connections2 = response2.json()
        
        assert len(connections1) == 1
        assert len(connections2) == 1
        assert connections1[0]["id"] == agent2_id
        assert connections2[0]["id"] == agent1_id
    
    def test_disconnect_two_agents_success(self):
        """Test successful disconnection between two agents."""
        # Setup with connected agents
        workflow_id = self.create_test_workflow()
        agent1_id = self.create_test_agent(workflow_id, "Agent 1")
        agent2_id = self.create_test_agent(workflow_id, "Agent 2")
        
        # Connect first
        connection_data = {"target_agent_id": agent2_id}
        response = client.post(f"/agents/{agent1_id}/connect", json=connection_data)
        assert response.status_code == 200
        
        # Disconnect
        response = client.post(f"/agents/{agent1_id}/disconnect", json=connection_data)
        assert response.status_code == 200
        assert "disconnected successfully" in response.json()["message"]
        
        # Verify disconnection
        response1 = client.get(f"/agents/{agent1_id}/connections")
        response2 = client.get(f"/agents/{agent2_id}/connections")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        connections1 = response1.json()
        connections2 = response2.json()
        
        assert len(connections1) == 0
        assert len(connections2) == 0
    
    def test_get_agent_connections_empty(self):
        """Test getting connections for agent with no connections."""
        workflow_id = self.create_test_workflow()
        agent_id = self.create_test_agent(workflow_id)
        
        response = client.get(f"/agents/{agent_id}/connections")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_multiple_connections(self):
        """Test agent connecting to multiple other agents."""
        # Setup
        workflow_id = self.create_test_workflow()
        agent1_id = self.create_test_agent(workflow_id, "Agent 1")
        agent2_id = self.create_test_agent(workflow_id, "Agent 2")
        agent3_id = self.create_test_agent(workflow_id, "Agent 3")
        
        # Connect agent1 to agent2 and agent3
        connection_data2 = {"target_agent_id": agent2_id}
        connection_data3 = {"target_agent_id": agent3_id}
        
        response1 = client.post(f"/agents/{agent1_id}/connect", json=connection_data2)
        response2 = client.post(f"/agents/{agent1_id}/connect", json=connection_data3)
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Verify agent1 has 2 connections
        response = client.get(f"/agents/{agent1_id}/connections")
        assert response.status_code == 200
        connections = response.json()
        assert len(connections) == 2
        
        connection_ids = [conn["id"] for conn in connections]
        assert agent2_id in connection_ids
        assert agent3_id in connection_ids
    
    # === ERROR HANDLING TESTS ===
    
    def test_connect_nonexistent_agent(self):
        """Test connecting to non-existent agent."""
        workflow_id = self.create_test_workflow()
        agent_id = self.create_test_agent(workflow_id)
        
        connection_data = {"target_agent_id": "nonexistent-id"}
        response = client.post(f"/agents/{agent_id}/connect", json=connection_data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_connect_from_nonexistent_agent(self):
        """Test connecting from non-existent agent."""
        workflow_id = self.create_test_workflow()
        agent_id = self.create_test_agent(workflow_id)
        
        connection_data = {"target_agent_id": agent_id}
        response = client.post(f"/agents/nonexistent-id/connect", json=connection_data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_self_connection_prevention(self):
        """Test that agents cannot connect to themselves."""
        workflow_id = self.create_test_workflow()
        agent_id = self.create_test_agent(workflow_id)
        
        connection_data = {"target_agent_id": agent_id}
        response = client.post(f"/agents/{agent_id}/connect", json=connection_data)
        
        assert response.status_code == 400
        assert "cannot connect to itself" in response.json()["detail"]
    
    def test_cross_workflow_connection_prevention(self):
        """Test that agents from different workflows cannot connect."""
        # Create two workflows with one agent each
        workflow1_id = self.create_test_workflow("Workflow 1")
        workflow2_id = self.create_test_workflow("Workflow 2")
        
        agent1_id = self.create_test_agent(workflow1_id, "Agent 1")
        agent2_id = self.create_test_agent(workflow2_id, "Agent 2")
        
        # Try to connect agents from different workflows
        connection_data = {"target_agent_id": agent2_id}
        response = client.post(f"/agents/{agent1_id}/connect", json=connection_data)
        
        assert response.status_code == 400
        assert "same workflow" in response.json()["detail"]
    
    def test_duplicate_connection_prevention(self):
        """Test that duplicate connections are handled gracefully."""
        workflow_id = self.create_test_workflow()
        agent1_id = self.create_test_agent(workflow_id, "Agent 1")
        agent2_id = self.create_test_agent(workflow_id, "Agent 2")
        
        # Connect once
        connection_data = {"target_agent_id": agent2_id}
        response1 = client.post(f"/agents/{agent1_id}/connect", json=connection_data)
        assert response1.status_code == 200
        
        # Try to connect again
        response2 = client.post(f"/agents/{agent1_id}/connect", json=connection_data)
        assert response2.status_code == 200  # Should succeed without duplicating
        
        # Verify only one connection exists
        response = client.get(f"/agents/{agent1_id}/connections")
        connections = response.json()
        assert len(connections) == 1
    
    def test_disconnect_nonexistent_connection(self):
        """Test disconnecting agents that aren't connected."""
        workflow_id = self.create_test_workflow()
        agent1_id = self.create_test_agent(workflow_id, "Agent 1")
        agent2_id = self.create_test_agent(workflow_id, "Agent 2")
        
        # Try to disconnect without connecting first
        connection_data = {"target_agent_id": agent2_id}
        response = client.post(f"/agents/{agent1_id}/disconnect", json=connection_data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    # === INTEGRATION TESTS ===
    
    def test_agent_deletion_cleans_connections(self):
        """Test that deleting an agent cleans up its connections."""
        workflow_id = self.create_test_workflow()
        agent1_id = self.create_test_agent(workflow_id, "Agent 1")
        agent2_id = self.create_test_agent(workflow_id, "Agent 2")
        
        # Connect agents
        connection_data = {"target_agent_id": agent2_id}
        response = client.post(f"/agents/{agent1_id}/connect", json=connection_data)
        assert response.status_code == 200
        
        # Delete agent1
        response = client.delete(f"/agents/{agent1_id}")
        assert response.status_code == 200
        
        # Verify agent2's connections are cleaned up
        response = client.get(f"/agents/{agent2_id}/connections")
        assert response.status_code == 200
        connections = response.json()
        assert len(connections) == 0
    
    def test_workflow_deletion_cleans_connections(self):
        """Test that deleting a workflow cleans up agent connections."""
        workflow_id = self.create_test_workflow()
        agent1_id = self.create_test_agent(workflow_id, "Agent 1")
        agent2_id = self.create_test_agent(workflow_id, "Agent 2")
        
        # Connect agents
        connection_data = {"target_agent_id": agent2_id}
        response = client.post(f"/agents/{agent1_id}/connect", json=connection_data)
        assert response.status_code == 200
        
        # Delete workflow
        response = client.delete(f"/workflows/{workflow_id}")
        assert response.status_code == 200
        
        # Verify agents and connections are cleaned up
        response1 = client.get(f"/agents/{agent1_id}")
        response2 = client.get(f"/agents/{agent2_id}")
        
        assert response1.status_code == 404
        assert response2.status_code == 404
    
    # === PERFORMANCE TESTS ===
    
    def test_connection_performance(self):
        """Test connection performance with multiple agents."""
        workflow_id = self.create_test_workflow()
        
        # Create 10 agents
        agent_ids = []
        for i in range(10):
            agent_id = self.create_test_agent(workflow_id, f"Agent {i}")
            agent_ids.append(agent_id)
        
        # Connect all agents to the first agent
        for i in range(1, 10):
            connection_data = {"target_agent_id": agent_ids[i]}
            response = client.post(f"/agents/{agent_ids[0]}/connect", json=connection_data)
            assert response.status_code == 200
        
        # Verify first agent has 9 connections
        response = client.get(f"/agents/{agent_ids[0]}/connections")
        assert response.status_code == 200
        connections = response.json()
        assert len(connections) == 9
        
        # Verify each other agent has 1 connection
        for i in range(1, 10):
            response = client.get(f"/agents/{agent_ids[i]}/connections")
            assert response.status_code == 200
            connections = response.json()
            assert len(connections) == 1
            assert connections[0]["id"] == agent_ids[0] 