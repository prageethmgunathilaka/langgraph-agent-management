"""Logging configuration for LangGraph Agent Management System."""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional
from app.utils.config import get_settings

class ColoredFormatter(logging.Formatter):
    """Colored log formatter for console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        """Format log record with colors."""
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)

def setup_logging(log_level: Optional[str] = None, log_file: Optional[str] = None) -> None:
    """Set up logging configuration."""
    settings = get_settings()
    
    # Use provided values or fall back to settings
    log_level = log_level or settings.log_level
    log_file = log_file or settings.log_file
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = ColoredFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if log file is specified
    if log_file:
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {log_level}, File: {log_file or 'None'}")

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)

class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return logging.getLogger(self.__class__.__name__)

# Context manager for logging function execution
class LogExecution:
    """Context manager for logging function execution."""
    
    def __init__(self, logger: logging.Logger, function_name: str, log_level: int = logging.INFO):
        self.logger = logger
        self.function_name = function_name
        self.log_level = log_level
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.log(self.log_level, f"Starting {self.function_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = datetime.now() - self.start_time
        if exc_type is None:
            self.logger.log(self.log_level, f"Completed {self.function_name} in {duration.total_seconds():.2f}s")
        else:
            self.logger.error(f"Failed {self.function_name} after {duration.total_seconds():.2f}s: {exc_val}")
        return False

# Decorator for logging function calls
def log_function_call(logger: Optional[logging.Logger] = None, log_level: int = logging.INFO):
    """Decorator to log function calls."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            func_logger = logger or logging.getLogger(func.__module__)
            with LogExecution(func_logger, func.__name__, log_level):
                return func(*args, **kwargs)
        return wrapper
    return decorator

# Utility functions for structured logging
def log_agent_event(agent_id: str, event: str, details: Optional[dict] = None):
    """Log agent-related events."""
    logger = logging.getLogger("agent_events")
    message = f"Agent {agent_id}: {event}"
    if details:
        message += f" - {details}"
    logger.info(message)

def log_workflow_event(workflow_id: str, event: str, details: Optional[dict] = None):
    """Log workflow-related events."""
    logger = logging.getLogger("workflow_events")
    message = f"Workflow {workflow_id}: {event}"
    if details:
        message += f" - {details}"
    logger.info(message)

def log_performance_metric(metric_name: str, value: float, unit: str = ""):
    """Log performance metrics."""
    logger = logging.getLogger("performance")
    logger.info(f"METRIC: {metric_name} = {value} {unit}")

def log_error_with_context(error: Exception, context: dict):
    """Log error with additional context."""
    logger = logging.getLogger("errors")
    logger.error(f"Error: {str(error)}", extra={"context": context}, exc_info=True) 