import logging
import logging.handlers
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Union


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging in production environments."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": os.getpid(),
            "thread_id": record.thread,
        }

        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, 'extra'):
            log_entry.update(record.extra)

        return json.dumps(log_entry, ensure_ascii=False)


def setup_logger(name: str = "viparser", log_level: str = "INFO", log_dir: str = "logs") -> logging.Logger:
    """
    Set up a logger with file and console handlers, supporting both structured and traditional logging.
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files
    
    Returns:
        Configured logger instance
    """
    # Get environment settings
    environment = os.getenv("ENVIRONMENT", "development").lower()
    debug_mode = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes", "on")
    log_level_env = os.getenv("LOG_LEVEL", log_level).upper()

    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level_env))

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    # Choose formatter based on environment
    console_formatter: Union[StructuredFormatter, logging.Formatter]
    file_formatter: Union[StructuredFormatter, logging.Formatter]

    if environment == "production" or environment == "staging":
        # Use structured JSON logging for production
        structured_formatter = StructuredFormatter()
        console_formatter = structured_formatter
        file_formatter = structured_formatter
    else:
        # Use human-readable logging for development
        human_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        console_formatter = human_formatter
        file_formatter = human_formatter

    # Console handler
    console_handler = logging.StreamHandler()
    if debug_mode:
        console_handler.setLevel(logging.DEBUG)
    else:
        console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler for all logs with rotation
    log_filename = f"{name}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_path / log_filename,
        maxBytes=50 * 1024 * 1024,  # 50MB (increased for production)
        backupCount=10  # Keep more backups for production
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Error file handler for errors only
    error_filename = f"{name}_errors.log"
    error_handler = logging.handlers.RotatingFileHandler(
        log_path / error_filename,
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=10
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    logger.addHandler(error_handler)

    # Add application context to all log records
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = old_factory(*args, **kwargs)
        record.app_name = "viparser"
        record.environment = environment
        return record

    logging.setLogRecordFactory(record_factory)

    return logger


def get_logger(name: str = "viparser") -> logging.Logger:
    """
    Get an existing logger or create a new one if it doesn't exist.
    
    Args:
        name: Logger name
    
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger
