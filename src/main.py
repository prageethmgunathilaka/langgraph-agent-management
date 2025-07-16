"""FastAPI application entry point."""

from fastapi import FastAPI

# Create FastAPI app with enhanced documentation
app = FastAPI(
    title="FastGraph",
    description="""
    ## A minimal FastAPI microservice skeleton
    
    This service provides:
    * **Hello World endpoint** - Simple greeting message
    * **Health Check endpoint** - Service status monitoring
    
    You can test all endpoints using this interactive documentation!
    """,
    version="0.1.0",
    contact={
        "name": "API Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
    },
)


@app.get(
    "/",
    summary="Hello World",
    description="Returns a friendly greeting message",
    response_description="Greeting message with service information",
    tags=["Main"]
)
async def hello_world():
    """
    Hello World endpoint.
    
    Returns a simple greeting message along with the service name.
    Perfect for testing if the API is working correctly.
    """
    return {"message": "Hello, World!", "service": "FastGraph"}


@app.get(
    "/health",
    summary="Health Check",
    description="Check if the service is running and healthy",
    response_description="Service health status",
    tags=["Monitoring"]
)
async def health_check():
    """
    Health check endpoint.
    
    Returns the current status of the service.
    Use this endpoint for:
    - Load balancer health checks
    - Monitoring system checks  
    - Service discovery
    """
    return {"status": "healthy", "service": "FastGraph"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000) 