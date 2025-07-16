#!/usr/bin/env python3
"""
Test Runner for LangGraph Agent Management System

This script provides easy access to run different test suites:
- Quick tests for rapid feedback during development
- Full integration tests for comprehensive validation
- Individual test categories for focused testing
"""

import sys
import subprocess
import argparse
from pathlib import Path

def run_command(cmd, description=""):
    """Run a command and handle output."""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False

def quick_test():
    """Run quick tests for rapid feedback."""
    cmd = "python -m pytest tests/test_integration.py::TestIntegration::test_root_endpoint tests/test_integration.py::TestIntegration::test_health_endpoint tests/test_integration.py::TestIntegration::test_workflow_lifecycle tests/test_integration.py::TestIntegration::test_agent_lifecycle -v"
    return run_command(cmd, "QUICK TESTS - Essential endpoints only")

def full_test():
    """Run complete integration test suite."""
    cmd = "python -m pytest tests/test_integration.py -v"
    return run_command(cmd, "FULL INTEGRATION TESTS - All endpoints")

def workflow_tests():
    """Run workflow-specific tests."""
    cmd = "python -m pytest tests/test_integration.py -k workflow -v"
    return run_command(cmd, "WORKFLOW TESTS - Workflow management only")

def agent_tests():
    """Run agent-specific tests."""
    cmd = "python -m pytest tests/test_integration.py -k agent -v"
    return run_command(cmd, "AGENT TESTS - Agent management only")

def validation_tests():
    """Run validation and error handling tests."""
    cmd = "python -m pytest tests/test_integration.py -k 'validation or error' -v"
    return run_command(cmd, "VALIDATION TESTS - Error handling and validation")

def performance_tests():
    """Run performance tests."""
    cmd = "python -m pytest tests/test_integration.py -k performance -v"
    return run_command(cmd, "PERFORMANCE TESTS - Load and performance validation")

def system_tests():
    """Run system endpoint tests."""
    cmd = "python -m pytest tests/test_integration.py -k 'root or health' -v"
    return run_command(cmd, "SYSTEM TESTS - Root and health endpoints")

def connection_tests():
    """Run agent connection tests."""
    cmd = "python -m pytest tests/test_agent_connections.py -v"
    return run_command(cmd, "AGENT CONNECTION TESTS - Task 4 functionality")

def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Test Runner for LangGraph Agent Management System")
    parser.add_argument("test_type", nargs="?", default="quick", 
                       choices=["quick", "full", "workflow", "agent", "validation", "performance", "system", "connections"],
                       help="Type of test to run (default: quick)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    print("🚀 LangGraph Agent Management System - Test Runner")
    print(f"📋 Running: {args.test_type} tests")
    
    # Test mapping
    test_functions = {
        "quick": quick_test,
        "full": full_test,
        "workflow": workflow_tests,
        "agent": agent_tests,
        "validation": validation_tests,
        "performance": performance_tests,
        "system": system_tests,
        "connections": connection_tests
    }
    
    # Run the selected test
    success = test_functions[args.test_type]()
    
    if success:
        print(f"\n✅ {args.test_type.upper()} TESTS PASSED!")
        sys.exit(0)
    else:
        print(f"\n❌ {args.test_type.upper()} TESTS FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main() 