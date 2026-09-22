"""Structured JSON logging configuration for the monorepo."""

import json
import logging
import sys
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Formatter that outputs JSON structured log lines."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include custom extra fields passed via extra={}
        if hasattr(record, "request_id"):
            log_data["request_id"] = getattr(record, "request_id")
        if hasattr(record, "endpoint"):
            log_data["endpoint"] = getattr(record, "endpoint")
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = getattr(record, "duration_ms")
        if hasattr(record, "status_code"):
            log_data["status_code"] = getattr(record, "status_code")

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def get_logger(name: str) -> logging.Logger:
    """Create and configure a structured logger instance.

    Args:
        name: Name of the logger module.

    Returns:
        logging.Logger: Configured logger.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
