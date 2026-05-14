#!/usr/bin/env python3
"""Shared logging utilities."""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import WatchedFileHandler


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for easy parsing by ELK/Loki."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "process": record.process,
        }
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_data)


def setup_logger(name: str) -> logging.Logger:
    """Set up a logger with file and console handlers.

    File handler uses WatchedFileHandler (multiprocess-safe) with date-timestamped
    filenames. Console shows WARNING+ by default, DEBUG+ when VERBOSE=1.
    Uses JSON format for file output, human-readable for console.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    log_dir = os.environ.get("LOG_DIR", "/tmp")
    log_timestamp = os.environ.get("LOG_TIMESTAMP", "true")

    if log_timestamp == "true":
        log_file = os.path.join(log_dir, f"claude-chat-{datetime.now():%Y-%m-%d}.log")
    else:
        log_file = os.path.join(log_dir, "claude-chat.log")

    logger.setLevel(logging.DEBUG)

    # JSON formatter for file handler
    json_handler = WatchedFileHandler(log_file)
    json_handler.setLevel(logging.DEBUG)
    json_handler.setFormatter(JSONFormatter())
    logger.addHandler(json_handler)

    # Human-readable formatter for console
    console_formatter = logging.Formatter(
        "%(asctime)s [%(process)d] %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler = logging.StreamHandler(sys.stderr)
    console_level = logging.DEBUG if os.environ.get("VERBOSE") else logging.WARNING
    console_handler.setLevel(console_level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger
