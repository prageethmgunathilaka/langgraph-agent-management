#!/usr/bin/env python3
"""
Comprehensive LLM Integration Test

This script tests the LLM integration for the Task 6 Hybrid Intelligence Architecture
by setting up the environment and running various LLM-dependent tests.
"""

import os
import sys
import json
import asyncio
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables from test.env
def load_test_env():
    """Load environment variables from test.env file."""
    env_file = project_root / "test.env"
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
                    print(f"Set {key}=***{value[-4:]}")
    else:
        print(f"Warning: {env_file} not found")

# Load environment variables
load_test_env()

# Now import the application components
from fastapi.testclient import TestClient
from app.main import app
from app.services.llm_service import LLMService, LLMServiceFactory
from app.services.task_service import TaskService
from app.models.schemas import IntelligenceLevel

# Test client
client = TestClient(app)

def test_llm_service_initialization():
    """Test that LLM service can be initialized with API key."""
    print("\n=== Testing LLM Service Initialization ===")
    
    try:
        llm_service = LLMServiceFactory.create_from_env()
        print("✅ LLM Service initialized successfully")
        
        # Test usage stats (available method)
        usage_stats = llm_service.get_usage_stats()
        print(f"Usage stats structure: {list(usage_stats.keys())}")
        
        return True
    except Exception as e:
        print(f"❌ LLM Service initialization failed: {e}")
        return False

async def test_llm_planning_request():
    """Test a direct LLM planning request."""
    print("\n=== Testing Direct LLM Planning Request ===")
    
    try:
        llm_service = LLMServiceFactory.create_from_env()
        
        # Test planning request using the correct method
        request = "Create a simple API endpoint that returns user data"
        response = await llm_service.generate_planning_workflow(request)
        
        print(f"✅ LLM planning successful")
        print(f"Response type: {type(response)}")
        print(f"Response content preview: {response.content[:100]}...")
        
        return True
    except Exception as e:
        print(f"❌ LLM planning failed: {e}")
        return False

def test_workflow_planning_endpoint():
    """Test the workflow planning endpoint with LLM integration."""
    print("\n=== Testing Workflow Planning Endpoint ===")
    
    try:
        request_data = {
            "request": "Create a simple API endpoint that returns user data",
            "intelligence_level": "BASIC"
        }
        
        response = client.post("/workflows/plan", json=request_data)
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            plan = response.json()
            print("✅ Workflow planning successful")
            print(f"Plan keys: {list(plan.keys())}")
            
            # Verify plan structure
            required_keys = ["workflow_id", "plan"]
            for key in required_keys:
                if key in plan:
                    print(f"  ✅ {key}: present")
                else:
                    print(f"  ❌ {key}: missing")
            
            if "plan" in plan and "tasks" in plan["plan"]:
                print(f"  ✅ Tasks count: {len(plan['plan']['tasks'])}")
                
            return True
        else:
            print(f"❌ Workflow planning failed with status {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Workflow planning endpoint test failed: {e}")
        return False

def test_workflow_execution_with_llm():
    """Test workflow execution with LLM intelligence levels."""
    print("\n=== Testing Workflow Execution with LLM ===")
    
    try:
        # First create a workflow plan
        request_data = {
            "request": "Create a simple echo API endpoint",
            "intelligence_level": "INTELLIGENT"
        }
        
        plan_response = client.post("/workflows/plan", json=request_data)
        
        if plan_response.status_code != 200:
            print(f"❌ Failed to create plan: {plan_response.status_code}")
            return False
            
        plan = plan_response.json()
        workflow_id = plan["workflow_id"]
        
        print(f"✅ Created workflow plan: {workflow_id}")
        
        # Now execute the workflow
        execution_data = {
            "intelligence_level": "INTELLIGENT"
        }
        
        exec_response = client.post(f"/workflows/{workflow_id}/execute", json=execution_data)
        
        print(f"Execution response status: {exec_response.status_code}")
        
        if exec_response.status_code == 200:
            result = exec_response.json()
            print("✅ Workflow execution successful")
            print(f"Execution ID: {result.get('execution_id')}")
            return True
        else:
            print(f"❌ Workflow execution failed: {exec_response.status_code}")
            print(f"Error: {exec_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Workflow execution test failed: {e}")
        return False

def test_llm_usage_tracking():
    """Test LLM usage tracking endpoint."""
    print("\n=== Testing LLM Usage Tracking ===")
    
    try:
        response = client.get("/llm/usage")
        
        print(f"LLM usage response status: {response.status_code}")
        
        if response.status_code == 200:
            usage = response.json()
            print("✅ LLM usage tracking successful")
            print(f"Usage keys: {list(usage.keys())}")
            
            # Check for expected usage structure
            expected_keys = ["total_requests", "total_tokens", "total_cost", "by_provider"]
            for key in expected_keys:
                if key in usage:
                    print(f"  ✅ {key}: {usage[key]}")
                else:
                    print(f"  ❌ {key}: missing")
            
            return True
        else:
            print(f"❌ LLM usage tracking failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ LLM usage tracking test failed: {e}")
        return False

def test_intelligence_levels():
    """Test different intelligence levels."""
    print("\n=== Testing Different Intelligence Levels ===")
    
    intelligence_levels = ["BASIC", "ADAPTIVE", "INTELLIGENT", "AUTONOMOUS"]
    results = []
    
    for level in intelligence_levels:
        try:
            request_data = {
                "request": f"Create a simple task for {level} intelligence",
                "intelligence_level": level
            }
            
            response = client.post("/workflows/plan", json=request_data)
            
            if response.status_code == 200:
                print(f"  ✅ {level}: Success")
                results.append(True)
            else:
                print(f"  ❌ {level}: Failed ({response.status_code})")
                results.append(False)
                
        except Exception as e:
            print(f"  ❌ {level}: Error - {e}")
            results.append(False)
    
    success_count = sum(results)
    print(f"\nIntelligence levels test: {success_count}/{len(intelligence_levels)} passed")
    return success_count == len(intelligence_levels)

async def main():
    """Run all LLM integration tests."""
    print("🚀 Starting LLM Integration Tests")
    print("=" * 50)
    
    # Check if OpenAI API key is set
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY not found in environment")
        return False
    
    print(f"✅ OpenAI API Key loaded: ***{os.getenv('OPENAI_API_KEY')[-4:]}")
    
    # Run all tests
    tests = [
        test_llm_service_initialization,
        test_llm_planning_request,
        test_workflow_planning_endpoint,
        test_workflow_execution_with_llm,
        test_llm_usage_tracking,
        test_intelligence_levels
    ]
    
    results = []
    for test in tests:
        try:
            if asyncio.iscoroutinefunction(test):
                result = await test()
            else:
                result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 50)
    print("🏁 LLM Integration Test Results")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    for i, test in enumerate(tests):
        status = "✅ PASS" if results[i] else "❌ FAIL"
        print(f"{status} {test.__name__}")
    
    print(f"\n📊 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All LLM integration tests passed!")
        return True
    else:
        print("⚠️  Some LLM integration tests failed.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 