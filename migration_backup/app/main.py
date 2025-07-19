"""Main FastAPI application for LangGraph Agent Management System."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.api.langgraph_routes import router as langgraph_router
from app.utils.logger import setup_logging
from app.utils.config import get_settings
from app.utils.errors import (
    BaseAppException, 
    app_exception_handler, 
    general_exception_handler
)

# Initialize logging
setup_logging()

# Get application settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="LangGraph Agent Management System",
    description="""
    ## LangGraph Agent Management System
    
    A comprehensive system for managing LangGraph agents and workflows.
    
    ### Features:
    * **Workflow Management** - Create, manage, and delete workflows
    * **Agent Management** - Create and manage LangGraph agents within workflows
    * **Agent Connections** - Connect agents to enable task delegation
    * **Status Tracking** - Monitor agent status and performance
    * **Task Delegation** - Main agents can spawn child agents and delegate tasks
    * **Resource Management** - Monitor and manage system resources
    
    ### API Endpoints:
    * `/workflows` - Workflow management
    * `/agents` - Agent management
    * `/health` - System health check
    """,
    version="0.1.0",
    contact={
        "name": "FastGraph Team",
        "email": "support@fastgraph.com",
    },
    license_info={
        "name": "MIT",
    },
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add exception handlers
app.add_exception_handler(BaseAppException, app_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Include API routes
app.include_router(router)
app.include_router(langgraph_router)

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    from app.utils.helpers import create_health_check_response
    return create_health_check_response()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True) 