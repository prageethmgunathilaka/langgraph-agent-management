"""Tests for the main FastAPI application."""

import pytest
from fastapi.testclient import TestClient

from src.main import app

# Create test client
client = TestClient(app)


def test_hello_world():
    """Test the hello world endpoint."""
    response = client.get("/")
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["message"] == "Hello, World!"
    assert data["service"] == "FastGraph"


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "FastGraph"


def test_docs_accessible():
    """Test that API documentation is accessible."""
    # Test Swagger UI
    response = client.get("/docs")
    assert response.status_code == 200
    
    # Test ReDoc
    response = client.get("/redoc")
    assert response.status_code == 200


def test_openapi_json():
    """Test OpenAPI JSON schema is accessible."""
    response = client.get("/openapi.json")
    
    assert response.status_code == 200
    
    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema
    assert schema["info"]["title"] == "FastGraph"
    assert schema["info"]["version"] == "0.1.0"


def test_invalid_endpoint():
    """Test accessing non-existent endpoint returns 404."""
    response = client.get("/nonexistent")
    assert response.status_code == 404 