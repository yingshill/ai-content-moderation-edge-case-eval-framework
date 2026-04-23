"""Shared test fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging handlers between tests to avoid handler accumulation."""
    import logging
    logger = logging.getLogger("modeval")
    yield
    logger.handlers.clear()
