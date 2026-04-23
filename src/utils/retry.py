"""Retry and rate-limiting utilities for API calls."""

from __future__ import annotations

import asyncio
import functools
import time
from typing import Any, Callable, TypeVar

from .logging import get_logger

logger = get_logger("utils.retry")

T = TypeVar("T")


class RateLimiter:
    """Token-bucket rate limiter for API calls.

    Args:
        requests_per_minute: Maximum requests per minute (0 = unlimited).
    """

    def __init__(self, requests_per_minute: int = 60) -> None:
        self._rpm = requests_per_minute
        self._interval = 60.0 / requests_per_minute if requests_per_minute > 0 else 0.0
        self._last_request: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a request slot is available."""
        if self._interval <= 0:
            return
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request
            if elapsed < self._interval:
                wait_time = self._interval - elapsed
                logger.debug(f"rate_limit wait_seconds={wait_time:.2f}")
                await asyncio.sleep(wait_time)
            self._last_request = time.monotonic()


async def retry_with_backoff(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int = 3,
    backoff_base: float = 2.0,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    **kwargs: Any,
) -> Any:
    """Retry an async function with exponential backoff.

    Args:
        func: Async callable to retry.
        max_retries: Maximum number of retry attempts.
        backoff_base: Base for exponential backoff (seconds).
        retryable_exceptions: Exception types that trigger a retry.

    Returns:
        Result of the function call.

    Raises:
        The last exception if all retries are exhausted.
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except retryable_exceptions as e:
            last_exception = e
            if attempt < max_retries:
                wait = backoff_base ** attempt
                logger.warning(
                    f"retry attempt={attempt + 1}/{max_retries} "
                    f"error={type(e).__name__}: {e} "
                    f"backoff_seconds={wait:.1f}"
                )
                await asyncio.sleep(wait)
            else:
                logger.error(
                    f"retry exhausted attempts={max_retries} "
                    f"error={type(e).__name__}: {e}"
                )

    raise last_exception  # type: ignore[misc]
