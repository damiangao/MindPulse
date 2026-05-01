#!/usr/bin/env python3
"""Shared logging utilities."""

from datetime import datetime
import logging
import os
import sys
from logging.handlers import WatchedFileHandler


def setup_logger(name: str) -> logging.Logger:
    """Set up a logger with file and console handlers.

    File handler uses WatchedFileHandler (multiprocess-safe) with date-timestamped
    filenames. Console shows WARNING+ by default, DEBUG+ when VERBOSE=1.
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
    formatter = logging.Formatter(
        "%(asctime)s [%(process)d] %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # WatchedFileHandler reopens file on each write — safe for multiprocess
    file_handler = WatchedFileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stderr)
    console_level = logging.DEBUG if os.environ.get("VERBOSE") else logging.WARNING
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
