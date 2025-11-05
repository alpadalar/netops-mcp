"""
Logging configuration for the NetOps MCP server.

This module handles logging setup and configuration:
- File and console logging handlers
- Log level management
- Format customization (including JSON)
- Handler lifecycle management
- Structured logging support
"""

import logging
import json
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from ..config.models import LoggingConfig


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    
    Outputs log records as JSON objects for easier parsing and analysis.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON-formatted log string
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


def setup_logging(config: LoggingConfig, json_format: bool = False) -> logging.Logger:
    """
    Configure and initialize logging system.
    
    Supports both traditional and JSON-structured logging formats.

    Args:
        config: Logging configuration
        json_format: Use JSON format for structured logging (default: False)

    Returns:
        Configured logger instance for "netops-mcp"
    """
    # Convert relative path to absolute
    log_file = config.file
    if log_file and not os.path.isabs(log_file):
        log_file = os.path.join(os.getcwd(), log_file)
        
    # Create handlers
    handlers = []
    
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, config.level.upper()))
        handlers.append(file_handler)
    
    # Console handler (INFO for production, ERROR for development)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, config.level.upper()))
    handlers.append(console_handler)
    
    # Configure formatters
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(config.format)
    
    for handler in handlers:
        handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.level.upper()))
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add new handlers
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # Create and return server logger
    logger = logging.getLogger("netops-mcp")
    logger.info(f"Logging initialized (format: {'JSON' if json_format else 'text'})")
    
    return logger


def get_structured_logger(name: str) -> logging.LoggerAdapter:
    """
    Get a logger adapter for structured logging.
    
    Allows adding extra fields to log messages.
    
    Args:
        name: Logger name
        
    Returns:
        LoggerAdapter for structured logging
    """
    logger = logging.getLogger(name)
    
    class StructuredLoggerAdapter(logging.LoggerAdapter):
        """Adapter for adding structured fields to logs."""
        
        def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
            """Add extra fields to log record."""
            extra = kwargs.get("extra", {})
            if "extra_fields" not in extra:
                extra["extra_fields"] = {}
            
            # Merge any additional fields
            for key, value in kwargs.items():
                if key not in ("extra", "exc_info", "stack_info", "stacklevel"):
                    extra["extra_fields"][key] = value
            
            kwargs["extra"] = extra
            return msg, kwargs
    
    return StructuredLoggerAdapter(logger, {})
