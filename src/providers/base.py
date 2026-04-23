"""Abstract base class for moderation providers."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..utils.logging import get_logger
from ..utils.retry import RateLimiter, retry_with_backoff

logger = get_logger("providers.base")


@dataclass
class ModerationResult:
    """Standardized result from any moderation provider."""

    harm_category: str | None
    severity: str  # benign | borderline | severe | critical
    confidence: float  # 0.0 - 1.0
    should_escalate: bool
    escalation_context: dict[str, Any] | None
    explanation: str
    raw_response: dict[str, Any]
    latency_ms: float
    provider_name: str = ""
    expected_action: str = ""  # predicted action: allow, flag_for_review, remove, remove_and_escalate

    def __post_init__(self) -> None:
        if self.severity not in ("benign", "borderline", "severe", "critical"):
            raise ValueError(f"Invalid severity: {self.severity!r}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0-1, got {self.confidence}")
        # Infer expected_action from severity if not explicitly set
        if not self.expected_action:
            self.expected_action = _SEVERITY_TO_ACTION.get(self.severity, "allow")


_SEVERITY_TO_ACTION: dict[str, str] = {
    "benign": "allow",
    "borderline": "flag_for_review",
    "severe": "remove",
    "critical": "remove_and_escalate",
}


@dataclass
class ModerationRequest:
    """Input to a moderation provider."""

    content: str
    content_id: str = ""
    language: str = "en"
    context: dict[str, Any] = field(default_factory=dict)
    policy_profile: str | None = None  # e.g. "tiktok", "rednote"


class ModerationProvider(ABC):
    """Abstract interface for moderation system adapters."""

    def __init__(
        self,
        rate_limit_rpm: int = 0,
        max_retries: int = 3,
        backoff_base: float = 2.0,
    ) -> None:
        self._rate_limiter = RateLimiter(rate_limit_rpm)
        self._max_retries = max_retries
        self._backoff_base = backoff_base

    @abstractmethod
    async def moderate(self, request: ModerationRequest) -> ModerationResult:
        """Run moderation on a single piece of content."""
        ...

    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier for this provider (e.g. 'openai', 'perspective')."""
        ...

    async def moderate_timed(self, request: ModerationRequest) -> ModerationResult:
        """Run moderation with rate limiting, retry, and latency tracking."""
        await self._rate_limiter.acquire()

        start = time.perf_counter()
        try:
            result = await retry_with_backoff(
                self.moderate,
                request,
                max_retries=self._max_retries,
                backoff_base=self._backoff_base,
                retryable_exceptions=(Exception,),
            )
        except Exception:
            logger.error(
                f"provider={self.provider_name()} "
                f"content_id={request.content_id} "
                f"status=failed"
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        result.latency_ms = elapsed_ms
        result.provider_name = self.provider_name()

        logger.info(
            f"provider={self.provider_name()} "
            f"content_id={request.content_id} "
            f"harm={result.harm_category} "
            f"severity={result.severity} "
            f"confidence={result.confidence:.3f} "
            f"latency_ms={elapsed_ms:.0f}"
        )
        return result

    async def close(self) -> None:
        """Clean up resources. Override in subclasses with HTTP clients."""
        pass
