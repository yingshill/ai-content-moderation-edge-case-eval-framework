"""Structured logging configuration for the evaluation framework."""

from __future__ import annotations

import logging
import sys
from typing import Any


def setup_logging(
    level: str = "INFO",
    format_style: str = "structured",
) -> logging.Logger:
    """Configure and return the root logger for the framework.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR).
        format_style: 'structured' for key=value pairs, 'simple' for plain text.

    Returns:
        Configured root logger.
    """
    logger = logging.getLogger("modeval")

    if logger.handlers:
        return logger  # Already configured

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stderr)

    if format_style == "structured":
        formatter = logging.Formatter(
            "%(asctime)s level=%(levelname)s module=%(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the 'modeval' namespace.

    Args:
        name: Logger name (e.g. 'providers.openai', 'scoring.metrics').

    Returns:
        Named logger instance.
    """
    return logging.getLogger(f"modeval.{name}")
