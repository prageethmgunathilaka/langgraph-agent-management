"""
Task Service for Hybrid Intelligence Architecture
Handles task lifecycle management, LLM-powered planning, and dynamic execution
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import uuid

from ..models.schemas import Task, TaskCreate, TaskUpdate, Agent
from .llm_service import LLMService, LLMServiceFactory, InferenceType
from .agent_service import AgentService

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING = "waiting"


class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IntelligenceLevel(Enum):
    BASIC = "basic"        # No LLM access, predefined logic only
    ADAPTIVE = "adaptive"  # LLM access for error recovery only
    INTELLIGENT = "intelligent"  # LLM access for decisions and adaptations
    AUTONOMOUS = "autonomous"     # Full LLM access for planning and execution


@dataclass
class TaskExecution:
    """Represents a task execution instance"""
    task_id: str
    agent_id: str
    status: TaskStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 3
    intelligence_level: IntelligenceLevel = IntelligenceLevel.BASIC
    llm_interactions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class WorkflowPlan:
    """Represents a structured workflow plan from LLM"""
    workflow_id: str
    title: str
    description: str
    steps: List[Dict[str, Any]]
    success_criteria: str
    failure_handling: str
    estimated_duration: int = 0
    created_at: datetime = field(default_factory=datetime.now)


class TaskService:
    """Enhanced task service with LLM integration and intelligent execution"""
    
    def __init__(self, agent_service: AgentService, llm_service: Optional[LLMService] = None):
        self.agent_service = agent_service
        self.llm_service = llm_service or self._initialize_llm_service()
        self.task_executions: Dict[str, TaskExecution] = {}
        self.workflow_plans: Dict[str, WorkflowPlan] = {}
        self.task_dependencies: Dict[str, Set[str]] = {}
        self.running_tasks: Set[str] = set()
        
    def _initialize_llm_service(self) -> Optional[LLMService]:
        """Initialize LLM service from environment if available"""
        try:
            return LLMServiceFactory.create_from_env()
        except Exception as e:
            logger.warning(f"Could not initialize LLM service: {e}")
            return None
    
    # Planning Phase Methods
    
    async def create_workflow_from_request(self, 
                                         request: str, 
                                         context: Optional[Dict[str, Any]] = None) -> WorkflowPlan:
        """Create structured workflow plan from complex request using LLM"""
        if not self.llm_service:
            raise ValueError("LLM service not available for planning")
        
        logger.info(f"Creating workflow plan for request: {request[:100]}...")
        
        # Generate workflow plan using LLM
        llm_response = await self.llm_service.generate_planning_workflow(request, context)
        
        try:
            plan_data = json.loads(llm_response.content)
            
            workflow_plan = WorkflowPlan(
                workflow_id=plan_data.get("workflow_id", str(uuid.uuid4())),
                title=plan_data.get("title", "Generated Workflow"),
                description=plan_data.get("description", ""),
                steps=plan_data.get("steps", []),
                success_criteria=plan_data.get("success_criteria", ""),
                failure_handling=plan_data.get("failure_handling", ""),
                estimated_duration=self._estimate_duration(plan_data.get("steps", []))
            )
            
            # Store the workflow plan
            self.workflow_plans[workflow_plan.workflow_id] = workflow_plan
            
            # Create task dependencies from steps
            self._create_task_dependencies(workflow_plan.steps)
            
            logger.info(f"Created workflow plan {workflow_plan.workflow_id} with {len(workflow_plan.steps)} steps")
            
            return workflow_plan
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            raise ValueError(f"Invalid workflow plan format: {e}")
    
    def _estimate_duration(self, steps: List[Dict[str, Any]]) -> int:
        """Estimate workflow duration based on steps"""
        total_duration = 0
        for step in steps:
            step_timeout = step.get("timeout", 300)  # Default 5 minutes
            total_duration += step_timeout
        return total_duration
    
    def _create_task_dependencies(self, steps: List[Dict[str, Any]]):
        """Create task dependencies from workflow steps"""
        for step in steps:
            step_id = step.get("step_id")
            dependencies = step.get("dependencies", [])
            
            if step_id:
                self.task_dependencies[step_id] = set(dependencies)
    
    # Task Execution Methods
    
    async def execute_workflow(self, 
                             workflow_id: str, 
                             intelligence_level: IntelligenceLevel = IntelligenceLevel.BASIC) -> Dict[str, Any]:
        """Execute a workflow plan with specified intelligence level"""
        if workflow_id not in self.workflow_plans:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow_plan = self.workflow_plans[workflow_id]
        logger.info(f"Executing workflow {workflow_id} with intelligence level {intelligence_level.value}")
        
        # Create agents for each step
        step_agents = await self._create_agents_for_workflow(workflow_plan, intelligence_level)
        
        # Execute steps in dependency order
        execution_results = {}
        
        for step in self._get_execution_order(workflow_plan.steps):
            step_id = step["step_id"]
            
            try:
                # Wait for dependencies to complete
                await self._wait_for_dependencies(step_id, execution_results)
                
                # Execute the step
                result = await self._execute_step(step, step_agents[step_id], intelligence_level)
                execution_results[step_id] = result
                
                logger.info(f"Step {step_id} completed successfully")
                
            except Exception as e:
                logger.error(f"Step {step_id} failed: {e}")
                
                # Handle failure with intelligence
                if intelligence_level in [IntelligenceLevel.ADAPTIVE, IntelligenceLevel.INTELLIGENT, IntelligenceLevel.AUTONOMOUS]:
                    recovery_result = await self._handle_step_failure(step, e, intelligence_level)
                    if recovery_result:
                        execution_results[step_id] = recovery_result
                        continue
                
                # If recovery failed or not available, fail the workflow
                execution_results[step_id] = {"status": "failed", "error": str(e)}
                break
        
        return {
            "workflow_id": workflow_id,
            "status": "completed" if all(r.get("status") == "completed" for r in execution_results.values()) else "failed",
            "results": execution_results,
            "execution_time": datetime.now().isoformat()
        }
    
    async def _create_agents_for_workflow(self, 
                                        workflow_plan: WorkflowPlan, 
                                        intelligence_level: IntelligenceLevel) -> Dict[str, str]:
        """Create agents for workflow execution"""
        step_agents = {}
        
        for step in workflow_plan.steps:
            step_id = step["step_id"]
            agent_type = step.get("agent_type", "general_agent")
            
            # Create agent with appropriate configuration
            agent_config = {
                "agent_type": agent_type,
                "intelligence_level": intelligence_level.value,
                "step_context": step,
                "llm_enabled": intelligence_level != IntelligenceLevel.BASIC
            }
            
            # Create agent through agent service
            agent_id = await self.agent_service.create_agent(
                workflow_id=workflow_plan.workflow_id,
                config=agent_config
            )
            
            step_agents[step_id] = agent_id
            logger.info(f"Created agent {agent_id} for step {step_id}")
        
        return step_agents
    
    def _get_execution_order(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get steps in dependency execution order"""
        # Simple topological sort
        ordered_steps = []
        remaining_steps = steps.copy()
        
        while remaining_steps:
            # Find steps with no unresolved dependencies
            ready_steps = []
            for step in remaining_steps:
                step_id = step["step_id"]
                dependencies = self.task_dependencies.get(step_id, set())
                
                # Check if all dependencies are already executed
                if all(dep_step["step_id"] in [s["step_id"] for s in ordered_steps] for dep_step in steps if dep_step["step_id"] in dependencies):
                    ready_steps.append(step)
            
            if not ready_steps:
                # Circular dependency or other issue
                logger.warning("Circular dependency detected, executing remaining steps in order")
                ordered_steps.extend(remaining_steps)
                break
            
            # Add ready steps to execution order
            for step in ready_steps:
                ordered_steps.append(step)
                remaining_steps.remove(step)
        
        return ordered_steps
    
    async def _wait_for_dependencies(self, step_id: str, execution_results: Dict[str, Any]):
        """Wait for step dependencies to complete"""
        dependencies = self.task_dependencies.get(step_id, set())
        
        for dep_id in dependencies:
            while dep_id not in execution_results:
                await asyncio.sleep(0.1)  # Wait for dependency to complete
            
            # Check if dependency succeeded
            if execution_results[dep_id].get("status") != "completed":
                raise Exception(f"Dependency {dep_id} failed")
    
    async def _execute_step(self, 
                          step: Dict[str, Any], 
                          agent_id: str, 
                          intelligence_level: IntelligenceLevel) -> Dict[str, Any]:
        """Execute a single workflow step"""
        step_id = step["step_id"]
        
        # Create task execution record
        execution = TaskExecution(
            task_id=step_id,
            agent_id=agent_id,
            status=TaskStatus.RUNNING,
            start_time=datetime.now(),
            intelligence_level=intelligence_level
        )
        
        self.task_executions[step_id] = execution
        self.running_tasks.add(step_id)
        
        try:
            # Execute the step based on agent type
            result = await self._execute_agent_action(step, agent_id, intelligence_level)
            
            # Update execution record
            execution.status = TaskStatus.COMPLETED
            execution.end_time = datetime.now()
            execution.result = result
            
            return {
                "status": "completed",
                "result": result,
                "execution_time": (execution.end_time - execution.start_time).total_seconds()
            }
            
        except Exception as e:
            execution.status = TaskStatus.FAILED
            execution.end_time = datetime.now()
            execution.error = str(e)
            raise
            
        finally:
            self.running_tasks.discard(step_id)
    
    async def _execute_agent_action(self, 
                                  step: Dict[str, Any], 
                                  agent_id: str, 
                                  intelligence_level: IntelligenceLevel) -> Dict[str, Any]:
        """Execute the actual agent action"""
        agent_type = step.get("agent_type", "general_agent")
        action = step.get("action", "")
        inputs = step.get("inputs", {})
        
        # Delegate to agent service for actual execution
        result = await self.agent_service.execute_agent_task(
            agent_id=agent_id,
            task_data={
                "action": action,
                "inputs": inputs,
                "step_context": step,
                "intelligence_level": intelligence_level.value
            }
        )
        
        return result
    
    async def _handle_step_failure(self, 
                                 step: Dict[str, Any], 
                                 error: Exception, 
                                 intelligence_level: IntelligenceLevel) -> Optional[Dict[str, Any]]:
        """Handle step failure with LLM assistance"""
        if not self.llm_service:
            return None
        
        step_id = step["step_id"]
        logger.info(f"Attempting intelligent recovery for step {step_id}")
        
        # Prepare context for LLM
        context = {
            "step": step,
            "error": str(error),
            "intelligence_level": intelligence_level.value,
            "execution_history": self.task_executions.get(step_id, {}).__dict__ if step_id in self.task_executions else {}
        }
        
        # Get recovery strategy from LLM
        recovery_response = await self.llm_service.dynamic_inference(
            situation=f"Step '{step_id}' failed with error: {error}",
            context=context,
            inference_type=InferenceType.ERROR_RECOVERY
        )
        
        try:
            recovery_data = json.loads(recovery_response.content)
            
            # Log LLM interaction
            if step_id in self.task_executions:
                self.task_executions[step_id].llm_interactions.append({
                    "type": "error_recovery",
                    "timestamp": datetime.now().isoformat(),
                    "response": recovery_data
                })
            
            # Implement recovery strategies
            for strategy in recovery_data.get("recovery_strategies", []):
                if strategy["strategy"] == "retry_with_backoff":
                    # Implement retry logic
                    return await self._retry_step_with_backoff(step, strategy["parameters"])
                elif strategy["strategy"] == "modify_and_retry":
                    # Modify step parameters and retry
                    return await self._modify_and_retry_step(step, strategy["parameters"])
            
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to process recovery response: {e}")
        
        return None
    
    async def _retry_step_with_backoff(self, step: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Retry step with exponential backoff"""
        max_retries = params.get("max_retries", 3)
        backoff_factor = params.get("backoff_factor", 2)
        
        for attempt in range(max_retries):
            try:
                await asyncio.sleep(backoff_factor ** attempt)
                return await self._execute_step(step, step["agent_id"], IntelligenceLevel.BASIC)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                continue
    
    async def _modify_and_retry_step(self, step: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Modify step parameters and retry"""
        # Apply modifications
        modified_step = step.copy()
        for key, value in params.items():
            if key in modified_step:
                modified_step[key] = value
        
        return await self._execute_step(modified_step, step["agent_id"], IntelligenceLevel.BASIC)
    
    # Task Management Methods
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get detailed task status"""
        if task_id not in self.task_executions:
            return {"status": "not_found"}
        
        execution = self.task_executions[task_id]
        
        return {
            "task_id": task_id,
            "status": execution.status.value,
            "agent_id": execution.agent_id,
            "start_time": execution.start_time.isoformat(),
            "end_time": execution.end_time.isoformat() if execution.end_time else None,
            "result": execution.result,
            "error": execution.error,
            "retries": execution.retries,
            "intelligence_level": execution.intelligence_level.value,
            "llm_interactions": len(execution.llm_interactions)
        }
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        if task_id in self.running_tasks:
            self.running_tasks.discard(task_id)
            
            if task_id in self.task_executions:
                execution = self.task_executions[task_id]
                execution.status = TaskStatus.CANCELLED
                execution.end_time = datetime.now()
            
            return True
        
        return False
    
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow execution status"""
        if workflow_id not in self.workflow_plans:
            return {"status": "not_found"}
        
        workflow_plan = self.workflow_plans[workflow_id]
        step_statuses = {}
        
        for step in workflow_plan.steps:
            step_id = step["step_id"]
            if step_id in self.task_executions:
                execution = self.task_executions[step_id]
                step_statuses[step_id] = {
                    "status": execution.status.value,
                    "start_time": execution.start_time.isoformat(),
                    "end_time": execution.end_time.isoformat() if execution.end_time else None
                }
            else:
                step_statuses[step_id] = {"status": "pending"}
        
        return {
            "workflow_id": workflow_id,
            "title": workflow_plan.title,
            "created_at": workflow_plan.created_at.isoformat(),
            "estimated_duration": workflow_plan.estimated_duration,
            "steps": step_statuses,
            "overall_status": self._calculate_workflow_status(step_statuses)
        }
    
    def _calculate_workflow_status(self, step_statuses: Dict[str, Dict[str, Any]]) -> str:
        """Calculate overall workflow status"""
        statuses = [step["status"] for step in step_statuses.values()]
        
        if any(status == "failed" for status in statuses):
            return "failed"
        elif any(status == "cancelled" for status in statuses):
            return "cancelled"
        elif any(status == "running" for status in statuses):
            return "running"
        elif all(status == "completed" for status in statuses):
            return "completed"
        else:
            return "pending"
    
    def get_llm_usage_stats(self) -> Dict[str, Any]:
        """Get LLM usage statistics"""
        if not self.llm_service:
            return {"llm_service": "not_available"}
        
        return self.llm_service.get_usage_stats()
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        return {
            "total_workflows": len(self.workflow_plans),
            "total_executions": len(self.task_executions),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len([e for e in self.task_executions.values() if e.status == TaskStatus.COMPLETED]),
            "failed_tasks": len([e for e in self.task_executions.values() if e.status == TaskStatus.FAILED]),
            "llm_usage": self.get_llm_usage_stats()
        } 