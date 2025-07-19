"""Configuration management for LangGraph Agent Management System."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from pydantic_settings import SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""

    # Application settings
    app_name: str = Field(default="LangGraph Agent Management System", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")

    # Server settings
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # Database settings (for future use)
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")

    # LLM API Keys
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")

    # Logging settings
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, alias="LOG_FILE")

    # Agent settings
    max_agents_per_workflow: int = Field(default=100, alias="MAX_AGENTS_PER_WORKFLOW")
    max_child_agents: int = Field(default=10, alias="MAX_CHILD_AGENTS")
    agent_timeout: int = Field(default=300, alias="AGENT_TIMEOUT")  # seconds

    # Resource limits
    max_memory_usage: int = Field(default=1024, alias="MAX_MEMORY_USAGE")  # MB
    max_cpu_usage: float = Field(default=80.0, alias="MAX_CPU_USAGE")  # percentage

    # Security settings
    secret_key: str = Field(default="your-secret-key-here", alias="SECRET_KEY")
    allowed_origins: str = Field(default="*", alias="ALLOWED_ORIGINS")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"  # Ignore extra environment variables
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


def validate_settings(settings: Settings) -> None:
    """Validate application settings."""
    if settings.debug:
        print("Running in debug mode")

    # Validate required settings
    if not settings.secret_key or settings.secret_key == "your-secret-key-here":
        if not settings.debug:
            raise ValueError("SECRET_KEY must be set in production")

    # Validate resource limits
    if settings.max_memory_usage <= 0:
        raise ValueError("MAX_MEMORY_USAGE must be positive")

    if settings.max_cpu_usage <= 0 or settings.max_cpu_usage > 100:
        raise ValueError("MAX_CPU_USAGE must be between 0 and 100")

    # Validate agent limits
    if settings.max_agents_per_workflow <= 0:
        raise ValueError("MAX_AGENTS_PER_WORKFLOW must be positive")

    if settings.max_child_agents <= 0:
        raise ValueError("MAX_CHILD_AGENTS must be positive")


# Environment detection
def is_production() -> bool:
    """Check if running in production environment."""
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def is_development() -> bool:
    """Check if running in development environment."""
    return os.getenv("ENVIRONMENT", "development").lower() == "development"


def is_testing() -> bool:
    """Check if running in testing environment."""
    return os.getenv("ENVIRONMENT", "development").lower() == "testing"
