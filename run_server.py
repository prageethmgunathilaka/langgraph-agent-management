#!/usr/bin/env python3
"""Simple script to run the FastAPI server."""

import uvicorn

if __name__ == "__main__":
    print("Starting LangGraph Agent Management System...")
    print("Server will be available at: http://localhost:8000")
    print("API Documentation: http://localhost:8000/docs")
    print("Press Ctrl+C to stop the server")
    
    uvicorn.run(
        "app.main:app",  # Use import string format for reload to work
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 