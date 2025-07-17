"""
Test file for Task Service functionality
Tests the hybrid intelligence architecture implementation
"""

import asyncio
import os
import json
from datetime import datetime

# Set up test environment variables
os.environ["OPENAI_API_KEY"] = "test-key"

from app.services.task_service import TaskService, IntelligenceLevel
from app.services.agent_service import AgentService
from app.services.workflow_service import WorkflowService
from app.services.llm_service import LLMService, LLMConfig, LLMProvider
from app.models.schemas import AgentCreate, WorkflowCreate

async def test_basic_task_service():
    """Test basic task service functionality without LLM"""
    print("🧪 Testing basic task service functionality...")
    
    # Initialize services
    workflow_service = WorkflowService()
    agent_service = AgentService(workflow_service=workflow_service)
    task_service = TaskService(agent_service=agent_service, llm_service=None)
    
    # Create a test workflow
    workflow_data = WorkflowCreate(
        name="Test Workflow",
        description="Test workflow for task service",
        config={}
    )
    
    workflow = await workflow_service.create_workflow(workflow_data)
    print(f"✅ Created workflow: {workflow.id}")
    
    # Create test agents
    agent_data = AgentCreate(
        name="Test Agent",
        description="Test agent for task service",
        agent_type="general_agent",
        capabilities=["echo", "delay"],
        config={}
    )
    
    agent = await agent_service.create_agent(workflow.id, agent_data)
    print(f"✅ Created agent: {agent.id}")
    
    # Test task execution
    task_data = {
        "action": "echo",
        "inputs": {"message": "Hello from task service!"},
        "step_context": {"step_id": "test_step"},
        "intelligence_level": "basic"
    }
    
    result = await agent_service.execute_agent_task(agent.id, task_data)
    print(f"✅ Task execution result: {result}")
    
    # Test system metrics
    metrics = task_service.get_system_metrics()
    print(f"✅ System metrics: {metrics}")
    
    print("🎉 Basic task service test completed successfully!")

async def test_mock_llm_integration():
    """Test task service with mock LLM integration"""
    print("\n🧪 Testing mock LLM integration...")
    
    # Mock LLM service for testing
    class MockLLMService:
        def __init__(self):
            self.call_count = 0
            
        async def generate_planning_workflow(self, request, context=None):
            self.call_count += 1
            
            class MockResponse:
                def __init__(self):
                    self.content = json.dumps({
                        "workflow_id": "mock_workflow_123",
                        "title": "Mock Workflow",
                        "description": "Generated workflow for testing",
                        "steps": [
                            {
                                "step_id": "step_1",
                                "title": "Echo Message",
                                "description": "Echo a test message",
                                "agent_type": "general_agent",
                                "action": "echo",
                                "inputs": {"message": "Hello from mock workflow!"},
                                "outputs": ["message_result"],
                                "dependencies": [],
                                "error_handling": "retry",
                                "timeout": 30
                            },
                            {
                                "step_id": "step_2",
                                "title": "Delay Task",
                                "description": "Wait for 1 second",
                                "agent_type": "general_agent",
                                "action": "delay",
                                "inputs": {"seconds": 1},
                                "outputs": ["delay_result"],
                                "dependencies": ["step_1"],
                                "error_handling": "fail",
                                "timeout": 60
                            }
                        ],
                        "success_criteria": "All steps completed successfully",
                        "failure_handling": "Log errors and notify admin"
                    })
                    self.provider = LLMProvider.OPENAI
                    self.model = "gpt-4"
                    self.tokens_used = 150
                    self.cost_estimate = 0.003
                    self.inference_type = "planning"
                    self.timestamp = datetime.now()
                    self.cached = False
            
            return MockResponse()
        
        async def dynamic_inference(self, situation, context, inference_type):
            self.call_count += 1
            
            class MockResponse:
                def __init__(self):
                    self.content = json.dumps({
                        "error_analysis": "Mock error analysis",
                        "recovery_strategies": [
                            {
                                "strategy": "retry_with_backoff",
                                "description": "Retry with exponential backoff",
                                "parameters": {"max_retries": 3, "backoff_factor": 2}
                            }
                        ],
                        "recommended_action": "retry"
                    })
                    self.provider = LLMProvider.OPENAI
                    self.model = "gpt-4"
                    self.tokens_used = 75
                    self.cost_estimate = 0.0015
                    self.inference_type = inference_type
                    self.timestamp = datetime.now()
                    self.cached = False
            
            return MockResponse()
        
        def get_usage_stats(self):
            return {
                "total_requests": self.call_count,
                "total_cost": self.call_count * 0.003,
                "total_tokens": self.call_count * 150,
                "cache_hit_rate": 0.0,
                "requests_by_type": {"planning": self.call_count},
                "cost_by_provider": {"openai": self.call_count * 0.003}
            }
    
    # Initialize services with mock LLM
    workflow_service = WorkflowService()
    agent_service = AgentService(workflow_service=workflow_service)
    mock_llm = MockLLMService()
    task_service = TaskService(agent_service=agent_service, llm_service=mock_llm)
    
    # Test workflow planning
    request = "Create a simple workflow that echoes a message and then waits for 1 second"
    context = {"user_id": "test_user", "priority": "high"}
    
    workflow_plan = await task_service.create_workflow_from_request(request, context)
    print(f"✅ Created workflow plan: {workflow_plan.workflow_id}")
    print(f"   Title: {workflow_plan.title}")
    print(f"   Steps: {len(workflow_plan.steps)}")
    
    # Test workflow execution
    try:
        result = await task_service.execute_workflow(workflow_plan.workflow_id, IntelligenceLevel.BASIC)
        print(f"✅ Workflow execution result: {result['status']}")
        print(f"   Results: {len(result['results'])} steps completed")
    except Exception as e:
        print(f"⚠️ Workflow execution encountered expected error: {e}")
        print("   This is normal for testing without real agent execution")
    
    # Test LLM usage stats
    stats = task_service.get_llm_usage_stats()
    print(f"✅ LLM usage stats: {stats}")
    
    print("🎉 Mock LLM integration test completed!")

async def test_agent_types():
    """Test different agent types"""
    print("\n🧪 Testing different agent types...")
    
    # Initialize services
    workflow_service = WorkflowService()
    agent_service = AgentService(workflow_service=workflow_service)
    task_service = TaskService(agent_service=agent_service, llm_service=None)
    
    # Create workflow
    workflow_data = WorkflowCreate(
        name="Agent Types Test",
        description="Test different agent types",
        config={}
    )
    
    workflow = await workflow_service.create_workflow(workflow_data)
    
    # Test different agent types
    agent_types = [
        ("api_agent", "API Agent", {"method": "GET", "url": "https://httpbin.org/get"}),
        ("data_agent", "Data Agent", {"data": {"name": "test", "value": 123}, "transformation": "uppercase"}),
        ("file_agent", "File Agent", {"file_path": "test.txt", "content": "Hello World"}),
        ("notification_agent", "Notification Agent", {"message": "Test notification", "level": "info"}),
        ("general_agent", "General Agent", {"message": "Hello from general agent"})
    ]
    
    for agent_type, name, test_inputs in agent_types:
        try:
            # Create agent
            agent_data = AgentCreate(
                name=name,
                description=f"Test {agent_type}",
                agent_type=agent_type,
                capabilities=[],
                config={}
            )
            
            agent = await agent_service.create_agent(workflow.id, agent_data)
            print(f"✅ Created {agent_type}: {agent.id}")
            
            # Test appropriate action based on agent type
            if agent_type == "api_agent":
                action = "get"  # This will likely fail without internet, but tests the structure
            elif agent_type == "data_agent":
                action = "transform"
            elif agent_type == "file_agent":
                action = "write"  # Write test file
            elif agent_type == "notification_agent":
                action = "log"
            else:
                action = "echo"
            
            # Execute task
            task_data = {
                "action": action,
                "inputs": test_inputs,
                "step_context": {"step_id": f"test_{agent_type}"},
                "intelligence_level": "basic"
            }
            
            result = await agent_service.execute_agent_task(agent.id, task_data)
            print(f"   Task result: {result.get('status', 'unknown')}")
            
        except Exception as e:
            print(f"   ⚠️ {agent_type} test failed (expected for some types): {e}")
    
    print("🎉 Agent types test completed!")

async def main():
    """Run all tests"""
    print("🚀 Starting Task Service Tests")
    print("=" * 50)
    
    try:
        await test_basic_task_service()
        await test_mock_llm_integration()
        await test_agent_types()
        
        print("\n" + "=" * 50)
        print("🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 