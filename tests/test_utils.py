"""Tests for utility modules: logging, retry, rate limiting."""

from __future__ import annotations

import asyncio
import logging

import pytest

from src.utils.logging import setup_logging, get_logger
from src.utils.retry import RateLimiter, retry_with_backoff


# --- Logging ---


class TestLogging:
    def test_setup_logging_returns_logger(self):
        logger = setup_logging(level="DEBUG", format_style="simple")
        assert logger.name == "modeval"
        assert logger.level == logging.DEBUG

    def test_get_logger_namespace(self):
        logger = get_logger("test.module")
        assert logger.name == "modeval.test.module"

    def test_setup_logging_idempotent(self):
        logger1 = setup_logging(level="INFO")
        handler_count = len(logger1.handlers)
        logger2 = setup_logging(level="DEBUG")  # Should not add another handler
        assert len(logger2.handlers) == handler_count


# --- Rate Limiter ---


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_unlimited(self):
        limiter = RateLimiter(requests_per_minute=0)
        # Should not block
        await limiter.acquire()
        await limiter.acquire()

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        # 6000 RPM = 100/sec = 10ms interval
        limiter = RateLimiter(requests_per_minute=6000)
        await limiter.acquire()
        await limiter.acquire()  # Should wait ~10ms
        # Just verify it doesn't error


# --- Retry ---


class TestRetryWithBackoff:
    @pytest.mark.asyncio
    async def test_succeeds_first_try(self):
        call_count = 0

        async def success():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await retry_with_backoff(success, max_retries=3)
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_succeeds_after_retries(self):
        call_count = 0

        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "ok"

        result = await retry_with_backoff(
            fail_then_succeed,
            max_retries=3,
            backoff_base=0.01,  # Fast for tests
        )
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exhausted_retries(self):
        async def always_fail():
            raise RuntimeError("Always fails")

        with pytest.raises(RuntimeError, match="Always fails"):
            await retry_with_backoff(
                always_fail,
                max_retries=2,
                backoff_base=0.01,
            )

    @pytest.mark.asyncio
    async def test_non_retryable_exception(self):
        call_count = 0

        async def type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("Wrong type")

        with pytest.raises(TypeError):
            await retry_with_backoff(
                type_error,
                max_retries=3,
                backoff_base=0.01,
                retryable_exceptions=(ValueError,),  # TypeError not retryable
            )
        assert call_count == 1  # No retries
