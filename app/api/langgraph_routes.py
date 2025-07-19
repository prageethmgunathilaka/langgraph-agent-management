"""
Simplified API routes using LangGraph service
Replaces complex custom orchestration with LangGraph's built-in capabilities
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from pydantic import BaseModel

from ..services.langgraph_service import LangGraphService
from ..models.schemas import IntelligenceLevel
from ..utils.logger import LoggerMixin

router = APIRouter(prefix="/v2", tags=["LangGraph Workflows"])

# Global service instance
langgraph_service = LangGraphService()


class WorkflowRequest(BaseModel):
    """Request to create a workflow"""
    request: str
    intelligence_level: str = "basic"


class WorkflowResponse(BaseModel):
    """Response from workflow creation"""
    workflow_id: str
    status: str
    message: str


@router.post("/workflows/create", response_model=WorkflowResponse)
async def create_workflow(request: WorkflowRequest):
    """Create a new workflow from a natural language request"""
    try:
        # Validate intelligence level
        try:
            intelligence_level = IntelligenceLevel(request.intelligence_level)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid intelligence level: {request.intelligence_level}"
            )
        
        # Create workflow
        workflow_id = await langgraph_service.create_workflow_from_request(
            request.request,
            intelligence_level
        )
        
        return WorkflowResponse(
            workflow_id=workflow_id,
            status="created",
            message=f"Workflow created successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/{workflow_id}/execute")
async def execute_workflow(workflow_id: str):
    """Execute a workflow"""
    try:
        results = await langgraph_service.execute_workflow(workflow_id)
        
        return {
            "workflow_id": workflow_id,
            "status": "completed",
            "results": results
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """Get workflow status"""
    try:
        status = await langgraph_service.get_workflow_status(workflow_id)
        return status
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/workflows/{workflow_id}")
async def cancel_workflow(workflow_id: str):
    """Cancel a running workflow"""
    try:
        success = await langgraph_service.cancel_workflow(workflow_id)
        
        return {
            "workflow_id": workflow_id,
            "status": "cancelled" if success else "failed",
            "message": "Workflow cancelled successfully" if success else "Failed to cancel workflow"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/metrics")
async def get_system_metrics():
    """Get system metrics"""
    try:
        metrics = langgraph_service.get_system_metrics()
        return metrics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/quick-execute")
async def quick_execute(request: WorkflowRequest):
    """Create and immediately execute a workflow"""
    try:
        # Validate intelligence level
        try:
            intelligence_level = IntelligenceLevel(request.intelligence_level)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid intelligence level: {request.intelligence_level}"
            )
        
        # Create workflow
        workflow_id = await langgraph_service.create_workflow_from_request(
            request.request,
            intelligence_level
        )
        
        # Execute immediately
        results = await langgraph_service.execute_workflow(workflow_id)
        
        return {
            "workflow_id": workflow_id,
            "status": "completed",
            "request": request.request,
            "intelligence_level": request.intelligence_level,
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check for LangGraph service"""
    try:
        metrics = langgraph_service.get_system_metrics()
        
        return {
            "status": "healthy",
            "service": "LangGraph Agent Management",
            "version": "2.0.0",
            "metrics": metrics
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        } 