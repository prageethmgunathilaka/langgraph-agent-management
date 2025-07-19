"""Helper utilities for LangGraph Agent Management System."""

import uuid
import hashlib
import json
import psutil
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
from app.utils.config import get_settings


def generate_id() -> str:
    """Generate a unique ID."""
    return str(uuid.uuid4())


def generate_short_id(length: int = 8) -> str:
    """Generate a short unique ID."""
    return str(uuid.uuid4()).replace("-", "")[:length]


def hash_string(text: str) -> str:
    """Generate SHA-256 hash of a string."""
    return hashlib.sha256(text.encode()).hexdigest()


def current_timestamp() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


def format_timestamp(dt: datetime) -> str:
    """Format datetime as ISO string."""
    return dt.isoformat()


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO timestamp string to datetime."""
    return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))


def serialize_json(obj: Any) -> str:
    """Serialize object to JSON string."""
    return json.dumps(obj, default=str, indent=2)


def deserialize_json(json_str: str) -> Any:
    """Deserialize JSON string to object."""
    return json.loads(json_str)


def safe_get(dictionary: Dict, key: str, default: Any = None) -> Any:
    """Safely get value from dictionary."""
    return dictionary.get(key, default)


def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """Merge two dictionaries."""
    result = dict1.copy()
    result.update(dict2)
    return result


def filter_dict(dictionary: Dict, keys: List[str]) -> Dict:
    """Filter dictionary to only include specified keys."""
    return {k: v for k, v in dictionary.items() if k in keys}


def exclude_dict_keys(dictionary: Dict, keys: List[str]) -> Dict:
    """Exclude specified keys from dictionary."""
    return {k: v for k, v in dictionary.items() if k not in keys}


def flatten_dict(dictionary: Dict, separator: str = ".") -> Dict:
    """Flatten nested dictionary."""

    def _flatten(obj, parent_key=""):
        items = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_key = f"{parent_key}{separator}{k}" if parent_key else k
                items.extend(_flatten(v, new_key).items())
        else:
            return {parent_key: obj}
        return dict(items)

    return _flatten(dictionary)


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Split list into chunks of specified size."""
    return [lst[i : i + chunk_size] for i in range(0, len(lst), chunk_size)]


def remove_duplicates(lst: List) -> List:
    """Remove duplicates from list while preserving order."""
    seen = set()
    result = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def get_system_info() -> Dict[str, Any]:
    """Get system information."""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return {
            "cpu_percent": cpu_percent,
            "memory_total_mb": memory.total / (1024 * 1024),
            "memory_used_mb": memory.used / (1024 * 1024),
            "memory_available_mb": memory.available / (1024 * 1024),
            "memory_percent": memory.percent,
            "disk_total_gb": disk.total / (1024 * 1024 * 1024),
            "disk_used_gb": disk.used / (1024 * 1024 * 1024),
            "disk_free_gb": disk.free / (1024 * 1024 * 1024),
            "disk_percent": (disk.used / disk.total) * 100,
            "timestamp": current_timestamp(),
        }
    except Exception as e:
        return {"error": str(e), "timestamp": current_timestamp()}


def check_resource_limits() -> Dict[str, Any]:
    """Check if system resources are within limits."""
    settings = get_settings()
    system_info = get_system_info()

    if "error" in system_info:
        return {"status": "error", "message": system_info["error"]}

    warnings = []

    # Check CPU usage
    if system_info["cpu_percent"] > settings.max_cpu_usage:
        warnings.append(f"CPU usage ({system_info['cpu_percent']}%) exceeds limit ({settings.max_cpu_usage}%)")

    # Check memory usage
    if system_info["memory_used_mb"] > settings.max_memory_usage:
        warnings.append(f"Memory usage ({system_info['memory_used_mb']:.1f}MB) exceeds limit ({settings.max_memory_usage}MB)")

    return {
        "status": "warning" if warnings else "ok",
        "warnings": warnings,
        "system_info": system_info,
        "limits": {"max_cpu_usage": settings.max_cpu_usage, "max_memory_usage": settings.max_memory_usage},
    }


def validate_email(email: str) -> bool:
    """Validate email format."""
    import re

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def validate_url(url: str) -> bool:
    """Validate URL format."""
    import re

    pattern = r"^https?://[^\s/$.?#].[^\s]*$"
    return re.match(pattern, url) is not None


def sanitize_string(text: str, max_length: int = 1000) -> str:
    """Sanitize string by removing dangerous characters and limiting length."""
    if not text:
        return ""

    # Remove null bytes and control characters
    sanitized = "".join(char for char in text if ord(char) >= 32 or char in "\n\r\t")

    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."

    return sanitized.strip()


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f}h"
    else:
        days = seconds / 86400
        return f"{days:.1f}d"


def format_bytes(bytes_value: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f}{unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f}PB"


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
    """Decorator for retrying functions with exponential backoff."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt == max_retries - 1:
                        raise last_exception

                    delay = min(base_delay * (2**attempt), max_delay)
                    time.sleep(delay)

            raise last_exception

        return wrapper

    return decorator


def rate_limit(calls_per_second: float = 1.0):
    """Decorator for rate limiting function calls."""
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]

    def decorator(func):
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed

            if left_to_wait > 0:
                time.sleep(left_to_wait)

            ret = func(*args, **kwargs)
            last_called[0] = time.time()
            return ret

        return wrapper

    return decorator


class Timer:
    """Context manager for timing code execution."""

    def __init__(self, name: str = "Timer"):
        self.name = name
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        self.end_time = time.time()

    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None:
            return 0.0

        end_time = self.end_time or time.time()
        return end_time - self.start_time

    def __str__(self) -> str:
        return f"{self.name}: {format_duration(self.elapsed)}"


def create_health_check_response() -> Dict[str, Any]:
    """Create a comprehensive health check response."""
    system_info = get_system_info()
    resource_check = check_resource_limits()

    return {
        "status": "healthy" if resource_check["status"] == "ok" else "degraded",
        "timestamp": current_timestamp(),
        "service": "LangGraph Agent Management System",
        "version": "0.1.0",
        "system": system_info,
        "resources": resource_check,
        "uptime": format_duration(time.time()),  # Approximation
    }
