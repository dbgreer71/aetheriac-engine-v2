"""
Logging utilities for AE v2 observability.

This module provides helpers for request ID generation and
structured JSON logging to stdout.
"""

import json
import logging
import random
import time
import uuid
from typing import Any

from fastapi import Request


def get_request_id(request: Request) -> str:
    """
    Get or generate request ID for correlation.

    Args:
        request: FastAPI request object

    Returns:
        Request ID string (from X-Request-ID header or generated)
    """
    # Check for existing request ID header
    request_id = request.headers.get("X-Request-ID")
    if request_id:
        return request_id

    # Generate new request ID
    return str(uuid.uuid4())


def json_log(level: str, msg: str, **fields: Any) -> None:
    """
    Log structured JSON to stdout.

    Args:
        level: Log level (info, warn, error, debug)
        msg: Log message
        **fields: Additional structured fields
    """
    log_entry = {
        "timestamp": time.time(),
        "level": level.upper(),
        "message": msg,
        **fields,
    }

    # Print single-line JSON to stdout
    print(json.dumps(log_entry, ensure_ascii=False))


def should_log(sample_rate: float = 1.0) -> bool:
    """
    Determine if log should be emitted based on sampling rate.

    Args:
        sample_rate: Sampling rate (0.0-1.0)

    Returns:
        True if log should be emitted
    """
    if sample_rate >= 1.0:
        return True
    if sample_rate <= 0.0:
        return False
    return random.random() < sample_rate


# Configure standard logging to use JSON format
def setup_json_logging(sample_rate: float = 1.0) -> None:
    """
    Configure logging to use JSON format.

    Args:
        sample_rate: Log sampling rate (0.0-1.0)
    """
    # Disable existing handlers
    logging.getLogger().handlers.clear()

    # Create custom handler that writes JSON to stdout
    class JSONHandler(logging.Handler):
        def emit(self, record):
            if not should_log(sample_rate):
                return

            # Convert log record to structured format
            log_entry = {
                "timestamp": record.created,
                "level": record.levelname,
                "message": record.getMessage(),
                "logger": record.name,
            }

            # Add exception info if present
            if record.exc_info:
                log_entry["exception"] = self.formatException(record.exc_info)

            # Add extra fields if present
            if hasattr(record, "fields"):
                log_entry.update(record.fields)

            print(json.dumps(log_entry, ensure_ascii=False))

    # Set up handler
    handler = JSONHandler()
    handler.setLevel(logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
