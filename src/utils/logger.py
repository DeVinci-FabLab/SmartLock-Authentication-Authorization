import sys
import json
from pathlib import Path
from typing import Any
from loguru import logger
from contextvars import ContextVar

# Create logs directory
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Context variable for request ID tracking
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class LogConfig:
    """Logger configuration"""
    
    # Log levels
    LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    # File rotation settings
    ROTATION = "500 MB"  # Rotate when file reaches 500MB
    RETENTION = "30 days"  # Keep logs for 30 days
    COMPRESSION = "zip"  # Compress old logs
    
    # Format settings
    CONSOLE_FORMAT = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # Fixed: Make request_id optional using get()
    FILE_FORMAT = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{extra[request_id]!s} | "  # Use !s to convert to string safely
        "{message}"
    )


def serialize_record(record: dict) -> str:
    """
    Serialize log record to JSON format for structured logging
    """
    subset = {
        "timestamp": record["time"].timestamp(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
    }
    
    # Add extra fields
    if record["extra"]:
        subset["extra"] = record["extra"]
    
    # Add exception info if present
    if record["exception"]:
        subset["exception"] = {
            "type": record["exception"].type.__name__,
            "value": str(record["exception"].value),
            "traceback": record["exception"].traceback,
        }
    
    return json.dumps(subset)


def formatter(record: dict) -> str:
    """
    Custom formatter that handles missing request_id gracefully
    """
    # Get request_id from extra, default to empty string
    request_id = record["extra"].get("request_id", "")
    
    # Build the format string
    format_str = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>"
    )
    
    # Add request_id if present
    if request_id:
        format_str += f" | <yellow>{request_id}</yellow>"
    
    format_str += " | <level>{message}</level>\n"
    
    return format_str


def file_formatter(record: dict) -> str:
    """
    File formatter that handles missing request_id gracefully
    """
    request_id = record["extra"].get("request_id", "-")
    
    return (
        f"{record['time']:YYYY-MM-DD HH:mm:ss.SSS} | "
        f"{record['level'].name: <8} | "
        f"{record['name']}:{record['function']}:{record['line']} | "
        f"{request_id} | "
        f"{record['message']}\n"
    )


def setup_logger(
    level: str = LogConfig.LEVEL,
    json_logs: bool = False,
    log_to_file: bool = True,
):
    """
    Configure Loguru logger
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Whether to use JSON formatting (useful for production)
        log_to_file: Whether to log to files
    """
    # Remove default handler
    logger.remove()
    
    # Console handler with colors
    logger.add(
        sys.stdout,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        level=level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
    
    if log_to_file:
        # General application logs
        logger.add(
            LOGS_DIR / "app.log",
            format=file_formatter,
            level=level,
            rotation=LogConfig.ROTATION,
            retention=LogConfig.RETENTION,
            compression=LogConfig.COMPRESSION,
            enqueue=True,  # Thread-safe
            backtrace=True,
            diagnose=True,
        )
        
        # Error logs (separate file for errors only)
        logger.add(
            LOGS_DIR / "errors.log",
            format=file_formatter,
            level="ERROR",
            rotation=LogConfig.ROTATION,
            retention=LogConfig.RETENTION,
            compression=LogConfig.COMPRESSION,
            enqueue=True,
            backtrace=True,
            diagnose=True,
        )
        
        # JSON logs for structured logging (production)
        if json_logs:
            logger.add(
                LOGS_DIR / "app.json",
                format=serialize_record,
                level=level,
                rotation=LogConfig.ROTATION,
                retention=LogConfig.RETENTION,
                compression=LogConfig.COMPRESSION,
                enqueue=True,
                serialize=True,
            )
    
    return logger


def get_logger(name: str = None):
    """
    Get a logger instance with optional name binding
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured logger instance
    """
    if name:
        return logger.bind(name=name)
    return logger


# Initialize logger on import
setup_logger()


# Export logger instance
__all__ = ["logger", "setup_logger", "get_logger", "request_id_var"]