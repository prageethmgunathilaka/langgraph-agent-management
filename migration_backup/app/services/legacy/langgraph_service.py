"""
LangGraph-based Agent Management Service
Simplified implementation using LangGraph for workflow orchestration
"""

import json
import asyncio
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from datetime import datetime
import uuid

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from ..models.schemas import (
    WorkflowPlan, TaskExecution, TaskStatus, IntelligenceLevel, 
    AgentType, AgentStatusEnum
)
from ..utils.logger import LoggerMixin


class WorkflowState(TypedDict):
    """State for LangGraph workflow"""
    workflow_id: str
    request: str
    plan: Optional[Dict[str, Any]]
    current_step: int
    steps: List[Dict[str, Any]]
    results: Dict[str, Any]
    errors: List[str]
    intelligence_level: str
    messages: List[Dict[str, Any]]


class LangGraphService(LoggerMixin):
    """Simplified agent management using LangGraph"""
    
    def __init__(self):
        self.checkpointer = MemorySaver()
        self.llm_models = self._initialize_llm_models()
        self.workflow_graphs: Dict[str, StateGraph] = {}
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.logger.info("LangGraphService initialized")
    
    def _initialize_llm_models(self) -> Dict[str, Any]:
        """Initialize LLM models for different intelligence levels"""
        models = {}
        
        try:
            models["openai"] = ChatOpenAI(model="gpt-4", temperature=0.1)
        except Exception as e:
            self.logger.warning(f"OpenAI model not available: {e}")
        
        try:
            models["anthropic"] = ChatAnthropic(model="claude-3-sonnet-20240229", temperature=0.1)
        except Exception as e:
            self.logger.warning(f"Anthropic model not available: {e}")
        
        try:
            models["google"] = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.1)
        except Exception as e:
            self.logger.warning(f"Google model not available: {e}")
        
        return models
    
    def _get_llm_for_intelligence_level(self, intelligence_level: IntelligenceLevel):
        """Get appropriate LLM based on intelligence level"""
        if intelligence_level == IntelligenceLevel.BASIC:
            return None  # No LLM needed for basic tasks
        
        # Use best available model for higher intelligence levels
        if "anthropic" in self.llm_models:
            return self.llm_models["anthropic"]
        elif "openai" in self.llm_models:
            return self.llm_models["openai"]
        elif "google" in self.llm_models:
            return self.llm_models["google"]
        
        return None
    
    # LangGraph Node Functions
    
    async def planning_node(self, state: WorkflowState) -> WorkflowState:
        """Plan workflow from request using LLM"""
        intelligence_level = IntelligenceLevel(state["intelligence_level"])
        llm = self._get_llm_for_intelligence_level(intelligence_level)
        
        if not llm:
            # Basic planning without LLM
            steps = [
                {
                    "step_id": "1",
                    "action": "echo",
                    "inputs": {"message": state["request"]},
                    "agent_type": "general_agent",
                    "timeout": 30
                }
            ]
        else:
            # LLM-powered planning
            planning_prompt = f"""
            Create a workflow plan for this request: {state['request']}
            
            Return a JSON object with this structure:
            {{
                "title": "Workflow Title",
                "description": "Brief description",
                "steps": [
                    {{
                        "step_id": "1",
                        "action": "specific_action",
                        "inputs": {{"key": "value"}},
                        "agent_type": "api_agent|data_agent|file_agent|notification_agent|general_agent",
                        "timeout": 300,
                        "dependencies": []
                    }}
                ]
            }}
            """
            
            response = await llm.ainvoke([HumanMessage(content=planning_prompt)])
            
            try:
                plan_data = json.loads(response.content)
                steps = plan_data.get("steps", [])
            except json.JSONDecodeError:
                # Fallback to basic step
                steps = [
                    {
                        "step_id": "1",
                        "action": "echo",
                        "inputs": {"message": state["request"]},
                        "agent_type": "general_agent",
                        "timeout": 30
                    }
                ]
        
        state["steps"] = steps
        state["plan"] = {
            "title": f"Workflow for: {state['request'][:50]}...",
            "description": "Generated workflow plan",
            "steps": steps
        }
        state["current_step"] = 0
        
        self.logger.info(f"Planned workflow {state['workflow_id']} with {len(steps)} steps")
        return state
    
    async def execution_node(self, state: WorkflowState) -> WorkflowState:
        """Execute current step"""
        if state["current_step"] >= len(state["steps"]):
            return state
        
        current_step = state["steps"][state["current_step"]]
        step_id = current_step["step_id"]
        
        try:
            # Execute step based on agent type
            result = await self._execute_step(current_step, state)
            
            # Store result
            state["results"][step_id] = {
                "status": "completed",
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info(f"Completed step {step_id} in workflow {state['workflow_id']}")
            
        except Exception as e:
            error_msg = f"Step {step_id} failed: {str(e)}"
            state["errors"].append(error_msg)
            state["results"][step_id] = {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.error(f"Step {step_id} failed in workflow {state['workflow_id']}: {e}")
        
        # Move to next step
        state["current_step"] += 1
        return state
    
    async def decision_node(self, state: WorkflowState) -> str:
        """Decide next action based on current state"""
        # Check if we have more steps to execute
        if state["current_step"] < len(state["steps"]):
            return "execute"
        
        # Check if we have errors and intelligence level allows recovery
        if state["errors"] and state["intelligence_level"] in ["intelligent", "autonomous"]:
            return "recovery"
        
        return "complete"
    
    async def recovery_node(self, state: WorkflowState) -> WorkflowState:
        """Handle errors and attempt recovery"""
        intelligence_level = IntelligenceLevel(state["intelligence_level"])
        llm = self._get_llm_for_intelligence_level(intelligence_level)
        
        if not llm:
            # Basic recovery - just log errors
            self.logger.warning(f"Workflow {state['workflow_id']} completed with errors: {state['errors']}")
            return state
        
        # LLM-powered recovery
        recovery_prompt = f"""
        The workflow encountered these errors: {state['errors']}
        
        Current results: {state['results']}
        
        Suggest recovery actions or mark as complete if errors are non-critical.
        Return JSON: {{"action": "retry|complete", "recovery_steps": []}}
        """
        
        response = await llm.ainvoke([HumanMessage(content=recovery_prompt)])
        
        try:
            recovery_data = json.loads(response.content)
            if recovery_data.get("action") == "retry":
                # Add recovery steps
                recovery_steps = recovery_data.get("recovery_steps", [])
                state["steps"].extend(recovery_steps)
                self.logger.info(f"Added {len(recovery_steps)} recovery steps to workflow {state['workflow_id']}")
        except json.JSONDecodeError:
            self.logger.warning(f"Could not parse recovery response for workflow {state['workflow_id']}")
        
        return state
    
    async def completion_node(self, state: WorkflowState) -> WorkflowState:
        """Complete workflow and generate summary"""
        summary = {
            "workflow_id": state["workflow_id"],
            "status": "completed" if not state["errors"] else "completed_with_errors",
            "total_steps": len(state["steps"]),
            "successful_steps": len([r for r in state["results"].values() if r.get("status") == "completed"]),
            "errors": state["errors"],
            "results": state["results"]
        }
        
        state["results"]["_summary"] = summary
        self.logger.info(f"Completed workflow {state['workflow_id']}: {summary}")
        return state
    
    # Step Execution Methods
    
    async def _execute_step(self, step: Dict[str, Any], state: WorkflowState) -> Dict[str, Any]:
        """Execute a single step based on agent type"""
        agent_type = step.get("agent_type", "general_agent")
        action = step.get("action", "")
        inputs = step.get("inputs", {})
        
        if agent_type == "api_agent":
            return await self._execute_api_task(action, inputs)
        elif agent_type == "data_agent":
            return await self._execute_data_task(action, inputs)
        elif agent_type == "file_agent":
            return await self._execute_file_task(action, inputs)
        elif agent_type == "notification_agent":
            return await self._execute_notification_task(action, inputs)
        else:
            return await self._execute_general_task(action, inputs)
    
    async def _execute_api_task(self, action: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API tasks"""
        import aiohttp
        
        method = inputs.get("method", "GET").upper()
        url = inputs.get("url", "")
        headers = inputs.get("headers", {})
        data = inputs.get("data", {})
        
        if not url:
            raise ValueError("URL is required for API tasks")
        
        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url, headers=headers) as response:
                    result = await response.json()
            elif method == "POST":
                async with session.post(url, headers=headers, json=data) as response:
                    result = await response.json()
            else:
                raise ValueError(f"Unsupported method: {method}")
        
        return {"status": "success", "data": result}
    
    async def _execute_data_task(self, action: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data processing tasks"""
        if action == "transform":
            data = inputs.get("data", {})
            transformation = inputs.get("transformation", "")
            
            if transformation == "uppercase":
                result = {k: v.upper() if isinstance(v, str) else v for k, v in data.items()}
            elif transformation == "filter_empty":
                result = {k: v for k, v in data.items() if v}
            else:
                result = data
            
            return {"status": "success", "data": result}
        
        return {"status": "success", "message": f"Data action: {action}"}
    
    async def _execute_file_task(self, action: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute file operations"""
        if action == "read":
            file_path = inputs.get("path", "")
            if not file_path:
                raise ValueError("File path is required")
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            return {"status": "success", "content": content}
        
        elif action == "write":
            file_path = inputs.get("path", "")
            content = inputs.get("content", "")
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            return {"status": "success", "message": f"Written to {file_path}"}
        
        return {"status": "success", "message": f"File action: {action}"}
    
    async def _execute_notification_task(self, action: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute notification tasks"""
        message = inputs.get("message", "")
        level = inputs.get("level", "info")
        
        if level == "error":
            self.logger.error(message)
        elif level == "warning":
            self.logger.warning(message)
        else:
            self.logger.info(message)
        
        return {"status": "success", "message": f"Logged: {message}"}
    
    async def _execute_general_task(self, action: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute general tasks"""
        if action == "echo":
            message = inputs.get("message", "")
            return {"status": "success", "message": message}
        
        elif action == "delay":
            seconds = inputs.get("seconds", 1)
            await asyncio.sleep(seconds)
            return {"status": "success", "delayed": seconds}
        
        return {"status": "success", "message": f"General action: {action}"}
    
    # Public API Methods
    
    async def create_workflow_from_request(self, request: str, intelligence_level: IntelligenceLevel = IntelligenceLevel.BASIC) -> str:
        """Create and start a workflow from a request"""
        workflow_id = str(uuid.uuid4())
        
        # Create LangGraph workflow
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("planning", self.planning_node)
        workflow.add_node("execute", self.execution_node)
        workflow.add_node("recovery", self.recovery_node)
        workflow.add_node("complete", self.completion_node)
        
        # Add edges
        workflow.add_edge(START, "planning")
        workflow.add_edge("planning", "execute")
        workflow.add_conditional_edges(
            "execute",
            self.decision_node,
            {
                "execute": "execute",
                "recovery": "recovery",
                "complete": "complete"
            }
        )
        workflow.add_edge("recovery", "execute")
        workflow.add_edge("complete", END)
        
        # Compile with checkpointer for persistence
        compiled_workflow = workflow.compile(checkpointer=self.checkpointer)
        
        # Store workflow
        self.workflow_graphs[workflow_id] = compiled_workflow
        
        # Initialize state
        initial_state = {
            "workflow_id": workflow_id,
            "request": request,
            "plan": None,
            "current_step": 0,
            "steps": [],
            "results": {},
            "errors": [],
            "intelligence_level": intelligence_level.value,
            "messages": []
        }
        
        self.active_workflows[workflow_id] = initial_state
        
        self.logger.info(f"Created workflow {workflow_id} for request: {request[:100]}...")
        return workflow_id
    
    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Execute a workflow"""
        if workflow_id not in self.workflow_graphs:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflow_graphs[workflow_id]
        initial_state = self.active_workflows[workflow_id]
        
        # Execute workflow
        config = {"configurable": {"thread_id": workflow_id}}
        
        final_state = None
        async for state in workflow.astream(initial_state, config):
            final_state = state
        
        # Update stored state
        self.active_workflows[workflow_id] = final_state
        
        return final_state.get("results", {})
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow status"""
        if workflow_id not in self.active_workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        state = self.active_workflows[workflow_id]
        
        return {
            "workflow_id": workflow_id,
            "status": "running" if state["current_step"] < len(state["steps"]) else "completed",
            "current_step": state["current_step"],
            "total_steps": len(state["steps"]),
            "errors": state["errors"],
            "results": state["results"]
        }
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow"""
        if workflow_id in self.active_workflows:
            del self.active_workflows[workflow_id]
        
        if workflow_id in self.workflow_graphs:
            del self.workflow_graphs[workflow_id]
        
        self.logger.info(f"Cancelled workflow {workflow_id}")
        return True
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system metrics"""
        return {
            "active_workflows": len(self.active_workflows),
            "total_workflows": len(self.workflow_graphs),
            "available_models": list(self.llm_models.keys()),
            "memory_usage": "N/A"  # Could add actual memory monitoring
        } 