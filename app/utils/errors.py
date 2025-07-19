"""Custom exceptions and error handling for LangGraph Agent Management System."""

from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


# Base exception classes
class BaseAppException(Exception):
    """Base exception class for application-specific errors."""

    def __init__(self, message: str, error_code: str = "GENERIC_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now()
        super().__init__(self.message)


# Workflow-related exceptions
class WorkflowError(BaseAppException):
    """Base class for workflow-related errors."""

    pass


class WorkflowNotFoundError(WorkflowError):
    """Raised when a workflow is not found."""

    def __init__(self, workflow_id: str):
        super().__init__(
            message=f"Workflow with ID '{workflow_id}' not found",
            error_code="WORKFLOW_NOT_FOUND",
            details={"workflow_id": workflow_id},
        )


class WorkflowAlreadyExistsError(WorkflowError):
    """Raised when trying to create a workflow that already exists."""

    def __init__(self, workflow_id: str):
        super().__init__(
            message=f"Workflow with ID '{workflow_id}' already exists",
            error_code="WORKFLOW_ALREADY_EXISTS",
            details={"workflow_id": workflow_id},
        )


class WorkflowDeletionError(WorkflowError):
    """Raised when workflow deletion fails."""

    def __init__(self, workflow_id: str, reason: str):
        super().__init__(
            message=f"Failed to delete workflow '{workflow_id}': {reason}",
            error_code="WORKFLOW_DELETION_ERROR",
            details={"workflow_id": workflow_id, "reason": reason},
        )


# Agent-related exceptions
class AgentError(BaseAppException):
    """Base class for agent-related errors."""

    pass


class AgentNotFoundError(AgentError):
    """Raised when an agent is not found."""

    def __init__(self, agent_id: str):
        super().__init__(
            message=f"Agent with ID '{agent_id}' not found", error_code="AGENT_NOT_FOUND", details={"agent_id": agent_id}
        )


class AgentAlreadyExistsError(AgentError):
    """Raised when trying to create an agent that already exists."""

    def __init__(self, agent_id: str):
        super().__init__(
            message=f"Agent with ID '{agent_id}' already exists",
            error_code="AGENT_ALREADY_EXISTS",
            details={"agent_id": agent_id},
        )


class AgentLimitExceededError(AgentError):
    """Raised when agent limits are exceeded."""

    def __init__(self, limit_type: str, current: int, maximum: int):
        super().__init__(
            message=f"{limit_type} limit exceeded: {current}/{maximum}",
            error_code="AGENT_LIMIT_EXCEEDED",
            details={"limit_type": limit_type, "current": current, "maximum": maximum},
        )


class AgentConnectionError(AgentError):
    """Raised when agent connection fails."""

    def __init__(self, agent_id: str, target_id: str, reason: str):
        super().__init__(
            message=f"Failed to connect agent '{agent_id}' to '{target_id}': {reason}",
            error_code="AGENT_CONNECTION_ERROR",
            details={"agent_id": agent_id, "target_id": target_id, "reason": reason},
        )


class AgentSpawnError(AgentError):
    """Raised when agent spawning fails."""

    def __init__(self, parent_id: str, reason: str):
        super().__init__(
            message=f"Failed to spawn child agent from parent '{parent_id}': {reason}",
            error_code="AGENT_SPAWN_ERROR",
            details={"parent_id": parent_id, "reason": reason},
        )


# Resource-related exceptions
class ResourceError(BaseAppException):
    """Base class for resource-related errors."""

    pass


class ResourceLimitExceededError(ResourceError):
    """Raised when resource limits are exceeded."""

    def __init__(self, resource_type: str, current: float, limit: float, unit: str = ""):
        super().__init__(
            message=f"{resource_type} limit exceeded: {current}{unit} > {limit}{unit}",
            error_code="RESOURCE_LIMIT_EXCEEDED",
            details={"resource_type": resource_type, "current": current, "limit": limit, "unit": unit},
        )


class MemoryLimitExceededError(ResourceLimitExceededError):
    """Raised when memory limit is exceeded."""

    def __init__(self, current_mb: float, limit_mb: float):
        super().__init__("Memory", current_mb, limit_mb, "MB")


class CPULimitExceededError(ResourceLimitExceededError):
    """Raised when CPU limit is exceeded."""

    def __init__(self, current_percent: float, limit_percent: float):
        super().__init__("CPU", current_percent, limit_percent, "%")


# LLM-related exceptions
class LLMError(BaseAppException):
    """Base class for LLM-related errors."""

    pass


class LLMConfigurationError(LLMError):
    """Raised when LLM configuration is invalid."""

    def __init__(self, provider: str, reason: str):
        super().__init__(
            message=f"Invalid LLM configuration for provider '{provider}': {reason}",
            error_code="LLM_CONFIGURATION_ERROR",
            details={"provider": provider, "reason": reason},
        )


class LLMConnectionError(LLMError):
    """Raised when LLM connection fails."""

    def __init__(self, provider: str, model: str, reason: str):
        super().__init__(
            message=f"Failed to connect to LLM {provider}/{model}: {reason}",
            error_code="LLM_CONNECTION_ERROR",
            details={"provider": provider, "model": model, "reason": reason},
        )


# MCP-related exceptions
class MCPError(BaseAppException):
    """Base class for MCP-related errors."""

    pass


class MCPConnectionError(MCPError):
    """Raised when MCP server connection fails."""

    def __init__(self, server_name: str, server_url: str, reason: str):
        super().__init__(
            message=f"Failed to connect to MCP server '{server_name}' at {server_url}: {reason}",
            error_code="MCP_CONNECTION_ERROR",
            details={"server_name": server_name, "server_url": server_url, "reason": reason},
        )


# Validation exceptions
class ValidationError(BaseAppException):
    """Raised when data validation fails."""

    def __init__(self, field: str, value: Any, reason: str):
        super().__init__(
            message=f"Validation failed for field '{field}': {reason}",
            error_code="VALIDATION_ERROR",
            details={"field": field, "value": str(value), "reason": reason},
        )


# Error handlers
def create_error_response(error: BaseAppException, status_code: int = 500) -> JSONResponse:
    """Create a standardized error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error.error_code,
            "message": error.message,
            "details": error.details,
            "timestamp": error.timestamp.isoformat(),
        },
    )


# Exception handler for FastAPI
async def app_exception_handler(request: Request, exc: BaseAppException) -> JSONResponse:
    """Global exception handler for application exceptions."""
    logger.error(
        f"Application error: {exc.message}",
        extra={"error_code": exc.error_code, "details": exc.details, "path": request.url.path, "method": request.method},
    )

    # Map exception types to HTTP status codes
    status_code_map = {
        WorkflowNotFoundError: 404,
        AgentNotFoundError: 404,
        WorkflowAlreadyExistsError: 409,
        AgentAlreadyExistsError: 409,
        AgentLimitExceededError: 429,
        ResourceLimitExceededError: 429,
        ValidationError: 400,
        LLMConfigurationError: 400,
        LLMConnectionError: 503,
        MCPConnectionError: 503,
    }

    status_code = status_code_map.get(type(exc), 500)
    return create_error_response(exc, status_code)


# Exception handler for general exceptions
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for general exceptions."""
    logger.error(f"Unexpected error: {str(exc)}", extra={"path": request.url.path, "method": request.method}, exc_info=True)

    error = BaseAppException(
        message="An unexpected error occurred", error_code="INTERNAL_SERVER_ERROR", details={"original_error": str(exc)}
    )

    return create_error_response(error, 500)


# Utility functions
def handle_service_error(func):
    """Decorator to handle service-level errors."""
    import asyncio

    if asyncio.iscoroutinefunction(func):

        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except BaseAppException:
                raise  # Re-raise application exceptions
            except Exception as e:
                logger.error(f"Service error in {func.__name__}: {str(e)}", exc_info=True)
                raise BaseAppException(
                    message=f"Service error in {func.__name__}",
                    error_code="SERVICE_ERROR",
                    details={"function": func.__name__, "error": str(e)},
                )

        return async_wrapper
    else:

        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except BaseAppException:
                raise  # Re-raise application exceptions
            except Exception as e:
                logger.error(f"Service error in {func.__name__}: {str(e)}", exc_info=True)
                raise BaseAppException(
                    message=f"Service error in {func.__name__}",
                    error_code="SERVICE_ERROR",
                    details={"function": func.__name__, "error": str(e)},
                )

        return sync_wrapper


def validate_required_field(value: Any, field_name: str) -> None:
    """Validate that a required field is not None or empty."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(field_name, value, "Field is required")


def validate_positive_number(value: float, field_name: str) -> None:
    """Validate that a number is positive."""
    if value <= 0:
        raise ValidationError(field_name, value, "Value must be positive")


def validate_range(value: float, field_name: str, min_val: float, max_val: float) -> None:
    """Validate that a value is within a specified range."""
    if value < min_val or value > max_val:
        raise ValidationError(field_name, value, f"Value must be between {min_val} and {max_val}")
