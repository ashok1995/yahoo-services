"""
Structured JSON logging for yahoo-services.
Logs to file with rotation: 10MB per file, keep 5 files.
"""

import json
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self, service_name: str = "yahoo-services"):
        super().__init__()
        self.service_name = service_name
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "service": self.service_name,
            "module": record.module,
            "message": record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra context if present
        if hasattr(record, "context"):
            log_data["context"] = record.context
        
        return json.dumps(log_data)


def setup_logger(
    name: str,
    log_level: str = "INFO",
    log_file: str = "/tmp/yahoo-services.log",
    service_name: str = "yahoo-services"
) -> logging.Logger:
    """
    Set up structured JSON logger with file rotation.
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Log file path
        service_name: Service name for structured logs
    
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # File handler with rotation (10MB, keep 5 files) - skip if not writable (e.g. Docker volume perms)
    log_path = Path(log_file)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(JSONFormatter(service_name))
        logger.addHandler(file_handler)
    except (PermissionError, OSError):
        pass  # Fall back to console only; Docker/capture will still get logs
    
    # Console handler (always; also only handler if file failed)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get logger instance."""
    return logging.getLogger(name)
