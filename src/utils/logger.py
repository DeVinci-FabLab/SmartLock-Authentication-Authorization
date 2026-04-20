import sys
from contextvars import ContextVar
from pathlib import Path

from loguru import logger

# Create logs directory
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Context variable for request ID tracking
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class LogConfig:
    """Logger configuration"""

    LEVEL = "INFO"
    ROTATION = "500 MB"
    RETENTION = "30 days"
    COMPRESSION = "zip"


def file_formatter(record: dict) -> str:
    """Plain text formatter for file output - no angle brackets"""
    request_id = record["extra"].get("request_id", "-")

    # Plain text format - NO angle brackets that could be parsed
    return (
        f"{record['time']:YYYY-MM-DD HH:mm:ss.SSS} | "
        f"{record['level'].name: <8} | "
        f"{record['name']}:{record['function']}:{record['line']} | "
        f"{request_id} | "
        f"{record['message']}\n"
    )


def setup_logger(
    level: str = LogConfig.LEVEL,
    log_to_file: bool = True,
):
    """Configure Loguru logger"""
    # Remove default handler
    logger.remove()

    # Console output - use plain string format, NOT a function
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
        # Application log file
        logger.add(
            LOGS_DIR / "app.log",
            format=file_formatter,  # Function is OK for file output
            level=level,
            rotation=LogConfig.ROTATION,
            retention=LogConfig.RETENTION,
            compression=LogConfig.COMPRESSION,
            enqueue=True,
            backtrace=True,
            diagnose=True,
        )

        # Error log file
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

    return logger


# Export
__all__ = ["logger", "setup_logger", "request_id_var"]
